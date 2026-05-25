from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TenantScopedModel(TimeStampedModel):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)ss",
    )

    class Meta:
        abstract = True


class TenantBranchScopedModel(TenantScopedModel):
    branch = models.ForeignKey(
        "restaurants.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)ss",
    )

    class Meta:
        abstract = True

    def clean(self) -> None:
        super().clean()
        if self.branch_id and self.tenant_id and self.branch.tenant_id != self.tenant_id:
            raise ValidationError("Selected branch does not belong to tenant.")


class CMSPage(TimeStampedModel):
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=140, unique=True)
    body = models.TextField(blank=True)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ["title"]

    def __str__(self) -> str:
        return self.title


class HomePageContent(TimeStampedModel):
    language = models.CharField(
        max_length=8,
        choices=(("ar", "Arabic"), ("en", "English")),
        default="ar",
        unique=True,
    )
    kicker = models.CharField(max_length=140, blank=True)
    title = models.CharField(max_length=255, blank=True)
    subtitle = models.TextField(blank=True)
    primary_cta = models.CharField(max_length=120, blank=True)
    secondary_cta = models.CharField(max_length=120, blank=True)
    problem_title = models.CharField(max_length=255, blank=True)
    problem_text = models.TextField(blank=True)
    solution_text = models.TextField(blank=True)
    highlights = models.TextField(
        blank=True,
        help_text="One line per highlight item.",
    )
    metrics = models.TextField(
        blank=True,
        help_text="One line per metric item.",
    )
    final_title = models.CharField(max_length=255, blank=True)
    final_text = models.TextField(blank=True)
    final_cta = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["language"]

    def __str__(self) -> str:
        return f"Home Content ({self.language})"


class FeaturesPageContent(TimeStampedModel):
    language = models.CharField(
        max_length=8,
        choices=(("ar", "Arabic"), ("en", "English")),
        default="ar",
        unique=True,
    )
    title = models.CharField(max_length=255, blank=True)
    subtitle = models.TextField(blank=True)
    cards = models.TextField(
        blank=True,
        help_text=(
            "One card per line. Format: Title|Description. "
            "Example: Cloud POS|Fast cashier workflows."
        ),
    )
    closing_title = models.CharField(max_length=255, blank=True)
    closing_text = models.TextField(blank=True)
    closing_cta = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["language"]

    def __str__(self) -> str:
        return f"Features Content ({self.language})"


class PricingPageContent(TimeStampedModel):
    language = models.CharField(
        max_length=8,
        choices=(("ar", "Arabic"), ("en", "English")),
        default="ar",
        unique=True,
    )
    title = models.CharField(max_length=255, blank=True)
    subtitle = models.TextField(blank=True)
    plan_badges = models.TextField(
        blank=True,
        help_text=(
            "One line per plan badge. Format: code|badge. "
            "Supported codes: basic, standard, multibranch, pro."
        ),
    )
    plan_descriptions = models.TextField(
        blank=True,
        help_text=(
            "One line per plan description. Format: code|description. "
            "Supported codes: basic, standard, multibranch, pro."
        ),
    )
    faq_items = models.TextField(
        blank=True,
        help_text="One line per FAQ item.",
    )
    money_back = models.CharField(max_length=255, blank=True)
    closing_cta = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["language"]

    def __str__(self) -> str:
        return f"Pricing Content ({self.language})"


class MarketingSlide(TimeStampedModel):
    language = models.CharField(
        max_length=8,
        choices=(("ar", "Arabic"), ("en", "English")),
        default="ar",
    )
    title = models.CharField(max_length=200)
    subtitle = models.TextField(blank=True)
    cta_text = models.CharField(max_length=120, blank=True)
    cta_url = models.CharField(max_length=240, blank=True)
    image_path = models.CharField(
        max_length=240,
        blank=True,
        help_text="Static path or full URL. Example: img/hero-slide-1.png",
    )
    order = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Marketing Slide"
        verbose_name_plural = "Marketing Slides"

    def __str__(self) -> str:
        return f"{self.title} ({self.language})"


class LeadRequest(TimeStampedModel):
    TYPE_DEMO = "demo"
    TYPE_TRIAL = "trial"
    TYPE_CONTACT = "contact"
    TYPE_CHOICES = [
        (TYPE_DEMO, "Demo"),
        (TYPE_TRIAL, "Trial"),
        (TYPE_CONTACT, "Contact"),
    ]

    CONTACT_PHONE = "phone"
    CONTACT_EMAIL = "email"
    CONTACT_WHATSAPP = "whatsapp"
    CONTACT_CHOICES = [
        (CONTACT_PHONE, "Phone"),
        (CONTACT_EMAIL, "Email"),
        (CONTACT_WHATSAPP, "WhatsApp"),
    ]

    TIME_MORNING = "morning"
    TIME_AFTERNOON = "afternoon"
    TIME_EVENING = "evening"
    TIME_CHOICES = [
        (TIME_MORNING, "Morning"),
        (TIME_AFTERNOON, "Afternoon"),
        (TIME_EVENING, "Evening"),
    ]

    INQUIRY_SALES = "sales"
    INQUIRY_PRICING = "pricing"
    INQUIRY_SUPPORT = "support"
    INQUIRY_PARTNERSHIP = "partnership"
    INQUIRY_OTHER = "other"
    INQUIRY_CHOICES = [
        (INQUIRY_SALES, "Sales"),
        (INQUIRY_PRICING, "Pricing"),
        (INQUIRY_SUPPORT, "Support"),
        (INQUIRY_PARTNERSHIP, "Partnership"),
        (INQUIRY_OTHER, "Other"),
    ]

    STATUS_NEW = "new"
    STATUS_CONTACTED = "contacted"
    STATUS_WON = "won"
    STATUS_LOST = "lost"
    STATUS_CHOICES = [
        (STATUS_NEW, "New"),
        (STATUS_CONTACTED, "Contacted"),
        (STATUS_WON, "Won"),
        (STATUS_LOST, "Lost"),
    ]

    name = models.CharField(max_length=160)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    company = models.CharField(max_length=160, blank=True)
    request_type = models.CharField(max_length=16, choices=TYPE_CHOICES, default=TYPE_DEMO)
    inquiry_category = models.CharField(max_length=24, choices=INQUIRY_CHOICES, blank=True)
    contact_method = models.CharField(max_length=16, choices=CONTACT_CHOICES, blank=True)
    preferred_time = models.CharField(max_length=16, choices=TIME_CHOICES, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_NEW)
    message = models.TextField(blank=True)
    source_page = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} - {self.request_type}"
