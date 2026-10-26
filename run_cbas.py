"""
Punto de entrada para ejecutar el sistema Cloud Backup and Audit System (CBAS).
1. Inicializa la base de datos SQLite local (cbas_audit.db).
2. Escanea la carpeta asociada (directorio_pyme/) y respalda los archivos iniciales en Dropbox.
3. Inicia el Agente Local Watchdog en segundo plano para detectar cada guardado en tiempo real.
4. Levanta la interfaz web en http://127.0.0.1:5050.
"""

from cbas.config import CBAS_BACKEND_HOST, CBAS_BACKEND_PORT, MONITORED_DIR
from cbas.backend import app, inicializar_carpeta_y_sincronizar
from cbas.agent import iniciar_observador_en_segundo_plano
from cbas.dropbox_service import verificar_cuenta_dropbox


def main():
    print("=" * 72)
    print("  CBAS - CONTROL DE VERSIONES Y RESPALDO EN DROPBOX CLOUD API")
    print("=" * 72)

    try:
        info = verificar_cuenta_dropbox()
        print(f"[OK] Cuenta Dropbox conectada: {info['nombre_mostrar']} ({info['email']})")
        print(f"[OK] Carpeta en Dropbox: {info['carpeta_boveda']}")
    except Exception as exc:
        print(f"[AVISO] No se pudo verificar la cuenta de Dropbox al iniciar: {exc}")

    print(f"[*] Carpeta local asociada: {MONITORED_DIR}")
    sincronizados = inicializar_carpeta_y_sincronizar()
    if sincronizados:
        print(f"[+] Se registraron {len(sincronizados)} archivos iniciales en Dropbox.")
    else:
        print("[+] Los archivos de la carpeta asociada ya estan sincronizados.")

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
