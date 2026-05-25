from __future__ import annotations

from django import forms

from core.models import LeadRequest


class LeadRequestForm(forms.ModelForm):
    class Meta:
        model = LeadRequest
        fields = [
            "name",
            "phone",
            "email",
            "company",
            "inquiry_category",
            "contact_method",
            "preferred_time",
            "message",
        ]
        widgets = {"message": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, language: str = "ar", **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

        if str(language).startswith("ar"):
            self.fields["name"].label = "الاسم الكامل"
            self.fields["email"].label = "البريد الإلكتروني"
            self.fields["phone"].label = "رقم الهاتف"
            self.fields["company"].label = "اسم المطعم/الشركة"
            self.fields["message"].label = "تفاصيل الطلب"
            self.fields["inquiry_category"].label = "نوع الاستفسار"
            self.fields["contact_method"].label = "طريقة التواصل المفضلة"
            self.fields["preferred_time"].label = "وقت التواصل المفضل"
            self.fields["inquiry_category"].choices = [
                ("", "اختر"),
                (LeadRequest.INQUIRY_SALES, "مبيعات"),
                (LeadRequest.INQUIRY_PRICING, "الأسعار والباقات"),
                (LeadRequest.INQUIRY_SUPPORT, "الدعم الفني"),
                (LeadRequest.INQUIRY_PARTNERSHIP, "شراكات"),
                (LeadRequest.INQUIRY_OTHER, "أخرى"),
            ]
            self.fields["contact_method"].choices = [
                ("", "اختر"),
                (LeadRequest.CONTACT_PHONE, "مكالمة هاتفية"),
                (LeadRequest.CONTACT_EMAIL, "البريد الإلكتروني"),
                (LeadRequest.CONTACT_WHATSAPP, "واتساب"),
            ]
            self.fields["preferred_time"].choices = [
                ("", "اختر"),
                (LeadRequest.TIME_MORNING, "صباحًا"),
                (LeadRequest.TIME_AFTERNOON, "مساءً"),
                (LeadRequest.TIME_EVENING, "ليلاً"),
            ]
        else:
            self.fields["inquiry_category"].choices = [
                ("", "Select"),
                *LeadRequest.INQUIRY_CHOICES,
            ]
            self.fields["contact_method"].choices = [
                ("", "Select"),
                *LeadRequest.CONTACT_CHOICES,
            ]
            self.fields["preferred_time"].choices = [
                ("", "Select"),
                *LeadRequest.TIME_CHOICES,
            ]
