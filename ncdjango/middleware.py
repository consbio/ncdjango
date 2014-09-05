from tastypie.authentication import ApiKeyAuthentication


class TastypieApiKeyMiddleware(object):
    """Middleware to authenticate users using API keys for regular Django views"""

    def process_request(self, request):
        ApiKeyAuthentication().is_authenticated(request)