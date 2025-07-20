from django import template
from exam.models import Subscription

register = template.Library()

@register.simple_tag
def get_subscription_status():
    return Subscription.get_current_subscription()