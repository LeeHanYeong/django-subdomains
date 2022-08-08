INSTALLED_APPS = ("subdomains",)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}
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

# Subdomain settings
SUBDOMAIN_DOMAIN = "example.com"
