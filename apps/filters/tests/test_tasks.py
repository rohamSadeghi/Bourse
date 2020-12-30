from django.core import management
from django.test import TestCase
from django.utils import timezone

from apps.filters.tasks import call_filters
from apps.tsetmc.models import NamadStat, NamadDailyStat, NamadHistory


class FilterTaskTestCase(TestCase):
    def setUp(self) -> None:
        management.call_command('loaddata', 'testing.json', verbosity=0)
        management.call_command('loaddata', 'common.json', verbosity=0)
        now = timezone.now()
        NamadDailyStat.objects.update(created_time=now)
        NamadStat.objects.update(created_time=now)
        NamadHistory.objects.update(created_time=now)

    def test_call_filters(self):
        expected_data = {
            'saf_karid': 6, 'saf_foroush': 22, 'hajm_mashkouk': 15,
            'foroush_bishtar': 15, 'foroush_kamtar': 15, 'cbc_haqiqi': 12,
            'cbc_hoqouqi': 9, 'taqaza_bartar': 15, 'arzeh_bartar': 15,
            'kharid_haqiqi': 15, 'foroush_haqiqi': 15, 'sharpi': 1,
            'range_mosbat': 2, 'por_taqaza': 15, 'kharid_forosh_mashkouk': 1,
            'shekar_navasani': 10, 'tavajoh_haqiqi': 1
        }
        result_data = call_filters()
        self.assertDictEqual(result_data, expected_data)
