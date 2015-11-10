import json
import os
from netCDF4 import Dataset
import numpy
from numpy.ma import masked_array
import pytest
from rasterio.dtypes import is_ndarray
from ncdjango.geoprocessing.evaluation import Lexer, Parser
from ncdjango.geoprocessing.exceptions import ExecutionError
from ncdjango.geoprocessing.params import StringParameter, IntParameter
from ncdjango.geoprocessing.tasks.raster import MaskByExpression, ApplyExpression, LoadRasterDataset, ArrayFromDataset
from ncdjango.geoprocessing.tasks.raster import MapByExpression, ReduceByExpression
from ncdjango.geoprocessing.workflow import Task, Workflow

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'test_data')


@pytest.fixture
def simple_task():
    class SimpleTask(Task):
        inputs = [
            StringParameter('str_in', required=True)
        ]
        outputs = [
            StringParameter('str_out')
        ]

        def execute(self, str_in):
            return str_in

    return SimpleTask()


@pytest.fixture
def simple_workflow():
    class SumTask(Task):
        name = 'test:sum'

        inputs = [
            IntParameter('int1', required=True),
            IntParameter('int2', required=True)
        ]

        outputs = [
            IntParameter('sum')
        ]

        def execute(self, int1, int2):
            return int1 + int2

    workflow = Workflow()

    workflow.inputs = [
        IntParameter('int1', required=True),
        IntParameter('int2', required=True),
        IntParameter('int3', required=True)
    ]
    workflow.outputs = [
        IntParameter('total')
    ]

    workflow.add_node('sum_1', SumTask(), {'int1': ('input', 'int1'), 'int2': ('input', 'int2')})
    workflow.add_node('sum_2', SumTask(), {'int1': ('input', 'int3'), 'int2': ('dependency', ('sum_1', 'sum'))})
    workflow.map_output('sum_2', 'sum', 'total')

    return workflow


class TestTask(object):
    def test_simple_task(self, simple_task):
        assert simple_task(str_in='Test')['str_out'] == 'Test'

    def test_simple_task_exceptions(self, simple_task):
        with pytest.raises(TypeError) as excinfo:
            simple_task()
        assert 'Missing required' in str(excinfo.value)
        assert 'str_in' in str(excinfo.value)

        with pytest.raises(TypeError) as excinfo:
            simple_task(str_in='Test', foo='bar')
        assert 'Unrecognized' in str(excinfo.value)
        assert 'foo' in str(excinfo.value)

    def test_simple_workflow_execution(self, simple_workflow):
        result = simple_workflow(int1=1, int2=2, int3=3)
        assert result['total'] == 6

    def test_simple_workflow_serialization(self, simple_workflow):
        expected_output = {
            "inputs": [
                {
                    "name": "int1",
                    "type": "int"
                },
                {
                    "name": "int2",
                    "type": "int"
                },
                {
                    "name": "int3",
                    "type": "int"
                }
            ],
            "outputs": [
                {
                    "name": "total",
                    "node": [
                        "sum_2",
                        "sum"
                    ]
                }
            ],
            "meta": {
                "name": None,
                "description": None
            },
            "workflow": [
                {
                    "inputs": {
                        "int2": {
                            "input": "int2",
                            "source": "input"
                        },
                        "int1": {
                            "input": "int1",
                            "source": "input"
                        }
                    },
                    "id": "sum_1",
                    "task": "test:sum"
                },
                {
                    "inputs": {
                        "int2": {
                            "source": "dependency",
                            "node": [
                                "sum_1",
                                "sum"
                            ]
                        },
                        "int1": {
                            "input": "int3",
                            "source": "input"
                        }
                    },
                    "id": "sum_2",
                    "task": "test:sum"
                }
            ]
        }

        assert json.loads(simple_workflow.to_json()) == expected_output

    def test_simple_workflow_deserialization(self, simple_workflow):
        serialized = simple_workflow.to_json()
        workflow = Workflow.from_json(serialized)

        assert json.loads(workflow.to_json()) == json.loads(serialized)

    def test_map_reduce_workflow(self):
        with open(os.path.join(TEST_DATA_DIR, 'map_reduce_workflow.json'), 'r') as f:
            workflow = Workflow.from_json(f.read())

        arr_1 = numpy.arange(10)
        arr_2 = numpy.arange(10, 20)
        arr_3 = numpy.arange(20, 30)
        expected = sum([x / numpy.max(x) for x in [arr_1, arr_2, arr_3]])
        result = workflow(arrays_in=[arr_1, arr_2, arr_3])
        array_out = result['array_out']

        assert is_ndarray(array_out)
        assert (array_out == expected).all()


class TestRasterTasks(object):
    def test_mask_by_expression(self):
        task = MaskByExpression()
        arr = numpy.concatenate((numpy.arange(25), numpy.arange(100, 150)))
        expr = 'abs(mean(x) - x) > std(x)'  # Mask out all values more than 1 std away from the mean
        result = task(array_in=arr, expression=expr)

        assert isinstance(result['array_out'], masked_array)
        assert (result['array_out'].mask == (numpy.absolute(numpy.mean(arr) - arr) > numpy.std(arr))).all()

    def test_apply_expression(self):
        task = ApplyExpression()
        arr = numpy.array([1, 2, 3])
        expr = '(x ** 2) / 2'
        result = task(array_in=arr, expression=expr)

        assert is_ndarray(result['array_out'])
        assert (result['array_out'] == numpy.array([.5, 2, 4.5])).all()

    def test_load_raster_dataset(self):
        task = LoadRasterDataset()
        result = task(path=os.path.join(TEST_DATA_DIR, 'simple_grid_2d.nc'))
        dataset = result['dataset_out']

        assert set(dataset.dimensions.keys()) == {'lat', 'lon'}
        assert dataset['value'].dimensions == ('lon', 'lat')
        assert dataset['value'][:].shape == (10, 10)

    def test_array_from_dataset(self):
        task = ArrayFromDataset()
        dataset = Dataset(os.path.join(TEST_DATA_DIR, 'simple_grid_2d.nc'))
        result = task(dataset=dataset, variable='value')
        arr = result['array_out']

        assert is_ndarray(arr)
        assert arr.shape == (10, 10)
        assert (arr == numpy.reshape(numpy.arange(100), (10, 10))).all()

    def test_map_by_expression(self):
        task = MapByExpression()
        arr_1 = numpy.arange(10)
        arr_2 = numpy.arange(10, 20)
        expr = 'x * 2'
        result = task(arrays_in=[arr_1, arr_2], expression=expr)
        arrays_out = result['arrays_out']

        assert all(is_ndarray(x) for x in arrays_out)
        assert len(arrays_out) == 2
        assert (arrays_out[0] == arr_1 * 2).all()
        assert (arrays_out[1] == arr_2 * 2).all()

    def test_reduce_by_expression(self):
        task = ReduceByExpression()
        arr_1 = numpy.arange(10)
        arr_2 = numpy.arange(10, 20)
        arr_3 = numpy.arange(20, 30)
        expected = arr_1 + arr_2 + arr_3
        expr = 'x + y'
        result = task(arrays_in=[arr_1, arr_2, arr_3], expression=expr)
        array_out = result['array_out']

        assert is_ndarray(array_out)
        assert (array_out == expected).all()

        initial = numpy.arange(10)
        expected += initial
        result = task(arrays_in=[arr_1, arr_2, arr_3], expression=expr, initial_array=initial)
        array_out = result['array_out']

        assert is_ndarray(array_out)
        assert (array_out == expected).all()

    def test_expression_errors(self):
        task = ApplyExpression()
        arr = numpy.array([1, 2, 3])

        with pytest.raises(ExecutionError) as excinfo:
            task(array_in=arr, expression='x ; 2')
        assert 'expression is invalid' in str(excinfo.value)

        with pytest.raises(ExecutionError) as excinfo:
            task(array_in=arr, expression='x <> 2')
        assert 'expression is invalid' in str(excinfo.value)

        with pytest.raises(ValueError) as excinfo:
            task(array_in=arr, expression='x + y')
        assert 'exactly one variable' in str(excinfo.value)


class TestEvaluations(object):
    def test_lexer(self):
        l = Lexer()

        assert l.get_names('min(x) + y < 5') == {'x', 'y'}

    def test_arithmetic(self):
        p = Parser()

        assert p.evaluate('1 + 1') == 2
        assert p.evaluate('1 * 1') == 1
        assert p.evaluate('1 + 2 * 3') == 7
        assert p.evaluate('3 * 2 + 1') == 7
        assert p.evaluate('(1 + 2) * 3') == 9
        assert p.evaluate('3 * (2 + 1)') == 9
        assert p.evaluate('1 + 7 * 6 / 3') == 15
        assert p.evaluate('(1 + 7) * 6 / 3') == 16
        assert p.evaluate('1 / 2') == 0.5  # Uses true division for ints, as in Python 3
        assert p.evaluate('1 + 2 ** 4') == 17
        assert p.evaluate('(1 + 2) ** 4') == 81
        assert p.evaluate('10 % 5') == 0

    def test_variables(self):
        p = Parser()
        context = {'x': 5, 'y': 2}

        assert p.evaluate('x', context=context) == 5
        assert p.evaluate('y', context=context) == 2
        assert p.evaluate('x + y', context=context) == 7
        assert p.evaluate('x > y', context=context) == True
        assert p.evaluate('(x + 1) * y', context=context) == 12
        assert p.evaluate('x == 5 and y == 2', context=context) == True

    def test_conditionals(self):
        p = Parser()

        assert p.evaluate('1 and 1') == 1
        assert p.evaluate('1 and 0') == 0
        assert p.evaluate('1 or 0') == 1
        assert p.evaluate('0 or 1') == 1
        assert p.evaluate('1 and 1 and 1') == 1
        assert p.evaluate('1 and 1 and 0') == 0
        assert p.evaluate('1 and 1 or 0') == 1
        assert p.evaluate('0 and 1 or 1') == 1
        assert p.evaluate('0 and (1 or 1)') == 0
        assert p.evaluate('1 and 1 and 1 or 0') == 1
        assert p.evaluate('0 and 1 and 1 or 1') == 1
        assert p.evaluate('0 and 1 and 1 or 0') == 0

        assert p.evaluate('1 > 2') == False
        assert p.evaluate('1 < 1') == False
        assert p.evaluate('1 < 2') == True
        assert p.evaluate('1 == 1') == True
        assert p.evaluate('1 <= 1') == True
        assert p.evaluate('1 <= 2') == True
        assert p.evaluate('1 >= 1') == True
        assert p.evaluate('1 >= 2') == False
        assert p.evaluate('1 + 1 >= 2') == True
        assert p.evaluate('1 + 1 > 2 - 1') == True
        assert p.evaluate('1 <= 2 and 1 + 1 >= 2') == True
        assert p.evaluate('1 <= 2 - 1 and 1 >= 2 - 1') == True

    def test_string(self):
        p = Parser()

        assert p.evaluate('"test"') == 'test'
        assert p.evaluate("'test'") == 'test'
        assert p.evaluate('"test" == "test"') == True
        assert p.evaluate('"foo" == "bar"') == False

    def test_bool(self):
        p = Parser()

        assert p.evaluate('true') == True
        assert p.evaluate('True') == True
        assert p.evaluate('TRUE') == True
        assert p.evaluate('false') == False
        assert p.evaluate('False') == False
        assert p.evaluate('FALSE') == False
        assert p.evaluate('1 > 2 == False') == True  # Note: this differs from Python's behavior
        assert p.evaluate('(1 > 2) == False') == True

    def test_ndarray(self):
        p = Parser()
        arr = numpy.array([1,2,3])
        context = {'x': arr}

        assert (p.evaluate('x * 2', context=context) == (arr * 2)).all()
        assert (p.evaluate('x <= 2', context=context) == (arr <= 2)).all()

    def test_functions(self):
        p = Parser()
        arr = numpy.concatenate((numpy.arange(25), numpy.arange(100, 150)))
        nd_arr = numpy.reshape(arr, (25, -1))
        context = {'x': arr}
        nd_context = {'x': nd_arr}

        assert p.evaluate('abs(-5)') == 5
        assert p.evaluate('abs(5)') == 5
        assert (p.evaluate('abs(x)', context={'x': numpy.array([-1, -2, 3])}) == numpy.array([1, 2, 3])).all()
        assert p.evaluate('min(x)', context=context) == 0
        assert (p.evaluate('min(x, 0)', context=nd_context) == numpy.nanmin(nd_arr, 0)).all()
        assert (p.evaluate('min(x, 1)', context=nd_context) == numpy.nanmin(nd_arr, 1)).all()
        assert p.evaluate('max(x)', context=context) == 149
        assert (p.evaluate('max(x, 0)', context=nd_context) == numpy.nanmax(nd_arr, 0)).all()
        assert (p.evaluate('max(x, 1)', context=nd_context) == numpy.nanmax(nd_arr, 1)).all()
        assert p.evaluate('median(x)', context=context) == 112
        assert (p.evaluate('median(x, 0)', context=nd_context) == numpy.nanmedian(nd_arr, 0)).all()
        assert (p.evaluate('median(x, 1)', context=nd_context) == numpy.nanmedian(nd_arr, 1)).all()
        assert p.evaluate('mean(x)', context=context) == 87
        assert (p.evaluate('mean(x, 0)', context=nd_context) == numpy.nanmean(nd_arr, 0)).all()
        assert (p.evaluate('mean(x, 1)', context=nd_context) == numpy.nanmean(nd_arr, 1)).all()
        assert round(p.evaluate('std(x)', context=context), 3) == 54.485
        assert (p.evaluate('std(x, 0)', context=nd_context) == numpy.nanstd(nd_arr, 0)).all()
        assert (p.evaluate('std(x, 1)', context=nd_context) == numpy.nanstd(nd_arr, 1)).all()
        assert round(p.evaluate('var(x)', context=context), 3) == 2968.667
        assert (p.evaluate('var(x, 0)', context=nd_context) == numpy.nanvar(nd_arr, 0)).all()
        assert (p.evaluate('var(x, 1)', context=nd_context) == numpy.nanvar(nd_arr, 1)).all()

        assert p.evaluate('min(x) < max(x)', context=context) == True
        assert p.evaluate('abs(min(x))', context={'x': numpy.array([-1, 2, 3])}) == 1
