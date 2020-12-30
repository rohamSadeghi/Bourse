##About hh

####Hh is a project that let people read articles about bourse indicators.
```


### ENVIRONMENT VARIABLES ###

DEBUG = True
DEVEL = True

ALLOWED_HOSTS = 'localhost, 127.0.0.1, '
SECRET_KEY = ''

#### Database variables ###
DB_ENGINE = ''
DB_NAME = ''
DB_USER = ''
DB_PASS = ''
DB_HOST = 'localhost'
DB_PORT = '5432'

### Celery Variavles ###
CELERY_TIMEZONE = 'Asia/Tehran'
CELERY_USER = ""
CELERY_PASS = ""
CELERY_HOST = "localhost:5672/"

### Cache variables ###

CACHE_BACKEND = 'django.core.cache.backends.memcached.MemcachedCache'
CACHE_LOCATION = ''
CACHE_PREFIX = 'HAMI_BOURSE'

### Redis variables ###
REDIS_HOST = 127.0.0.1
REDIS_PORT = 6379
REDIS_PASS = ''

### Sentry variables ###

SENTRY_KEY = ''
SENTRY_HOST = ''
SENTRY_PROJECT_ID = ''
SENTRY_ENV = ''

### ELK variables ###

ELASTICSEARCH_HOST = 'localhost'
ELASTICSEARCH_PORT = '9200'
ELASTICSEARCH_USER = ''
ELASTICSEARCH_PASS = ''
ARTICLE_INDEX_NAME = ''

### Simple JWT variables ###
ACCESS_TOKEN_LIFETIME = 120
REFRESH_TOKEN_LIFETIME = 3600

### SMS gate way variables ###

SMS_GATE_WAY_URL = ''
SMS_GATE_WAY_TOKEN = ''
VERIFY_CODE_MIN = 10000
VERIFY_CODE_MAX = 99999

### Payment gateway variables ###
PAYMENT_GATE_WAY_URL = ''
PAYMENT_SERVICE_SECRET = ''

ARTICLE_THUMBNAIL_SIZE = '400x300'

### Tsetmc Variables ###
BASE_URL = 'http://tsetmc.com'
SECTION_QUEUE_NAME = 'sections'

### Crontab Variables ###
SECTION_QUEUE_NAME = 'sections'
FIND_AND_INSERT_NAMADS_CRONTAB = "{'day_of_week': '0-3, 6', 'hour': '*/4', 'minute': '0'}"
# Determines insert_sections crontab period per minute (periodic task)
INSERT_SECTIONS_CRONTAB = "{'day_of_week': '0-3, 6', 'hour': '9-12', 'minute': '*'}"
INSERT_NAMAD_DAILY_CRONTAB = "{'day_of_week': '0-3, 6', 'hour': '9-10', 'minute': '10-30/5'}"
INSERT_LAST_HISTORY_CRONTAB = "{'day_of_week': '0-3, 6', 'hour': '3', 'minute': '0'}"
CHECK_NAMAD_STATUS_CRONTAB = "{'day_of_week': '0-3, 6', 'minute': '*/15'}"

### Media and static variables ###
MEDIA_URL = 'Domain/media/'
STATIC_URL = 'Domain/static/'
