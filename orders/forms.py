from __future__ import annotations

from django import forms
from django.forms import modelformset_factory

from orders.models import Order, OrderItem


class OrderEditForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["status", "notes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].widget.attrs.setdefault("class", "form-select")
        self.fields["notes"].widget.attrs.setdefault("class", "form-control")
        self.fields["notes"].widget.attrs.setdefault("rows", 2)


class OrderItemEditForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ["quantity", "notes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["quantity"].widget.attrs.setdefault("class", "form-control")
        self.fields["notes"].widget.attrs.setdefault("class", "form-control")

    def clean_quantity(self):
        value = self.cleaned_data.get("quantity")
        if value is None or value <= 0:
            raise forms.ValidationError("Quantity must be greater than zero.")
        return value


OrderItemFormSet = modelformset_factory(
    OrderItem,
    form=OrderItemEditForm,
    extra=0,
    can_delete=False,
)
