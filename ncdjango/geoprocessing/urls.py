from django.conf.urls import url, include
from rest_framework.routers import SimpleRouter

from ncdjango.geoprocessing.views import ProcessingJobsViewset

router = SimpleRouter()
router.register(r'jobs', ProcessingJobsViewset)

urlpatterns = [
    url(r'^rest/', include(router.urls, namespace='geoprocesing'))
]
