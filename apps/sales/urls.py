from django.urls import path

from .views import (ClientCanDeleteView, ClientListCreateView,
                    ClientRetrieveUpdateDestroyView, FullSaleCreateView,
                    SaleCanEditView, SaleDetailCanEditView, SaleDetailEditView,
                    SaleDetailsBySaleView, SaleEditView, SaleListView,
                    SaleObservationsView, SaleRetrieveView, SalesByClientView,
                    SalesByHarvestClassificationView)

app_name = "sales"

urlpatterns = [
    path(
        "clients/",
        ClientListCreateView.as_view(),
        name="client-list-create",
    ),
    path(
        "clients/<int:pk>/",
        ClientRetrieveUpdateDestroyView.as_view(),
        name="client-detail",
    ),
    path(
        "clients/<int:pk>/can-delete/",
        ClientCanDeleteView.as_view(),
        name="client-can-delete",
    ),
    path(
        "sales/by-client/<int:client_id>/",
        SalesByClientView.as_view(),
        name="sales-by-client",
    ),
    path(
        "sales/by-harvest-classification/<int:hc_id>/",
        SalesByHarvestClassificationView.as_view(),
        name="sales-by-harvest-classification",
    ),
    path(
        "sales/",
        SaleListView.as_view(),
        name="sale-list",
    ),
    path(
        "sales/create/",
        FullSaleCreateView.as_view(),
        name="sale-create",
    ),
    path(
        "sales/<int:pk>/",
        SaleRetrieveView.as_view(),
        name="sale-detail",
    ),
    path(
        "sales/<int:pk>/edit/",
        SaleEditView.as_view(),
        name="sale-edit",
    ),
    path(
        "sales/<int:pk>/observations/",
        SaleObservationsView.as_view(),
        name="sale-observations",
    ),
    path(
        "sales/<int:pk>/can-edit/",
        SaleCanEditView.as_view(),
        name="sale-can-edit",
    ),
    path(
        "sale-details/by-sale/<int:sale_id>/",
        SaleDetailsBySaleView.as_view(),
        name="sale-details-by-sale",
    ),
    path(
        "sale-details/<int:pk>/",
        SaleDetailEditView.as_view(),
        name="sale-detail-edit",
    ),
    path(
        "sale-details/<int:pk>/can-edit/",
        SaleDetailCanEditView.as_view(),
        name="sale-detail-can-edit",
    ),
]
