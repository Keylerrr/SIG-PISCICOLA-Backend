# 🧪 Script de Prueba - API SIG-PISCICOLA Estanques

## Inicio Rápido

### 1. Inicia el servidor Django

En una terminal, en la carpeta del proyecto:

```bash
python manage.py runserver
```

Deberás ver algo como:
```
Starting development server at http://127.0.0.1:8000/
```

### 2. Ejecuta el script de prueba

En otra terminal:

```bash
python test_api.py
```

## ¿Qué prueba el script?

El script ejecuta 12 pruebas completas del API:

1. ✅ **Verificar conexión** al servidor
2. ✅ **Registro de usuario** - Crear usuario test
3. ✅ **Login** - Obtener token JWT
4. ✅ **Crear estanque** - POST /estanques/
5. ✅ **Listar estanques** - GET /estanques/
6. ✅ **Filtrar estanques** - GET /estanques/?estado=activo
7. ✅ **Buscar estanque** - GET /estanques/?search=EST
8. ✅ **Obtener detalle** - GET /estanques/{id}/
9. ✅ **Actualizar estanque** - PATCH /estanques/{id}/
10. ✅ **Cambiar estado** - PATCH /estanques/{id}/cambiar-estado/
11. ✅ **Toggle interruptor** - PATCH /estanques/{id}/toggle-estado/
12. ✅ **Eliminar estanque** - DELETE /estanques/{id}/

## Ejemplos de Salida Esperada

```
============================================================
  Verificando conexión al servidor
============================================================

✅ Servidor disponible en http://localhost:8000

============================================================
  3. CREAR ESTANQUE
============================================================

ℹ️  Creando estanque...
Datos enviados:
{
  "granja_id": 1,
  "codigo": "EST-TEST-001",
  "nombre": "Estanque de Prueba",
  ...
}

✅ Estanque creado exitosamente (ID: 1)

============================================================
  RESUMEN DE PRUEBAS
============================================================

Prueba                         Resultado       
─────────────────────────────────────────────
Verificar Servidor             ✅ EXITOSA
Registro                       ✅ EXITOSA
Login                          ✅ EXITOSA
...
─────────────────────────────────────────────
Total: 12/12 pruebas exitosas

🎉 ¡TODAS LAS PRUEBAS PASARON!
```

## Requisitos

```bash
pip install requests
```

O instala desde requirements.txt:

```bash
pip install -r requirements.txt
```

## Solución de Problemas

### ❌ "No se puede conectar a http://localhost:8000"

**Solución**: Asegúrate que el servidor Django está corriendo

```bash
python manage.py runserver
```

### ❌ "Error 403: Forbidden"

**Solución**: Verifica que el token JWT es válido. El script lo obtiene automáticamente.

### ❌ "Error 400: Bad Request"

**Solución**: Verifica los datos enviados en el script. Puede ser que falte algún campo requerido.

### ❌ "Error 500: Internal Server Error"

**Solución**: Revisa los logs del servidor Django para más detalles.

## Personalizar el Script

Puedes editar estas variables en `test_api.py`:

```python
BASE_URL = "http://localhost:8000"  # Cambia si está en otro puerto

# En la función registro():
data = {
    "email": "test@piscicola.com",  # Cambia el email
    "password": "TestPassword123",    # Cambia la contraseña
}

# En la función crear_estanque():
data = {
    "granja_id": 1,     # Cambia al ID de tu granja
    "codigo": "EST-001", # Cambia el código
    "nombre": "Mi Estanque",  # Cambia el nombre
    "capacidad": 5000,  # Cambia la capacidad
}
```

## Ejecutar Pruebas Individuales

Si quieres ejecutar solo una prueba, puedes editar `main()` en el script:

```python
# Solo ejecutar login y crear estanque
tests = [
    ("Login", login),
    ("Crear Estanque", crear_estanque),
]
```

## Más Información

- 📖 [Documentación de Requests](https://requests.readthedocs.io/)
- 🔒 [JWT en Django REST](https://django-rest-framework-simplejwt.readthedocs.io/)
- 🐳 [Manual de Django](https://docs.djangoproject.com/)
