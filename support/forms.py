from __future__ import annotations

from django import forms

from support.models import SupportTicket


class SupportTicketForm(forms.ModelForm):
    class Meta:
        model = SupportTicket
        fields = ["tenant", "subject", "description", "status", "priority", "assigned_to"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, language: str = "ar", **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        self.fields["status"].widget.attrs.setdefault("class", "form-select")
        self.fields["priority"].widget.attrs.setdefault("class", "form-select")
        self.fields["tenant"].widget.attrs.setdefault("class", "form-select")
        self.fields["assigned_to"].widget.attrs.setdefault("class", "form-select")

        if str(language).startswith("ar"):
            self.fields["tenant"].label = "المطعم"
            self.fields["subject"].label = "عنوان التذكرة"
            self.fields["description"].label = "وصف المشكلة"
            self.fields["status"].label = "الحالة"
            self.fields["priority"].label = "الأولوية"
            self.fields["assigned_to"].label = "مُسندة إلى"
