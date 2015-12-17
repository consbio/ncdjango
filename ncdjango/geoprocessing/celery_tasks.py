import json
from celery.task import task

from ncdjango.geoprocessing.utils import get_task_instance, process_web_inputs, process_web_outputs, REGISTERED_JOBS
from ncdjango.models import ProcessingJob


@task(bind=True)
def run_job(self, job_name, inputs):
    t = get_task_instance(job_name)
    results = t(**process_web_inputs(t, inputs))

    job_info = REGISTERED_JOBS[job_name]
    ProcessingJob.objects.filter(celery_id=self.request.id).update(outputs=json.dumps(
        process_web_outputs(results, self.request.id, job_info.get('publish_raster_results', False))
    ))
