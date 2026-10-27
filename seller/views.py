import csv

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.db.models import ProtectedError
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, TemplateView, UpdateView

from catalog.models import Book

from . import services
from .forms import BookForm
from .permissions import is_seller


class SellerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Anonymous visitors go to the storefront login page; logged-in non-sellers get 403."""

    login_url = "storefront:login"
    redirect_field_name = "next"

    def test_func(self):
        return is_seller(self.request.user)

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied
        return super().handle_no_permission()


class OwnBookMixin(SellerRequiredMixin):
    """Only the seller's own books exist as far as these views are concerned.

    Someone else's book id therefore gives a 404, so a seller can neither see
    nor change another seller's listing.
    """

    model = Book

    def get_queryset(self):
        return Book.objects.filter(seller=self.request.user)


class DashboardView(SellerRequiredMixin, TemplateView):
    template_name = "seller/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get("q", "").strip()
        books = list(services.seller_books(self.request.user, query))
        for book in books:
            book.state = services.stock_state(book.stock)
        context.update(
            kpis=services.inventory_kpis(self.request.user),
            books=books,
            q=query,
            recent_orders=services.recent_orders(self.request.user),
        )
        return context


class BookCreateView(SellerRequiredMixin, CreateView):
    model = Book
    form_class = BookForm
    template_name = "seller/book_form.html"
    success_url = reverse_lazy("seller:dashboard")
    extra_context = {"heading": "Add a book", "submit_label": "Add book"}

    def form_valid(self, form):
        form.instance.seller = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f"{self.object.title} was added.")
        return response


class BookUpdateView(OwnBookMixin, UpdateView):
    form_class = BookForm
    template_name = "seller/book_form.html"
    success_url = reverse_lazy("seller:dashboard")
    extra_context = {"heading": "Edit book", "submit_label": "Save changes"}

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"{self.object.title} was updated.")
        return response


class BookDeleteView(OwnBookMixin, DeleteView):
    template_name = "seller/book_confirm_delete.html"
    success_url = reverse_lazy("seller:dashboard")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["has_orders"] = self.object.order_items.exists()
        return context

    def form_valid(self, form):
        title = self.object.title
        try:
            self.object.delete()
        except ProtectedError:
            messages.error(
                self.request,
                f"{title} has been ordered, so it cannot be deleted. Set its stock to 0 instead.",
            )
            return redirect("seller:dashboard")
        messages.success(self.request, f"{title} was deleted.")
        return redirect(self.success_url)


class AnalyticsView(SellerRequiredMixin, TemplateView):
    template_name = "seller/analytics.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        months = services.parse_range(self.request.GET.get("months"))
        context.update(
            report=services.sales_report(self.request.user, months),
            months=months,
            ranges=services.ALLOWED_RANGES,
        )
        return context


class AnalyticsExportView(SellerRequiredMixin, View):
    def get(self, request):
        months = services.parse_range(request.GET.get("months"))
        report = services.sales_report(request.user, months)
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="seller-sales-{months}-months.csv"'
        writer = csv.writer(response)
        writer.writerow(["Month", "Revenue (INR)", "Units sold", "Orders"])
        for row in report["monthly"]:
            writer.writerow(
                [services.csv_safe(row["label"]), row["revenue"], row["units"], row["orders"]]
            )
        return response
