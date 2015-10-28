from numpy import ma
import six
from ncdjango.geoprocessing.evaluation import Lexer, Parser
from ncdjango.geoprocessing.exceptions import ExecutionError
from ncdjango.geoprocessing.params import NdArrayParameter, StringParameter, RasterDatasetParameter, ListParameter
from ncdjango.geoprocessing.workflow import Task
from netCDF4 import Dataset


class LoadRasterDataset(Task):
    """Loads a raster dataset from a NetCDF file."""

    name = 'raster:load_dataset'
    inputs = [StringParameter('path', required=True)]
    outputs = [RasterDatasetParameter('dataset_out')]

    def execute(self, path):
        return Dataset(path, 'r')


class ArrayFromDataset(Task):
    """Reads a variable from a raster dataset into an array."""

    name = 'raster:array_from_dataset'
    inputs = [RasterDatasetParameter('dataset', required=True), StringParameter('variable', required=True)]
    outputs = [NdArrayParameter('array_out')]

    def execute(self, dataset, variable):
        return dataset[variable][:]


class ExpressionMixin(object):
    """A mixin class to handle expression parsing and error handling."""

    def get_expression_names(self, expression):
        try:
            return list(Lexer().get_names(expression))
        except SyntaxError as e:
            raise ExecutionError('The expression is invalid ({0}): {1}'.format(str(e), expression), self)

    def evaluate_expression(self, expression, context={}):
        try:
            return Parser().evaluate(expression, context=context)
        except (SyntaxError, NameError) as e:
            raise ExecutionError(
                'The expression is invalid ({0}): {1}\nContext: {2}'.format(str(e), expression, str(context)),
                self
            )


class SingleArrayExpressionBase(ExpressionMixin, Task):
    """Base class for tasks with a single array and expression as inputs."""

    inputs = [NdArrayParameter('array_in', required=True), StringParameter('expression', required=True)]
    outputs = [NdArrayParameter('array_out')]

    def get_context(self, arr, expr):
        """
        Returns a context dictionary for use in evaluating the expression.

        :param arr: The input array.
        :param expr: The input expression.
        """

        expression_names = self.get_expression_names(expr)

        if len(expression_names) > 1:
            raise ValueError('The expression must not have more than one variable (the array).')

        return {expression_names[0]: arr}


class MaskByExpression(SingleArrayExpressionBase):
    """Applies a mask to an array based on an expression."""

    name = 'raster:mask_by_expression'

    def execute(self, array_in, expression):
        """Creates and returns a masked view of the input array."""

        context = self.get_context(array_in, expression)
        return ma.masked_where(self.evaluate_expression(expression, context), array_in)


class ApplyExpression(SingleArrayExpressionBase):
    """Applies an expression to an array and returns a new array of the results."""

    name = 'raster:apply_expression'

    def execute(self, array_in, expression):
        """Returns a new array, resulting from applying the expression to the input array."""

        context = self.get_context(array_in, expression)
        return self.evaluate_expression(expression, context)


class MapByExpression(SingleArrayExpressionBase):
    """Applies a given expression to a list of arrays, returning a list with new arrays."""

    name = 'raster:map_by_expression'
    inputs = [
        ListParameter(NdArrayParameter(''), 'arrays_in', required=True),
        StringParameter('expression', required=True)
    ]
    outputs = [ListParameter(NdArrayParameter(''), 'arrays_out')]

    def execute(self, arrays_in, expression):
        return [self.evaluate_expression(expression, self.get_context(a, expression)) for a in arrays_in]


class ReduceByExpression(ExpressionMixin, Task):
    """Iteratively reduces a list of arrays using an expression."""

    name = 'raster:reduce_by_expression'
    inputs = [
        ListParameter(NdArrayParameter(''), 'arrays_in', required=True),
        StringParameter('expression', required=True),
        NdArrayParameter('initial_array', required=False)
    ]
    outputs = [NdArrayParameter('array_out')]

    def execute(self, arrays_in, expression, initial_array=None):
        expression_names = self.get_expression_names(expression)

        if len(expression_names) != 2:
            raise ValueError("The expression must have exactly two variables.")

        def reduce_fn(x, y):
            context = {
                expression_names[0]: x,
                expression_names[1]: y
            }
            return self.evaluate_expression(expression, context)

        args = [reduce_fn, arrays_in]
        if initial_array is not None:
            args.append(initial_array)

        return six.moves.reduce(*args)
