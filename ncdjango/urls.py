from django.conf import settings
from django.conf.urls import patterns, include, url
from django.core.exceptions import ImproperlyConfigured
from django.utils.importlib import import_module
from tastypie.api import Api
from ncdjango.api import TemporaryFileResource, ServiceResource, VariableResource
from ncdjango.views import TemporaryFileUploadFormView, TemporaryFileUploadUrlView, TemporaryFileDownloadView

DEFAULT_INSTALLED_INTERFACES = (
    'ncdjango.interfaces.data',
    'ncdjango.interfaces.arcgis_extended',
    'ncdjango.interfaces.arcgis'
)
INSTALLED_INTERFACES = getattr(settings, 'NC_INSTALLED_INTERFACES', DEFAULT_INSTALLED_INTERFACES)


urlpatterns = patterns('')

for interface in INSTALLED_INTERFACES:
    try:
        module = import_module("{}.urls".format(interface))
    except (ImportError, TypeError):
        raise ImproperlyConfigured("Can't find ncdjango interface: {}".format(interface))

    try:
        urlpatterns += getattr(module, 'urlpatterns')
    except AttributeError:
        raise ImproperlyConfigured("Interface URLs file has no urlpatterns")

api = Api(api_name="admin")
api.register(TemporaryFileResource())
api.register(ServiceResource())
api.register(VariableResource())

urlpatterns += patterns('',
    url(r'^api/admin/upload-by-url/$', TemporaryFileUploadUrlView.as_view(), name='nc_admin_upload_by_url'),
    url(r'^api/admin/upload/$', TemporaryFileUploadFormView.as_view(), name='nc_admin_upload'),
    url(r'^api/admin/download/(?P<uuid>[0-9\w\-]+)/$', TemporaryFileDownloadView.as_view(), name='nc_admin_download'),
    url(r'^api/', include(api.urls)),
    url(r'^geoprocessing/', include('ncdjango.geoprocessing.urls'))
)
