# django-subdomains2

django-subdomains2 is a fork of the no longer managed [django-subdomain](https://github.com/tkaemming/django-subdomains) repo.

Tested on Python 3.8, 3.9, 3.10 and Django 3.2, 4.0

## Installation

```shell
pip install django-subdomains2
```

## Quick Start

1. Add `subdomains.middleware.SubdomainURLRoutingMiddleware` to your `MIDDLEWARE` in your Django settings file. If you are using `django.middleware.common.CommonMiddleware`, the subdomain middlware should come before `CommonMiddleware`  
   ```python
   MIDDLEWARE = [
       ...
       "subdomains.middleware.SubdomainURLRoutingMiddleware",
       "django.middleware.common.CommonMiddleware",
       ...
   ]
   ```

2. Configure the `SUBDOMAIN_URLCONFS` dictionary in Django settings file.  

   ```python
   # This is the urlconf that will be used for any subdomain that is not
   # listed in "SUBDOMAIN_URLCONFS", or if the HTTP "Host" header does not
   # contain the correct domain.
   # If you're planning on using wildcard subdomains, this should correspond
   # to the urlconf that will be used for the wildcard subdomain. For example,
   # 'test.mysite.com' will load the ROOT_URLCONF, since it is not
   # defined in "SUBDOMAIN_URLCONFS".
   ROOT_URLCONF = "myproject.urls.frontend"
   
   # A dictionary of urlconf module paths, keyed by their subdomain.
   SUBDOMAIN_URLCONFS = {
       None: "myproject.urls.frontend",
       "www": "myproject.urls.frontend",
       "api": "myproject.urls.api",
       "admin": "myproject.urls.admin",
   }
   ```

3. Configure the `SUBDOMAIN_DOMAIN` in Django settings file.  
   ```python
   SUBDOMAIN_DOMAIN = "mysite.com"
   ```

4. If you want to use the subdomain-based `{% url %}` template tag, add `subdomains` to your `INSTALLED_APPS`.

## Basic Usage

### Using Subdomains in Views

On each request, a `subdomain` attribute will be added to the `request` object. You can use this attribute to effect view logic, like in this example:

```python
def user_profile(request):
    try:
        # Retrieve the user account associated with the current subdomain.
        user = User.objects.get(username=request.subdomain)
    except User.DoesNotExist:
        # No user matches the current subdomain, so return a generic 404.
        raise Http404
```

### Resolving Named URLs by Subdomain

Included is a `subdomains.utils.reverse()` function that responds similarly to [`django.core.urlresolvers.reverse()`](https://docs.djangoproject.com/en/dev/ref/urlresolvers/#reverse), but accepts optional `subdomain` and `scheme` arguments and does not allow a `urlconf` parameter.

If no `subdomain` argument is provided, the URL will be resolved relative to the `SUBDOMAIN_URLCONFS[None]` or `ROOT_URLCONF`, in order. The protocol scheme is the value of `settings.DEFAULT_URL_SCHEME`, or if unset, `http`:

```python
>>> from subdomains.utils import reverse
>>> reverse('home')
'http://example.com/'
>>> reverse('user-profile', kwargs={'username': 'ted'})
'http://example.com/users/ted/'
>>> reverse('home', scheme='https')
'https://example.com/'
```

For subdomains, the URL will be resolved relative to the `SUBDOMAIN_URLCONFS[subdomain]` value if it exists, otherwise falling back to the `ROOT_URLCONF`:

```python
>>> from subdomains.utils import reverse
>>> reverse('home', subdomain='api')
'http://api.example.com/'
>>> reverse('home', subdomain='wildcard')
'http://wildcard.example.com/'
>>> reverse('login', subdomain='wildcard')
'http://wildcard.example.com/login/'
```

If a URL cannot be resolved, a [`django.urls.exceptions.NoReverseMatch`](https://docs.djangoproject.com/en/dev/ref/exceptions/#noreversematch) will be raised.

### Resolving Named URLs in Templates

The `subdomainurls` template tag library contains a `url` tag that takes an optional `subdomain` argument as it’s first positional argument, or as named argument. The following are all valid invocations of the tag:

```
{% load subdomainurls %}
{% url 'home' %}
{% url 'home' 'subdomain' %}
{% url 'home' subdomain='subdomain' %}
{% url 'user-profile' username='ted' %}
{% url 'user-profile' subdomain='subdomain' username='ted' %}
```

If `request` is in the template context when rendering and no subdomain is provided, the URL will be attempt to be resolved by relative to the current subdomain. If no request is available, the URL will be resolved using the same rules as a call to `subdomains.utils.reverse()` without a `subdomain` argument value. An easy way to ensure this functionality is available is to add `django.core.context_processors.request()` is in your `settings.TEMPLATES["OPTIONS"]["context_processors"]` list.

## Test

```
tox
```

## Deploy

```
pip install build setuptools wheel
python -m build
twine upload dist/*
```

