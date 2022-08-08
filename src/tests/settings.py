INSTALLED_APPS = (
    "django.contrib.sites",
    "subdomains",
)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}
SITE_ID = 1
MIDDLEWARE = (
    "django.middleware.common.CommonMiddleware",
    "subdomains.middleware.SubdomainURLRoutingMiddleware",
)
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
    },
]
ALLOWED_HOSTS = [
    ".example.com",
]
USE_TZ = True
