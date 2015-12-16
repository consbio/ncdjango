from rest_framework import viewsets
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import CreateModelMixin

from ncdjango.models import ProcessingJob
from ncdjango.geoprocessing.serializers import ProcessingJobSerializer


# class ProcessingJobsViewset(CreateModelMixin, GenericAPIView):
class ProcessingJobsViewset(viewsets.ModelViewSet):
    queryset = ProcessingJob.objects.all()
    serializer_class = ProcessingJobSerializer

