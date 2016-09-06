Tasks
=====

Tasks represent a unit of work in the geoprocessing framework. These can be built-in, or user-defined.

Basic Task
----------

A basic task has a name, input and output parameters, and an ``execute`` method.

.. code-block:: python

    class MultiplyArray(Task):
        """ Multiply the values in an array by a given factor """

        name = 'multiply_array'

        inputs = [
            NdArrayParameter('array_in', required=True),
            NumberParameter('factor', required=True)
        ]

        outputs = [
            NdArrayParameter('array_out')
        ]

        def execute(array_in, factor):
            return array_in * factor

Normally, the ``execute`` method will never be called directly. Instead, the ``__call__`` method of the base ``Task``
class is called; it validates and cleans the parameters (e.g., converting the string ``"3"`` into the number ``3`` for
a ``NumberParameter`` input), then calls ``execute`` with the cleaned values.

Default Inputs
--------------

To specify a default value for a task input, set ``required=False`` on the parameter, and provide a default value for
it in the ``execute`` method.

.. code-block:: python

    class MultiplyArray(Task):
        """ Multiply the values in an array by a given factor """

        name = 'multiply_array'

        inputs = [
            NdArrayParameter('array_in', required=True),
            NumberParameter('factor', required=False)
        ]

        outputs = [
            NdArrayParameter('array_out')
        ]

        def execute(array_in, factor=5):
            return array_in * factor

Multiple Return Values
----------------------

If your task has multiple return values, return a ``ParameterCollection`` object. ``ParameterCollection`` behaves like
a dictionary; you can set your return values like you would a dict object.

.. code-block:: python

    class Divide(Task)
        """ Perform a divide operation an return value and remainder """

        name = 'divide'

        inputs = [
            IntParameter('numerator', required=True),
            IntParameter('denominator', required=True)
        ]

        outputs = [
            IntParameter('result'),
            IntParameter('remainder')
        ]

        def execute(numerator, denominator):
            output = ParameterCollection(self.outputs)

            output['result'] = numerator // denominator # Integer division
            output['remainder'] = numerator % denominator

            return output
