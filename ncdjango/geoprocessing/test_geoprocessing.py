import json
import pytest
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
                },
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
                }
            ]
        }

        assert json.loads(simple_workflow.to_json()) == expected_output

    def test_simple_workflow_deserialization(self, simple_workflow):
        serialized = simple_workflow.to_json()
        workflow = Workflow.from_json(serialized)

        assert json.loads(workflow.to_json()) == json.loads(serialized)
