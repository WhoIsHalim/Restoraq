from django.urls import path

from printing.views import PrintJobAckView, PrintJobCreateView, QZCertificateView, QZSignView
app_name = "printing"

urlpatterns = [
    path("qz/certificate/", QZCertificateView.as_view(), name="qz-certificate"),
    path("qz/sign/", QZSignView.as_view(), name="qz-sign"),
    path("jobs/<int:job_id>/ack/", PrintJobAckView.as_view(), name="job-ack"),
    path("api/jobs/", PrintJobCreateView.as_view(), name="print-job"),
]
