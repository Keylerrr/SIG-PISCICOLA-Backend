#!/usr/bin/env python
"""
Script para ejecutar servidor y pruebas automáticamente
Uso: python run_tests.py
"""

import subprocess
import time
import sys
import os
from pathlib import Path

# Directorio del proyecto
PROJECT_DIR = Path(__file__).parent
PYTHON_PATH = r"C:\Users\Jaider Contreras\AppData\Local\Programs\Python\Python312\python.exe"

def print_banner(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def run_command(command, description, settings=None):
    """Ejecutar comando con manejo de errores"""
    print(f"[...] {description}...")

    env = os.environ.copy()
    if settings:
        env["DJANGO_SETTINGS_MODULE"] = settings

    try:
        result = subprocess.run(
            command,
            cwd=PROJECT_DIR,
            env=env,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            print(f"[OK] {description} - OK")
            return True
        else:
            print(f"[FAIL] {description} - FALLO")
            if result.stderr:
                print(f"Error: {result.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        print(f"[FAIL] {description} - TIMEOUT")
        return False
    except Exception as e:
        print(f"[FAIL] {description} - Exception: {e}")
        return False

def main():
    print_banner("[TEST RUNNER] - SIG-PISCICOLA Estanques")

    # 1. Migraciones
    print("\n[SETUP] Fase 1: Preparar base de datos...")
    if not run_command(
        [PYTHON_PATH, "manage.py", "migrate", "--settings=configs.test_settings"],
        "Ejecutar migraciones",
        "configs.test_settings"
    ):
        print("Error: No se pudieron ejecutar migraciones")
        return False

    # 2. Iniciar servidor en background
    print("\n[SETUP] Fase 2: Iniciar servidor Django...")
    print("Iniciando servidor en puerto 8000...")

    server_process = subprocess.Popen(
        [PYTHON_PATH, "manage.py", "runserver", "--settings=configs.test_settings"],
        cwd=PROJECT_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Esperar a que el servidor inicie
    time.sleep(3)

    if server_process.poll() is not None:
        print("Error: El servidor no pudo iniciarse")
        _, err = server_process.communicate()
        print(err[:500])
        return False

    print("OK: Servidor iniciado")

    # 3. Ejecutar pruebas
    print("\n[TESTS] Fase 3: Ejecutar pruebas...")
    time.sleep(1)

    try:
        result = subprocess.run(
            [PYTHON_PATH, "test_api.py"],
            cwd=PROJECT_DIR,
            capture_output=False,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            print("\nOK: Pruebas completadas exitosamente")
            success = True
        else:
            print("\nError: Algunas pruebas fallaron")
            success = False
    except Exception as e:
        print(f"Error ejecutando pruebas: {e}")
        success = False
    finally:
        # 4. Detener servidor
        print("\n[CLEANUP] Deteniendo servidor...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
            print("OK: Servidor detenido")
        except subprocess.TimeoutExpired:
            print("Forzando terminacion del servidor...")
            server_process.kill()

    # 5. Resumen
    print_banner("Resumen Final")
    if success:
        print("[SUCCESS] TODAS LAS PRUEBAS PASARON!")
        print("\nProximos pasos:")
        print("  1. Ejecutar 'python manage.py migrate' en la BD remota")
        print("  2. Iniciar servidor en produccion")
        print("  3. Documentar endpoints en Postman")
    else:
        print("[ERROR] Algunas pruebas fallaron. Revisa los errores arriba.")

    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
