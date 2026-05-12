# Planes de producción (`ProductionPlan`)

Documentación alineada con el backend **SIG-PISCICOLA** (`apps/cycle`: modelo, serializers y vistas).

---

## 1. Rol en el dominio

Un **plan de producción** define parámetros esperados de un cultivo para una **granja** (`farm`) y una **especie** (`specie`): tipo de producción, duración en días, mortalidad esperada, peso final esperado y, opcionalmente, tasa de reproducción esperada.

Los **ciclos** (`Cycle`) referencian un plan mediante `production_plan`. Al validar un ciclo se exige que el plan sea de la **misma granja** y la **misma especie** que el ciclo, y que el plan **no esté eliminado lógicamente** (`deleted_at` nulo).

---

## 2. Modelo de datos

**Tabla:** `production_plan`  
**Clase Django:** `apps.cycle.models.ProductionPlan`

| Campo | Tipo | Obligatorio | Notas |
|--------|------|-------------|--------|
| `id` | entero | auto | Clave primaria |
| `farm` | FK → `farms.Farm` | sí | Granja propietaria |
| `specie` | FK → `species.Specie` | sí | Especie del plan |
| `name` | string (máx. 150) | sí | Nombre descriptivo |
| `type` | string | sí | Valores: ver § 2.1 |
| `total_days` | entero ≥ 0 | sí | `PositiveIntegerField` (incluye 0 a nivel modelo) |
| `expected_mortality_rate` | float | sí | Porcentaje; validación API 0–100 (§ 4) |
| `expected_final_weight` | float | sí | Validación API &gt; 0 cuando se envía (§ 4) |
| `expected_reproduction_rate` | float | no | `null` permitido |
| `version` | entero | sí | Por defecto 1; solo lectura en API |
| `is_current` | boolean | sí | Indica versión vigente del linaje; solo lectura en API |
| `parent` | FK → `ProductionPlan` | no | Plan del que deriva esta versión; solo lectura en API |
| `created_at` | datetime | auto | Solo lectura en API |
| `updated_at` | datetime | auto | Solo lectura en API |
| `deleted_at` | datetime | no | Soft delete; solo lectura en API |

### 2.1 Valores de `type`

Definidos en `ProductionPlan.Type`:

| Valor en API | Constante |
|--------------|-----------|
| `nursery` | Nursery |
| `growout` | Growout |
| `breeding` | Breeding |

---

## 3. Versionado (comportamiento de `PATCH`)

No se **editan in place** los planes al versionar: un **`PATCH`** sobre un plan con **`is_current: true`**:

1. Crea una **nueva fila** con los campos enviados en el cuerpo; los campos omitidos se copian del plan actual.
2. Asigna `version = versión_anterior + 1`, `is_current = true`, `parent = plan_anterior`.
3. Marca el plan anterior con `is_current = false`.

Si se intenta **`PATCH`** sobre un plan con **`is_current: false`**, el serializer responde error textual: *"No se puede actualizar un plan que no es la versión actual."*

La **especie** y la **granja** de la nueva versión se toman **siempre** del plan anterior (`instance`); no se pueden cambiar por versionado (§ 4).

---

## 4. Reglas del serializer (`ProductionPlanSerializer`)

### 4.1 Campos de solo lectura (`read_only_fields`)

En respuestas y reglas de escritura:

- `farm` — La granja la fija la **URL** (`farm_pk`) en `POST` mediante `perform_create` → `save(farm_id=farm_pk)`. No debe enviarse para modificar la granja.
- `version`, `is_current`, `parent`, `created_at`, `updated_at`, `deleted_at` — Gestionados por el servidor; **`deleted_at`** no se modifica por `PATCH` del plan (la baja es vía `DELETE`).

### 4.2 Creación (`POST`)

- **`specie`**: obligatorio en el cuerpo (no es read-only).
- **`farm`**: no se envía como dato de negocio editable; el backend asigna la granja de la ruta.

### 4.3 Actualización (`PATCH`, nueva versión)

- Si el cuerpo incluye la clave **`specie`**, se rechaza con: *"La especie no se puede cambiar al versionar un plan de producción."*
- **`farm`** no es aceptado como escritura (read-only).

### 4.4 Validaciones numéricas (`validate`)

- **`expected_mortality_rate`**: si viene en los datos validados, debe estar entre **0 y 100** (inclusive).
- **`expected_final_weight`**: si viene y no es `null`, debe ser **mayor que 0**.
- **`expected_reproduction_rate`**: sin rango extra en serializer (solo restricciones del modelo / `null`).

---

## 5. Endpoints HTTP

Prefijo típico de la API: **`/api/`** (ver `project/urls.py` e inclusión de `apps.cycle.urls`).

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/farms/{farm_pk}/production-plans/` | Lista planes de la granja no borrados |
| `POST` | `/api/farms/{farm_pk}/production-plans/` | Crea un plan |
| `GET` | `/api/farms/{farm_pk}/production-plans/{pk}/` | Detalle por id |
| `PATCH` | `/api/farms/{farm_pk}/production-plans/{pk}/` | Nueva versión si el plan es actual (`is_current`) |
| `DELETE` | `/api/farms/{farm_pk}/production-plans/{pk}/` | Soft delete (`deleted_at`); respuesta **204** sin cuerpo |

### 5.1 Queryset

- Listado y detalle: `farm_id = farm_pk` y **`deleted_at` IS NULL**.
- Orden listado: `-created_at`.

Los planes con soft delete **no** aparecen en listados ni son recuperables por el `get_queryset` habitual del detalle.

---

## 6. Autenticación y permisos

- Autenticación por defecto: **JWT** (`Authorization: Bearer <token>`).
- **Lectura** (`GET`): `AdminOr(IsFarmMember)` — administrador global o usuario con acceso a la granja (perfil completo según middleware de cuentas).
- **Escritura** (`POST`, `PATCH`, `DELETE`): `AdminOr(CanManageCycle)` — administrador o permiso efectivo **`MANAGE_CYCLE`** en esa granja (`apps.farms.permissions`, `FarmPermission.MANAGE_CYCLE`). Dueños de granja y rol **Productor** pasan según la lógica de `HasFarmPermission`.

---

## 7. Relación con ciclos (`Cycle`)

- El ciclo incluye `production_plan` (FK, `on_delete=PROTECT` a nivel modelo para borrados físicos; en la API el plan se da de baja con **soft delete**).
- Validación en **`CycleSerializer`**: el plan debe pertenecer a la **misma granja** y a la **misma especie** que el ciclo.
- Si el plan tiene **`deleted_at` no nulo**, se rechaza con mensaje del estilo: *"El plan de producción no está disponible (ha sido eliminado)."*

Así se evita asociar ciclos a planes que la API ya no expone como activos.

---

## 8. Ejemplos para el cliente

### 8.1 Crear plan

`POST /api/farms/3/production-plans/`

```json
{
  "specie": 1,
  "name": "Engorde tilapia 2026",
  "type": "growout",
  "total_days": 120,
  "expected_mortality_rate": 8.5,
  "expected_final_weight": 450,
  "expected_reproduction_rate": null
}
```

Respuesta incluirá `farm: 3` (o el id correspondiente), `version: 1`, `is_current: true`, `parent: null`, fechas, etc.

### 8.2 Nueva versión del plan

`PATCH /api/farms/3/production-plans/10/`  
(solo si el plan `10` tiene `is_current: true`)

```json
{
  "name": "Engorde tilapia 2026 v2",
  "total_days": 130,
  "expected_mortality_rate": 9.0
}
```

La respuesta es el **nuevo** objeto (nuevo `id`, `version` incrementada). El cliente debe usar el nuevo `id` para referencias futuras (p. ej. ciclos nuevos).

No incluir `specie` ni intentar cambiar `farm` en el `PATCH`.

### 8.3 Eliminar (soft delete)

`DELETE /api/farms/3/production-plans/10/` → **204 No Content**.

---

## 9. OpenAPI / Swagger

El proyecto usa **drf-spectacular**. El esquema suele exponerse en rutas como `/api/schema/` o UI Swagger según la configuración de URLs del proyecto.

---

## 10. Consideraciones adicionales

| Tema | Detalle |
|------|---------|
| Varias versiones “actueras” | No hay restricción en BD contra condiciones de carrera; dos `PATCH` concurrentes al mismo plan podrían generar escenarios raros. Uso normal: un cliente a la vez o reintentos. |
| `total_days = 0` | Válido en modelo; si el negocio exige mínimo 1, habría que añadir validación explícita. |
| Historial | Planes viejos con `is_current: false` siguen en BD; el listado por defecto mezcla todas las versiones no borradas ordenadas por creación. El front puede filtrar `is_current === true` o seguir la cadena `parent`. |

---

## 11. Referencia de código

- Modelo: `apps/cycle/models.py` — `ProductionPlan`
- Serializer: `apps/cycle/serializers.py` — `ProductionPlanSerializer`
- Vistas: `apps/cycle/views.py` — `ProductionPlanViewSet`
- Rutas: `apps/cycle/urls.py` — rutas `production-plans`
