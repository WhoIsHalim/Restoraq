from django.urls import path

from accounts.views import ProfileView, UserLoginView, UserLogoutView, switch_language

app_name = "accounts"

urlpatterns = [
    path("login/", UserLoginView.as_view(), name="login"),
    path("logout/", UserLogoutView.as_view(), name="logout"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("lang/<str:language_code>/", switch_language, name="switch-language"),
]
