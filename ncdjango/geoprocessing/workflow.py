import copy
import json
import logging
import six
import time
from ncdjango.geoprocessing.params import ParameterCollection, Parameter

logger = logging.getLogger(__name__)


class TaskBase(type):
    """Parameter metaclass, used to register parameter classes for lookup by name."""

    _tasks_by_name = {}

    def __new__(mcs, name, bases, attrs):
        new_class = super(TaskBase, mcs).__new__(mcs, name, bases, attrs)

        name = getattr(new_class, 'name', None)
        if name:
            mcs._tasks_by_name[new_class.name] = new_class

        setattr(new_class, '_tasks_by_name', mcs._tasks_by_name)

        return new_class


class Task(six.with_metaclass(TaskBase)):
    """A discrete task with defined inputs and outputs. Extended to implement specific functionality."""

    name = ''
    inputs = []  # A list of `Parameter` objects defining accepted inputs for this task
    outputs = []  # A list of `Parameter` objects defining expected outputs for this task
    allow_extra_args = False  # If true, task may be called with kwargs not defined in `inputs`

    def __init__(self):
        self.inputs = copy.copy(self.inputs)
        self.outputs = copy.copy(self.outputs)

    def __call__(self, **kwargs):
        """
        Performs parameter validation and calls `self.execute()` with cleaned parameters. Always returns a
        `ParameterCollection` object representing the task output(s).
        """

        call_kwargs = self.validate_inputs(kwargs)

        if self.name:
            logger.info('Starting task {0}...'.format(self.name))
        start = time.time()
        try:
            ret = self.execute(**call_kwargs)
        except:
            if self.name:
                logger.exception('Task {0} failed.'.format(self.name))
            raise
        if self.name:
            logger.info('Task {0} finished in {1:.3f} seconds'.format(self.name, time.time() - start))

        if isinstance(ret, ParameterCollection):
            outputs = ret
        else:
            outputs = ParameterCollection(self.outputs)
            if self.outputs:
                outputs[self.outputs[0].name] = ret

        return outputs

    def validate_inputs(self, inputs):
        params = ParameterCollection(self.inputs)
        call_kwargs = {}

        for k, v in six.iteritems(inputs):
            try:
                params[k] = v
            except KeyError:
                if self.allow_extra_args:
                    call_kwargs[k] = v
                else:
                    raise TypeError('Unrecognized parameter: {}'.format(k))

        if not params.is_complete:
            missing_parameters = set(x.name for x in self.inputs if x.required).difference(set(inputs.keys()))
            raise TypeError('Missing required parameters: {}'.format(tuple(missing_parameters)))

        call_kwargs.update(params.format_args())
        return call_kwargs

    @classmethod
    def by_name(cls, name):
        return cls._tasks_by_name.get(name)

    def execute(self, **kwargs):
        """
        This should be implemented by child classes to perform the actual work of the task. Arguments should match
        input parameters for this task. Likewise, returned value(s) should match the output parameters.
        """

        raise NotImplementedError


class WorkflowNode(object):
    """
    Used by `Workflow` to represent a single node (a unique id, a task, and input mappings) in the workflow.
    """

    def __init__(self, node_id, task, inputs):
        self.id = node_id
        self.task = task
        self.inputs = inputs

        self.completed = False
        self.outputs = None

    def add_input(self, name, source, value):
        self.inputs[name] = (source, value)


class Workflow(Task):
    """A specialized task to manage the processing of many inter-related tasks."""

    def __init__(self, name=None, description=None):
        """Constructs the workflow from a dictionary structure."""

        super(Workflow, self).__init__()

        self.name = name
        self.description = description

        self.nodes_by_id = {}
        self.dependents_by_node_id = {}
        self.output_mapping = {}  # {<workflow output param name>: (<node id>, <task output param name>), ...}

    def _execute_node(self, node, workflow_inputs):
        task_inputs = {}

        for name, (source, value) in six.iteritems(node.inputs):
            if source == 'input':
                if value in workflow_inputs:
                    task_inputs[name] = workflow_inputs[value]
            elif source == 'dependency':
                dependency = self.nodes_by_id[value[0]]

                if not dependency.completed:
                    self._execute_node(dependency, workflow_inputs)

                if value[1] in dependency.outputs:
                    task_inputs[name] = dependency.outputs[value[1]]

                dependents = self.dependents_by_node_id[dependency.id]
                dependents.remove(node.id)
                if not dependents:
                    dependency.outputs = None  # Allow release of outputs which are no longer needed
            elif source == 'literal':
                task_inputs[name] = value
            else:
                raise ValueError('Invalid input source: {0}'.format(source))

        node.outputs = node.task(**task_inputs).format_args()
        node.completed = True

    def execute(self, **kwargs):
        outputs = ParameterCollection(self.outputs)

        for param, (node_id, name) in six.iteritems(self.output_mapping):
            node = self.nodes_by_id[node_id]

            if not node.completed:
                self._execute_node(node, kwargs)

            outputs[param] = node.outputs[name]

        for node in six.itervalues(self.nodes_by_id):
            node.outputs = None
            node.completed = False

        return outputs

    def add_node(self, node_id, task, inputs):
        """
        Adds a node to the workflow.

        :param node_id: A unique identifier for the new node.
        :param task: The task to run.
        :param inputs: A mapping of inputs from workflow inputs, or outputs from other nodes. The format should be
            `{input_name: (source, value), ...}` where `input_name` is the parameter name for the task input, source is
            "input" or "dependency" and `value` is either the workflow input name (if source is "input") or a 2-tuple
            with a node id and an output parameter name from that node's task to map to the input.
        """

        if node_id in self.nodes_by_id:
            raise ValueError('The node {0} already exists in this workflow.'.format(node_id))

        node = WorkflowNode(node_id, task, inputs)
        self.nodes_by_id[node_id] = node

        for source, value in six.itervalues(inputs):
            if source == 'dependency':
                dependents = self.dependents_by_node_id.get(value[0], set())
                dependents.add(node_id)
                self.dependents_by_node_id[value[0]] = dependents

    def map_output(self, node_id, node_output_name, parameter_name):
        """
        Maps the output from a node to a workflow output.

        :param node_id: The id of the node to map from.
        :param node_output_name: The output parameter name for the node task to map to the workflow output.
        :param parameter_name: The workflow output parameter name.
        """

        self.output_mapping[parameter_name] = (node_id, node_output_name)

        dependents = self.dependents_by_node_id.get(node_id, set())
        dependents.add('output_{}'.format(parameter_name))
        self.dependents_by_node_id[node_id] = dependents

    def to_json(self, indent=None):
        """Serialize this workflow to JSON"""

        inputs = ParameterCollection(self.inputs)

        d = {
            'meta': {
                'name': self.name,
                'description': self.description
            },
            'inputs': [],
            'workflow': [],
            'outputs': [{'name': k, 'node': v} for k, v in six.iteritems(self.output_mapping)]
        }

        for parameter in self.inputs:
            input_info = {
                'name': parameter.name,
                'type': parameter.id
            }

            args, kwargs = parameter.serialize_args()
            args = list(args)
            args.pop(0)  # 'name' is already taken care of
            kwargs.pop('required', None)  # 'required' is assumed True for workflow inputs
            if args or kwargs:
                input_info['args'] = [args, kwargs]

            d['inputs'].append(input_info)

        for node in sorted(six.itervalues(self.nodes_by_id), key=lambda x: x.id):
            task_name = node.task.name
            if not task_name:
                raise ValueError('The task {0} does not have a name and therefore cannot be serialized.'.format(
                    node.task.__class__.__name__)
                )

            node_inputs = {}
            for input_name, (source, value) in six.iteritems(node.inputs):
                input_info = {'source': source}

                if source == 'input':
                    input_info['input'] = inputs.by_name[value].name
                else:
                    input_info['node'] = value

                node_inputs[input_name] = input_info

            d['workflow'].append({
                'id': node.id,
                'task': task_name,
                'inputs': node_inputs
            })

        return json.dumps(d, indent=indent)

    @classmethod
    def from_json(cls, text):
        """Return a new workflow, deserialized from a JSON string"""

        d = json.loads(text)

        meta = d.get('meta', {})
        workflow = cls(name=meta.get('name'), description=meta.get('description'))

        for workflow_input in d.get('inputs', []):
            parameter_cls = Parameter.by_id(workflow_input['type'])

            args = [workflow_input['name']]
            kwargs = {'required': True}
            if workflow_input.get('args'):
                args = workflow_input['args'][0] + args
                kwargs.update(workflow_input['args'][1])
                args, kwargs = parameter_cls.deserialize_args(args, kwargs)

            workflow.inputs.append(parameter_cls(*args, **kwargs))

        for node in d.get('workflow', []):
            node_inputs = {}
            for k, v in six.iteritems(node.get('inputs', {})):
                node_inputs[k] = (v['source'], v.get('input') or v.get('node'))

            workflow.add_node(node['id'], Task.by_name(node['task'])(), node_inputs)

        for output in d.get('outputs', []):
            node = output['node']
            node_parameters = ParameterCollection(workflow.nodes_by_id[node[0]].task.outputs)

            # Add parameter to workflow output
            output_param = copy.copy(node_parameters.by_name[node[1]])
            output_param.name = output['name']
            workflow.outputs.append(output_param)

            workflow.map_output(node[0], node[1], output['name'])

        return workflow
