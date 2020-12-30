from __future__ import absolute_import, unicode_literals
from collections import defaultdict
import logging

import pika
import requests

from bs4 import BeautifulSoup

from celery.schedules import crontab
from celery import shared_task
from celery.task import periodic_task

from datetime import datetime
from decouple import config
from itertools import chain
from hashlib import md5
from hazm import Normalizer

from django.core.cache import cache
from django.db.models import Max
from django.utils import timezone
from khayyam import JalaliDatetime

from conf import settings
# from conf.celery import app
from utils.utils import update_namad_data
from .utils import extract_script_values, check_running, close_running
from .models import NamadStat, NamadDailyStat, NamadHistory
from apps.namads.models import Namad

logger = logging.getLogger(__name__)
logging.getLogger("pika").setLevel(logging.WARNING)

BASE_URL = 'http://tsetmc.com'

SECTION_QUEUE_NAME = config('SECTION_QUEUE_NAME')

SECTIONS_INDEX_MAP = {
    # Table A
    "00": "checksum_time",
    "01": "status",
    "02": "pl",
    "03": "pc",
    "04": "pf",
    "05": "py",
    "06": "pmax",
    "07": "pmin",
    "08": "tno",
    "09": "tvol",
    "010": "tval",

    # Table B
    "20": "zd1",
    "21": "qd1",
    "22": "pd1",
    "23": "po1",
    "24": "qo1",
    "25": "zo1",
    "26": "zd2",
    "27": "qd2",
    "28": "pd2",
    "29": "po2",
    "210": "qo2",
    "211": "zo2",
    "212": "zd3",
    "213": "qd3",
    "214": "pd3",
    "215": "po3",
    "216": "qo3",
    "217": "zo3",

    # Table C
    "40": "Buy_I_Volume",
    "41": "Buy_N_Volume",
    "43": "Sell_I_Volume",
    "44": "Sell_N_Volume",
    "45": "Buy_CountI",
    "46": "Buy_CountN",
    "48": "Sell_CountI",
    "49": "Sell_CountN"
}

SECTIONS_TO_INSERT = [
    0,
    # 1,
    2,
    # 3,
    4,
    # 5,
    # 6,
    # 7,
    # 8
]  # Section parts which will be inserted to mongo, [0, 1, 3, 4] are the most important parts (table 1)

normalizer = Normalizer()


@periodic_task(run_every=crontab(**settings.INSERT_NAMAD_DAILY_CRONTAB))
def p_namad_stat_daily():
    """
    This function will run every day and insert some stats based on home page of each namad that is
    "stock_number"; "base_volume"; "floating_stock"; "total_transaction_average".
    :return: True after the job is done
    """
    file_lock = check_running(p_namad_stat_daily.__name__)

    if not file_lock:
        logger.info(
            "[Another {} is already running]".format(
                p_namad_stat_daily.__name__
            )
        )
        return False

    today = timezone.now().replace(hour=0, minute=0, second=0)
    existing_namads = NamadDailyStat.objects.filter(created_time__gte=today).distinct('namad_id').values_list('namad_id', flat=True)

    # namad_keys = namad_collection.find({"namad_key": {"$nin": today_stats}})
    namad_keys = Namad.objects.exclude(id__in=existing_namads)

    for nk in namad_keys:
        insert_daily_details.delay(nk.id)
        logger.debug(f"Daily stat called - [namad_id: {nk.id}]")

    if file_lock:
        close_running(file_lock)

    return True


@periodic_task(run_every=crontab(**settings.FIND_AND_INSERT_NAMADS_CRONTAB))
def collect_namads():
    """
    This function will search on the base namad page and insert important namads to mongo collection.
    :return: True after the job is done
    """

    exclude_list = [
        'تملی',
        'تسه',
        'افاد',
        'اراد',
        'اجاد',
    ]
    all_flows = [
        {
            "flow_key": "MostVisited",
            "flow_list": [1, 2, 27, 28, 29],
            "pantree": "151317"
        },
        {
            "flow_key": "Priority",
            "flow_list": [1, ],
            "pantree": "151317"
        },
        {
            "flow_key": "",
            "flow_list": [1, ],
            "pantree": "151316"
        },
    ]

    inserted_count = 0

    namads_to_create = []
    for flow in all_flows:
        for f_l in flow["flow_list"]:
            try:
                base_r_params = {
                    'Partree': flow["pantree"],
                    'Type': flow["flow_key"],
                    'Flow': f_l
                }
                base_r = requests.get(
                    f'{BASE_URL}/Loader.aspx',
                    params=base_r_params,
                    timeout=(settings.TSETMC_CONNECTION_CONNECT_TIMEOUT, settings.TSETMC_CONNECTION_READ_TIMEOUT)
                )
                base_r.raise_for_status()

            except requests.HTTPError as err:
                logger.error(
                    "[Exception occurred with base request]-"
                    "[Status: {}]-"
                    "[Error body: {}]-"
                    "[Error type: {}]".format(
                        base_r.status_code,
                        str(err),
                        type(err)
                    )
                )
                continue

            except Exception as err:
                logger.error(
                    "[Bare exception occurred with base request]-"
                    "[Error body: {}]-"
                    "[Error type: {}]".format(
                        str(err),
                        type(err)
                    )
                )
                continue

            logger.info("[Crawling for url: {}]-[Func name: {}]".format(
                base_r.url,
                collect_namads.__name__)
            )

            parsed_html = BeautifulSoup(base_r.text, features="html.parser")
            rows = parsed_html.find("table", {"class": "table1"}).find("tbody").find_all("tr")

            for row in rows:
                try:
                    tds = row.find_all("td")
                    namad = tds[0].a.string.strip()
                    name = tds[1].a.string.strip()
                    namad_key = tds[0].a.attrs['href'].split("&i=")[1]

                except Exception as e:
                    logger.error(
                        "[Exception occurred when trying to find all td tags]-"
                        "[Error body: {}]-"
                        "[Error type: {}]".format(
                            str(e),
                            type(e)
                        )
                    )
                    continue

                if any(namad.startswith(ex) for ex in exclude_list):
                    continue

                if Namad.objects.filter(id=namad_key).exists():
                    continue

                try:
                    params = {
                        "i": namad_key,
                        "ParTree": "151311"
                    }
                    namad_r = requests.get(
                        f'{BASE_URL}/Loader.aspx',
                        params=params,
                        timeout=(settings.TSETMC_CONNECTION_CONNECT_TIMEOUT, settings.TSETMC_CONNECTION_READ_TIMEOUT)
                    )
                    namad_r.raise_for_status()
                except Exception as e:
                    logger.error(
                        "[Bare exception occurred with namad request]-"
                        "[Error body: {}]-"
                        "[Error type: {}]-"
                        "[Func name: {}]".format(
                            str(e),
                            type(e),
                            collect_namads.__name__
                        )
                    )
                    continue

                namads_to_create.append(Namad(
                    id=namad_key,
                    name=normalizer.normalize(namad),
                    title=normalizer.normalize(name)
                ))
                inserted_count += 1

    Namad.objects.bulk_create(namads_to_create, ignore_conflicts=True)

    logger.info(
        "[Insert namad job runs successfully]-"
        "[Inserted records count: {}]-"
        "[Func name: {}]".format(
            inserted_count,
            collect_namads.__name__
        )
    )

    return True


@shared_task
def insert_daily_details(namad_key):
    """
    This function will insert details of each namad for daily collection.
    :param namad_key: key of each namad
    :return: True after the job is done and False if any eny exception occurs
    """

    namad_r_params = {
        "ParTree": 151311,
        "i": namad_key
    }

    try:
        namad_r = requests.get(
            f'{BASE_URL}/Loader.aspx',
            params=namad_r_params,
            timeout=(settings.TSETMC_CONNECTION_CONNECT_TIMEOUT, settings.TSETMC_CONNECTION_READ_TIMEOUT)
        )
        namad_r.raise_for_status()
    except requests.HTTPError as err:
        logger.error(
            "[namad request HTTPError]-"
            "[Status code: {}]-"
            "[Namad key: {}]".format(
                namad_r.status_code,
                namad_key,
            )
        )
        return False

    except Exception as err:
        logger.error(
            "[namad request Exception]-"
            "[Error body: {}]-"
            "[Error type: {}]"
            "[Namad key: {}]".format(
                str(err),
                type(err),
                namad_key,
            )
        )
        return False

    logger.info(
        "[URL request was successful]-"
        "[Namad key: {}]".format(
            namad_key
        )
    )

    parsed_html = BeautifulSoup(namad_r.text, features="html.parser")
    script_dict = extract_script_values(
        parsed_html=parsed_html,
        namad_key=namad_key,
        func_name=insert_daily_details.__name__,
        logger=logger
    )

    if not script_dict:
        return False
    daily_data = dict(
        namad_id=namad_key,
        tmax=int(script_dict.get('PSGelStaMax')),
        tmin=int(script_dict.get('PSGelStaMin')),
        stock_number=int(script_dict.get('ZTitad')),
        base_volume=int(script_dict.get('BaseVol')),
        floating_stock=float(script_dict.get('KAjCapValCpsIdx') or 0),
        total_transaction_average=script_dict.get('QTotTran5JAvg'),
        eps=int(script_dict.get('EstimatedEPS') or 0),
        sector_pe=float(script_dict['SectorPE']) if script_dict.get('SectorPE') else None
    )
    NamadDailyStat.objects.create(**daily_data)

    _script = script_dict.get('CSecVal') or None
    _market = normalizer.normalize(script_dict.get('Title').split("-")[1].strip())
    _group_name = normalizer.normalize(script_dict.get('LSecVal'))

    Namad.objects.filter(id=namad_key).update(
        script=_script,
        group_name=_group_name,
        market=_market
    )
    daily_data.update({'group_name': _group_name, 'market': _market})
    daily_data['stock_number'] = f"{daily_data['stock_number'] / 1e9:,} B"
    daily_data['base_volume'] = f"{daily_data['base_volume'] / 1e6:,} M"
    update_namad_data(namad_key, 'daily', daily_data)
    _script = script_dict.get('CSecVal') or None
    _market = script_dict.get('Title').split("-")[1].strip()

    Namad.objects.filter(id=namad_key).update(
        script=_script,
        group_name=normalizer.normalize(script_dict.get('LSecVal')),
        market=normalizer.normalize(_market)
    )

    return True


@periodic_task(run_every=crontab(**settings.INSERT_SECTIONS_CRONTAB))
def p_section_stat():
    """
       This function will insert field values to sections based on namad collection
       from mongo db.
       :return: True after the job is done and False if another task is already running
       """
    pika_connection = None

    try:
        pika_conn_params = pika.URLParameters(
            settings.CELERY_BROKER_URL
        )
        pika_connection = pika.BlockingConnection(pika_conn_params)
        pika_channel = pika_connection.channel()
        pika_queue = pika_channel.queue_declare(
            queue=SECTION_QUEUE_NAME, durable=True,
            exclusive=False, auto_delete=False
        )
        q_len = pika_queue.method.message_count
    except Exception as conn_err:
        logger.error(
            "[Exception occurred with making pika connection]-"
            "[Error body: {}]-"
            "[Error type: {}]".format(
                str(conn_err),
                type(conn_err)
            )
        )
        return False

    finally:
        if pika_connection is not None:
            pika_connection.close()

    if q_len and not settings.DEVEL:
        logger.info(
            "[Another insert sections still running]-"
            "[Remaining queue: {}]".format(
                q_len
            )
        )
        return False

    links = Namad.objects.filter(script__isnull=False, is_allowed=True).values('id', 'script')
    for link in links:
        insert_namad_sections.delay(link['id'], link['script'])

    logger.info("[Data inserted successfully]")
    return True


@periodic_task(run_every=crontab(**settings.CHECK_NAMAD_STATUS_CRONTAB))
def p_check_namads_status():
    """
    This task will check each namad status, in case if their status has been changed
    :return: True after the job is done
    """
    invalid_namads = Namad.objects.filter(script__isnull=False, is_allowed=False).values('id', 'script')
    url = f'{BASE_URL}/tsev2/data/instinfodata.aspx'
    before_update_count = invalid_namads.count()

    for namad in invalid_namads.iterator():
        namad_id, script = namad['id'], namad['script']
        params = {
            "i": namad_id,
            "c": f'{script}+'
        }
        _r = object
        try:
            _r = requests.get(
                url,
                params=params,
                timeout=(settings.TSETMC_CONNECTION_CONNECT_TIMEOUT, settings.TSETMC_CONNECTION_READ_TIMEOUT)
            )
            _r.raise_for_status()
        except requests.HTTPError:
            logger.error(
                "[TSETMC HTTPError]-"
                "[Namad key: {}]-"
                "[Status code: {}]".format(
                    namad_id,
                    _r.status_code,
                )
            )
            continue
        except requests.exceptions.ConnectTimeout:
            logger.error(
                "[TSETMC ConnectTimeout]-"
                "[Namad key: {}]-"
                "[Connection Timeout = {}]".format(
                    namad_id,
                    settings.TSETMC_CONNECTION_CONNECT_TIMEOUT
                )
            )
            continue
        except Exception as e:
            logger.error(
                "[TSETMC Exception]-"
                "[Error body: {}]-"
                "[Error type: {}]".format(
                    str(e),
                    type(e)
                )
            )
            continue

        logger.info(
            "[URL request was successful]-"
            "[Namad key: {}]-"
            "[Func name: {}]".format(
                namad_id,
                p_check_namads_status.__name__
            )
        )

        all_sections = _r.text.split(';')
        section0 = all_sections[0].split(',')

        if section0[1].strip() in ['A', 'AR']:
            Namad.objects.filter(id=namad_id).update(is_allowed=True)
            logger.info(
                "[Namad status changed]-"
                "[Namad key: {}]".format(
                    namad_id,
                )
            )

    logger.info(
        "[Status check job done]-"
        "[total changed status: {}]".format(
            before_update_count - invalid_namads.count()
        )
    )
    return True


@shared_task(queue=SECTION_QUEUE_NAME)
def insert_namad_sections(namad_key, script, count=0):
    """
    This function will insert specific sections for each namad.
    :param namad_key: key of specific namad
    :param script: value of the appending value of url
    :param count: exception count for retrying the task
    :return: True after the job is done and False if any exception occurs with retry count 10
    """
    invalid_sections = ['0', '']

    today_namad = NamadDailyStat.objects.filter(
        namad_id=namad_key,
        created_time__gt=timezone.now().replace(hour=0)
    ).order_by('-pk').first()
    if today_namad is None:
        logger.error(f"[Could not find stock number]-[Namad key: {namad_key}]-[script: {script}]")
        return False

    url = f'{BASE_URL}/tsev2/data/instinfodata.aspx'
    params = {
        "i": namad_key,
        "c": f'{script}+'
    }
    count += 1
    if count >= 10:
        logger.error(
            "[URL could not be reached--retry count: 10]-[Namad key: {}]-[Func name: {}]".format(
                namad_key,
                insert_namad_sections.__name__
            )
        )
        return False

    final_r = object
    try:
        final_r = requests.get(
            url,
            params=params,
            timeout=(settings.TSETMC_CONNECTION_CONNECT_TIMEOUT, settings.TSETMC_CONNECTION_READ_TIMEOUT)
        )
        final_r.raise_for_status()
    except requests.HTTPError as err:
        logger.error(
            "[TSETMC HTTPError]-"
            "[Namad key: {}]-"
            "[Status code: {}]".format(
                namad_key,
                final_r.status_code,
            )
        )
        # TODO: Enable or Disable should be added
        # insert_namad_sections.delay(namad_key, script, count)
        return False
    except requests.exceptions.ConnectTimeout:
        logger.error(
            "[TSETMC ConnectTimeout]-"
            "[Namad key: {}]-"
            "[Connection Timeout = {}]".format(
                namad_key,
                settings.TSETMC_CONNECTION_CONNECT_TIMEOUT
            )
        )
        # TODO: Enable or Disable should be added
        # insert_namad_sections.delay(namad_key, script, count)
        return False
    except Exception as e:
        logger.error(
            "[TSETMC Exception]-"
            "[Error body: {}]-"
            "[Error type: {}]".format(
                str(e),
                type(e)
            )
        )
        # TODO: Enable or Disable should be added
        # insert_namad_sections.delay(namad_key, script, count)
        return False

    logger.info(
        "[URL request was successful]-"
        "[Namad key: {}]-"
        "[Func name: {}]".format(
            namad_key,
            insert_namad_sections.__name__
        )
    )

    all_sections = final_r.text.split(';')
    section0 = all_sections[0].split(',')
    hashed_value = md5('{};{};{};{}'.format(section0[0], section0[2], section0[5], section0[10]).encode()).hexdigest()
    cache_value = cache.get(str(namad_key))

    if cache_value == hashed_value \
            or not section0[1].strip() in ['A', 'AR'] \
            or (
            datetime.now().hour > 9 and (
            any(x in invalid_sections for x in section0[:10]) or all_sections[4] == ''
    )
    ):
        if section0[1].strip() != 'A':
            Namad.objects.filter(id=namad_key).update(is_allowed=False)
        logger.debug(
            "[Namad has not changed]-"
            "[Namad key: {}]".format(
                namad_key,
            )
        )
        return False

    ready_data = dict()
    for index, section in enumerate(all_sections):
        if index not in SECTIONS_TO_INSERT:
            continue

        section_value = section.split(',')

        if index == 2:
            structured_section = []
            for temp_i in range(len(section_value) - 1):
                sub_section = list(map(int, section_value[temp_i].split('@')))
                structured_section.append(sub_section)

            section_value = list(chain(*structured_section))

        for sec_index, sec_value in enumerate(section_value):
            if "{}{}".format(index, sec_index) not in SECTIONS_INDEX_MAP.keys():
                continue

            if index == 1 and sec_index == 3:
                try:
                    sec_value = float(sec_value.split("<div class='pn'>")[1].split("</div>")[0])
                except IndexError:
                    pass

            try:
                val = float(sec_value) if int(sec_value) != float(sec_value) else int(sec_value)

            except (ValueError, TypeError):
                val = sec_value.strip() if sec_value != '' else None

            if val not in ['', None]:
                ready_data[SECTIONS_INDEX_MAP.get("{}{}".format(index, sec_index))] = val

    if not ready_data.get("Buy_I_Volume"):
        logger.info("[Namad's checksum time is not valid]-[Namad key: {}]".format(namad_key))
        return False

    ready_data['mv'] = ready_data['pc'] * int(today_namad.stock_number)
    ready_data['plc'] = ready_data['pl'] - ready_data['py']
    ready_data['plp'] = round((ready_data['plc'] / ready_data['py']) * 100, 2)
    ready_data['pcc'] = ready_data['pc'] - ready_data['py']
    ready_data['pcp'] = round((ready_data['pcc'] / ready_data['py']) * 100, 2)

    ready_data['tmin'] = today_namad.tmin
    ready_data['tmax'] = today_namad.tmax
    ready_data['stock_number'] = today_namad.stock_number
    ready_data['base_volume'] = today_namad.base_volume
    ready_data['floating_stock'] = today_namad.floating_stock
    ready_data['total_transaction_average'] = today_namad.total_transaction_average

    ready_data['namad_id'] = namad_key

    try:
        sections_data = dict(
            checksum_time=ready_data['checksum_time'],
            status=ready_data['status'],
            pl=ready_data['pl'],
            pc=ready_data['pc'],
            pf=ready_data['pf'],
            py=ready_data['py'],
            pmax=ready_data['pmax'],
            pmin=ready_data['pmin'],
            tno=ready_data['tno'],
            tvol=ready_data['tvol'],
            tval=ready_data['tval'],
            zd1=ready_data['zd1'],
            qd1=ready_data['qd1'],
            pd1=ready_data['pd1'],
            po1=ready_data['po1'],
            qo1=ready_data['qo1'],
            zo1=ready_data['zo1'],
            zd2=ready_data['zd2'],
            qd2=ready_data['qd2'],
            pd2=ready_data['pd2'],
            po2=ready_data['po2'],
            qo2=ready_data['qo2'],
            zo2=ready_data['zo2'],
            zd3=ready_data['zd3'],
            qd3=ready_data['qd3'],
            pd3=ready_data['pd3'],
            po3=ready_data['po3'],
            qo3=ready_data['qo3'],
            zo3=ready_data['zo3'],
            buy_i_volume=ready_data['Buy_I_Volume'],
            buy_n_volume=ready_data['Buy_N_Volume'],
            sell_i_volume=ready_data['Sell_I_Volume'],
            sell_n_volume=ready_data['Sell_N_Volume'],
            buy_counti=ready_data['Buy_CountI'],
            buy_countn=ready_data['Buy_CountN'],
            sell_counti=ready_data['Sell_CountI'],
            sell_countn=ready_data['Sell_CountN'],
            mv=ready_data['mv'],
            plc=ready_data['plc'],
            plp=ready_data['plp'],
            pcc=ready_data['pcc'],
            pcp=ready_data['pcp'],
            tmin=ready_data['tmin'],
            tmax=ready_data['tmax'],
            stock_number=ready_data['stock_number'],
            base_volume=ready_data['base_volume'],
            floating_stock=ready_data['floating_stock'],
            total_transaction_average=ready_data['total_transaction_average']
        )
        NamadStat.objects.create(
            namad_id=namad_key,
            **sections_data
        )
        order_status_table = [
            [
                f"{sections_data.pop(f'zd{i}'):,}",
                f"{sections_data.pop(f'qd{i}'):,}",
                f"{sections_data.pop(f'pd{i}'):,}",
                f"{sections_data.pop(f'po{i}'):,}",
                f"{sections_data.pop(f'qo{i}'):,}",
                f"{sections_data.pop(f'zo{i}'):,}"
            ] for i in range(1, 4)
        ]
        _i = ''
        buy_per_i = round(
            (sections_data['pc'] * sections_data['buy_i_volume']) / sections_data['buy_counti'], 2
        ) if sections_data['buy_counti'] else _i
        sell_per_i = round(
            (sections_data['pc'] * sections_data['sell_n_volume']) / sections_data['sell_counti'], 2
        ) if sections_data['sell_counti'] else _i

        sections_data.update(
            {
                'money_entry_data': {
                    # Real Part
                    'buy_per_i': f"{round(buy_per_i / 1e6, 2):,} M" if buy_per_i else _i,
                    'sell_per_i': f"{round(sell_per_i / 1e6, 2):,} M" if sell_per_i else _i,
                    'i_buyer_seller_pow': round(
                        (sections_data['buy_i_volume'] * sections_data['sell_counti']) / (sections_data['buy_counti'] * sections_data['sell_i_volume']), 2
                    ) if all([sections_data['buy_counti'], sections_data['sell_i_volume']]) else _i,
                    # Legal Part
                    'buy_per_n': f"{round((sections_data['pc'] * sections_data['buy_n_volume']) / (sections_data['buy_countn'] * 1e6), 2):,} M" if sections_data['buy_countn'] else _i,
                    'sell_per_n': f"{round((sections_data['pc'] * sections_data['sell_n_volume']) / (sections_data['sell_countn'] * 1e6), 2):,} M" if sections_data['sell_countn'] else _i,
                    'n_buyer_seller_pow': round(
                        (sections_data['buy_n_volume'] * sections_data['sell_countn']) / (sections_data['buy_countn'] * sections_data['sell_n_volume']), 2
                    ) if all([sections_data['buy_countn'], sections_data['sell_n_volume']]) else _i
                },
                'order_status_table': order_status_table
            },

        )

        sections_data['money_entry_graph'] = (
            int(timezone.now().timestamp() * 1000),
            buy_per_i,
            sell_per_i,
            sections_data['money_entry_data']['i_buyer_seller_pow']
        )
        # converting to million
        sections_data['base_volume'] = f"{sections_data['base_volume'] / 1e6:,} M"
        # converting to billion
        b_convert_keys = ('tvol', 'tval', 'mv', 'stock_number')
        for _k in b_convert_keys:
            sections_data[_k] = f"{sections_data[_k] / 1e9:,} B"
        update_namad_data(namad_key, 'sections', sections_data)
    except Exception as e:
        logger.error(f"[Bare Exception occurred]-[error: {str(e)}]")

    cache.set(str(namad_key), hashed_value, 60 * 60 * 4)

    logger.info(
        "[Data inserted successfully]-"
        "[Namad key: {}]".format(
            namad_key
        )
    )

    return namad_key


@periodic_task(run_every=crontab(**settings.INSERT_LAST_HISTORY_CRONTAB))
def p_insert_namads_last_history():
    """
    This function will find last section and insert it to namad history collection and truncate section collection.
    :return: True after the job is done
    """
    # The meaning of expected_time is 12:30:00
    expected_time = timezone.now().replace(hour=12, minute=30, second=0, microsecond=0)
    today_stats_lte = NamadStat.objects.values("namad_id").filter(checksum_time__lte=expected_time.time()).annotate(last_record=Max('id'))
    today_stats_gte = NamadStat.objects.values("namad_id").filter(checksum_time__gt=expected_time.time()).annotate(last_record=Max('id'))

    stats = defaultdict(list)
    for r1 in today_stats_lte:
        stats[r1['namad_id']].append(r1['last_record'])
    for r2 in today_stats_gte:
        stats[r2['namad_id']].append(r2['last_record'])

    namad_history_list = []
    for namad_id, stat_ids in stats.items():
        namad_stats = NamadStat.objects.filter(pk__in=stat_ids).order_by('pk')
        namad_history = NamadHistory(namad_id=namad_id)
        for i, ns in enumerate(namad_stats):
            _close = dict(
                zd1=ns.zd1,
                qd1=ns.qd1,
                pd1=ns.pd1,
                po1=ns.po1,
                qo1=ns.qo1,
                zo1=ns.zo1,
                zd2=ns.zd2,
                qd2=ns.qd2,
                pd2=ns.pd2,
                po2=ns.po2,
                qo2=ns.qo2,
                zo2=ns.zo2,
                zd3=ns.zd3,
                qd3=ns.qd3,
                pd3=ns.pd3,
                po3=ns.po3,
                qo3=ns.qo3,
                zo3=ns.zo3,
            )
            if i == 0:
                for f_name in [f.name for f in NamadStat._meta.fields]:
                    setattr(namad_history, f_name, getattr(ns, f_name))
                namad_history.stat_date = ns.created_time
                namad_history.b_closed = _close
            else:
                namad_history.a_closed = _close
        namad_history_list.append(namad_history)

    NamadHistory.objects.bulk_create(namad_history_list, ignore_conflicts=True)
    NamadStat.objects.all().delete()

    history_data = NamadHistory.objects.filter(
        stat_date__gte=timezone.now() - timezone.timedelta(days=365),
    ).values_list('namad_id', 'stat_date', 'pc', 'tvol')

    logger.info(
        f"[Insert daily cache data started]"
    )
    to_cache_data = defaultdict(list)
    for namad_id, stat_date, pc, tvol in history_data.iterator():
        to_cache_data[namad_id].append(
            (
                stat_date.strftime('%Y-%m-%d'),
                JalaliDatetime(stat_date).strftime('%Y-%m-%d'),
                pc,
                tvol
            )
        )

    for namad_id, data in to_cache_data.items():
        update_namad_data(namad_id, 'daily', {'price_volume_graph': data})
        update_namad_data(namad_id, 'sections', {}, clear=True)
    logger.info(
        f"[Insert daily cache data finished]"
    )

    Namad.objects.filter(is_allowed=False).update(is_allowed=True)
