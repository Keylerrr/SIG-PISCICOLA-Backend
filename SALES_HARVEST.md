# Cambio: `available_weight_g` en Harvest API

Fecha: 2026-05-30

Resumen

Hemos añadido un nuevo campo en la API de `harvest` llamado `available_weight_g` que representa, para cada `HarvestClassification`, el peso (en gramos) disponible teniendo en cuenta:

- El peso total registrado en la clasificación (`total_weight_g`).
- Menos el peso ya derivado a lotes (`HarvestClassificationDerivation.total_weight_g`).
- Menos el peso ya vendido (suma de `SaleDetail.quantity` asociados a la clasificación).

Cálculo:

available_weight_g = max(total_weight_g - derived_weight - sold_weight, 0)

Endpoints afectados

- `GET /farms/<farm_pk>/harvests/` — devuelve la lista de cosechas; cada `classification` ahora incluye `available_weight_g`.
- `GET /farms/<farm_pk>/harvests/<id>/` — detalle de cosecha; las `classifications` en el response incluyen `available_weight_g`.
- `GET /farms/<farm_pk>/harvests/<harvest_pk>/classifications/` — listado de clasificaciones para una cosecha; cada item incluye `available_weight_g`.

Ejemplo de respuesta (fragmento de `classification`)

{
  "id": 123,
  "size_category": "Medium",
  "fish_count": 100,
  "total_weight_g": "5000.00",
  "derived_fish_count": 20,
  "available_fish_count": 80,
  "available_weight_g": "3500.00",
  "created_at": "2026-05-15T12:00:00Z",
  "updated_at": "2026-05-15T12:00:00Z"
}

Notas de implementación

- La lógica está implementada en `apps/harvest/utils.py` como `get_classification_available_weight_g(classification, exclude_detail_id=None)`.
- La función consulta las derivaciones (`HarvestClassificationDerivation`) y las ventas (`SaleDetail`) para calcular la cantidad restante en gramos.
- Para evitar dependencia directa entre módulos, la función obtiene `SaleDetail` con `apps.get_model("sales", "SaleDetail")`.

Cambios en `sales`

- `apps/sales/utils.py` ahora delega el cálculo de disponibilidad en gramos a `apps.harvest.utils.get_classification_available_weight_g`.
- Efectos principales:
  - Al crear una venta (`POST /sales/create/`) la validación de cantidad disponible utiliza el valor calculado por `harvest`.
  - Al editar un `SaleDetail` (`PATCH /sale-details/<pk>/`) la validación también usa el cálculo centralizado.

Razonamiento

- Centralizar el cálculo en `harvest` garantiza que todos los consumidores (front, ventas, derivados) obtengan la misma definición de "peso disponible".
- Se mantiene la separación de responsabilidades: las ventas no modifican `Harvest` directamente; la trazabilidad sigue siendo responsabilidad de `harvest`.

Impacto para frontend

- Mostrar ambos valores (`available_fish_count` y `available_weight_g`) evita ambigüedades entre "piezas" y "peso".
- El frontend debe leer `available_weight_g` ya que representa el peso real que se puede vender/derivar.

Archivos modificados

- Modificado: `apps/harvest/utils.py` (nueva función `get_classification_available_weight_g`).
- Modificado: `apps/harvest/serializers.py` (añadido `available_weight_g` a `HarvestClassificationSerializer`).
- Modificado: `apps/sales/utils.py` (delegación al nuevo helper de `harvest`).

Si quieres, puedo también:

- Añadir un campo `available_weight_g` directamente en la respuesta de endpoints de `sales` que consultan clasificaciones (por ejemplo, `sales/by-harvest-classification/`).
- Crear una pequeña migración o script para recalcular y cachear disponibilidad si el rendimiento es una preocupación.
