from django.conf import settings
from django.conf.urls import patterns, url, include
from ncdjango.interfaces.arcgis.views import GetImageView, CatalogView, MapServiceView

ARCGIS_BASE_URL = getattr(settings, 'NC_ARCGIS_BASE_URL', 'arcgis/rest/')


urlpatterns = patterns('',
    url(r'^{}services/$'.format(ARCGIS_BASE_URL), CatalogView.as_view(), name='nc_arcgis_catalog'),
    url(r'^{}services/(?P<service_name>[\w\-/]+)/MapServer/'.format(ARCGIS_BASE_URL), include(patterns('',
        url(r'^$', MapServiceView.as_view(), name='nc_arcgis_mapservice'),
        url(r'^export/$', GetImageView.as_view(), name='nc_arcgis_get_image')
    )))
)