from django.urls import path

from hr.views import EmployeeCreateView, EmployeeListView, EmployeeUpdateView

app_name = "hr"

urlpatterns = [
    path("employees/", EmployeeListView.as_view(), name="employees"),
    path("employees/new/", EmployeeCreateView.as_view(), name="employee-create"),
    path("employees/<int:pk>/edit/", EmployeeUpdateView.as_view(), name="employee-edit"),
]
