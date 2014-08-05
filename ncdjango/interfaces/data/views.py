import json
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
import numpy
from ncdjango.exceptions import ConfigurationError
from ncdjango.interfaces.data.classify import jenks, quantile, equal
from ncdjango.views import ServiceView, NetCdfDatasetMixin

MAX_UNIQUE_VALUES = getattr(settings, 'NC_MAX_UNIQUE_VALUES', 100)

CLASSIFY_METHODS = {
    'jenks': jenks,
    'quantile': quantile,
    'equal': equal
}


class DataViewBase(NetCdfDatasetMixin, ServiceView):
    def get_service_name(self, request, *args, **kwargs):
        return kwargs['service_name']

    def get_variable(self):
        return get_object_or_404(self.service.variable_set.all(), name=self.kwargs.get('variable_name'))


class RangeView(DataViewBase):
    """Returns value ranges for a variable in a service"""

    def handle_request(self, request, **kwargs):
        variable = self.get_variable()
        dataset = self.open_dataset(self.service)

        try:
            variable_data = dataset.variables[variable.variable][:]
            min_value = float(numpy.min(variable_data))
            max_value = float(numpy.max(variable_data))

            data = {
                'min': int(min_value) if min_value.is_integer() else min_value,
                'max': int(max_value) if max_value.is_integer() else max_value
            }

            return HttpResponse(json.dumps(data))
        finally:
            self.close_dataset()


class ClassifyView(DataViewBase):
    """Generates classbreaks for a variable in a service"""

    def handle_request(self, request, **kwargs):
        if kwargs.get('method', '').lower() in ('jenks', 'quantile', 'equal'):
            method = kwargs['method'].lower()
        else:
            raise ConfigurationError('Invalid method')

        try:
            num_breaks = int(kwargs.get('breaks'))
        except (ValueError, TypeError):
            raise ConfigurationError('Invalid number of breaks')

        variable = self.get_variable()
        dataset = self.open_dataset(self.service)

        try:
            variable_data = dataset.variables[variable.variable][:].ravel()
            min_value = float(numpy.min(variable_data))
            classes = CLASSIFY_METHODS[method](variable_data, num_breaks)
            classes = [int(x) if float(x).is_integer() else x for x in classes]

            data = {
                'breaks': classes,
                'min': int(min_value) if min_value.is_integer() else min_value
            }

            return HttpResponse(json.dumps(data))
        finally:
            self.close_dataset()


class UniqueValuesView(DataViewBase):
    """Returns unique values for a variable"""

    def handle_request(self, request, **kwargs):
        variable = self.get_variable()
        dataset = self.open_dataset(self.service)

        try:
            unique_data = numpy.unique(dataset.variables[variable.variable][:])
            data = {
                'num_values': len(unique_data)
            }
            if len(unique_data) > MAX_UNIQUE_VALUES:
                unique_data = unique_data[:MAX_UNIQUE_VALUES]
            data['values'] = [int(x) if float(x).is_integer() else float(x) for x in unique_data]

            return HttpResponse(json.dumps(data))
        finally:
            self.close_dataset()