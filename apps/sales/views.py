from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers as drf_serializers
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SaleDetail
from .serializers import (ClientCreateSerializer, ClientDetailSerializer,
                          ClientListSerializer, ClientUpdateSerializer,
                          SaleCreateSerializer, SaleDetailByHarvestSerializer,
                          SaleDetailCreateSerializer, SaleDetailListSerializer,
                          SaleDetailSerializer, SaleDetailUpdateSerializer,
                          SaleListSerializer, SaleUpdateSerializer)
from .services import (EDIT_WINDOW_MINUTES, can_delete_client, can_edit_sale,
                       can_edit_sale_detail, create_client, create_full_sale,
                       delete_client, edit_sale, edit_sale_detail, get_client,
                       get_sale, list_clients, list_sale_details_by_sale,
                       list_sales, list_sales_client,
                       list_sales_harvest_classification, update_client,
                       update_sale_observations)


class _SaleItemInputSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = SaleDetail
        fields = ["harvest_classification", "quantity", "unit", "price"]

    def validate_quantity(self, value):
        if value <= 0:
            raise drf_serializers.ValidationError("La cantidad debe ser mayor a cero.")
        return value

    def validate_price(self, value):
        if value < 0:
            raise drf_serializers.ValidationError("El precio no puede ser negativo.")
        return value


def _edit_window_payload(reference_dt) -> dict:
    deadline = reference_dt + timedelta(minutes=EDIT_WINDOW_MINUTES)
    within = timezone.now() <= deadline
    return {
        "can_edit": within,
        "window_minutes": EDIT_WINDOW_MINUTES,
        "deadline": deadline.isoformat(),
    }


class ClientListCreateView(APIView):

    def get(self, request: Request) -> Response:
        qp = request.query_params
        filters = {
            k: qp.get(k)
            for k in ("farm_id", "client_type", "document_type", "search")
            if qp.get(k) is not None
        }
        clients = list_clients(filters)
        serializer = ClientListSerializer(clients, many=True)
        return Response(serializer.data)

    def post(self, request: Request) -> Response:
        serializer = ClientCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        client = create_client(serializer.validated_data)
        return Response(
            ClientDetailSerializer(client).data,
            status=status.HTTP_201_CREATED,
        )


class ClientRetrieveUpdateDestroyView(APIView):

    def get(self, request: Request, pk: int) -> Response:
        client = get_client(pk)
        return Response(ClientDetailSerializer(client).data)

    def patch(self, request: Request, pk: int) -> Response:
        client = get_client(pk)
        serializer = ClientUpdateSerializer(client, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = update_client(pk, serializer.validated_data)
        return Response(ClientDetailSerializer(updated).data)

    def delete(self, request: Request, pk: int) -> Response:
        delete_client(pk)  # raises ValidationError if client has sales
        return Response(status=status.HTTP_204_NO_CONTENT)


class ClientCanDeleteView(APIView):
    def get(self, request: Request, pk: int) -> Response:
        get_client(pk)  # raise 400 if not found
        can_delete = can_delete_client(pk)
        return Response(
            {
                "can_delete": can_delete,
                "reason": (
                    None
                    if can_delete
                    else "El cliente tiene ventas asociadas y no puede eliminarse."
                ),
            }
        )


class SaleListView(APIView):

    def get(self, request: Request) -> Response:
        qp = request.query_params
        filters = {
            k: qp.get(k)
            for k in (
                "farm_id",
                "client_id",
                "payment_method",
                "date_from",
                "date_to",
                "invoice_number",
            )
            if qp.get(k) is not None
        }
        sales = list_sales(filters)
        serializer = SaleListSerializer(sales, many=True)
        return Response(serializer.data)


class FullSaleCreateView(APIView):
    def post(self, request: Request) -> Response:
        raw_details = request.data.get("details", [])
        if not isinstance(raw_details, list):
            return Response(
                {"details": "Se esperaba una lista de detalles."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sale_input = {k: v for k, v in request.data.items() if k != "details"}

        sale_ser = SaleCreateSerializer(data=sale_input)
        sale_ser.is_valid(raise_exception=True)

        detail_errors: dict = {}
        detail_sers: list[_SaleItemInputSerializer] = []

        for idx, item in enumerate(raw_details):
            ser = _SaleItemInputSerializer(data=item)
            if ser.is_valid():
                detail_sers.append(ser)
            else:
                detail_errors[f"details[{idx}]"] = ser.errors

        if detail_errors:
            return Response(detail_errors, status=status.HTTP_400_BAD_REQUEST)

        farm = sale_ser.validated_data["farm"]
        details_data = [{**ser.validated_data, "farm": farm} for ser in detail_sers]

        sale = create_full_sale(
            sale_data=sale_ser.validated_data,
            details_data=details_data,
            created_by=request.user,
        )

        return Response(
            SaleDetailSerializer(sale).data,
            status=status.HTTP_201_CREATED,
        )


class SaleRetrieveView(APIView):

    def get(self, request: Request, pk: int) -> Response:
        sale = get_sale(pk)
        return Response(SaleDetailSerializer(sale).data)


class SaleEditView(APIView):

    def patch(self, request: Request, pk: int) -> Response:
        sale = get_sale(pk)
        serializer = SaleUpdateSerializer(sale, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = edit_sale(pk, serializer.validated_data)
        return Response(SaleDetailSerializer(updated).data)


class SaleObservationsView(APIView):

    def patch(self, request: Request, pk: int) -> Response:
        observations = request.data.get("observations")
        if observations is None:
            return Response(
                {"observations": "Este campo es requerido."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not isinstance(observations, str):
            return Response(
                {"observations": "Se esperaba una cadena de texto."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        sale = update_sale_observations(pk, observations)
        return Response(SaleDetailSerializer(sale).data)


class SaleCanEditView(APIView):

    def get(self, request: Request, pk: int) -> Response:
        sale = get_sale(pk)
        return Response(_edit_window_payload(sale.created_at))


class SalesByClientView(APIView):

    def get(self, request: Request, client_id: int) -> Response:
        get_client(client_id)
        sales = list_sales_client(client_id)
        return Response(SaleListSerializer(sales, many=True).data)


class SalesByHarvestClassificationView(APIView):

    def get(self, request: Request, hc_id: int) -> Response:
        sales = list_sales_harvest_classification(hc_id)
        return Response(SaleDetailSerializer(sales, many=True).data)


class SaleDetailsBySaleView(APIView):

    def get(self, request: Request, sale_id: int) -> Response:
        get_sale(sale_id)
        details = list_sale_details_by_sale(sale_id)
        return Response(SaleDetailListSerializer(details, many=True).data)


class SaleDetailEditView(APIView):

    def patch(self, request: Request, pk: int) -> Response:
        from .services import _get_detail_or_404

        detail = _get_detail_or_404(pk)
        serializer = SaleDetailUpdateSerializer(detail, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        # edit_sale_detail() raises PermissionDenied (→ 403) if window has expired
        updated = edit_sale_detail(pk, serializer.validated_data)
        return Response(SaleDetailListSerializer(updated).data)


class SaleDetailCanEditView(APIView):

    def get(self, request: Request, pk: int) -> Response:
        from .services import _get_detail_or_404

        detail = _get_detail_or_404(pk)
        return Response(_edit_window_payload(detail.sale.created_at))
