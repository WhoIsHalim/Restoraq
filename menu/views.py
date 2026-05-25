from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import get_language
from django.views.generic import FormView, ListView, TemplateView, UpdateView

from core.constants import BRANCH_SCOPED_ROLES
from featureflags.services import FeatureService
from inventory.models import Recipe
from menu.forms import CategoryForm, ProductForm, RecipeForm
from menu.models import Category, Product
from tenants.models import Tenant
from restaurants.models import Branch


MENU_WRITE_ROLES = {"RestaurantOwner", "BranchManager", "InventoryManager"}


class MenuContextMixin(LoginRequiredMixin):
    def get_tenant(self):
        tenant = getattr(self.request, "tenant", None)
        if not tenant:
            raise PermissionDenied("Tenant context is required.")
        return tenant

    def get_membership(self):
        return getattr(self.request, "membership", None)

    def apply_branch_scope(self, queryset):
        membership = self.get_membership()
        if membership and membership.role_name in BRANCH_SCOPED_ROLES and membership.primary_branch_id:
            return queryset.filter(branch=membership.primary_branch)
        return queryset

    def can_write(self):
        if self.request.user.is_superuser:
            return True
        membership = self.get_membership()
        return bool(membership and membership.role_name in MENU_WRITE_ROLES)

    def ensure_write_access(self):
        if not self.can_write():
            raise PermissionDenied("You are not allowed to modify menu data.")


class CategoryListView(MenuContextMixin, ListView):
    model = Category
    template_name = "menu/categories.html"
    context_object_name = "categories"
    paginate_by = 30

    def get_queryset(self):
        qs = Category.objects.filter(tenant=self.get_tenant()).select_related("branch")
        return self.apply_branch_scope(qs).order_by("display_order", "name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_write"] = self.can_write()
        return context


class CategoryCreateView(MenuContextMixin, FormView):
    template_name = "menu/category_form.html"
    form_class = CategoryForm

    def dispatch(self, request, *args, **kwargs):
        self.ensure_write_access()
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.get_tenant()
        kwargs["membership"] = self.get_membership()
        kwargs["language"] = getattr(self.request, "LANGUAGE_CODE", "en")
        return kwargs

    def form_valid(self, form):
        category = form.save(commit=False)
        category.tenant = self.get_tenant()
        category.save()
        messages.success(
            self.request,
            "تم إنشاء تصنيف المنيو بنجاح." if self.request.LANGUAGE_CODE.startswith("ar") else "Menu category created successfully.",
        )
        return redirect("menu:categories")


class CategoryUpdateView(MenuContextMixin, UpdateView):
    model = Category
    template_name = "menu/category_form.html"
    form_class = CategoryForm
    pk_url_kwarg = "pk"

    def dispatch(self, request, *args, **kwargs):
        self.ensure_write_access()
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = Category.objects.filter(tenant=self.get_tenant())
        return self.apply_branch_scope(qs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.get_tenant()
        kwargs["membership"] = self.get_membership()
        kwargs["language"] = getattr(self.request, "LANGUAGE_CODE", "en")
        return kwargs

    def form_valid(self, form):
        messages.success(
            self.request,
            "تم تحديث تصنيف المنيو بنجاح." if self.request.LANGUAGE_CODE.startswith("ar") else "Menu category updated successfully.",
        )
        return super().form_valid(form)

    def get_success_url(self):
        return redirect("menu:categories").url


class ProductListView(MenuContextMixin, ListView):
    model = Product
    template_name = "menu/products.html"
    context_object_name = "products"
    paginate_by = 30

    def get_queryset(self):
        qs = Product.objects.filter(tenant=self.get_tenant()).select_related("branch", "category")
        return self.apply_branch_scope(qs).order_by("name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_write"] = self.can_write()
        return context


class ProductCreateView(MenuContextMixin, FormView):
    template_name = "menu/product_form.html"
    form_class = ProductForm

    def dispatch(self, request, *args, **kwargs):
        self.ensure_write_access()
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.get_tenant()
        kwargs["membership"] = self.get_membership()
        kwargs["language"] = getattr(self.request, "LANGUAGE_CODE", "en")
        return kwargs

    def form_valid(self, form):
        product = form.save(commit=False)
        product.tenant = self.get_tenant()
        if form.cleaned_data.get("apply_to_all_branches"):
            product.branch = None
        product.save()
        messages.success(
            self.request,
            "تم إنشاء صنف المنيو بنجاح." if self.request.LANGUAGE_CODE.startswith("ar") else "Menu product created successfully.",
        )
        return redirect("menu:products")


class ProductUpdateView(MenuContextMixin, UpdateView):
    model = Product
    template_name = "menu/product_form.html"
    form_class = ProductForm
    pk_url_kwarg = "pk"

    def dispatch(self, request, *args, **kwargs):
        self.ensure_write_access()
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = Product.objects.filter(tenant=self.get_tenant())
        return self.apply_branch_scope(qs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.get_tenant()
        kwargs["membership"] = self.get_membership()
        kwargs["language"] = getattr(self.request, "LANGUAGE_CODE", "en")
        return kwargs

    def form_valid(self, form):
        if form.cleaned_data.get("apply_to_all_branches"):
            form.instance.branch = None
        messages.success(
            self.request,
            "تم تحديث صنف المنيو بنجاح." if self.request.LANGUAGE_CODE.startswith("ar") else "Menu product updated successfully.",
        )
        return super().form_valid(form)

    def get_success_url(self):
        return redirect("menu:products").url


class ProductRecipeManageView(MenuContextMixin, TemplateView):
    template_name = "menu/product_recipes.html"

    def dispatch(self, request, *args, **kwargs):
        self.ensure_write_access()
        if not FeatureService.is_enabled(self.get_tenant(), "recipes"):
            raise PermissionDenied("Recipes feature is not enabled for your plan.")
        return super().dispatch(request, *args, **kwargs)

    def get_product(self):
        qs = Product.objects.filter(tenant=self.get_tenant())
        qs = self.apply_branch_scope(qs)
        return get_object_or_404(qs, id=self.kwargs["pk"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.get_product()
        form = kwargs.get("form") or RecipeForm(
            tenant=self.get_tenant(),
            branch=product.branch,
            language=getattr(self.request, "LANGUAGE_CODE", "en"),
        )
        context["product"] = product
        context["recipes"] = Recipe.objects.filter(tenant=self.get_tenant(), product=product).select_related("ingredient")
        context["form"] = form
        return context

    def post(self, request, *args, **kwargs):
        product = self.get_product()
        if request.POST.get("action") == "delete":
            recipe_id = request.POST.get("recipe_id")
            Recipe.objects.filter(tenant=self.get_tenant(), product=product, id=recipe_id).delete()
            messages.success(
                request,
                "تم حذف مكوّن الصنف." if request.LANGUAGE_CODE.startswith("ar") else "Recipe line deleted.",
            )
            return redirect("menu:product-recipes", pk=product.id)

        form = RecipeForm(
            request.POST,
            tenant=self.get_tenant(),
            branch=product.branch,
            language=getattr(request, "LANGUAGE_CODE", "en"),
        )
        if form.is_valid():
            Recipe.objects.update_or_create(
                tenant=self.get_tenant(),
                product=product,
                ingredient=form.cleaned_data["ingredient"],
                defaults={
                    "branch": product.branch,
                    "quantity_per_unit": form.cleaned_data["quantity_per_unit"],
                },
            )
            messages.success(
                request,
                "تم حفظ مكوّنات الصنف." if request.LANGUAGE_CODE.startswith("ar") else "Recipe line saved.",
            )
            return redirect("menu:product-recipes", pk=product.id)
        return self.render_to_response(self.get_context_data(form=form))


class PublicMenuView(TemplateView):
    template_name = "menu/public_menu.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = get_object_or_404(Tenant, slug=self.kwargs["tenant_slug"], is_active=True)
        branch_code = (self.request.GET.get("branch") or "").strip()
        branch = None
        if branch_code:
            branch = Branch.objects.filter(tenant=tenant, code__iexact=branch_code, is_active=True).first()

        categories = Category.objects.filter(tenant=tenant, is_active=True)
        products = Product.objects.filter(tenant=tenant, is_active=True)
        if branch:
            categories = categories.filter(branch__in=[branch, None])
            products = products.filter(branch__in=[branch, None])

        products_payload = []
        for product in products.select_related("category").order_by("name"):
            image_path = product.image.url if product.image else ""
            if image_path:
                try:
                    image_path = self.request.build_absolute_uri(image_path)
                except Exception:
                    pass
            products_payload.append(
                {
                    "id": product.id,
                    "name": product.name,
                    "price": product.price,
                    "category_id": product.category_id,
                    "image": image_path,
                }
            )

        language = (get_language() or tenant.default_language or "ar").split("-")[0]
        context["tenant"] = tenant
        context["branch"] = branch
        context["categories"] = categories.order_by("display_order", "name")
        context["products"] = products_payload
        context["active_language"] = language
        context["text_direction"] = "rtl" if language.startswith("ar") else "ltr"
        return context
