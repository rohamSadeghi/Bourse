from django.conf import settings

settings.CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],
        },
    },
}
settings.CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '192.168.2.21',
        'KEY_PREFIX': 'HAMI_BOURSE_STAGING',
        'TIMEOUT': 10,
    }
}
