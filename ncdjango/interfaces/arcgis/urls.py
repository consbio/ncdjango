from django.conf import settings
from django.conf.urls import patterns, url, include
from ncdjango.interfaces.arcgis.views import GetImageView, MapServiceListView, MapServiceDetailView, LayerDetailView, \
    LegendView
from ncdjango.interfaces.arcgis.views import LayerListView, IdentifyView

ARCGIS_BASE_URL = getattr(settings, 'NC_ARCGIS_BASE_URL', 'arcgis/rest/')


urlpatterns = patterns('',
    url(r'^{}services/?$'.format(ARCGIS_BASE_URL), MapServiceListView.as_view(), name='nc_arcgis_catalog'),
    url(r'^{}services/(?P<service_name>[\w\-/]+)/MapServer/?'.format(ARCGIS_BASE_URL), include(patterns('',
        url(r'^$', MapServiceDetailView.as_view(), name='nc_arcgis_mapservice'),
        url(r'^export/?$', GetImageView.as_view(), name='nc_arcgis_get_image'),
        url(r'^identify/?$', IdentifyView.as_view(), name='nc_arcgis_identify'),
        url(r'^layers/?$', LayerListView.as_view(), name='nc_arcgis_layer_list'),
        url(r'^layers/(?P<layer_index>[0-9]+)/?$', LayerDetailView.as_view(), name='nc_arcgis_layer_detail'),
        url(r'^legend/?$', LegendView.as_view(), name='nc_arcgis_legend')
    )))
)