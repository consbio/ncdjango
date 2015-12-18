import json
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
import math
import numpy
import pyproj
from shapely.geometry.point import Point
from ncdjango.exceptions import ConfigurationError
from ncdjango.interfaces.data.classify import jenks, quantile, equal
from ncdjango.interfaces.data.forms import PointForm
from ncdjango.utils import project_geometry
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

            return HttpResponse(json.dumps(data), content_type='application/json')
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

            return HttpResponse(json.dumps(data), content_type='application/json')
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
            data['values'] = [
                x for x in
                (int(x) if float(x).is_integer() else float(x) for x in unique_data)
                if not math.isnan(x)
            ]

            return HttpResponse(json.dumps(data), content_type='application/json')
        finally:
            self.close_dataset()


class ValuesAtPointView(DataViewBase):
    """Returns all values (through time) at a given point"""

    form_class = PointForm

    def handle_request(self, request, **kwargs):
        variable = self.get_variable()
        form_params = {'projection': pyproj.Proj(str(variable.projection))}
        form_params.update(kwargs)
        form = self.form_class(form_params)
        if form.is_valid():
            form_data = form.cleaned_data
        else:
            raise ConfigurationError

        point = project_geometry(
            Point(form_data['x'], form_data['y']), form_data['projection'], pyproj.Proj(str(variable.projection))
        )
        data = {'values': []}
        dataset = self.open_dataset(self.service)

        try:
            dataset_variable = dataset.variables[variable.variable]
            dimensions = dataset_variable.dimensions
            shape = [dimensions.index(variable.y_dimension), dimensions.index(variable.x_dimension)]

            if variable.time_dimension:
                shape.append(dimensions.index(variable.time_dimension))

            skip_dimensions = 0
            for i, dimension in enumerate(dimensions):
                if dimension not in (variable.y_dimension, variable.x_dimension, variable.time_dimension):
                    shape.insert(0, i)
                    skip_dimensions += 1

            variable_data = dataset.variables[variable.variable][:].transpose(*shape)
            for __ in range(skip_dimensions):
                variable_data = variable_data[0]

            cell_size = (
                float(variable.full_extent.width) / variable_data.shape[1],
                float(variable.full_extent.height) / variable_data.shape[0]
            )

            cell_index = [
                int(float(point.x-variable.full_extent.xmin) / cell_size[0]),
                int(float(point.y-variable.full_extent.ymin) / cell_size[1])
            ]

            if not self.is_y_increasing(variable):
                cell_index[1] = variable_data.shape[0] - cell_index[1] - 1

            if variable_data.shape[1] > cell_index[0] >= 0 and variable_data.shape[0] > cell_index[1] >= 0:
                variable_data = variable_data[cell_index[1], cell_index[0]]
                data['values'] = [
                    None if math.isnan(x) else x for x in
                    (int(x) if float(x).is_integer() else float(x) for x in variable_data)
                ]

            return HttpResponse(json.dumps(data), content_type='application/json')
        finally:
            self.close_dataset()
