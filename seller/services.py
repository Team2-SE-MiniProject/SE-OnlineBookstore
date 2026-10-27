"""Query and report logic for the seller pages (kept out of the views so it is easy to test).

Sales are read from OrderItem rows for books the seller owns. Orders whose status
is cancelled/canceled/failed (any letter case) are not counted as sales.
"""
from datetime import date, datetime
from decimal import Decimal

from django.conf import settings
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum, Value
from django.db.models.functions import Coalesce, TruncMonth
from django.utils import timezone

from catalog.models import Book
from orders.models import Order, OrderItem

LOW_STOCK_THRESHOLD = 5
ALLOWED_RANGES = (3, 6, 12)
DEFAULT_RANGE = 12
EXCLUDED_STATUSES = ("cancelled", "canceled", "failed")

MONEY = DecimalField(max_digits=14, decimal_places=2)
ZERO = Value(Decimal("0.00"), output_field=MONEY)
LINE_TOTAL = ExpressionWrapper(F("quantity") * F("unit_price"), output_field=MONEY)


def stock_state(stock):
    if stock <= 0:
        return {"label": "Out of stock", "icon": "✖", "css": "bad"}
    if stock <= LOW_STOCK_THRESHOLD:
        return {"label": "Low stock", "icon": "⚠", "css": "warn"}
    return {"label": "In stock", "icon": "✔", "css": "ok"}


def seller_books(seller, query=""):
    books = Book.objects.filter(seller=seller)
    query = (query or "").strip()
    if query:
        books = books.filter(
            Q(title__icontains=query)
            | Q(author__icontains=query)
            | Q(genre__icontains=query)
            | Q(isbn__icontains=query)
        )
    return books.order_by("title")


def counted_items(seller):
    """Order lines for the seller's books, minus cancelled/failed orders."""
    items = OrderItem.objects.filter(book__seller=seller)
    for status in EXCLUDED_STATUSES:
        items = items.exclude(order__status__iexact=status)
    return items


def inventory_kpis(seller):
    agg = Book.objects.filter(seller=seller).aggregate(
        titles=Count("id"),
        units=Coalesce(Sum("stock"), 0),
        low=Count("id", filter=Q(stock__gte=1, stock__lte=LOW_STOCK_THRESHOLD)),
        out=Count("id", filter=Q(stock=0)),
    )
    sold = counted_items(seller).aggregate(n=Coalesce(Sum("quantity"), 0))["n"]
    return {
        "titles": agg["titles"],
        "units": agg["units"],
        "low_stock": agg["low"],
        "out_of_stock": agg["out"],
        "units_sold": sold,
    }


def recent_orders(seller, limit=5):
    seller_total = Sum(
        ExpressionWrapper(F("items__quantity") * F("items__unit_price"), output_field=MONEY),
        filter=Q(items__book__seller=seller),
    )
    return list(
        Order.objects.filter(items__book__seller=seller)
        .select_related("user")
        .annotate(seller_total=seller_total)
        .order_by("-created_at", "-id")[:limit]
    )


def parse_range(value):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return DEFAULT_RANGE
    return number if number in ALLOWED_RANGES else DEFAULT_RANGE


def month_starts(count, today=None):
    """First day of each of the last `count` months, oldest first, ending this month."""
    today = today or timezone.localdate()
    months = []
    for back in range(count - 1, -1, -1):
        year, month = today.year, today.month - back
        while month <= 0:
            month += 12
            year -= 1
        months.append(date(year, month, 1))
    return months


def _start_of(day):
    moment = datetime(day.year, day.month, day.day)
    return timezone.make_aware(moment) if settings.USE_TZ else moment


def sales_report(seller, months_back, today=None):
    months = month_starts(months_back, today)
    items = counted_items(seller).filter(order__created_at__gte=_start_of(months[0]))

    grouped = (
        items.annotate(month=TruncMonth("order__created_at"))
        .values("month")
        .annotate(
            revenue=Sum(LINE_TOTAL),
            units=Sum("quantity"),
            orders=Count("order", distinct=True),
        )
    )
    by_month = {(row["month"].year, row["month"].month): row for row in grouped}

    monthly = []
    for first in months:
        row = by_month.get((first.year, first.month))
        monthly.append(
            {
                "label": first.strftime("%b %Y"),
                "short": first.strftime("%b"),
                "revenue": row["revenue"] if row else Decimal("0.00"),
                "units": row["units"] if row else 0,
                "orders": row["orders"] if row else 0,
            }
        )

    totals = items.aggregate(
        revenue=Coalesce(Sum(LINE_TOTAL), ZERO),
        units=Coalesce(Sum("quantity"), 0),
        orders=Count("order", distinct=True),
    )
    orders = totals["orders"]
    average = (totals["revenue"] / orders).quantize(Decimal("0.01")) if orders else Decimal("0.00")

    change = None
    if len(monthly) >= 2 and monthly[-2]["revenue"] > 0:
        change = round(float((monthly[-1]["revenue"] - monthly[-2]["revenue"]) / monthly[-2]["revenue"] * 100), 1)

    top_books = list(
        items.values("book_id", "book__title")
        .annotate(units=Sum("quantity"), revenue=Sum(LINE_TOTAL))
        .order_by("-units", "book__title")[:5]
    )
    genres = [
        {"genre": row["book__genre"] or "Uncategorised", "revenue": row["revenue"]}
        for row in items.values("book__genre").annotate(revenue=Sum(LINE_TOTAL)).order_by("-revenue")
    ]

    return {
        "months": months_back,
        "monthly": monthly,
        "revenue": totals["revenue"],
        "units": totals["units"],
        "orders": orders,
        "average_order_value": average,
        "change_percent": change,
        "top_books": top_books,
        "genres": genres,
        "chart": chart_geometry(monthly),
    }


def chart_geometry(monthly):
    """Pre-computed SVG numbers (as strings) so the template needs no JavaScript."""
    width, height = 720, 300
    left, right, top, bottom = 70, 10, 20, 50
    highest = max((m["revenue"] for m in monthly), default=Decimal("0")) or Decimal("1")
    slot = (width - left - right) / max(len(monthly), 1)
    bars = []
    for index, month in enumerate(monthly):
        bar_height = (height - top - bottom) * float(month["revenue"] / highest)
        x = left + index * slot + slot * 0.15
        bar_width = slot * 0.7
        bars.append(
            {
                "x": f"{x:.1f}",
                "y": f"{height - bottom - bar_height:.1f}",
                "w": f"{bar_width:.1f}",
                "h": f"{bar_height:.1f}",
                "cx": f"{x + bar_width / 2:.1f}",
                "short": month["short"],
                "label": month["label"],
                "revenue": month["revenue"],
            }
        )
    return {
        "width": width,
        "height": height,
        "left": left,
        "right_edge": width - right,
        "top": top,
        "baseline": height - bottom,
        "label_y": height - bottom + 16,
        "max_value": highest,
        "bars": bars,
    }


def csv_safe(value):
    """Stop spreadsheet programs from running text that starts like a formula."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value
