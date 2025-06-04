from importlib import import_module

from django.conf import settings
from django.urls import include, re_path
from django.core.exceptions import ImproperlyConfigured
from tastypie.api import Api

from .api import TemporaryFileResource, ServiceResource, VariableResource
from .views import (
    TemporaryFileUploadFormView,
    TemporaryFileUploadUrlView,
    TemporaryFileDownloadView,
)

DEFAULT_INSTALLED_INTERFACES = (
    "ncdjango.interfaces.data",
    "ncdjango.interfaces.arcgis_extended",
    "ncdjango.interfaces.arcgis",
)
INSTALLED_INTERFACES = getattr(
    settings, "NC_INSTALLED_INTERFACES", DEFAULT_INSTALLED_INTERFACES
)


app_name = "ncdjango"
urlpatterns = []

for interface in INSTALLED_INTERFACES:
    try:
        module = import_module("{}.urls".format(interface))
    except (ImportError, TypeError):
        raise ImproperlyConfigured(
            "Can't find ncdjango interface: {}".format(interface)
        )

    try:
        urlpatterns += getattr(module, "urlpatterns")
    except AttributeError:
        raise ImproperlyConfigured("Interface URLs file has no urlpatterns")

api = Api(api_name="admin")
api.register(TemporaryFileResource())
api.register(ServiceResource())
api.register(VariableResource())

urlpatterns += [
    re_path(
        r"^api/admin/upload-by-url/$",
        TemporaryFileUploadUrlView.as_view(),
        name="nc_admin_upload_by_url",
    ),
    re_path(
        r"^api/admin/upload/$",
        TemporaryFileUploadFormView.as_view(),
        name="nc_admin_upload",
    ),
    re_path(
        r"^api/admin/download/(?P<uuid>[0-9\w\-]+)/$",
        TemporaryFileDownloadView.as_view(),
        name="nc_admin_download",
    ),
    re_path(r"^api/", include(api.urls)),
    re_path(r"^geoprocessing/", include("ncdjango.geoprocessing.urls")),
]
