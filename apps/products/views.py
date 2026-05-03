from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import AdminOr, IsAdmin
from apps.farms.permissions import IsFarmOwner
from apps.purchases.utils import get_product_stock

from .models import Product, Supplier, TypeProduct
from .serializers import (ProductSerializer, SupplierSerializer,
                          TypeProductSerializer)
from .utils import soft_delete


class TypeProductViewSet(viewsets.ModelViewSet):
    queryset = TypeProduct.objects.order_by("name")
    serializer_class = TypeProductSerializer
    http_method_names = ["get", "post", "patch", "delete"]

    def get_permissions(self):
        if self.action == "list" or self.action == "retrieve":
            return [AllowAny()]
        return [IsAdmin()]


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    http_method_names = ["get", "post", "patch", "delete"]

    def get_permissions(self):
        return [AdminOr(IsFarmOwner)()]

    def get_queryset(self):
        qs = (
            Product.objects.filter(
                farm_id=self.kwargs["farm_pk"],
                deleted_at__isnull=True,
            )
            .select_related("type_product", "unit")
            .order_by("name")
        )

        # GET /farms/{farm_pk}/products/?type_product_id=X
        type_product_id = self.request.query_params.get("type_product_id")
        if type_product_id:
            qs = qs.filter(type_product_id=type_product_id)

        return qs

    def perform_create(self, serializer):
        serializer.save(farm_id=self.kwargs["farm_pk"])

    def destroy(self, request, *args, **kwargs):
        soft_delete(self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"], url_path="stock")
    def stock(self, request, farm_pk=None, pk=None):
        product = self.get_object()
        return Response(
            {
                "product_id": product.id,
                "product_name": product.name,
                "unit": product.unit.symbol,
                "stock": get_product_stock(product_id=product.id, farm_id=farm_pk),
            }
        )

    @action(detail=False, methods=["get"], url_path="stock")
    def stock_list(self, request, farm_pk=None):
        products = self.get_queryset()
        data = [
            {
                "product_id": p.id,
                "product_name": p.name,
                "unit": p.unit.symbol,
                "stock": get_product_stock(product_id=p.id, farm_id=farm_pk),
            }
            for p in products
        ]
        return Response(data)


class SupplierViewSet(viewsets.ModelViewSet):
    serializer_class = SupplierSerializer
    http_method_names = ["get", "post", "patch", "delete"]

    def get_permissions(self):
        return [AdminOr(IsFarmOwner)()]

    def get_queryset(self):
        return Supplier.objects.filter(
            farm_id=self.kwargs["farm_pk"],
            deleted_at__isnull=True,
        ).order_by("name")

    def perform_create(self, serializer):
        serializer.save(farm_id=self.kwargs["farm_pk"])

    def destroy(self, request, *args, **kwargs):
        soft_delete(self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)
