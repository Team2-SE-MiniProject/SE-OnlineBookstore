from rest_framework import serializers

from .models import Book


class BookListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ["id", "title", "author", "price", "cover"]

class BookDetailSerializer(serializers.ModelSerializer):
    in_stock = serializers.SerializerMethodField()
    can_add_to_cart = serializers.SerializerMethodField()
    can_add_to_wishlist = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            "id", "title", "author", "isbn", "genre", "description",
            "price", "cover", "stock", "in_stock",
            "can_add_to_cart", "can_add_to_wishlist", "reviews",
        ]

    def get_in_stock(self, obj):
        return obj.stock > 0

    def get_can_add_to_cart(self, obj):
        return obj.stock > 0

    def get_can_add_to_wishlist(self, obj):
        return True

    def get_reviews(self, obj):
        # Placeholder section, filled in Sprint 2 (BOOK-F-060-062)
        return {"average_rating": None, "count": 0, "items": []}
