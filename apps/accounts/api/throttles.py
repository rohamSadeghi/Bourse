from rest_framework.throttling import ScopedRateThrottle, AnonRateThrottle


class PhoneNumberScopedRateThrottle(ScopedRateThrottle):
    def allow_request(self, request, view):
        # We can only determine the scope once we're called by the view.
        self.scope = getattr(view, self.scope_attr, None)

        # If a view does not have a `throttle_scope` always allow the request
        if not self.scope:
            return True

        # In order to throttle ip if phone number is not in data
        if not 'phone_number' in request.data:
            view.throttle_scope = 'free_register'

        # Determine the allowed request rate as we normally would during
        # the `__init__` call.
        self.rate = self.get_rate()
        self.num_requests, self.duration = self.parse_rate(self.rate)

        # We can now proceed as normal.
        return super().allow_request(request, view)

    def get_cache_key(self, request, view):
        if 'phone_number' in request.data:
            return self.cache_format % {
                'scope': self.scope,
                'ident': request.data['phone_number']
            }

        return super().get_cache_key(request, view)


class IPThrottle(ScopedRateThrottle):
    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident,
        }


class RegisterThrottle(AnonRateThrottle):
    rate = '3/minute'
