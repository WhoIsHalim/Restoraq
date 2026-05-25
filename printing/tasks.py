from __future__ import annotations

from celery import shared_task

from printing.models import PrintJob
from printing.services import PrintService


@shared_task
def retry_failed_print_jobs() -> int:
    processed = 0
    jobs = PrintJob.objects.filter(status__in=[PrintJob.STATUS_QUEUED, PrintJob.STATUS_FAILED], attempts__lt=10)[:200]
    for job in jobs:
        try:
            PrintService.mark_sent(job)
            processed += 1
        except Exception as exc:  # pragma: no cover
            PrintService.mark_failed(job, str(exc))
    return processed
