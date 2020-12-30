import logging

from celery.schedules import crontab
from celery.task import periodic_task
from channels.layers import get_channel_layer

from django.db.models import Sum, Count, F, ExpressionWrapper, FloatField, Max, BigIntegerField, Min
from django.db.models.functions import Cast
from django.core.cache import cache
from django.utils import timezone

from conf import settings
from apps.tsetmc.models import NamadStat, NamadHistory
from asgiref.sync import async_to_sync

from .models import SignalFilter

logger = logging.getLogger(__name__)
MONEY_THRESHOLD = 1e2

DATA_CONVERTER = {
    'saf_kharid': lambda x: (x[0], f"{x[1]:,}", x[2], f"{x[3]:,}"),
    'saf_foroush': lambda x: (x[0], f"{x[1]:,}", x[2], f"{x[3]:,}"),
    'hajm_mashkouk': lambda x: (x[0], f"{x[1]:,}", x[2], f"{round(x[3] / 1e6, 2):,} M", f"{round(x[4], 2):,}"),
    'foroush_bishtar': lambda x: (x[0], f"{x[1]:,}", f"{round(x[2] / 1e6, 2):,} M", f"{round(x[3] / 1e6, 2):,} M", round(x[4], 2)),
    'foroush_kamtar': lambda x: (x[0], f"{x[1]:,}", f"{round(x[2] / 1e6, 2):,} M", f"{round(x[3] / 1e6, 2):,} M", round(x[4], 2)),
    'cbc_haqiqi': lambda x: (x[0], f"{x[1]:,}", f"{round(x[2] / 1e6, 2)} M", f"{round(x[3] / 1e6, 2)} M"),
    'cbc_hoqouqi': lambda x: (x[0], f"{x[1]:,}", f"{round(x[2] / 1e6, 2)} M", f"{round(x[3] / 1e6, 2)} M"),
    'taqaza_bartar': lambda x: (x[0], f"{x[1]:,}", f"{round(x[2] / 1e9):,} B", f"{x[3]:,}"),
    'arzeh_bartar': lambda x: (x[0], f"{x[1]:,}", f"{round(x[2] / 1e9):,} B", f"{x[3]:,}"),
    'kharid_haqiqi': lambda x: (x[0], f"{x[1]:,}", x[2], f"{round(x[3] / 1e6, 2):,} M", f"{x[4]:,}", round(x[5], 2)),
    'foroush_haqiqi': lambda x: (x[0], f"{x[1]:,}", x[2], f"{round(x[3] / 1e6, 2):,} M", f"{x[4]:,}", round(x[5], 2)),
    'sharpi': lambda x: (x[0], f"{x[1]:,}", x[2], f"{x[3]:,}"),
    'range_mosbat': lambda x: (x[0], f"{x[1]:,}", x[2], f"{x[3]:,}", x[4], x[5].strftime("%H:%M:%S")),
    'por_taqaza': lambda x: (x[0], round(x[1], 2), f"{round(x[2] / 1e9, 2):,} B"),
    'shekar_navasani': lambda x: (x[0], f"{x[1]:,}", x[2], f"{round(x[3], 2):,}", f"{round(x[4], 2):,}", f"{round(x[5] / 1e9, 2):,} B"),
    'kharid_forosh_mashkouk': lambda x: (
        x[0].strftime("%H:%M:%S"), x[1], x[2], f"{round(x[3] / 1e9, 2):,} B", f"{round(x[4] / 1e9, 2):,} B", f"{round(x[5] / 1e9, 2):,} B",
        f"{round(x[6], 2):,}", f"{x[7]:,}"),
    'tavajoh_haqiqi': lambda x: (x[0], f"{x[1]:,}", x[2], f"{round(x[3], 2):,}", f"{round(x[4] / 1e9, 2):,} B", f"{round(x[5], 2):,}")
}


def post_data(filter_code, signal_data):
    # Empty cache on new day signal
    _last_touch = cache.get_or_set(f'{filter_code}_last_touched', timezone.now())
    if _last_touch.date() != timezone.now().date():
        cache.delete(filter_code)
        cache.delete(f'{filter_code}_last_touched')

    # Do not send empty data
    if not signal_data:
        logger.warning(
            f"[Filter signal data was empty]-[filter_code: {filter_code}]"
        )
        return 0

    try:
        _filter = SignalFilter.objects.select_related('category').get(filter_code=filter_code, is_enable=True)
    except SignalFilter.DoesNotExist:
        logger.warning(
            f"[Filter Code not found]-[filter_code: {filter_code}]"
        )
        return 0

    if filter_code == 'kharid_forosh_mashkouk':
        _prev_signal_data = cache.get(filter_code, [])
        signal_data = list(set(signal_data) - set([p[:-1] for p in _prev_signal_data]))
        signal_data.sort(key=lambda x: x[0], reverse=True)

        # signal_data = [s + ([p[1:3] for p in _prev_signal_data].count(s[1:3]) + 1,) for s in signal_data]
        for i, s in enumerate(signal_data):
            s += (1,)
            for old in _prev_signal_data:
                if s[1] == old[1] and s[2] == old[2]:
                    s = s[:-1] + (max(old[8]+1, s[-1]),)
            signal_data[i] = s

        signal_data += _prev_signal_data

    cache.set(filter_code, signal_data)
    layer = get_channel_layer()

    _channel = 'free_signals' if _filter.category.is_free else 'filter_signals'
    async_to_sync(layer.group_send)(
        _channel,
        {
            'type': 'filter_signals.message',
            'content': {'filter_code': filter_code, 'data': signal_data}
        }
    )

    return len(signal_data)


def process_data(func):
    def wrapper(*args, **kwargs):
        kwargs['last_stat'] = NamadStat.objects.values('namad__id').annotate(max_id=Max('id')).values_list('max_id', flat=True)
        return post_data(func.__name__, list(map(DATA_CONVERTER[func.__name__], func(*args, **kwargs))))

    return wrapper


@periodic_task(run_every=crontab(**settings.INSERT_SECTIONS_CRONTAB))
def call_filters():
    return {
        'saf_karid': saf_kharid(),
        'saf_foroush': saf_foroush(),
        'hajm_mashkouk': hajm_mashkouk(),
        'foroush_bishtar': foroush_bishtar(),
        'foroush_kamtar': foroush_kamtar(),
        'cbc_haqiqi': cbc_haqiqi(),
        'cbc_hoqouqi': cbc_hoqouqi(),
        'taqaza_bartar': taqaza_bartar(),
        'arzeh_bartar': arzeh_bartar(),
        'kharid_haqiqi': kharid_haqiqi(),
        'foroush_haqiqi': foroush_haqiqi(),
        'sharpi': sharpi(),
        'range_mosbat': range_mosbat(),
        'por_taqaza': por_taqaza(),
        'kharid_forosh_mashkouk': kharid_forosh_mashkouk(),
        'shekar_navasani': shekar_navasani(),
        'tavajoh_haqiqi': tavajoh_haqiqi(),
    }


@process_data
def saf_kharid(*args, **kwargs):
    return NamadStat.objects.filter(
        id__in=kwargs['last_stat'],
        pl__lt=F('tmax'),
        pl__gt=ExpressionWrapper(0.2 * F('py') + 0.8 * F('tmax'), output_field=FloatField())
    ).values_list(
        'namad__name',
        'pl',
        'plp',
        'pc'
    )


@process_data
def saf_foroush(*args, **kwargs):
    return NamadStat.objects.filter(
        id__in=kwargs['last_stat'],
        pl__gt=F('tmin'),
        pl__lt=ExpressionWrapper(0.2 * F('py') + 0.8 * F('tmin'), output_field=FloatField())
    ).values_list(
        'namad__name',
        'pl',
        'plp',
        'pc'
    )


@process_data
def hajm_mashkouk(*args, **kwargs):
    return NamadStat.objects.filter(
        id__in=kwargs['last_stat'],
        total_transaction_average__gt=0
    ).annotate(
        tvol_tta=Cast('tvol', output_field=FloatField()) / Cast('total_transaction_average', output_field=FloatField())
    ).order_by(
        '-tvol_tta'
    ).values_list(
        'namad__name',
        'pl',
        'plp',
        'tvol',
        'tvol_tta'
    )[:15]


@process_data
def foroush_bishtar(*args, **kwargs):
    return NamadStat.objects.filter(
        id__in=kwargs['last_stat'],
        buy_counti__gt=0,
        buy_i_volume__gt=0,
        sell_counti__gt=0,
        sell_i_volume__gt=0,
    ).annotate(
        kharid_avg=Cast('buy_i_volume', output_field=FloatField()) * Cast('pc', output_field=FloatField()) / Cast('buy_counti',
                                                                                                                  output_field=FloatField()),
        foroush_avg=Cast('sell_i_volume', output_field=FloatField()) * Cast('pc', output_field=FloatField()) / Cast('sell_counti',
                                                                                                                    output_field=FloatField())
    ).filter(
        foroush_avg__gt=0,
    ).annotate(
        saraneh=Cast('kharid_avg', output_field=FloatField()) / Cast('foroush_avg', output_field=FloatField())
    ).order_by(
        '-saraneh'
    ).values_list(
        'namad__name',
        'pl',
        'kharid_avg',
        'foroush_avg',
        'saraneh'
    )[:15]


@process_data
def foroush_kamtar(*args, **kwargs):
    return NamadStat.objects.filter(
        id__in=kwargs['last_stat'],
        buy_counti__gt=0,
        buy_i_volume__gt=0,
        sell_counti__gt=0,
        sell_i_volume__gt=0,
    ).annotate(
        kharid_avg=Cast('buy_i_volume', output_field=FloatField()) * Cast('pc', output_field=FloatField()) / Cast('buy_counti',
                                                                                                                  output_field=FloatField()),
        foroush_avg=Cast('sell_i_volume', output_field=FloatField()) * Cast('pc', output_field=FloatField()) / Cast('sell_counti',
                                                                                                                    output_field=FloatField()),
    ).filter(
        foroush_avg__gt=0,
    ).annotate(
        saraneh=Cast('kharid_avg', output_field=FloatField()) / Cast('foroush_avg', output_field=FloatField())
    ).order_by(
        'saraneh'
    ).values_list(
        'namad__name',
        'pl',
        'kharid_avg',
        'foroush_avg',
        'saraneh'
    )[:15]


@process_data
def cbc_haqiqi(*args, **kwargs):
    return NamadStat.objects.filter(
        id__in=kwargs['last_stat'],
        # total_transaction_average__gt=0,
        tvol__gt=0
    ).annotate(
        # e=Cast('tvol', output_field=FloatField()) / Cast('total_transaction_average', output_field=FloatField()),
        j=Cast('buy_n_volume', output_field=FloatField()) / Cast('tvol', output_field=FloatField()),
        k=Cast('sell_i_volume', output_field=FloatField()) / Cast('tvol', output_field=FloatField())
    ).filter(
        # e__gt=1,
        j__gt=0.5,
        k__gt=0.7
    ).values_list(
        'namad__name',
        'pl',
        'sell_i_volume',
        'buy_n_volume'
    )


@process_data
def cbc_hoqouqi(*args, **kwargs):
    return NamadStat.objects.filter(
        id__in=kwargs['last_stat'],
        # total_transaction_average__gt=0,
        tvol__gt=0
    ).annotate(
        # e=Cast('tvol', output_field=FloatField()) / Cast('total_transaction_average', output_field=FloatField()),
        j=Cast('sell_n_volume', output_field=FloatField()) / Cast('tvol', output_field=FloatField()),
        k=Cast('buy_i_volume', output_field=FloatField()) / Cast('tvol', output_field=FloatField())
    ).filter(
        # e__gt=1,
        j__gt=0.5,
        k__gt=0.7
    ).values_list(
        'namad__name',
        'pl',
        'buy_i_volume',
        'sell_n_volume'
    )


@process_data
def taqaza_bartar(*args, **kwargs):
    return NamadStat.objects.filter(
        id__in=kwargs['last_stat'],
        pl=F('tmax')
    ).annotate(
        top_demand_q=Cast(F('pl'), output_field=BigIntegerField()) * Cast(F('qd1'), output_field=BigIntegerField())
    ).order_by(
        '-top_demand_q'
    ).values_list(
        'namad__name',
        'pl',
        'top_demand_q',
        'pc'
    )[:15]


@process_data
def arzeh_bartar(*args, **kwargs):
    return NamadStat.objects.filter(
        id__in=kwargs['last_stat'],
        pl=F('tmin')
    ).annotate(
        top_supply_q=Cast(F('pl'), output_field=BigIntegerField()) * Cast(F('qo1'), output_field=BigIntegerField())
    ).order_by(
        '-top_supply_q'
    ).values_list(
        'namad__name',
        'pl',
        'top_supply_q',
        'pc'
    )[:15]


@process_data
def kharid_haqiqi(*args, **kwargs):
    return NamadStat.objects.filter(
        id__in=kwargs['last_stat'],
        buy_counti__gt=0,
        sell_counti__gt=0
    ).annotate(
        kharid_avg=Cast('buy_i_volume', output_field=FloatField()) * Cast('pc', output_field=FloatField()) / Cast('buy_counti',
                                                                                                                  output_field=FloatField()),
        foroush_avg=Cast('sell_i_volume', output_field=FloatField()) * Cast('pc', output_field=FloatField()) / Cast('sell_counti',
                                                                                                                    output_field=FloatField())
    ).annotate(
        saraneh=Cast('kharid_avg', output_field=FloatField()) / Cast('foroush_avg', output_field=FloatField())
    ).order_by(
        '-kharid_avg'
    ).values_list(
        'namad__name',
        'pl',
        'plp',
        'kharid_avg',
        'buy_counti',
        'saraneh'
    )[:15]


@process_data
def foroush_haqiqi(*args, **kwargs):
    return NamadStat.objects.filter(
        id__in=kwargs['last_stat'],
        buy_counti__gt=0,
        sell_counti__gt=0,
        sell_i_volume__gt=0
    ).annotate(
        kharid_avg=Cast('buy_i_volume', output_field=FloatField()) * Cast('pc', output_field=FloatField()) / Cast('buy_counti',
                                                                                                                  output_field=FloatField()),
        foroush_avg=Cast('sell_i_volume', output_field=FloatField()) * Cast('pc', output_field=FloatField()) / Cast('sell_counti',
                                                                                                                    output_field=FloatField())
    ).annotate(
        saraneh=Cast('foroush_avg', output_field=FloatField()) / Cast('kharid_avg', output_field=FloatField())
    ).order_by(
        '-foroush_avg'
    ).values_list(
        'namad__name',
        'pl',
        'plp',
        'foroush_avg',
        'sell_counti',
        'saraneh'
    )[:15]


@process_data
def sharpi(*args, **kwargs):
    history_last_records = NamadHistory.objects.values('namad_id').annotate(max_id=Max('id')).values_list('max_id', flat=True)
    yesterday_stats = NamadHistory.objects.filter(
        pk__in=history_last_records,
        pl=F('tmax')
    ).values_list('namad_id', flat=True)

    return NamadStat.objects.filter(
        id__in=kwargs['last_stat'],
        namad_id__in=yesterday_stats,
        pmax=F('tmax'),
        pl__lt=F('pmax')
    ).values_list(
        'namad__name',
        'pl',
        'plp',
        'pc'
    )


@process_data
def range_mosbat(*args, **kwargs):
    namad_ids = NamadStat.objects.filter(
        created_time__gte=timezone.now() - timezone.timedelta(minutes=5)
    ).values('namad').annotate(stat_count=Count('*')).filter(stat_count__gte=2).values_list('namad_id', flat=True)

    range_mosbat_list = []
    for namad_id in namad_ids:
        namad_stats = NamadStat.objects.select_related('namad').filter(namad_id=namad_id).order_by('-pk')[:2]
        second_stat = namad_stats[0]
        first_stat = namad_stats[1]

        if first_stat.plp - second_stat.plp > 1.5:
            range_mosbat_list.append((
                first_stat.namad.name,
                first_stat.pl,
                first_stat.plp,
                first_stat.pc,
                first_stat.pcp,
                first_stat.created_time
            ))

    return range_mosbat_list


@process_data
def por_taqaza(*args, **kwargs):
    return NamadStat.objects.filter(
        id__in=kwargs['last_stat'],
    ).values(
        'namad__group_name'
    ).annotate(
        sum_buy_i_volume=Sum('buy_i_volume'),
        sum_buy_counti=Sum('buy_counti'),
        sum_sell_i_volume=Sum('sell_i_volume'),
        sum_sell_counti=Sum('sell_counti'),
        sum_entered_money=Sum(Cast('pc', output_field=BigIntegerField()) * (F('buy_i_volume') - F('sell_i_volume')))
    ).filter(
        sum_buy_i_volume__gt=0,
        sum_buy_counti__gt=0,
        sum_sell_i_volume__gt=0,
        sum_sell_counti__gt=0
    ).annotate(
        saraneh_foroush=Cast('sum_sell_i_volume', output_field=FloatField()) / Cast('sum_sell_counti', output_field=FloatField()),
        saraneh_kharid=Cast('sum_buy_i_volume', output_field=FloatField()) / Cast('sum_buy_counti', output_field=FloatField()),
    ).annotate(
        saraneh=Cast('saraneh_kharid', output_field=FloatField()) / Cast('saraneh_foroush', output_field=FloatField())
    ).order_by(
        '-saraneh'
    ).values_list(
        'namad__group_name',
        'saraneh',
        'sum_entered_money'
    )[:15]


@process_data
def shekar_navasani(*args, **kwargs):
    return NamadStat.objects.filter(
        id__in=kwargs['last_stat'],
        total_transaction_average__gt=0,
        buy_counti__gt=30,
        sell_counti__gt=0
    ).annotate(
        tvol_tta=Cast('tvol', output_field=FloatField()) / Cast('total_transaction_average', output_field=FloatField()),
        kharid_avg=Cast('buy_i_volume', output_field=FloatField()) * Cast('pc', output_field=FloatField()) / Cast('buy_counti', output_field=FloatField()),
        foroush_avg=Cast('sell_i_volume', output_field=FloatField()) * Cast('pc', output_field=FloatField()) / Cast('sell_counti', output_field=FloatField()),
    ).filter(
        foroush_avg__gt=0
    ).annotate(
        saraneh=F('kharid_avg') / F('foroush_avg'),
        entered_money=Cast('pc', output_field=BigIntegerField()) * (F('buy_i_volume') - F('sell_i_volume'))
    ).filter(
        saraneh__gt=2,
        kharid_avg__gt=MONEY_THRESHOLD * 1e6,
        tvol_tta__gt=1
    ).values_list(
        'namad__name',
        'pl',
        'plp',
        'tvol_tta',
        'saraneh',
        'entered_money'
    )


@process_data
def tavajoh_haqiqi(*args, **kwargs):
    min_max = {ns['namad_id']: ns for ns in NamadHistory.objects.filter(
        created_time__gt=timezone.now() - timezone.timedelta(days=30)
    ).values(
        'namad_id'
    ).annotate(
        max=Max('pl'),
        min=Min('pl')
    ).filter(
        max__gt=F('min')
    ).values(
        'namad_id',
        'max',
        'min'
    )}

    namad_stats = NamadStat.objects.select_related('namad').filter(
        id__in=kwargs['last_stat'],
        buy_counti__gt=0,
        sell_counti__gt=0,
        total_transaction_average__gt=0,
        tvol__gt=0
    ).annotate(
        saraneh_kharid=Cast('buy_i_volume', output_field=FloatField()) / Cast('buy_counti', output_field=FloatField()),
        saraneh_foroush=Cast('sell_i_volume', output_field=FloatField()) / Cast('sell_counti', output_field=FloatField()),
        saraneh=F('saraneh_kharid') / F('saraneh_foroush'),
        # monthly_distance=(Cast('pl', output_field=FloatField()) - namad['pl_min']) * 1e2 / (namad['pl_max'] - namad['pl_min']),
        j=Cast('sell_n_volume', output_field=FloatField()) / Cast('tvol', output_field=FloatField()),
        entered_money=Cast('pc', output_field=BigIntegerField()) * (F('buy_i_volume') - F('sell_i_volume')),
        tvol_tta=Cast('tvol', output_field=FloatField()) / Cast('total_transaction_average', output_field=FloatField()),
    ).filter(
        saraneh__gt=10,
        j__lt=0.2,
        # monthly_distance__lt=20
    ).values_list(
        'namad_id',
        'namad__name',
        'pl',
        'plp',
        'saraneh',
        'entered_money',
        'tvol_tta'
    )

    return [ns[1:] for ns in namad_stats if min_max.get(ns[0]) and ((ns[2] - min_max[ns[0]]['min']) * 1e2 / (min_max[ns[0]]['max'] - min_max[ns[0]]['min'])) < 20]


@process_data
def kharid_forosh_mashkouk(*args, **kwargs):
    namad_ids = NamadStat.objects.values('namad').annotate(stat_count=Count('*')).filter(stat_count__gte=2).values_list('namad_id', flat=True)

    kharid_foroush_list = []
    for namad_id in namad_ids:
        namad_stats = NamadStat.objects.select_related('namad').filter(namad_id=namad_id).order_by('-pk')[:2]
        latest_stat = namad_stats[0]
        second_latest_stat = namad_stats[1]

        kharid_lahze = (latest_stat.buy_i_volume - second_latest_stat.buy_i_volume) * latest_stat.pl
        buyers_count = latest_stat.buy_counti - second_latest_stat.buy_counti

        foroush_lahze = (latest_stat.sell_i_volume - second_latest_stat.sell_i_volume) * latest_stat.pl
        sellers_count = latest_stat.sell_counti - second_latest_stat.sell_counti
        try:
            kharid_lahze_avg = kharid_lahze / buyers_count
            foroush_lahze_avg = foroush_lahze / sellers_count
            saraneh_kharid = latest_stat.buy_i_volume * latest_stat.pc / latest_stat.buy_counti
            saraneh_foroush = latest_stat.sell_i_volume * latest_stat.pc / latest_stat.sell_counti
            saraneh = saraneh_kharid / saraneh_foroush
        except ZeroDivisionError:
            continue

        if kharid_lahze_avg / 1e7 > MONEY_THRESHOLD:
            kharid_foroush_list.append((
                latest_stat.created_time,
                latest_stat.namad.name,
                'خرید مشکوک',
                kharid_lahze_avg,
                saraneh_kharid,
                saraneh_foroush,
                saraneh,
                latest_stat.pl
            ))

        if foroush_lahze_avg / 1e7 > MONEY_THRESHOLD:
            kharid_foroush_list.append((
                latest_stat.created_time,
                latest_stat.namad.name,
                'فروش مشکوک',
                foroush_lahze_avg,
                saraneh_kharid,
                saraneh_foroush,
                saraneh,
                latest_stat.pl
            ))

    return kharid_foroush_list

# @shared_task
# def hajm_emrouz():
#     last_stats = NamadStat.objects.values('namad__id').annotate(max_id=Max('id')).values_list('max_id', flat=True)
#
#     hajm_emrouz_list = NamadStat.objects.filter(
#         id__in=last_stats,
#         total_transaction_average__gt=0
#     ).annotate(
#         t_v=ExpressionWrapper(F('tvol') / F('total_transaction_average'), output_field=FloatField())
#     ).order_by(
#         '-t_v'
#     ).values_list(
#         'namad__name',
#         'pl',
#         'tvol',
#         't_v'
#     )[:15]
#
#     # hajm_emrouz_list = list()
#     # for namad in today_volume:
#     #     hajm_emrouz_list.append([
#     #         namad.namad.name,
#     #         namad.pl,
#     #         namad.tvol,
#     #         round(namad.tvol / namad.total_transaction_average, 2)
#     #     ])
#
#     if hajm_emrouz_list:
#         post_data("hajm_emrouz", hajm_emrouz_list)
#
#     return hajm_emrouz_list
#
#
# def intcomma(data_list):
#     for row in data_list:
#         new_row = [f'{value:,}' if (type(value) is int or type(value) is float) else value for value in row]
#         yield new_row
#
#
# def round_float(data_list):
#     for row in data_list:
#         new_row = [round(value, 2) if (type(value) is float) else value for value in row]
#         yield new_row
