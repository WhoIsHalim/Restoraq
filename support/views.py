from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, ListView, UpdateView

from tenants.decorators import system_role_required
from support.forms import SupportTicketForm
from support.models import SupportTicket


def _is_ar(request) -> bool:
    return (getattr(request, "LANGUAGE_CODE", "ar") or "ar").split("-")[0] == "ar"


@method_decorator(system_role_required, name="dispatch")
class SupportTicketListView(LoginRequiredMixin, ListView):
    model = SupportTicket
    template_name = "system/support_tickets.html"
    context_object_name = "tickets"
    paginate_by = 30

    def get_queryset(self):
        qs = SupportTicket.objects.select_related("tenant", "created_by", "assigned_to")
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs


@method_decorator(system_role_required, name="dispatch")
class SupportTicketCreateView(LoginRequiredMixin, CreateView):
    model = SupportTicket
    template_name = "system/support_ticket_form.html"
    form_class = SupportTicketForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["language"] = (getattr(self.request, "LANGUAGE_CODE", "ar") or "ar").split("-")[0]
        return kwargs

    def form_valid(self, form):
        ticket = form.save(commit=False)
        ticket.created_by = self.request.user
        ticket.save()
        messages.success(
            self.request,
            "تم إنشاء التذكرة بنجاح." if _is_ar(self.request) else "Support ticket created.",
        )
        return redirect("system:support-tickets")


@method_decorator(system_role_required, name="dispatch")
class SupportTicketUpdateView(LoginRequiredMixin, UpdateView):
    model = SupportTicket
    template_name = "system/support_ticket_form.html"
    form_class = SupportTicketForm
    pk_url_kwarg = "pk"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["language"] = (getattr(self.request, "LANGUAGE_CODE", "ar") or "ar").split("-")[0]
        return kwargs

    def form_valid(self, form):
        ticket = form.save(commit=False)
        ticket.save(update_fields=["tenant", "subject", "description", "status", "priority", "assigned_to", "updated_at"])
        messages.success(
            self.request,
            "تم تحديث التذكرة." if _is_ar(self.request) else "Support ticket updated.",
        )
        return redirect("system:support-tickets")
