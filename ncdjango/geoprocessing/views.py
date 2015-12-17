from rest_framework import viewsets

from ncdjango.models import ProcessingJob
from ncdjango.geoprocessing.serializers import ProcessingJobSerializer


class ProcessingJobsViewset(viewsets.ModelViewSet):
    queryset = ProcessingJob.objects.all()
    serializer_class = ProcessingJobSerializer
    lookup_field = 'uuid'
