from django.core.paginator import EmptyPage, Paginator
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Book
from .serializers import BookListSerializer

PAGE_SIZE = 20


class BookListView(APIView):
    """GET /api/books/ - paginated catalog (BOOK-F-010)."""

    permission_classes = [AllowAny]  # guests can browse (SAD 4.5)

    def get(self, request):
        try:
            page = int(request.query_params.get("page", "1"))
            if page < 1:
                raise ValueError
        except ValueError:
            return Response(
                {"code": "invalid_page", "message": "page must be a positive integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        paginator = Paginator(Book.objects.all(), PAGE_SIZE)
        try:
            books = list(paginator.page(page).object_list)
        except EmptyPage:
            books = []  # past the last page: empty list, not an error

        return Response(
            {
                "results": BookListSerializer(books, many=True).data,
                "page": page,
                "total": paginator.count,
            }
        )