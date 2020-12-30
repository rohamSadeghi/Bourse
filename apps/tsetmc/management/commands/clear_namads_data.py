from django.core.management.base import BaseCommand

from apps.namads.models import Namad
from utils.utils import redis_cache


class Command(BaseCommand):
    help = "Clear all namads cached data"

    def handle(self, *args, **options):
        namad_ids = Namad.objects.values_list('id', flat=True)
        self.stdout.write(f"Total deleted redis cache count: {redis_cache.delete_many(namad_ids)}")
        self.stdout.write(f"Total namads count: {namad_ids.count()}")
