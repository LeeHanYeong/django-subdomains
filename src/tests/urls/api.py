from django.urls import path

from tests.urls.default import urlpatterns as default_patterns
from tests.views import view

urlpatterns = default_patterns + [
    path("", view, name="home"),
    path("view/", view, name="view"),
]
