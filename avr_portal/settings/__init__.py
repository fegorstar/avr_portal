import os
from decouple import config
from django.core.exceptions import ImproperlyConfigured

ENV_SETTING = config('ENV_SETTING')

if ENV_SETTING == 'development':
    from .development import *
elif ENV_SETTING == 'production':
    from .production import *
else:
    raise ImproperlyConfigured(
        "ENV_SETTING environment variable is not set correctly.")
