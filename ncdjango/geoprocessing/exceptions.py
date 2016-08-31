class ExecutionError(RuntimeError):
    def __init__(self, message, task):
        super(ExecutionError, self).__init__(
            "An exception occurred while executing the task '{0}': {1}".format(task.name, message)
        )
