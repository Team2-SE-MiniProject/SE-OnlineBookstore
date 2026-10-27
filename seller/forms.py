from django import forms
from django.core.exceptions import ValidationError

from catalog.models import Book


class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ["title", "author", "isbn", "genre", "description", "price", "stock", "cover"]
        labels = {"isbn": "ISBN", "cover": "Cover image link"}
        help_texts = {
            "isbn": "Optional.",
            "genre": "Optional, for example Fiction or Science.",
            "price": "Price in rupees, for example 499.00.",
            "stock": "Number of copies available to sell.",
            "cover": "Optional. A web link to the cover image.",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "price": forms.NumberInput(attrs={"step": "0.01", "min": "0.01", "inputmode": "decimal"}),
            "stock": forms.NumberInput(attrs={"step": "1", "min": "0", "inputmode": "numeric"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sync_aria()

    def full_clean(self):
        super().full_clean()
        self._sync_aria()

    def _sync_aria(self):
        """Tie hint and error text to each input for screen readers."""
        for name, field in self.fields.items():
            ids = []
            if field.help_text:
                ids.append(f"id_{name}_hint")
            if self.is_bound and name in self.errors:
                ids.append(f"id_{name}_error")
                field.widget.attrs["aria-invalid"] = "true"
            else:
                field.widget.attrs.pop("aria-invalid", None)
            if ids:
                field.widget.attrs["aria-describedby"] = " ".join(ids)

    def clean_price(self):
        price = self.cleaned_data.get("price")
        if price is None or price <= 0:
            raise ValidationError("Enter a price greater than zero.")
        return price

    def clean_title(self):
        title = (self.cleaned_data.get("title") or "").strip()
        if not title:
            raise ValidationError("Enter a title.")
        return title
