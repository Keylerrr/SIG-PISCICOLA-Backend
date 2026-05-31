# Documentación de Endpoints — Sales

Este documento describe los endpoints expuestos por la app `sales/`, el esquema JSON esperado, los permisos requeridos, los campos y las razones comunes de fallo.

**Permisos (global)**

- Todos los endpoints de `sales/` usan la clase de permisos `apps.farms.permissions.CanManageInventory`.
- En la práctica esto significa: el acceso está pensado para Admin o usuarios con permiso `MANAGE_INVENTORY` en la finca (farm).
- Nota importante sobre alcance: la implementación de `CanManageInventory` determina la granja a partir de `view.kwargs` (`farm_pk`, `farm_id` o `pk`). Para endpoints que no incluyen `farm_pk` en la URL (por ejemplo `POST /sales/create/`) el permiso puede no ser capaz de inferir la granja desde la ruta y la comprobación queda en el comportamiento por defecto de la clase de permisos. Si necesitas que la comprobación se haga siempre por `farm` en el body, puedo ajustar las vistas para extraer `farm` del body y validar explícitamente.

**Formato general de errores**

- 400 Bad Request: errores de validación (mensajes y estructura provienen de serializers / `ValidationError`).
- 403 Forbidden: errores de permiso o ventanas de edición expiradas (mensajes detallados desde `PermissionDenied`).
- 404 Not Found: raramente usado; en `sales` los helpers suelen lanzar `ValidationError` con `detail` para recursos no encontrados (devuelve 400).

---

## Endpoints

Nota: todas las rutas están en el espacio de URLs de la app `sales` (véase [apps/sales/urls.py](apps/sales/urls.py)). Las rutas a continuación son relativas a la raíz donde se monta la app.

### Clientes

#### GET /sales/clients/

- Descripción: lista clientes. Soporta filtros por query params.
- Query params: `farm_id`, `client_type`, `document_type`, `search`.
- Permisos: Admin o CanManageInventory.
- Response (200): lista de objetos con campos mínimos:
  - `id`, `farm`, `client_type`, `name`, `document_type`, `document_number`, `phone`, `email`.

#### POST /sales/clients/

- Descripción: crear cliente.
- Permisos: Admin o CanManageInventory.
- Body (JSON) - ejemplo:

```json
{
  "farm": 1,
  "client_type": "natural",
  "name": "Juan Pérez",
  "document_type": "CC",
  "document_number": "12345678",
  "phone": "+57 300 0000000",
  "email": "juan@example.com",
  "address": "Direccion",
  "observations": ""
}
```

- Campos obligatorios: `farm`, `client_type`, `name`, `document_type`, `document_number`, `date` no aplica aquí.
- Validaciones y casos de fallo (400):
  - `name` menor a 2 caracteres → "El nombre debe tener al menos 2 caracteres.".
  - `document_number` con formato inválido según `document_type` → mensaje específico.
  - Cliente jurídico (`client_type == juridico`) requiere `document_type == NIT` y viceversa para naturales.
  - Duplicado en la misma finca → "Ya existe un cliente con este tipo y número de documento registrado en esta finca."

#### GET /sales/clients/<pk>/
- Descripción: obtener detalle de cliente.
- Permisos: Admin o CanManageInventory.
- Error si cliente no encontrado: 400 con `{"detail": "Cliente con id=<pk> no encontrado."}`

#### PATCH /sales/clients/<pk>/
- Descripción: actualizar cliente (parcial).
- Permisos: Admin o CanManageInventory.
- Body: los mismos campos que en POST (todos opcionales en PATCH).
- Validaciones: mismas que en creación; duplicados o validaciones de formato devuelven 400.

#### DELETE /sales/clients/<pk>/
- Descripción: eliminar cliente.
- Permisos: Admin o CanManageInventory.
- Éxito: 204 No Content.
- Falla (400): si el cliente tiene ventas asociadas (no se permite eliminar):
  - `{"detail": "No es posible eliminar el cliente porque tiene ventas asociadas. Considere desactivarlo en su lugar."}`

#### GET /sales/clients/<pk>/can-delete/
- Response (200):
```json
{ "can_delete": true, "reason": null }
```
- O bien `can_delete: false` con `reason` explicando por qué no se puede.

---

### Ventas (Sales)

#### GET /sales/
- Descripción: lista ventas.
- Query params soportados: `farm_id`, `client_id`, `payment_method`, `date_from`, `date_to`, `invoice_number`.
- Permisos: Admin o CanManageInventory.
- Response: lista de ventas con campos: `id`, `farm`, `client`, `invoice_number`, `payment_method`, `date`, `created_by`.

#### POST /sales/create/
- Descripción: crear una venta completa con sus detalles (líneas).
- Permisos: Admin o CanManageInventory.
- Body (JSON) — ejemplo:

```json
{
  "farm": 1,
  "client": 2,                 // opcional
  "invoice_number": "F-2026-001",
  "payment_method": "efectivo",
  "observations": "Venta a cliente X",
  "date": "2026-05-30",
  "details": [
    { "harvest_classification": 12, "quantity": "1500.00", "unit": 3, "price": "5.00" },
    { "harvest_classification": 13, "quantity": "500.00", "unit": 3, "price": "6.00" }
  ]
}
```

- Campos importantes / reglas:
  - `farm`: id de la finca (obligatorio).
  - `invoice_number`: string (obligatorio, único por finca).
  - `payment_method`: uno de `efectivo`, `transferencia`.
  - `date`: fecha de la venta (obligatoria).
  - `details`: lista obligatoria; cada item debe tener:
    - `harvest_classification`: id de `HarvestClassification` (obligatorio).
    - `quantity`: decimal > 0. *Nota importante*: en la lógica actual `quantity` se maneja como peso en gramos para clasificaciones de cosecha y se usa en las validaciones de stock (see `available_weight_g`). El frontend debe enviar la cantidad en gramos cuando corresponda.
    - `unit`: id de `Unit` (representa la unidad; no hay validación fuerte del tipo en backend — front debe garantizar congruencia con `quantity`).
    - `price`: precio unitario (decimal, >= 0).

- Validaciones y fallos comunes:
  - 400 `{"details": "Se esperaba una lista de detalles."}` si `details` no es una lista.
  - 400 si falta alguno de los campos del `Sale` (serializers) o son inválidos — mensajes específicos (ej. factura vacía).
  - 400 si `invoice_number` ya existe en la misma `farm`: "Ya existe una venta con este número de factura en esta finca."
  - 400 item-level: "La cantidad debe ser mayor a cero." / "El precio no puede ser negativo." (si aplican).
  - 400 creación: "Una venta debe contener al menos un detalle de producto." (si `details` está vacío).
  - 400 si una misma `harvest_classification` aparece más de una vez en `details`:
    - "La clasificación de cosecha id=<id> aparece más de una vez. Cada clasificación debe tener un único detalle por venta."
  - 400 si faltan clasificaciones (ids que no existan):
    - `{"details": "Clasificaciones de cosecha no encontradas: {missing}."}`
  - 400 si la cantidad pedida supera la disponibilidad en gramos calculada por `harvest` (ver `available_weight_g`):
    - `{"quantity": "Peso solicitado (X g) supera el disponible (Y g) para la clasificación '<categoria>'."}`
  - 403 Forbidden en caso de falta de permiso según `CanManageInventory` (mensaje genérico de permiso).

- Respuesta exitosa (201): objeto `Sale` + `details` (ver `SaleDetailSerializer`). El campo `created_by` se toma del `request.user`.

#### GET /sales/<pk>/
- Descripción: obtener detalle de una venta (incluye `items` y `total`).
- Permisos: Admin o CanManageInventory.
- Falla si venta no encontrada: 400 con `{"detail": "Venta con id=<pk> no encontrada."}`.

#### PATCH /sales/<pk>/edit/
- Descripción: edición parcial de una venta.
- Permisos: Admin o CanManageInventory.
- Campos editables (ventana de edición = 15 minutos desde `created_at`):
  - Dentro de la ventana (<= 15 min): se permiten `client`, `invoice_number`, `payment_method`, `observations`, `date`.
  - Fuera de la ventana: sólo `observations`.
- Si se intenta editar campos no permitidos fuera de la ventana: 403 `PermissionDenied` con mensaje:
  - "Han transcurrido más de 15 minutos desde la creación de la venta. Solo se puede modificar 'observations'. Campos no permitidos en este momento: <lista>." 
- Validación de `invoice_number` duplicado también devuelve 400.

#### PATCH /sales/<pk>/observations/
- Body esperado:
```json
{ "observations": "texto" }
```
- Reglas: campo obligatorio y debe ser string.
- Fallos: 400 si falta o no es string.

#### GET /sales/<pk>/can-edit/
- Devuelve: `{"can_edit": true|false, "window_minutes": 15, "deadline": "<ISO>"}`.

#### GET /sales/by-client/<client_id>/
- Listado de ventas para un cliente.
- Error si cliente no existe: 400 `{"detail": "Cliente con id=<client_id> no encontrado."}`.

#### GET /sales/by-harvest-classification/<hc_id>/
- Lista de ventas que incluyen detalles con la clasificación `hc_id`.
- Devuelve una lista (posible vacía) sin error si no hay ventas.

---

### Detalles de líneas de venta (SaleDetail)

#### GET /sale-details/by-sale/<sale_id>/
- Lista de `SaleDetail` para la venta indicada.
- Error si la venta no existe: 400 `{"detail": "Venta con id=<sale_id> no encontrada."}`.

#### PATCH /sale-details/<pk>/
- Edición de un detalle de venta.
- Body (parcial) — campos admitidos: `harvest_classification`, `quantity`, `unit`, `price`.
- Validaciones importantes:
  - `quantity` > 0.
  - `price` >= 0.
  - No puede existir ya otra línea en la misma venta con la misma `harvest_classification` (se valida y devuelve 400 si ocurre).
  - Si se cambia `quantity` o `harvest_classification`, se verifica disponibilidad de peso mediante la función centralizada `harvest.utils.get_classification_available_weight_g(...)`. Si la cantidad solicitada supera la disponibilidad, devuelve 400 con mensaje:
    - `"Peso solicitado (X g) supera el disponible (Y g) para la clasificación '...'."`
  - Si la ventana de edición de la venta (15 min) expiró, se devuelve 403 con:
    - `"Han transcurrido más de 15 minutos desde la creación de la venta. Los detalles de venta ya no pueden ser modificados."`

#### GET /sale-details/<pk>/can-edit/
- Devuelve la misma estructura de `can_edit` que para la venta: `{"can_edit": true|false, "window_minutes": 15, "deadline": "<ISO>"}`.

---

## Casos de fallo frecuentes (resumen)

- 400 ValidationError: datos obligatorios faltantes, formatos inválidos, duplicados (`invoice_number`, cliente), cantidades negativas o cero.
- 400 No encontrado: en `sales` los helpers devuelven `ValidationError` con `detail` para recursos no encontrados (revisar mensaje exacto: "Venta con id=... no encontrada.").
- 400 Stock insuficiente: intentos de vender más gramos de los disponibles por `HarvestClassification`.
- 403 Permiso denegado: usuario no Admin ni con `CanManageInventory` (o ventana de edición expiró).

---

## Notas operativas y recomendaciones para frontend

- Mostrar ambos campos al usuario cuando muestre clasificaciones de cosecha:
  - `available_fish_count` (peces disponibles) — proviene de `harvest`.
  - `available_weight_g` (gramos disponibles) — ahora expuesto por `harvest` y usado por `sales` para validar ventas.
- En la UI asegúrate de enviar `quantity` en la unidad correcta (para clasificacions de cosecha: gramos). El backend usa `quantity` como peso para las validaciones de stock.
- Para endpoints de creación (`POST /sales/create/`), incluye `farm` en el body; si deseas que la autorización se base en la finca, considera añadir `farm_pk` en la URL o pedir que el backend extraiga `farm` del body para validar permisos (puedo implementarlo si lo deseas).

---

Si quieres, genero ejemplos de requests/responses más completos o pruebas unitarias que cubran los casos listados. También puedo añadir `available_weight_g` en las respuestas de endpoints `sales/by-harvest-classification/` si prefieres que el frontend obtenga esa información directamente desde `sales` en lugar de consultar `harvest`.
