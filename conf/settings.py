import ast
from datetime import timedelta

from pathlib import Path

from decouple import config, Csv

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
DEBUG = config('DEBUG', default=False, cast=bool)
DEVEL = config('DEVEL', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost', cast=Csv())

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config("SECRET_KEY")

# Application definition

INSTALLED_APPS = [
    # Local
    'apps.accounts',
    'apps.blog',
    'apps.commenting',
    'apps.namads',
    'apps.transactions',
    'apps.filters',
    'apps.tsetmc',

    # Third parties
    'channels',
    'django_filters',
    'rest_framework',
    'rest_framework_swagger',
    'taggit',
    'taggit_autosuggest',
    'django_elasticsearch_dsl',
    'django_elasticsearch_dsl_drf',
    'ckeditor',
    'sorl.thumbnail',
    'django_json_ld',

    # Default
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'conf.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates', ],
        'APP_DIRS': False,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.blog.context_processors.categories',
            ],
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ],
        },
    },
]

ASGI_APPLICATION = "conf.asgi.application"
WSGI_APPLICATION = 'conf.wsgi.application'

# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': config('DB_ENGINE', default='django.db.backends.postgresql_psycopg2'),
        'HOST': config('DB_HOST', default=''),
        'PORT': config('DB_PORT', default=''),
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASS'),
    }
}

# Redis configs
REDIS_BASE_URL = "redis://:{redis_pass}@{redis_host}:{redis_port}/0"
REDIS_URL = REDIS_BASE_URL.format(
    redis_pass=config('REDIS_PASS'),
    redis_host=config('REDIS_HOST', default='localhost'),
    redis_port=config('REDIS_PORT', default=6379, cast=int)
)
CACHE_KEY_PREFIX = config('CACHE_PREFIX', default='HAMIBOURSE')
CACHES = {
    'default': {
        'BACKEND': config('CACHE_BACKEND'),
        'LOCATION': config('CACHE_LOCATION'),
        'KEY_PREFIX': CACHE_KEY_PREFIX,
        'TIMEOUT': None,
    },
    "redis": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient"
        },
        "KEY_PREFIX": CACHE_KEY_PREFIX,
        'TIMEOUT': None,
    }
}
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(REDIS_URL), ],
        },
    },
}
# Celery Config
CELERY_TIMEZONE = 'Asia/Tehran'
CELERY_ENABLE_UTC = False
# CELERY_RESULT_BACKEND = 'rpc://'
CELERY_BROKER_URL = 'amqp://%(USER)s:%(PASS)s@%(HOST)s' % {
    'USER': config('CELERY_USER'),
    'PASS': config('CELERY_PASS'),
    'HOST': config('CELERY_HOST'),
}
FIND_AND_INSERT_NAMADS_CRONTAB = ast.literal_eval(config('FIND_AND_INSERT_NAMADS_CRONTAB'))
INSERT_SECTIONS_CRONTAB = ast.literal_eval(config('INSERT_SECTIONS_CRONTAB'))
INSERT_NAMAD_DAILY_CRONTAB = ast.literal_eval(config('INSERT_NAMAD_DAILY_CRONTAB'))
INSERT_LAST_HISTORY_CRONTAB = ast.literal_eval(config('INSERT_LAST_HISTORY_CRONTAB'))
CHECK_NAMAD_STATUS_CRONTAB = ast.literal_eval(config('CHECK_NAMAD_STATUS_CRONTAB'))
TSETMC_CONNECTION_READ_TIMEOUT = config('TSETMC_CONNECTION_READ_TIMEOUT', default=6, cast=int)
TSETMC_CONNECTION_CONNECT_TIMEOUT = config('TSETMC_CONNECTION_CONNECT_TIMEOUT', default=3, cast=int)

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.coreapi.AutoSchema',
    'EXCEPTION_HANDLER': 'utils.exception_handlers.custom_exception_handler',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_RATES': {
        'register': '2/minute',
        'free_register': '5/hour'
    },
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=config('ACCESS_TOKEN_LIFETIME', default=120, cast=int)),
    'REFRESH_TOKEN_LIFETIME': timedelta(minutes=config('REFRESH_TOKEN_LIFETIME', default=3600, cast=int)),
    'ROTATE_REFRESH_TOKENS': True,
}

# ElasticSearch configs
ELK_BASE_URL = 'elasticsearch://{username}:{password}@{host_ip}:{host_port}'
ELASTIC_SEARCH_URL = ELK_BASE_URL.format(
    username=config('ELASTICSEARCH_USER'),
    password=config('ELASTICSEARCH_PASS'),
    host_ip=config('ELASTICSEARCH_HOST'),
    host_port=config('ELASTICSEARCH_PORT')
)
ELASTICSEARCH_DSL = {
    'default': {
        'hosts': [ELASTIC_SEARCH_URL]
    },
}
ARTICLE_INDEX_NAME = config('ARTICLE_INDEX_NAME')

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Authentication
AUTH_USER_MODEL = 'accounts.User'
AUTHENTICATION_BACKENDS = (
    'apps.accounts.backends.SMSBackend',
    'django.contrib.auth.backends.ModelBackend',
)

# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Tehran'
USE_I18N = False
USE_L10N = False
USE_TZ = False

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/
STATIC_ROOT = BASE_DIR / 'static'
STATIC_URL = config('STATIC_URL', default='/static/')

MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = config('MEDIA_URL', default='/media/')

if DEVEL is False:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration

    SENTRY_KEY = config('SENTRY_KEY')
    SENTRY_HOST = config('SENTRY_HOST')
    SENTRY_PROJECT_ID = config('SENTRY_PROJECT_ID')
    SENTRY_ENV = config('SENTRY_ENV')

    sentry_sdk.init(
        dsn=f"https://{SENTRY_KEY}@{SENTRY_HOST}/{SENTRY_PROJECT_ID}",
        integrations=[DjangoIntegration(), CeleryIntegration()],
        default_integrations=False,

        # If you wish to associate users to errors (assuming you are using
        # django.contrib.auth) you may enable sending PII data.
        send_default_pii=True,

        # Custom settings
        debug=DEBUG,
        environment=SENTRY_ENV
    )
else:
    CORS_ORIGIN_ALLOW_ALL = True
    INSTALLED_APPS.append(
        'corsheaders'
    )
    MIDDLEWARE.append(
        'corsheaders.middleware.CorsMiddleware',
    )

LOG_DIR = BASE_DIR / 'logs'
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '[%(asctime)s] %(levelname)s %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'verbose': {
            'format': '[%(asctime)s] %(levelname)s [%(filename)s.%(funcName)s:%(lineno)d] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
            'formatter': 'verbose'
        },
        'file': {
            'level': 'DEBUG' if DEBUG else 'INFO',
            'class': 'logging.FileHandler',
            'filename': LOG_DIR / 'django.log',
            'formatter': 'verbose' if DEBUG else 'simple',
        },
        'db_queries': {
            'level': 'DEBUG',
            'filters': ['require_debug_true'],
            'class': 'logging.FileHandler',
            'filename': LOG_DIR / 'db_queries.log',
        },
        'null': {
            'level': 'DEBUG',
            'class': 'logging.NullHandler',
        },
    },
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',
            'handlers': ['db_queries'],
            'propagate': False,
        },
        'accounts': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
        },
        'blog': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
        },
        'transactions': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
        },
        'commenting': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
        },
        'namads': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
        },
        'tsetmc': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
        },
        'tsetmc.tasks': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'filters.tasks': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'full',
        'height': 300,
        'width': 800,
        'resize_dir': 'both',
        'enterMode': 2,  # 1 for add p tags and 2 for add br tags
        'extraPlugins': 'video',
        'allowedContent': True,
    },
}

SMS_GATE_WAY_URL = config('SMS_GATE_WAY_URL', default='')
SMS_GATE_WAY_TOKEN = config('SMS_GATE_WAY_TOKEN', default='')
VERIFY_CODE_MIN = config('VERIFY_CODE_MIN', cast=int, default=10000)
VERIFY_CODE_MAX = config('VERIFY_CODE_MAX', cast=int, default=99999)

PAYMENT_GATE_WAY_URL = config('PAYMENT_GATE_WAY_URL', default='')
PAYMENT_SERVICE_SECRET = config('PAYMENT_SERVICE_SECRET', default='')

ARTICLE_THUMBNAIL_SIZE = config('ARTICLE_THUMBNAIL_SIZE', default='400x300')
