import json

from ncdjango.geoprocessing.celery_tasks import run_job
from ncdjango.geoprocessing.utils import REGISTERED_JOBS, get_task_instance
from ncdjango.models import ProcessingJob
from rest_framework import serializers


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
        task = get_task_instance(data['job'])
        missing_params = set(x.name for x in task.inputs if x.required).difference(set(data['inputs'].keys()))

        if missing_params:
            raise serializers.ValidationError('Missing task inputs: {}'.format(','.join(missing_params)))

        return data

    def create(self, validated_data):
        result = run_job.delay(validated_data['job'], validated_data['inputs'])
        request = self.context['request']

        # Get real IP address if request has been forwarded
        forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded_for:
            ip_address = forwarded_for.split(',', 1)[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')

        return ProcessingJob.objects.create(
            job=validated_data['job'], celery_id=result.id, status='pending',
            inputs=json.dumps(validated_data['inputs']), user_ip=ip_address,
            user=request.user if request.user.is_authenticated() else None
        )
