from django.urls import path
from .views import (
    user_registration,
    check_availability,
    profile_view,
    search_users_view,
    public_profile_view,
    login_view,
    send_otp,
    verify_otp,
    reset_password,
    user_list,
    get_user_reviews,
)

urlpatterns = [
    path("register/", user_registration, name="user-register"),
    path("check-value/", check_availability, name="check-value"),
    path("login/", login_view, name="login"),
    path("profile/", profile_view, name="profile"),
    path("search/", search_users_view, name="search_users"),
    path("profile/<int:user_id>/", public_profile_view, name="public_profile"),
    path("profile/update/", profile_view, name="update-profle"),
    path("send-otp/", send_otp, name="send-otp"),
    path("verify-otp/", verify_otp, name="verify-otp"),
    path("reset-password/", reset_password, name="reset-password"),
    path("users/", user_list, name="list-users"),
    path("reviews/<int:user_id>/", get_user_reviews, name="user-reviews"),
]
