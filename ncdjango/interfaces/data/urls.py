from django.conf.urls import patterns, url, include
from ncdjango.interfaces.data.views import RangeView, ClassifyView, UniqueValuesView, ValuesAtPointView


urlpatterns = patterns('',
    url(r'^data/services/(?P<service_name>[\w\-\./]+)/(?P<variable_name>[\w\-\./]+)/info/', include(patterns('',
        url(r'^range/$', RangeView.as_view(), name='data_range'),
        url(r'^classify/$', ClassifyView.as_view(), name='data_classify'),
        url(r'^unique/$', UniqueValuesView.as_view(), name='data_unique'),
        url(r'^values-at-point/$', ValuesAtPointView.as_view(), name='data_values_at_point')
    )))
)