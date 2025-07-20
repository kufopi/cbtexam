# exam/middleware.py
from django.http import HttpResponseRedirect
from django.urls import reverse
from .models import Subscription
from django.utils import timezone

class SubscriptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.exempt_paths = [
            reverse('activate_subscription'),
            reverse('subscription_expired'),
            reverse('admin:index'),
            '/static/',
            '/media/',
            '/logout/',  # Also exempt logout to prevent loops
            '/login/',
        ]
    
    def __call__(self, request):
        # Skip middleware for exempt paths
        if any(request.path.startswith(path) for path in self.exempt_paths):
            return self.get_response(request)
            
        subscription = Subscription.get_current_subscription()
        
        # Redirect to activation page if subscription expired
        if not subscription.is_active():
            if request.path != reverse('subscription_expired'):
                return HttpResponseRedirect(reverse('subscription_expired'))
        
        response = self.get_response(request)
        return response