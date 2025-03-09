from django.urls import path
from .views import (
    all_rides,
    req_mail,
)

urlpatterns = [
    path("all/", all_rides, name="link-ride"),
    path('send-mail/', req_mail, name='req_email'),
]
