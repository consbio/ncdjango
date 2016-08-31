import numbers
from types import GeneratorType

from django.core.exceptions import ObjectDoesNotExist
from fiona.collection import Collection
import netCDF4
import numpy
from shapely.geometry.base import BaseGeometry
import six

from ncdjango.geoprocessing.data import Raster
from ncdjango.models import Service
from ncdjango.views import NetCdfDatasetMixin


class ParameterNotValidError(ValueError):
    """Indicates that a value is not valid for the parameter type"""


class ParameterBase(type):
    """Parameter metaclass, used to register parameter classes for lookup by name."""

    _parameters_by_id = {}

    def __new__(mcs, name, bases, attrs):
        new_class = super(ParameterBase, mcs).__new__(mcs, name, bases, attrs)

        name = getattr(new_class, 'id', None)
        if name:
            mcs._parameters_by_id[new_class.id] = new_class

        setattr(new_class, '_parameters_by_id', mcs._parameters_by_id)

        return new_class


class Parameter(six.with_metaclass(ParameterBase)):
    """
    Base parameter (input, output, or uniform) class for a task or workflow. Extended to implement specific parameter
    types.
    """

    id = None  # A unique name for this parameter, used for serialization

    def __init__(self, name, required=True):
        """
        :param name: The parameter name. This will be used as a keyword argument to the task's `execute()` method.
        :param required: When True, input validation will fail if no value is provided.
        """

        self.name = name
        self.required = required

    @classmethod
    def by_id(cls, param_id):
        return cls._parameters_by_id.get(param_id)

    def clean(self, value):
        """Cleans and returns the given value, or raises a ParameterNotValidError exception"""

        return value

    def serialize_args(self):
        """Returns (args, kwargs) to be used when deserializing this parameter."""

        return (self.name,), {'required': True}

    @staticmethod
    def deserialize_args(args, kwargs):
        """Returns deserialized forms of (args, kwargs) to be used when re-constructing this parameter."""

        return args, kwargs


class ParameterCollection(object):
    """Manages a collection of parameter types and values"""

    def __init__(self, parameters):
        """
        :param parameters: A list of `Parameter` objects
        """

        self.parameters = parameters
        self.by_name = {p.name: p for p in self.parameters}
        self.values = {}

    def __setitem__(self, key, value):
        self.values[key] = self.by_name[key].clean(value)

    def __getitem__(self, item):
        return self.values.get(item)

    @property
    def is_complete(self):
        """Do all required parameters have values?"""

        return all(p.name in self.values for p in self.parameters if p.required)

    def format_args(self):
        """Returns dictionary containing values for all named parameters."""

        return self.values


class AnyParameter(Parameter):
    """Accepts any value"""

    id = 'any'


class MultiParameter(Parameter):
    """
    Accepts a value matching one of several defined types.
    E.g., `MultiParameter([StringParameter(''), DictParameter('')])` will accept both strings and dictionaries.
    """

    id = 'multiple'

    def __init__(self, types, *args, **kwargs):
        """
        :param types: A list of `Parameter` instances to accept.
        """

        super(MultiParameter, self).__init__(*args, **kwargs)

        self.types = types

    def clean(self, value):
        """Cleans and returns the given value, or raises a ParameterNotValidError exception"""

        for parameter_obj in self.types:
            try:
                return parameter_obj.clean(value)
            except ParameterNotValidError:
                continue

        raise ParameterNotValidError

    def serialize_args(self):
        """Returns (args, kwargs) to be used when deserializing this parameter."""

        args, kwargs = super(MultiParameter, self).serialize_args()
        args.insert(0, [[t.id, t.serialize_args()] for t in self.types])

        return args, kwargs

    @staticmethod
    def deserialize_args(args, kwargs):
        args, kwargs = super(MultiParameter, MultiParameter).deserialize_args(args[1:], kwargs)

        types = []
        for type_id, type_args in args[0]:
            type_cls = Parameter.by_id(type_id)
            type_args, type_kwargs = type_cls.deserialize_args(*type_args)
            types.append(type_cls(*type_args, **type_kwargs))

        args.insert(0, types)

        return args, kwargs


class ListParameter(Parameter):
    """
    Accepts a list of a given parameter type. This parameter will accept either a list-type object (list, tuple, set)
    or a generator object. If it receives a generator object, `clean()` will also return a generator object. Otherwise,
    it will return a list.
    """

    id = 'list'

    def __init__(self, param_type, *args, **kwargs):
        """
        :param param_type: A `Parameter` instance.
        """

        super(ListParameter, self).__init__(*args, **kwargs)

        self.param_type = param_type

    def clean(self, value):
        """Cleans and returns the given value, or raises a ParameterNotValidError exception"""

        if not isinstance(value, (list, tuple, set, GeneratorType)):
            value = [value]

        gen = (self.param_type.clean(x) for x in value)

        if isinstance(value, GeneratorType):
            return gen
        else:
            return list(gen)

    def serialize_args(self):
        """Returns (args, kwargs) to be used when deserializing this parameter."""

        args, kwargs = super(ListParameter, self).serialize_args()
        args.insert(0, [self.param_type.id, self.param_type.serialize_args()])

    @staticmethod
    def deserialize_args(args, kwargs):
        type_id, type_args = args[0]
        args, kwargs = super(ListParameter, ListParameter).deserialize_args(args[1:], kwargs)

        type_cls = Parameter.by_id(type_id)
        type_args, type_kwargs = type_cls.deserialize_args(*type_args)
        args.insert(0, type_cls(*type_args, **type_kwargs))

        return args, kwargs


class StringParameter(Parameter):
    """Accepts a string. Will convert numbers to string."""

    id = 'string'

    def clean(self, value):
        """Cleans and returns the given value, or raises a ParameterNotValidError exception"""

        if isinstance(value, six.string_types):
            return value
        elif isinstance(value, numbers.Number):
            return str(value)

        raise ParameterNotValidError


class NumberParameter(Parameter):
    """Accepts a number. Will convert numeric strings."""

    id = 'number'

    def clean(self, value):
        """Cleans and returns the given value, or raises a ParameterNotValidError exception"""

        if isinstance(value, numbers.Number):
            return value
        elif isinstance(value, six.string_types):
            try:
                value = float(value)
                return int(value) if value.is_integer() else value
            except ValueError:
                raise ParameterNotValidError

        raise ParameterNotValidError


class IntParameter(NumberParameter):
    """Accepts an integer value. Will convert strings, other numbers."""

    id = 'int'

    def clean(self, value):
        """Cleans and returns the given value, or raises a ParameterNotValidError exception"""

        return int(super(IntParameter, self).clean(value))


class FloatParameter(NumberParameter):
    """Accepts a float value. Will convert strings, other numbers."""

    id = 'float'

    def clean(self, value):
        """Cleans and returns the given value, or raises a ParameterNotValidError exception"""

        return float(super(FloatParameter, self).clean(value))


class BooleanParameter(Parameter):
    """Accepts a boolean value. Will cast other objects to bool. Will treat a string, "false" as False."""

    id = 'bool'

    def clean(self, value):
        """Cleans and returns the given value, or raises a ParameterNotValidError exception"""

        if isinstance(value, six.string_types) and value.lower() == 'false':
            return False

        return bool(value)


class DictParameter(Parameter):
    """Accepts a dictionary"""

    id = 'dict'

    def clean(self, value):
        """Cleans and returns the given value, or raises a ParameterNotValidError exception"""

        if isinstance(value, (dict, list)):
            return value

        raise ParameterNotValidError


class NdArrayParameter(Parameter):
    """Accepts a numpy array or Python list"""

    id = 'array'

    def clean(self, value):
        """Cleans and returns the given value, or raises a ParameterNotValidError exception"""

        if isinstance(value, numpy.ndarray):
            return value
        elif isinstance(value, (list, tuple)):
            return numpy.array(value)

        raise ParameterNotValidError


class RasterParameter(Parameter):
    """Accepts a `Raster` instance"""

    id = 'raster'

    def clean(self, value):
        """Cleans and returns the given value, or raises a ParameterNotValidError exception"""

        if isinstance(value, Raster):
            return value

        raise ParameterNotValidError


class FeatureParameter(Parameter):
    """Accepts a single feature (as a Shapely geometry object)"""

    id = 'feature'

    # Todo: geometry type checking

    def clean(self, value):
        """Cleans and returns the given value, or raises a ParameterNotValidError exception"""

        if isinstance(value, BaseGeometry):
            return value

        raise ParameterNotValidError


class FeatureCollectionParameter(FeatureParameter):
    """Accepts a list of features (as Shapely geometry objects)"""

    id = 'feature_collection'

    def clean(self, value):
        """Cleans and returns the given value, or raises a ParameterNotValidError exception"""

        if isinstance(value, (list, tuple)):
            return [super(FeatureCollectionParameter, self).clean(x) for x in value]

        raise ParameterNotValidError


class RasterDatasetParameter(Parameter):
    """Accepts a NetCDF `Dataset` object"""

    id = 'raster_dataset'

    def clean(self, value):
        """Cleans and returns the given value, or raises a ParameterNotValidError exception"""

        if isinstance(value, netCDF4.Dataset):
            return value

        raise ParameterNotValidError


class FeatureDatasetParameter(Parameter):
    """Accepts a Fiona `Collection` object"""

    id = 'feature_dataset'

    def clean(self, value):
        """Cleans and returns the given value, or raises a ParameterNotValidError exception"""

        if isinstance(value, Collection):
            return value

        raise ParameterNotValidError


class RegisteredDatasetParameter(NetCdfDatasetMixin, Parameter):
    """Used by the web API to map registered datasets to inputs"""

    def __init__(self, *args, **kwargs):
        self.service = None

        super(RegisteredDatasetParameter, self).__init__(*args, **kwargs)

    def clean(self, value):
        """Cleans and returns the given value, or raises a ParameterNotValidError exception"""

        if not isinstance(value, six.string_types):
            raise ParameterNotValidError

        try:
            source, value = value.split('://', 1)
        except ValueError:
            raise ParameterNotValidError

        if source == 'service':
            if ':' in value:
                service_name, variable_name = value.split(':', 1)
            else:
                service_name = value
                variable_name = None

            try:
                self.service = Service.objects.get(name=service_name)
            except ObjectDoesNotExist:
                raise ParameterNotValidError("Service '{}' not found".format(service_name))

            if variable_name:
                try:
                    variable = self.service.variable_set.all().get(variable=variable_name)
                except ObjectDoesNotExist:
                    raise ParameterNotValidError("Variable '{}' not found".format(variable_name))

                data = self.get_grid_for_variable(variable)
                return Raster(data, variable.full_extent, 1, 0, self.is_y_increasing(variable))
            else:
                return self.dataset
        else:
            raise ParameterNotValidError('Invalid source: {}'.format(source))
