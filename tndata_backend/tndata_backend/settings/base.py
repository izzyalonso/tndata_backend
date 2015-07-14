"""
Django settings for tndata_backend project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

ADMINS = (
    ('Brad Montgomery', 'bkmontgomery@tndata.org'),
)
MANAGERS = ADMINS
DEFAULT_FROM_EMAIL = 'webmaster@tndata.org'
SERVER_EMAIL = 'webmaster@tndata.org'

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

SECRET_KEY = 'xt67918srm3f=0$#k%7quk+&pdtwy7#n=pfn%4kzyae$kxmw%j'
DEBUG = False
TEMPLATE_DEBUG = False
ALLOWED_HOSTS = [
    'localhost', '127.0.0.1',
    '.tndata.org', '.tndata.org.', '104.236.244.232',
    'brad.ngrok.io', 'tndata.ngrok.io',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates')
        ],
        'OPTIONS': {
            'loaders': [
                ('django.template.loaders.cached.Loader', [
                    'django.template.loaders.filesystem.Loader',
                    'django.template.loaders.app_directories.Loader',
                ]),
            ],
            'context_processors': (
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.debug",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.tz",
            ),
        },
    },
]


INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'django_extensions',
    'goals',
    'jsonfield',
    'notifications',
    'recurrence',
    'rest_framework',
    'rest_framework.authtoken',
    'survey',
    'userprofile',
    'utils',
)

# Settings for Google Cloud Messaging.
GCM = {
    'API_KEY': 'AIzaSyCi5AGkIhEWPrO8xo3ec3MIo7-tGlRtng0',
}

AUTHENTICATION_BACKENDS = (
    'utils.backends.EmailAuthenticationBackend',
    'django.contrib.auth.backends.ModelBackend',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.BrokenLinkEmailsMiddleware',  # Send email on 404
    'django.middleware.common.CommonMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'utils.middleware.TimezoneMiddleware',
)

ROOT_URLCONF = 'tndata_backend.urls'
WSGI_APPLICATION = 'tndata_backend.wsgi.application'

# Production Database settings.
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'tndata_backend',
        'USER': 'tndata_backend',
        'PASSWORD': 'plicater-nonurban-outlaw-moonfall',
        'HOST': '127.0.0.1',
        'PORT': '5432',
    }
}

# Caching
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}


# django.contrib.auth settings.
LOGIN_URL = 'login'  # Named url patter for the built-in auth
LOGOUT_URL = 'logout'
LOGIN_REDIRECT_URL = '/'


# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
TIME_FORMAT = "g:ia e"  # 5:30pm CDT
DATE_FORMAT = "N j, Y"  # Jan 3, 2015
DATETIME_FORMAT = "N j, Y g:iaO e"  # Jan. 3, 2015 5:30pm+200 CDT
SHORT_DATE_FORMAT = "m/d/Y"  # 01/03/2015
SHORT_DATETIME_FORMAT = "H:iO"  # 17:30+200

USE_I18N = True
USE_L10N = True
USE_TZ = True

# Media Uploads, default
MEDIA_ROOT = "/webapps/tndata_backend/uploads/"
MEDIA_URL = "http://app.tndata.org/media/"

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/
STATIC_URL = 'http://app.tndata.org/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'collected_static_files')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Messages tags: Updated to represent Foundation alert classes.
from django.contrib.messages import constants as message_constants
MESSAGE_TAGS = {
    message_constants.DEBUG: 'debug secondary',
    message_constants.INFO: 'info',
    message_constants.SUCCESS: 'success',
    message_constants.WARNING: 'warning',
    message_constants.ERROR: 'error alert'
}


# Django Rest Framework
REST_FRAMEWORK = {
    'PAGINATE_BY': 100,  # Turns on Pagination.
    # Testing: http://www.django-rest-framework.org/api-guide/testing/#configuration
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
}


# django-cors-headers
# https://github.com/ottoyiu/django-cors-headers/
CORS_ORIGIN_ALLOW_ALL = False
CORS_ORIGIN_WHITELIST = (
    'localhost',
    '127.0.0.1'
)


# This is just the test Web/api token.
# https://api.slack.com/web
SLACK_API_TOKEN = 'xoxp-4823219390-6288403475-6868819906-193c4a'
SLACK_CHANNEL = "#tech"
SLACK_USERNAME = "app.tndata.org"
