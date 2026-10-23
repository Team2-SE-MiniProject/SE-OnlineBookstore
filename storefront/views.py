from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

# ensure_csrf_cookie makes sure the browser has a CSRF cookie, which the page's
# JavaScript sends back as a header when it calls the APIs.


@method_decorator(ensure_csrf_cookie, name="dispatch")
class BooksPageView(TemplateView):
    """Storefront home: the browsable, searchable book list."""

    template_name = "storefront/books.html"


@method_decorator(ensure_csrf_cookie, name="dispatch")
class LoginPageView(TemplateView):
    """Login form. It posts to the existing /accounts/login/ endpoint."""

    template_name = "storefront/login.html"


class StorefrontLoginRequired(LoginRequiredMixin):
    """Anonymous visitors are sent to our login page, then back to where they were."""

    login_url = "storefront:login"
    redirect_field_name = "next"


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CartPageView(StorefrontLoginRequired, TemplateView):
    template_name = "storefront/cart.html"


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CheckoutPageView(StorefrontLoginRequired, TemplateView):
    template_name = "storefront/checkout.html"


@require_POST
def logout_view(request):
    logout(request)
    return redirect("storefront:books")