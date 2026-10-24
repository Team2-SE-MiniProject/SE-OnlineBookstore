from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import IsAdminRole, IsSeller


class SellerManagementView(APIView):
    """Example endpoint restricted to sellers and administrators."""

    permission_classes = [IsAuthenticated, IsSeller | IsAdminRole]

    def get(self, request):
        return Response({"message": "Seller management access granted."})
