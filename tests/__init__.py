from django.conf import settings
import django

if not settings.configured:
    settings.configure(INSTALLED_APPS=('django.contrib.auth', 'django.contrib.contenttypes', 'tests.testapp',),
                       ROOT_URLCONF='tests.testapp.urls',
                       DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}})
    django.setup()
