from django.urls import re_path, include
from rest_framework.routers import SimpleRouter

from .views import ProcessingJobsViewset


router = SimpleRouter()
router.register(r"jobs", ProcessingJobsViewset)

urlpatterns = [
    re_path(
        r"^rest/", include((router.urls, "geoprocessing"), namespace="geoprocessing")
    )
]
