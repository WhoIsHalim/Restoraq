from __future__ import annotations

import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponseBadRequest, JsonResponse
from django.views import View

from orders.models import Order
from printing.models import PrintJob
from printing.services import PrintService


class QZCertificateView(LoginRequiredMixin, View):
    def get(self, request):
        # Replace with real certificate chain in production.
        return JsonResponse({"certificate": "-----BEGIN CERTIFICATE-----\nDEMO\n-----END CERTIFICATE-----"})


class QZSignView(LoginRequiredMixin, View):
    def post(self, request: HttpRequest):
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON")
        message = payload.get("message", "")
        return JsonResponse({"signature": PrintService.qz_sign(message)})


class PrintJobAckView(LoginRequiredMixin, View):
    def post(self, request, job_id: int):
        job = PrintJob.objects.filter(id=job_id).first()
        if not job:
            return HttpResponseBadRequest("Print job not found")
        PrintService.acknowledge(job)
        return JsonResponse({"status": "acked", "job_id": job.id})


class PrintJobCreateView(LoginRequiredMixin, View):
    def post(self, request: HttpRequest):
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON")
        order_id = payload.get("order_id")
        template_type = payload.get("template_type")
        tenant = getattr(request, "tenant", None)
        order = Order.objects.filter(id=order_id, tenant=tenant).first()
        if not order:
            return HttpResponseBadRequest("Order not found")
        try:
            job = PrintService.create_manual_job(order=order, template_type=template_type)
        except ValueError as exc:
            return HttpResponseBadRequest(str(exc))
        return JsonResponse({"job_id": job.id, "status": job.status})
