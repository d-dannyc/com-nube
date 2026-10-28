"""
Punto de entrada para ejecutar el sistema Cloud Backup and Audit System (CBAS).
1. Inicializa la base de datos SQLite local (cbas_audit.db).
2. Inicia la sincronización de la carpeta asociada en segundo plano.
3. Inicia el Agente Local Watchdog en segundo plano para detectar cada guardado en tiempo real.
4. Levanta la interfaz web en http://127.0.0.1:5050.
"""

from cbas.config import CBAS_BACKEND_HOST, CBAS_BACKEND_PORT, MONITORED_DIR
from cbas.backend import app
from cbas.database import inicializar_base_datos
from cbas.agent import iniciar_observador_en_segundo_plano


def main():
    print("=" * 72)
    print("  CBAS - CONTROL DE VERSIONES Y RESPALDO EN DROPBOX CLOUD API")
    print("=" * 72)

    inicializar_base_datos()
    MONITORED_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[*] Carpeta local asociada: {MONITORED_DIR}")
    print('[*] Sincronización en segundo plano; los fallos se reintentan cada 15 segundos.')

    observador = iniciar_observador_en_segundo_plano()
    print("[OK] Monitor de archivos activo (genera versiones automaticamente al guardar).")
    print(f"[OK] Interfaz web disponible en: http://{CBAS_BACKEND_HOST}:{CBAS_BACKEND_PORT}")
    print("=" * 72)

    try:
        app.run(host=CBAS_BACKEND_HOST, port=CBAS_BACKEND_PORT, debug=False, use_reloader=False)
    finally:
        observador.stop()
        observador.join()


if __name__ == "__main__":
    main()
