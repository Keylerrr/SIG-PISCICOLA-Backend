import requests
import json
import sys

BASE_URL = "http://localhost:8000"
TOKEN = None
ESTANQUE_ID = None

# Colores para output
GREEN = '\033[92m'
RED = '\033[91m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def print_section(title):
    print(f"\n{BLUE}{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}{RESET}\n")

def print_success(msg):
    print(f"{GREEN}✅ {msg}{RESET}")

def print_error(msg):
    print(f"{RED}❌ {msg}{RESET}")

def print_info(msg):
    print(f"{YELLOW}ℹ️  {msg}{RESET}")

def print_response(title, data):
    print(f"{BLUE}{title}:{RESET}")
    print(json.dumps(data, indent=2, ensure_ascii=False))

def check_server():
    """Verificar que el servidor esté corriendo"""
    print_section("Verificando conexión al servidor")
    try:
        response = requests.get(f"{BASE_URL}/auth/login/", timeout=2)
        print_success(f"Servidor disponible en {BASE_URL}")
        return True
    except requests.exceptions.ConnectionError:
        print_error(f"No se puede conectar a {BASE_URL}")
        print_info("Asegúrate que el servidor Django está corriendo:")
        print_info("  python manage.py runserver")
        return False
    except Exception as e:
        print_error(f"Error: {e}")
        return False

def registro():
    """Registrar nuevo usuario"""
    print_section("1. REGISTRO DE USUARIO")

    data = {
        "name": "Test User",
        "email": "test@piscicola.com",
        "password": "TestPassword123",
        "phone": "3001234567"
    }

    print_info("Registrando usuario...")
    print_response("Datos enviados", data)

    try:
        response = requests.post(f"{BASE_URL}/auth/register/", json=data)

        if response.status_code == 201:
            resultado = response.json()
            print_success("Usuario registrado exitosamente")
            print_response("Respuesta", resultado)
            return True
        else:
            print_error(f"Error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print_error(f"Excepción: {e}")
        return False

def login():
    """Login y obtener token"""
    global TOKEN
    print_section("2. LOGIN Y OBTENER TOKEN")

    data = {
        "email": "test@piscicola.com",
        "password": "TestPassword123"
    }

    print_info("Intentando login...")
    print_response("Credenciales", data)

    try:
        response = requests.post(f"{BASE_URL}/auth/login/", json=data)

        if response.status_code == 200:
            resultado = response.json()
            TOKEN = resultado["tokens"]["access"]
            print_success(f"Login exitoso")
            print_info(f"Token obtenido: {TOKEN[:30]}...")
            print_response("Respuesta completa", resultado)
            return True
        else:
            print_error(f"Error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print_error(f"Excepción: {e}")
        return False

def crear_estanque():
    """Crear un nuevo estanque"""
    global ESTANQUE_ID
    print_section("3. CREAR ESTANQUE")

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "granja_id": 1,
        "codigo": "EST-TEST-001",
        "nombre": "Estanque de Prueba",
        "tipo": "estanque",
        "estado": "activo",
        "capacidad": 5000,
        "descripcion": "Estanque creado para pruebas del API"
    }

    print_info("Creando estanque...")
    print_response("Datos enviados", data)

    try:
        response = requests.post(f"{BASE_URL}/estanques/", json=data, headers=headers)

        if response.status_code == 201:
            resultado = response.json()
            ESTANQUE_ID = resultado["id"]
            print_success(f"Estanque creado exitosamente (ID: {ESTANQUE_ID})")
            print_response("Respuesta", resultado)
            return True
        else:
            print_error(f"Error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print_error(f"Excepción: {e}")
        return False

def listar_estanques():
    """Listar todos los estanques"""
    print_section("4. LISTAR ESTANQUES")

    headers = {"Authorization": f"Bearer {TOKEN}"}

    print_info("Obteniendo listado de estanques...")

    try:
        response = requests.get(f"{BASE_URL}/estanques/", headers=headers)

        if response.status_code == 200:
            resultado = response.json()
            print_success(f"{len(resultado)} estanque(s) encontrado(s)")

            for est in resultado:
                print(f"\n  📦 {est['codigo']} - {est['nombre']}")
                print(f"     Estado: {est['estado']}")
                print(f"     Capacidad: {est['capacidad']} L")
                print(f"     Interruptor: {'Activo' if est['activo_interruptor'] else 'Inactivo'}")

            return True
        else:
            print_error(f"Error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print_error(f"Excepción: {e}")
        return False

def filtrar_estanques():
    """Filtrar estanques por estado"""
    print_section("5. FILTRAR ESTANQUES")

    headers = {"Authorization": f"Bearer {TOKEN}"}
    params = {"estado": "activo", "granja_id": 1}

    print_info("Filtrando estanques por estado='activo' y granja_id=1...")
    print_response("Parámetros de filtro", params)

    try:
        response = requests.get(f"{BASE_URL}/estanques/", params=params, headers=headers)

        if response.status_code == 200:
            resultado = response.json()
            print_success(f"{len(resultado)} estanque(s) encontrado(s) con filtros")
            print_response("Resultados", resultado)
            return True
        else:
            print_error(f"Error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print_error(f"Excepción: {e}")
        return False

def buscar_estanque():
    """Buscar estanque por código/nombre"""
    print_section("6. BUSCAR ESTANQUE")

    headers = {"Authorization": f"Bearer {TOKEN}"}
    params = {"search": "EST"}

    print_info("Buscando estanques con 'EST' en código o nombre...")
    print_response("Parámetros de búsqueda", params)

    try:
        response = requests.get(f"{BASE_URL}/estanques/", params=params, headers=headers)

        if response.status_code == 200:
            resultado = response.json()
            print_success(f"{len(resultado)} estanque(s) encontrado(s) con búsqueda")
            print_response("Resultados", resultado)
            return True
        else:
            print_error(f"Error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print_error(f"Excepción: {e}")
        return False

def obtener_detalle():
    """Obtener detalle de un estanque"""
    print_section("7. OBTENER DETALLE DE ESTANQUE")

    if not ESTANQUE_ID:
        print_error("No hay estanque_id disponible")
        return False

    headers = {"Authorization": f"Bearer {TOKEN}"}

    print_info(f"Obteniendo detalle del estanque {ESTANQUE_ID}...")

    try:
        response = requests.get(f"{BASE_URL}/estanques/{ESTANQUE_ID}/", headers=headers)

        if response.status_code == 200:
            resultado = response.json()
            print_success(f"Detalle obtenido")
            print_response("Datos del estanque", resultado)
            return True
        else:
            print_error(f"Error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print_error(f"Excepción: {e}")
        return False

def actualizar_estanque():
    """Actualizar estanque"""
    print_section("8. ACTUALIZAR ESTANQUE")

    if not ESTANQUE_ID:
        print_error("No hay estanque_id disponible")
        return False

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "nombre": "Estanque Actualizado",
        "capacidad": 6000,
        "estado": "en_uso"
    }

    print_info(f"Actualizando estanque {ESTANQUE_ID}...")
    print_response("Datos a actualizar", data)

    try:
        response = requests.patch(f"{BASE_URL}/estanques/{ESTANQUE_ID}/", json=data, headers=headers)

        if response.status_code == 200:
            resultado = response.json()
            print_success(f"Estanque actualizado")
            print_response("Respuesta", resultado)
            return True
        else:
            print_error(f"Error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print_error(f"Excepción: {e}")
        return False

def cambiar_estado():
    """Cambiar estado operativo"""
    print_section("9. CAMBIAR ESTADO OPERATIVO")

    if not ESTANQUE_ID:
        print_error("No hay estanque_id disponible")
        return False

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }

    data = {"estado": "en_limpieza"}

    print_info(f"Cambiando estado del estanque {ESTANQUE_ID} a 'en_limpieza'...")
    print_response("Datos enviados", data)

    try:
        response = requests.patch(f"{BASE_URL}/estanques/{ESTANQUE_ID}/cambiar-estado/", json=data, headers=headers)

        if response.status_code == 200:
            resultado = response.json()
            print_success(f"Estado cambiado exitosamente")
            print_response("Respuesta", resultado)
            return True
        else:
            print_error(f"Error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print_error(f"Excepción: {e}")
        return False

def toggle_interruptor():
    """Toggle del interruptor"""
    print_section("10. TOGGLE INTERRUPTOR (Activar/Desactivar)")

    if not ESTANQUE_ID:
        print_error("No hay estanque_id disponible")
        return False

    headers = {"Authorization": f"Bearer {TOKEN}"}

    print_info(f"Toggling interruptor del estanque {ESTANQUE_ID}...")

    try:
        response = requests.patch(f"{BASE_URL}/estanques/{ESTANQUE_ID}/toggle-estado/", headers=headers)

        if response.status_code == 200:
            resultado = response.json()
            print_success(f"Interruptor toggled")
            print_response("Respuesta", resultado)
            return True
        else:
            print_error(f"Error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print_error(f"Excepción: {e}")
        return False

def cambiar_a_inactivo():
    """Cambiar a estado inactivo para poder eliminar"""
    print_section("11. CAMBIAR A ESTADO INACTIVO (Preparar para eliminar)")

    if not ESTANQUE_ID:
        print_error("No hay estanque_id disponible")
        return False

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }

    data = {"estado": "inactivo"}

    print_info(f"Cambiando estado a 'inactivo'...")

    try:
        response = requests.patch(f"{BASE_URL}/estanques/{ESTANQUE_ID}/cambiar-estado/", json=data, headers=headers)

        if response.status_code == 200:
            resultado = response.json()
            print_success(f"Estado cambiado a inactivo")
            print_response("Respuesta", resultado)
            return True
        else:
            print_error(f"Error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print_error(f"Excepción: {e}")
        return False

def eliminar_estanque():
    """Eliminar estanque"""
    print_section("12. ELIMINAR ESTANQUE")

    if not ESTANQUE_ID:
        print_error("No hay estanque_id disponible")
        return False

    headers = {"Authorization": f"Bearer {TOKEN}"}

    print_info(f"Eliminando estanque {ESTANQUE_ID}...")

    try:
        response = requests.delete(f"{BASE_URL}/estanques/{ESTANQUE_ID}/", headers=headers)

        if response.status_code == 200:
            resultado = response.json()
            print_success(f"Estanque eliminado exitosamente")
            print_response("Respuesta", resultado)
            return True
        else:
            print_error(f"Error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print_error(f"Excepción: {e}")
        return False

def main():
    """Ejecutar todas las pruebas"""
    print(f"\n{BLUE}")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║          TEST COMPLETO API SIG-PISCICOLA ESTANQUES         ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"{RESET}")

    # Verificar servidor
    if not check_server():
        print(f"\n{RED}Abortando pruebas.{RESET}")
        return

    # Ejecutar pruebas
    tests = [
        ("Registro", registro),
        ("Login", login),
        ("Crear Estanque", crear_estanque),
        ("Listar Estanques", listar_estanques),
        ("Filtrar Estanques", filtrar_estanques),
        ("Buscar Estanque", buscar_estanque),
        ("Obtener Detalle", obtener_detalle),
        ("Actualizar Estanque", actualizar_estanque),
        ("Cambiar Estado", cambiar_estado),
        ("Toggle Interruptor", toggle_interruptor),
        ("Cambiar a Inactivo", cambiar_a_inactivo),
        ("Eliminar Estanque", eliminar_estanque),
    ]

    resultados = []
    for nombre, test_func in tests:
        try:
            resultado = test_func()
            resultados.append((nombre, resultado))
        except Exception as e:
            print_error(f"Error inesperado en {nombre}: {e}")
            resultados.append((nombre, False))

    # Resumen final
    print_section("RESUMEN DE PRUEBAS")
    exitosas = sum(1 for _, r in resultados if r)
    total = len(resultados)

    print(f"\n{'Prueba':<30} {'Resultado':<15}")
    print("─" * 45)
    for nombre, resultado in resultados:
        estado = f"{GREEN}✅ EXITOSA{RESET}" if resultado else f"{RED}❌ FALLÓ{RESET}"
        print(f"{nombre:<30} {estado}")

    print("─" * 45)
    print(f"Total: {GREEN}{exitosas}/{total}{RESET} pruebas exitosas")

    if exitosas == total:
        print(f"\n{GREEN}🎉 ¡TODAS LAS PRUEBAS PASARON!{RESET}\n")
    else:
        print(f"\n{YELLOW}⚠️  Algunas pruebas fallaron. Revisa los errores arriba.{RESET}\n")

if __name__ == "__main__":
    main()
