from django.urls import path

from tests.views import view

urlpatterns = [
    path("", view, name="home"),
    path("example/", view, name="example"),
]
