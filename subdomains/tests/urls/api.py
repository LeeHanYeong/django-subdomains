from django.urls import path

from subdomains.tests.urls.default import urlpatterns as default_patterns
from subdomains.tests.views import view

urlpatterns = default_patterns + [
    path("", view, name="home"),
    path("view/", view, name="view"),
]
