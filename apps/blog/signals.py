from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from django_elasticsearch_dsl.registries import registry

from apps.blog.models import Article


@receiver(post_save, sender=Article)
def update_document(sender, instance, created, **kwargs):
    """
        Update document on added/changed records.
    """
    registry.update(instance)

    if not all([instance.is_enable, instance.approved_user]):
        registry.delete(instance, raise_on_error=False)


@receiver(post_delete, sender=Article)
def delete_document(sender, instance, **kwargs):
    """
        Update document on deleted records.
    """
    registry.delete(instance, raise_on_error=False)
