from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated

from accounts.models import Address


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            "id",
            "recipient_name",
            "line1",
            "line2",
            "city",
            "state",
            "postal_code",
            "country",
            "phone",
            "is_default",
        ]
        read_only_fields = ["id", "is_default"]


class AddressListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/addresses/  - the logged-in user's delivery addresses.
    POST /api/addresses/  - add one (the first address becomes the default).
    """

    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # a plain list is enough here

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user).order_by("-is_default", "-id")

    def perform_create(self, serializer):
        is_first = not Address.objects.filter(user=self.request.user).exists()
        serializer.save(user=self.request.user, is_default=is_first)