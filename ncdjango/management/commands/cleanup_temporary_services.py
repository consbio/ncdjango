from django.core.management import BaseCommand

from ncdjango.geoprocessing.celery_tasks import cleanup_temporary_services


class Command(BaseCommand):
    help = 'Delete expired, temporary services created from geoprocessing results.'

    def handle(self, *args, **options):
        cleanup_temporary_services()
