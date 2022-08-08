import logging
import operator
import re

from django.conf import settings
from django.utils.cache import patch_vary_headers

from subdomains.utils import get_domain

logger = logging.getLogger(__name__)
lower = operator.methodcaller("lower")

UNSET = object()


class SubdomainURLRoutingMiddleware:
    """
    A middleware class that allows for subdomain-based URL routing.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        self.process_request_subdomain(request)
        self.process_request_urlconf(request)
        response = self.get_response(request)
        self.process_response(response)
        return response

    @staticmethod
    def process_request_subdomain(request):
        domain, host = map(lower, (get_domain(), request.get_host()))

        pattern = r"^(?:(?P<subdomain>.*?)\.)?%s(?::.*)?$" % re.escape(domain)
        matches = re.match(pattern, host)

        if matches:
            request.subdomain = matches.group("subdomain")
        else:
            request.subdomain = None
            logger.warning(
                "The host {host} does not belong to the domain {domain}, "
                "unable to identify the subdomain for this request".format(
                    host=request.get_host(),
                    domain=domain,
                )
            )

    @staticmethod
    def process_request_urlconf(request):
        """
        Sets the current request's ``urlconf`` attribute to the urlconf
        associated with the subdomain, if it is listed in
        ``settings.SUBDOMAIN_URLCONFS``.
        """
        SubdomainURLRoutingMiddleware.process_request_subdomain(request)
        subdomain = getattr(request, "subdomain", UNSET)

        if subdomain is not UNSET:
            urlconf = settings.SUBDOMAIN_URLCONFS.get(subdomain)
            if urlconf is not None:
                logger.debug(f"Using urlconf {repr(urlconf)} for subdomain: {repr(subdomain)}")
                request.urlconf = urlconf

    @staticmethod
    def process_response(response):
        """
        Forces the HTTP ``Vary`` header onto requests to avoid having responses
        cached across subdomains.
        """
        if getattr(settings, "FORCE_VARY_ON_HOST", True):
            patch_vary_headers(response, ("Host",))
        return
