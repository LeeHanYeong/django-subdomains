import functools
import warnings
from urllib import parse as urlparse

import mock
from django.template import Context, Template
from django.test import TestCase
from django.test.client import RequestFactory
from django.test.utils import override_settings
from django.urls import NoReverseMatch, set_urlconf

from subdomains.middleware import SubdomainURLRoutingMiddleware
from subdomains.utils import reverse, urljoin


def prefix_values(dictionary, prefix):
    return dict((key, f"{prefix}.{value}") for key, value in dictionary.items())


class SubdomainTestMixin(object):
    DOMAIN = "example.com"
    URL_MODULE_PATH = "subdomains.tests.urls"

    def setUp(self):
        from django.contrib.sites.models import Site

        self.middleware = SubdomainURLRoutingMiddleware
        self.site = Site.objects.get_current()
        self.site.domain = self.DOMAIN
        self.site.save()

    @override_settings(
        DEFAULT_URL_SCHEME="http",
        ROOT_URLCONF=f"{URL_MODULE_PATH}.application",
        SUBDOMAIN_URLCONFS=prefix_values(
            {
                None: "marketing",
                "api": "api",
                "www": "marketing",
            },
            prefix=URL_MODULE_PATH,
        ),
        MIDDLEWARE=(
            "django.middleware.common.CommonMiddleware",
            "subdomains.middleware.SubdomainURLRoutingMiddleware",
        ),
    )
    def run(self, *args, **kwargs):
        super().run(*args, **kwargs)

    def get_path_to_urlconf(self, name):
        """
        Returns the full path to the given urlconf.
        """
        return ".".join((self.URL_MODULE_PATH, name))

    def get_host_for_subdomain(self, subdomain=None):
        """
        Returns the hostname for the provided subdomain.
        """
        if subdomain is not None:
            host = f"{subdomain}.{self.site.domain}"
        else:
            host = f"{self.site.domain}"
        return host


class SubdomainMiddlewareTestCase(SubdomainTestMixin, TestCase):
    def test_subdomain_attribute(self):
        def subdomain(subdomain_name):
            """
            Returns the subdomain associated with the request by the middleware
            for the given subdomain.
            """
            host = self.get_host_for_subdomain(subdomain_name)
            request = RequestFactory().get("/", HTTP_HOST=host)
            self.middleware.process_request_subdomain(request)
            return request.subdomain

        self.assertEqual(subdomain(None), None)
        self.assertEqual(subdomain("www"), "www")
        self.assertEqual(subdomain("www.subdomain"), "www.subdomain")
        self.assertEqual(subdomain("subdomain"), "subdomain")
        self.assertEqual(subdomain("another.subdomain"), "another.subdomain")

    def test_www_domain(self):
        def host(host):
            """
            Returns the subdomain for the provided HTTP Host.
            """
            request = RequestFactory().get("/", HTTP_HOST=host)
            self.middleware.process_request_subdomain(request)
            return request.subdomain

        self.site.domain = f"www.{self.DOMAIN}"
        self.site.save()

        with override_settings(REMOVE_WWW_FROM_DOMAIN=False):
            self.assertEqual(host(f"www.{self.DOMAIN}"), None)

            # Squelch the subdomain warning for cleaner test output, since we
            # already know that this is an invalid subdomain.
            with warnings.catch_warnings(record=True) as warnlist:
                self.assertEqual(host(f"www.subdomain.{self.DOMAIN}"), None)
                self.assertEqual(host(f"subdomain.{self.DOMAIN}"), None)

            # Trick pyflakes into not warning us about variable usage.
            del warnlist

            self.assertEqual(host(f"subdomain.www.{self.DOMAIN}"), "subdomain")
            self.assertEqual(host(f"www.subdomain.www.{self.DOMAIN}"), "www.subdomain")

        with override_settings(REMOVE_WWW_FROM_DOMAIN=True):
            self.assertEqual(host(f"www.{self.DOMAIN}"), "www")
            self.assertEqual(host(f"subdomain.{self.DOMAIN}"), "subdomain")
            self.assertEqual(host(f"subdomain.www.{self.DOMAIN}"), "subdomain.www")

    def test_case_insensitive_subdomain(self):
        host = f"WWW.{self.DOMAIN}"
        request = RequestFactory().get("/", HTTP_HOST=host)
        self.middleware.process_request_subdomain(request)
        self.assertEqual(request.subdomain, "www")

        host = f"www.{self.DOMAIN.upper()}"
        request = RequestFactory().get("/", HTTP_HOST=host)
        self.middleware.process_request_subdomain(request)
        self.assertEqual(request.subdomain, "www")


class SubdomainURLRoutingTestCase(SubdomainTestMixin, TestCase):
    def test_url_routing(self):
        def urlconf(subdomain):
            """
            Returns the URLconf associated with this request.
            """
            host = self.get_host_for_subdomain(subdomain)
            request = RequestFactory().get("/", HTTP_HOST=host)
            self.middleware.process_request_urlconf(request)
            return getattr(request, "urlconf", None)

        self.assertEqual(urlconf(None), self.get_path_to_urlconf("marketing"))
        self.assertEqual(urlconf("www"), self.get_path_to_urlconf("marketing"))
        self.assertEqual(urlconf("api"), self.get_path_to_urlconf("api"))

        # Falls through to the actual ROOT_URLCONF.
        self.assertEqual(urlconf("subdomain"), None)

    def test_appends_slash(self):
        for subdomain in (None, "api", "wildcard"):
            host = self.get_host_for_subdomain(subdomain)
            path = "/example"  # No trailing slash.
            response = self.client.get(path, HTTP_HOST=host)
            self.assertEqual(response.status_code, 301)

            # Whether the response's Location header contains the URL prefix
            # here doesn't actually matter, since it will be considered
            # relative to the request URL, which *did* include the HTTP Host
            # header. To pave over inconsistencies between Django versions, we
            # normalize them both to be prefixed with the requested host. (If a
            # *different* base host is returned in the Location header, this
            # should override our default base and error.)
            normalize = functools.partial(urlparse.urljoin, f"http://{host}/")

            self.assertEqual(
                normalize(response["Location"]),
                normalize(path + "/"),
            )


class SubdomainURLReverseTestCase(SubdomainTestMixin, TestCase):
    def test_url_join(self):
        self.assertEqual(urljoin(self.DOMAIN), f"http://{self.DOMAIN}")
        self.assertEqual(urljoin(self.DOMAIN, scheme="https"), f"https://{self.DOMAIN}")

        with override_settings(DEFAULT_URL_SCHEME="https"):
            self.assertEqual(urljoin(self.DOMAIN), f"https://{self.DOMAIN}")

        self.assertEqual(urljoin(self.DOMAIN, path="/example/"), f"http://{self.DOMAIN}/example/")

    def test_implicit_reverse(self):
        # Uses settings.SUBDOMAIN_URLCONFS[None], if it exists.
        # Otherwise would perform the same behavior as `test_wildcard_reverse`.
        self.assertEqual(reverse("home"), f"http://{self.DOMAIN}/")

    def test_explicit_reverse(self):
        # Uses explicitly provided settings.SUBDOMAIN_URLCONF[subdomain]
        self.assertEqual(reverse("home", subdomain="api"), f"http://api.{self.DOMAIN}/")
        self.assertEqual(reverse("view", subdomain="api"), f"http://api.{self.DOMAIN}/view/")

    def test_wildcard_reverse(self):
        # Falls through to settings.ROOT_URLCONF
        subdomain = "wildcard"
        self.assertEqual(reverse("home", subdomain), f"http://{subdomain}.{self.DOMAIN}/")
        self.assertEqual(reverse("view", subdomain), f"http://{subdomain}.{self.DOMAIN}/view/")

    def test_reverse_subdomain_mismatch(self):
        self.assertRaises(NoReverseMatch, lambda: reverse("view"))

    def test_reverse_invalid_urlconf_argument(self):
        self.assertRaises(
            TypeError,
            lambda: reverse("home", urlconf=self.get_path_to_urlconf("marketing")),
        )

    def test_using_not_default_urlconf(self):
        # Ensure that changing the currently active URLconf to something other
        # than the default still resolves wildcard subdomains correctly.
        set_urlconf(self.get_path_to_urlconf("api"))

        subdomain = "wildcard"

        # This will raise NoReverseMatch if we're using the wrong URLconf for
        # the provided subdomain.
        self.assertEqual(reverse("application", subdomain=subdomain), f"http://{subdomain}.{self.DOMAIN}/application/")


class SubdomainTemplateTagTestCase(SubdomainTestMixin, TestCase):
    def make_template(self, template):
        return Template("{% load subdomainurls %}" + template)

    def test_without_subdomain(self):
        defaults = {"view": "home"}
        template = self.make_template("{% url view %}")

        context = Context(defaults)
        rendered = template.render(context).strip()
        self.assertEqual(rendered, f"http://{self.DOMAIN}/")

    def test_with_subdomain(self):
        defaults = {"view": "home"}
        template = self.make_template("{% url view subdomain=subdomain %}")

        for subdomain in ("www", "api", "wildcard"):
            context = Context(dict(defaults, subdomain=subdomain))
            rendered = template.render(context).strip()
            self.assertEqual(rendered, f"http://{subdomain}.{self.DOMAIN}/")

    def test_no_reverse(self):
        template = self.make_template("{% url view subdomain=subdomain %}")

        context = Context({"view": "__invalid__"})
        self.assertRaises(NoReverseMatch, lambda: template.render(context))

    def test_implied_subdomain_from_request(self):
        template = self.make_template("{% url view %}")
        defaults = {"view": "home"}

        request = mock.Mock()
        request.subdomain = None

        context = Context(dict(defaults, request=request))
        rendered = template.render(context).strip()
        self.assertEqual(rendered, f"http://{self.DOMAIN}/")

        for subdomain in ("www", "api", "wildcard"):
            request = mock.Mock()
            request.subdomain = subdomain

            context = Context(dict(defaults, request=request))
            rendered = template.render(context).strip()
            self.assertEqual(rendered, f"http://{subdomain}.{self.DOMAIN}/")
