from decimal import Decimal, InvalidOperation

from django.core.paginator import EmptyPage, Paginator
from django.db.models import Avg, F, Q
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Book
from .serializers import BookDetailSerializer, BookListSerializer

PAGE_SIZE = 20

# sort value -> ordering. The extra "id" keeps pagination stable when values tie.
SORTS = {
    "title": ("title", "id"),
    "price_asc": ("price", "id"),
    "price_desc": ("-price", "id"),
    "newest": ("-created_at", "-id"),
}

#list of valid sorts
SORT_OPTIONS = [*SORTS, "rating"]


def bad_request(code, message):
    return Response(
        {"code": code, "message": message}, status=status.HTTP_400_BAD_REQUEST
    )


def parse_price(raw):
    value = Decimal(raw)  # raises InvalidOperation for text like "abc"
    if not value.is_finite() or value < 0:  # rejects NaN, Infinity and negatives
        raise InvalidOperation
    return value


class BookListView(APIView):
    """
    GET /api/books/ - paginated catalog with search, filter and sort.
    BOOK-F-010 (catalog) and BOOK-F-011 (search, filter, sort).

    Query params:
      q          search words; every word must match title, author, genre or ISBN
      genre      exact genre (case-insensitive)
      min_price  lowest price
      max_price  highest price
      sort       title (default) | price_asc | price_desc | newest
      page       page number, starting at 1
    """

    permission_classes = [AllowAny]  # guests can browse (SAD 4.5)

    def get(self, request):
        params = request.query_params

        try:
            page = int(params.get("page", "1"))
            if page < 1:
                raise ValueError
        except ValueError:
            return bad_request("invalid_page", "page must be a positive integer.")

        sort = params.get("sort", "title")
        if sort not in SORT_OPTIONS:
            return bad_request(
                "invalid_sort", f"sort must be one of: {', '.join(SORT_OPTIONS)}."
            )

        books = Book.objects.all()

        for term in params.get("q", "").split():
            match = (
                Q(title__icontains=term)
                | Q(author__icontains=term)
                | Q(genre__icontains=term)
                | Q(isbn__icontains=term)
            )
            digits = term.replace("-", "")  # lets 978-0-... match a stored 9780...
            if digits and digits != term:
                match |= Q(isbn__icontains=digits)
            books = books.filter(match)

        genre = params.get("genre", "").strip()
        if genre:
            books = books.filter(genre__iexact=genre)

        try:
            if params.get("min_price"):
                books = books.filter(price__gte=parse_price(params["min_price"]))
            if params.get("max_price"):
                books = books.filter(price__lte=parse_price(params["max_price"]))
        except InvalidOperation:
            return bad_request(
                "invalid_price", "min_price and max_price must be non-negative numbers."
            )

        if sort == "rating":
            books = books.annotate(avg_rating=Avg("reviews__rating"))
            ordering = (F("avg_rating").desc(nulls_last=True), "id")
        else:
            ordering = SORTS[sort]

        paginator = Paginator(books.order_by(*ordering), PAGE_SIZE)
        
        try:
            page_books = list(paginator.page(page).object_list)
        except EmptyPage:
            page_books = []  # past the last page: empty list, not an error

        return Response(
            {
                "results": BookListSerializer(page_books, many=True).data,
                "page": page,
                "total": paginator.count,
            }
        )

class BookDetailView(APIView):
    """
    GET /api/books/<id>/ - full details of one book.
    SRS 2.2 (Product detail view with ratings and reviews).
    """

    permission_classes = [AllowAny]  # guests can browse

    def get(self, request, pk):
        try:
            book = Book.objects.get(pk=pk)
        except Book.DoesNotExist:
            return Response(
                {"code": "not_found", "message": "Book not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(BookDetailSerializer(book).data)
