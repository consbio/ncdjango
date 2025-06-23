from django.urls import re_path, include

from .views import RangeView, ClassifyView, UniqueValuesView, ValuesAtPointView


urlpatterns = [
    re_path(
        r"^data/services/(?P<service_name>[\w\-\./]+)/(?P<variable_name>[\w\-\./]+)/info/",
        include(
            [
                re_path(r"^range/$", RangeView.as_view(), name="data_range"),
                re_path(r"^classify/$", ClassifyView.as_view(), name="data_classify"),
                re_path(r"^unique/$", UniqueValuesView.as_view(), name="data_unique"),
                re_path(
                    r"^values-at-point/$",
                    ValuesAtPointView.as_view(),
                    name="data_values_at_point",
                ),
            ]
        ),
    )
]
