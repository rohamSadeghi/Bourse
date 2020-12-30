from django.core.cache import cache

from apps.blog.models import Category

CATEGORIES_TREE_CACHE_TIMEOUT = 4 * 60 * 60


def categories(request):
    """
    Return a lazy 'nav_categories' context variable
    """
    categories = cache.get('nav_categories')

    if categories is None:
        categories = Category.category_tree()
        cache.set('nav_categories', categories, CATEGORIES_TREE_CACHE_TIMEOUT)

    return {'nav_categories': categories}
