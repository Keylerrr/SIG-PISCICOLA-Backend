# Análisis: Sales ↔ Harvest

Resumen rápido

- Revisé las apps `sales` y `harvest` para verificar la lógica de venta y disponibilidad.
- Encontré y arreglé errores en `sales` que impedían el correcto funcionamiento (imports y reexport).
- Verifiqué que el diseño actual mantiene la trazabilidad en `harvest` (no se modifica directamente), y que `sales` suma lo vendido para calcular lo restante por clasificación (en peso).
- Añadí control de permisos en las vistas de `sales` para requerir `Admin` o permiso `CanManageInventory`.

¿Qué encontré (detallado)?

- `apps/harvest/models.py`:
  - `HarvestClassification` define `fish_count` (número de peces) y `total_weight_g` (peso total en gramos).
  - `get_classification_available_fish_count` (en `harvest.utils`) calcula disponibilidad en piezas como `fish_count - derivaciones` (no incluye ventas).

- `apps/sales`:
  - La lógica de `sales` opera en peso (`quantity` en `SaleDetail` se trata como gramos en la validación). En `apps/sales/utils.py` existe la función `get_classification_available_weight_g` que calcula disponibilidad en gramos como:
    `classification.total_weight_g - derived_weight - sold_weight`.
  - La creación y edición de `SaleDetail` valida contra esta disponibilidad en peso y no modifica objetos de `harvest` (correcto según el requisito).
  - `create_full_sale` ya maneja bloqueo (`select_for_update`) y evita sobreventa concurrente mediante la variable `consumed_in_tx` (correcto).

Inconsistencias observadas

- "Vendible" según `available_fish_count > 0` (piezas) vs la validación de venta (peso):
  - `harvest` considera vendible cuando hay peces no derivados (`fish_count - derivado > 0`).
  - `sales` valida por peso (`total_weight_g - derivaciones - vendidos`), por lo que puede haber casos donde `available_fish_count > 0` pero la disponibilidad en gramos sea 0 (por ejemplo si ya se vendió todo el peso de la clasificación en ventas previas).
  - Esto no es necesariamente un bug: refleja dos medidas diferentes (pieza vs peso). Pero es importante saberlo para evitar confusiones en la UI/UX o en reglas de negocio.

Cambios realizados (solo `sales`)

- `apps/sales/utils.py`
  - Corregí un import erróneo: `apps.harvests.models` → `apps.harvest.models`.
  - Verifiqué y dejé intacta la lógica que calcula disponibilidad en gramos (`get_classification_available_weight_g`).

- `apps/sales/services.py` (nuevo)
  - Añadí un pequeño adaptador que reexporta las funciones públicas usadas por las vistas (`create_full_sale`, `edit_sale`, etc.).
  - Razonamiento: `views.py` importaba `from .services import ...` pero no existía `services.py` (refactor incompleto). Crear este archivo es la corrección mínima y no cambia la API.

- `apps/sales/views.py`
  - Importé `CanManageInventory` desde `apps.farms.permissions` y añadí `permission_classes = [CanManageInventory]` en todas las vistas del módulo.
  - Razonamiento: `CanManageInventory` ya retorna True para el rol Admin, por lo que satisface la condición "Admin OR CanManageInventory" indicada.

Archivos modificados / añadidos

- Modificado: [apps/sales/utils.py](apps/sales/utils.py#L1-L240)
- Modificado: [apps/sales/views.py](apps/sales/views.py#L1-L360)
- Añadido: [apps/sales/services.py](apps/sales/services.py#L1-L80)
- Añadido: [SALES_HARVEST_ANALYSIS.md](SALES_HARVEST_ANALYSIS.md#L1-L200)

Recomendaciones

- Si la intención de negocio es que "vendible" signifique que aún haya peso disponible para venta, conviene unificar la definición y mostrar ambos valores en la UI:
  - "available_fish_count" (piezas) y "available_weight_g" (gramos).
  - Para mantener separación de responsabilidades, sugiero:
    - No modificar `harvest` automáticamente desde `sales` (mantener trazabilidad).
    - Añadir en `harvest.serializers` (o en un endpoint de `sales`) un campo `available_weight_g` que llame a la función de `sales` o a un helper común que incluya ventas en el cálculo.
- Si lo prefieres, puedo:
  - Implementar el campo `available_weight_g` en `harvest.serializers` (esto requiere cambios en `harvest`).
  - O bien, exponer un endpoint en `sales` que devuelva la disponibilidad combinada por clasificación (sin tocar `harvest`).

Siguientes pasos que puedo realizar ahora

- Añadir `available_weight_g` al API de `harvest` (requiere cambios en `harvest`).
- O bien, crear un endpoint en `sales` que reporte disponibilidad por clasificación incluyendo ventas.

Si quieres que implemente alguna de estas recomendaciones, dime cuál prefieres y lo hago.
