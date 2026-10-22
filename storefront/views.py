from django.views.generic import TemplateView


class BooksPageView(TemplateView):
    """Storefront home: the browsable, searchable book list."""

    template_name = "storefront/books.html"