from django.conf.urls import patterns, url, include
from ncdjango.interfaces.arcgis.urls import ARCGIS_BASE_URL
from ncdjango.interfaces.arcgis_extended.views import GetImageView, LegendView


urlpatterns = patterns('',
    url(r'^{}services/(?P<service_name>[\w\-/]+)/MapServer/'.format(ARCGIS_BASE_URL), include(patterns('',
        url(r'^export/$', GetImageView.as_view(), name='nc_arcgis_get_image'),
        url(r'^legend/$', LegendView.as_view(), name='nc_arcgis_legend')
    )))
)