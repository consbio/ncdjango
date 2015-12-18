from rest_framework import viewsets, mixins

from ncdjango.models import ProcessingJob
from ncdjango.geoprocessing.serializers import ProcessingJobSerializer


class ProcessingJobsViewset(mixins.CreateModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = ProcessingJob.objects.all()
    serializer_class = ProcessingJobSerializer
    lookup_field = 'uuid'
