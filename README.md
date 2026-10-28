# CBAS — Cloud Backup & Audit System

Proyecto de Computación en la Nube. Respaldo de archivos en Dropbox y registra sus versiones en SQLite. Su panel web permite consultar cambios, descargar copias y restaurar versiones anteriores.

## Requisitos

- Python 3.11 o superior.
- Una cuenta de Dropbox, una aplicación en [Dropbox Developers](https://www.dropbox.com/developers/apps) y conexión a Internet.

## Instalación en Windows

En PowerShell, clona el repositorio y prepara el entorno:

```powershell
git clone https://github.com/d-dannyc/com-nube.git
cd com-nube
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
```

## Conectar Dropbox

1. Abre tu aplicación en Dropbox Developers o crea una con acceso **App Folder**.
2. En **Permissions**, habilita `account_info.read`, `files.metadata.read`, `files.content.read` y `files.content.write`.
3. Obtén la **App key** y el **App secret** en **Settings**.
4. Ejecuta el asistente y sigue el enlace de autorización que muestra:

```powershell
.\.venv\Scripts\python.exe scripts\setup_oauth.py
```

El asistente guarda las credenciales en `.env`. Si ya tienes configurado ese archivo, puedes omitir este paso. No compartas ni subas `.env` al repositorio.

## Iniciar y usar

```powershell
.\.venv\Scripts\python.exe run_cbas.py
```

Abre **http://127.0.0.1:5050** y mantén la terminal abierta. Para detener el sistema, pulsa **Ctrl+C**.

Guarda los archivos directamente en `directorio_pyme/`: se respaldan automáticamente en Dropbox. Desde el panel puedes seleccionar un archivo y consultar, comparar, descargar o restaurar sus versiones. La restauración pide confirmación antes de reemplazar el archivo local.

Para cambiar el puerto o la carpeta remota, consulta las variables de `.env.example`, agrégalas a `.env` y reinicia el programa.
