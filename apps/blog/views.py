from django.http import Http404
from django.shortcuts import get_object_or_404
from django.views.generic import ListView

from django_json_ld.views import JsonLdDetailView

from apps.blog.models import Article, Category, ArticleComment
from utils.permissions import check_content_permission


def article_content_view(request, pk):
    article_obj = get_object_or_404(Article.approves.all(), pk=pk)
    response = check_content_permission(request, article_obj)
    return response


class HomeView(ListView):
    queryset = Category.objects.filter(is_enable=True)
    template_name = 'blog/home.html'

    def get_context_data(self, *, object_list=None, **kwargs):
        return {'categories': Category.category_tree()}


class ArticleListView(ListView):
    queryset = Article.approves.all()
    template_name = 'blog/article_list.html'
    paginate_by = 12

    def __init__(self):
        super().__init__()
        self._category = None

    def get_queryset(self):
        try:
            self._category = Category.objects.get(id=self.kwargs['category_id'], is_enable=True)
        except Category.DoesNotExist:
            raise Http404()
        return super().get_queryset().filter(categories=self._category)

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data()
        context['category'] = self._category
        context['page_range'] = range(1, context['page_obj'].paginator.num_pages+1)
        return context


class ArticleDetailView(JsonLdDetailView):
    queryset = Article.approves.prefetch_related(
        'tags',
        'namads',
    ).select_related(
        'profile'
    )
    template_name = 'blog/article_detail.html'

    def get_context_data(self, **kwargs):
        article = self.get_object()
        context = super().get_context_data()
        context['keywords'] = ", ".join(article.tags.values_list('name', flat=True))
        context['comments'] = ArticleComment.approves.filter(article=article).select_related('user')
        return context
