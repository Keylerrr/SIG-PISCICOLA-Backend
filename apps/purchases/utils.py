from django.db.models import Q, Sum

from .models import Buy, InventoryMovement, PurchaseDetail


def _create_inventory_movement(buy: Buy, detail: PurchaseDetail) -> InventoryMovement:
    return InventoryMovement.objects.create(
        farm=buy.farm,
        product=detail.product,
        movement_type=InventoryMovement.MovementType.IN,
        quantity=detail.quantity,
        unit_cost=detail.unit_value,
        total_cost=detail.total_value,
        observations=buy.comments,
        source_type=InventoryMovement.SourceType.PURCHASE,
        source_id=detail.id,
    )


def _delete_details_with_movements(buy: Buy) -> None:
    detail_ids = buy.details.values_list("id", flat=True)
    InventoryMovement.objects.filter(
        source_type=InventoryMovement.SourceType.PURCHASE,
        source_id__in=detail_ids,
    ).delete()
    buy.details.all().delete()


def get_product_stock(product_id: int, farm_id: int) -> float:

    from .models import InventoryMovement as IM

    result = InventoryMovement.objects.filter(
        product_id=product_id,
        farm_id=farm_id,
    ).aggregate(
        total_in=Sum(
            "quantity",
            filter=Q(movement_type__in=[IM.MovementType.IN, IM.MovementType.INITIAL]),
        ),
        total_out=Sum("quantity", filter=Q(movement_type=IM.MovementType.OUT)),
    )
    return float((result["total_in"] or 0) - (result["total_out"] or 0))
