from .base import *

SECRET_KEY = "django-insecure-dev"
DEBUG = True
ALLOWED_HOSTS = ["*"]
CORS_ALLOW_ALL_ORIGINS = True
BACKEND_URL = "http://localhost:3000"

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
        "NAME": "piscicola",
        "USER": "piscicola_user",
        "PASSWORD": "STtIkSjHtk1gV0GEYomHQ27mNRV5mvA3",
        "HOST": "dpg-d7eq1c3bc2fs738ckjlg-a.virginia-postgres.render.com",
        "PORT": "5432",
        "OPTIONS": {
            "sslmode": "require",
        },
    }
}
