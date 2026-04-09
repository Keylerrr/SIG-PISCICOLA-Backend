from .base import *

SECRET_KEY = "django-insecure-dev"
DEBUG = True
ALLOWED_HOSTS = ["*"]
FRONTEND_URL = "https://backend-pongase-trucha.onrender.com"

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "pawsy1225@gmail.com"
EMAIL_HOST_PASSWORD = "snih gqwz fcyc qzkv"
DEFAULT_FROM_EMAIL = "pawsy1225@gmail.com"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "psicola",
        "USER": "psicola_user",
        "PASSWORD": "woHPZ3R4nuEHiqH5D3wwEKpHwd91hSCI",
        "HOST": "dpg-d7bvbs0sfn5c73b1rvig-a.virginia-postgres.render.com",
        "PORT": "5432",
    }
}


