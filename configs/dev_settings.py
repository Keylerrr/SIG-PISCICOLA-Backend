from project.settings import *

DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "psicola",
        "USER": "postgres",
        "PASSWORD": "test123",
        "HOST": "database-db-1",
        "PORT": "5432",
    }
}
