from django.contrib.auth import logout
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

# ensure_csrf_cookie makes sure the browser has a CSRF cookie, which the page's
# JavaScript sends back as a header when it calls the cart API.


@method_decorator(ensure_csrf_cookie, name="dispatch")
class BooksPageView(TemplateView):
    """Storefront home: the browsable, searchable book list."""

    template_name = "storefront/books.html"


@method_decorator(ensure_csrf_cookie, name="dispatch")
class LoginPageView(TemplateView):
    """Login form. It posts to the existing /accounts/login/ endpoint."""

    template_name = "storefront/login.html"


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CartPageView(TemplateView):
    """The logged-in user's cart. Anonymous visitors are sent to the login page."""

    template_name = "storefront/cart.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(
                request.get_full_path(), login_url=reverse("storefront:login")
            )
        return super().dispatch(request, *args, **kwargs)


@require_POST
def logout_view(request):
    logout(request)
    return redirect("storefront:books")