import json
from rest_framework import serializers

from ncdjango.geoprocessing.celery_tasks import run_job
from ncdjango.geoprocessing.utils import REGISTERED_JOBS, get_task_instance
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
        return value or {}

    def create(self, validated_data):
        task = get_task_instance(validated_data['job'])

        inputs = json.dumps(validated_data['inputs'])
        result = run_job.delay(validated_data['job'], inputs)

        return ProcessingJob.objects.create(
            job=validated_data['job'], celery_id=result.id, status='pending', inputs=inputs
        )
