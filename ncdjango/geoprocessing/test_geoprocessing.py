import json
import numpy
import pytest
from ncdjango.geoprocessing.evaluation import Lexer, Parser
from ncdjango.geoprocessing.params import StringParameter, IntParameter
from ncdjango.geoprocessing.workflow import Task, Workflow


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
    def test_simple_task(self):
        class SimpleTask(Task):
            inputs = [
                StringParameter('str_in', required=True)
            ]
            outputs = [
                StringParameter('str_out')
            ]

            def execute(self, str_in):
                return str_in

        task = SimpleTask()
        assert task(str_in='Test')['str_out'] == 'Test'

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


    class TestEvaluations(object):
        def test_lexer(self):
            l = Lexer()

            assert l.get_names('x + y < 5') == {'x', 'y'}

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
