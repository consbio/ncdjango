from django.conf.urls import patterns, url, include
from ncdjango.interfaces.arcgis.urls import ARCGIS_BASE_URL
from ncdjango.interfaces.arcgis.views import MapServiceDetailView, IdentifyView, LayerListView, LayerDetailView
from ncdjango.interfaces.arcgis_extended.views import GetImageView, LegendView


urlpatterns = patterns('',
    url(r'^{}services/(?P<service_name>[\w\-/]+)/MapServer/?'.format(ARCGIS_BASE_URL), include(patterns('',
        url(r'^$', MapServiceDetailView.as_view(), name='nc_arcgis_mapservice'),
        url(r'^export/?$', GetImageView.as_view(), name='nc_arcgis_get_image'),
        url(r'^identify/?$', IdentifyView.as_view(), name='nc_arcgis_identify'),
        url(r'^layers/?$', LayerListView.as_view(), name='nc_arcgis_layer_list'),
        url(r'^layers/(?P<layer_index>[0-9]+)/?$', LayerDetailView.as_view(), name='nc_arcgis_layer_detail'),
        url(r'^legend/?$', LegendView.as_view(), name='nc_arcgis_legend')
    )))
)