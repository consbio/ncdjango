from django.urls import re_path, include

from ncdjango.interfaces.arcgis.urls import ARCGIS_BASE_URL
from ncdjango.interfaces.arcgis.views import (
    MapServiceDetailView,
    IdentifyView,
    LayerListView,
    LayerDetailView,
)
from .views import GetImageView, LegendView


urlpatterns = [
    re_path(
        r"^{}services/(?P<service_name>[\w\-/]+)/MapServer/?".format(ARCGIS_BASE_URL),
        include(
            [
                re_path(
                    r"^$", MapServiceDetailView.as_view(), name="nc_arcgis_mapservice"
                ),
                re_path(
                    r"^export/?$", GetImageView.as_view(), name="nc_arcgis_get_image"
                ),
                re_path(
                    r"^identify/?$", IdentifyView.as_view(), name="nc_arcgis_identify"
                ),
                re_path(
                    r"^layers/?$", LayerListView.as_view(), name="nc_arcgis_layer_list"
                ),
                re_path(
                    r"^layers/(?P<layer_index>[0-9]+)/?$",
                    LayerDetailView.as_view(),
                    name="nc_arcgis_layer_detail",
                ),
                re_path(r"^legend/?$", LegendView.as_view(), name="nc_arcgis_legend"),
            ]
        ),
    )
]
