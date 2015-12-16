import time
from celery.task import task


@task
def run_job(job, inputs):
    time.sleep(30)
