import copy
import json
from rest_framework import serializers

from ncdjango.geoprocessing.celery_tasks import run_job
from ncdjango.geoprocessing.params import ParameterNotValidError
from ncdjango.geoprocessing.utils import REGISTERED_JOBS, get_task_instance, process_web_inputs
from ncdjango.models import ProcessingJob


class ProcessingJobSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    inputs = serializers.JSONField(allow_null=True)
    outputs = serializers.JSONField(read_only=True)

    class Meta:
        model = ProcessingJob
        fields = ('uuid', 'job', 'created', 'status', 'inputs', 'outputs')
        read_only_fields = ('uuid', 'created', 'status')

    def validate_job(self, value):
        if value not in REGISTERED_JOBS:
            raise serializers.ValidationError('Invalid job name')
        return value

    def validate_inputs(self, value):
        if value:
            try:
                return json.loads(value, strict=False)
            except ValueError:
                raise serializers.ValidationError('Invalid input JSON')

        return {}

    def validate(self, data):
        try:
            process_web_inputs(get_task_instance(data['job']), copy.copy(data['inputs']))
        except (ParameterNotValidError, TypeError) as e:
            raise serializers.ValidationError('Invalid task input: {}'.format(str(e)))

        return data

    def create(self, validated_data):
        result = run_job.delay(validated_data['job'], validated_data['inputs'])
        request = self.context['request']

        return ProcessingJob.objects.create(
            job=validated_data['job'], celery_id=result.id, status='pending',
            inputs=json.dumps(validated_data['inputs']), user_ip=request.META.get('REMOTE_ADDR'),
            user=request.user if request.user.is_authenticated() else None
        )
