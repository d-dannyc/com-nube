# Guia de Instalacion y Puesta en Marcha — CBAS

Esta guia contiene el paso a paso detallado para clonar, configurar y ejecutar el sistema **CBAS (Cloud Backup & Audit System)** en cualquier ordenador (Windows, Linux o macOS).

---

## 1. Requisitos Previos

Antes de comenzar, asegurate de tener instalado en tu computadora:

* **Python 3.11** o superior. Puedes comprobar tu version ejecutando:
  ```bash
  python --version
  ```
* **Git** para clonar el repositorio:
  ```bash
  git --version
  ```
* **Conexion a Internet** y una cuenta gratuita en [Dropbox](https://www.dropbox.com/).

---

## 2. Clonar el Repositorio

Abre una terminal (PowerShell en Windows o Bash en Linux/macOS) y clona el proyecto:

```bash
git clone https://github.com/d-dannyc/com-nube.git
cd com-nube
```

---

## 3. Crear y Activar el Entorno Virtual

Es recomendable utilizar un entorno virtual para aislar las librerias del proyecto.

### En Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
*(Si PowerShell bloquea la ejecucion de scripts, ejecuta una vez: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

### En Windows (Simbolo del sistema / CMD):
```cmd
python -m venv .venv
.\.venv\Scripts\activate.bat
```

### En Linux o macOS (Bash / Zsh):
```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

## 4. Instalar Dependencias

Con el entorno virtual activado, instala exactamente las versiones fijadas en el archivo de bloqueo:

```bash
pip install -r requirements.lock.txt
```

> **Nota:** La libreria interna de CBAS para previsualizar y comparar documentos de Word (`.docx`) viene incluida en el proyecto (`cbas/documents.py`), por lo que no necesitas tener instalado Microsoft Office ni programas externos.

---

## 5. Crear la Aplicacion en Dropbox Developers

Para que tu instalacion pueda comunicarse con la nube de Dropbox, debes registrar una aplicacion gratuita en la consola de desarrolladores. Solo toma 2 minutos:

1. Ingresa a la consola de desarrolladores de Dropbox:
   [https://www.dropbox.com/developers/apps](https://www.dropbox.com/developers/apps)
2. Inicia sesion con tu cuenta de Dropbox y haz clic en el boton **Create app**.
3. Completa los siguientes 3 campos:
   * **1. Choose an API:** Selecciona **Scoped access**.
   * **2. Choose the type of access:** Selecciona **App folder** (esto crea una carpeta exclusiva para el sistema, sin acceso al resto de tus archivos personales).
   * **3. Name your app:** Escribe un nombre unico (ejemplo: `CBAS-Pyme-TuNombre`).
4. Haz clic en **Create app**.
5. Ve a la pestaña **Permissions** y marca unicamente estas 4 casillas:
   * `account_info.read` (permite consultar el estado de la cuenta y espacio disponible).
   * `files.metadata.read` (permite consultar las revisiones y fechas de los archivos).
   * `files.content.read` (permite descargar versiones anteriores para comparacion y recuperacion).
   * `files.content.write` (permite respaldar y actualizar archivos en la nube).
6. Haz clic en el boton **Submit** al pie de la pagina para guardar los permisos.
7. Regresa a la pestaña **Settings** y copia:
   * **App key** (cadena visible de texto).
   * **App secret** (haz clic en *Show* y copiala).

---

## 6. Vinculacion Automatica (Asistente OAuth 2.0)

CBAS cuenta con un asistente interactivo que realiza la autorizacion y genera el token de acceso permanente de forma automatica:

Ejecuta en tu terminal:

```bash
python scripts/setup_oauth.py
```

Sigue los 4 pasos que te pedira la consola:
1. Pega tu **App key** y presiona Enter.
2. Pega tu **App secret** y presiona Enter.
3. El asistente imprimira un enlace web. Copialo, pegalo en tu navegador, inicia sesion con tu cuenta de Dropbox y presiona **Permitir** (Allow).
4. Dropbox te entregara un codigo de autorizacion. Copialo, pegalo en la terminal y presiona Enter.

Al finalizar, veras el mensaje:
```text
[OK] Vinculacion OAuth 2.0 completada con exito.
[OK] Credenciales guardadas en: .env
```

El archivo `.env` quedara configurado automaticamente en la raiz de tu proyecto con un **Refresh Token** permanente que nunca caduca.

---

## 7. Iniciar el Sistema

Para arrancar el servidor web y el agente de monitoreo en segundo plano simultaneamente:

```bash
python run_cbas.py
```

Veras un mensaje de confirmacion similar a este:
```text
========================================================================
  CBAS - CONTROL DE VERSIONES Y RESPALDO EN DROPBOX CLOUD API
========================================================================
[*] Carpeta local asociada: .../directorio_pyme
[*] Sincronizacion en segundo plano activa.
[OK] Monitor de archivos activo (genera versiones automaticamente al guardar).
[OK] Interfaz web disponible en: http://127.0.0.1:5050
========================================================================
```

Abre tu navegador en:
**http://127.0.0.1:5050**

Mantén la terminal abierta mientras uses el sistema. Para detenerlo, presiona `Ctrl + C`.

---

## 8. Verificacion y Prueba Rapida de Funcionamiento

Para comprobar que todo funciona correctamente en menos de 2 minutos:

1. Con el sistema corriendo, crea o copia cualquier archivo (ejemplo: `nota_prueba.txt` o un documento `.docx`) dentro de la carpeta local `directorio_pyme/`.
2. Ve al panel web (**http://127.0.0.1:5050**): veras que el archivo aparece inmediatamente en la lista con su version inicial (`v1`).
3. Abre el archivo en tu computadora, escribe algo nuevo y guardalo. En menos de 2 segundos, el panel web detectara el guardado y creara la version `v2`.
4. En el panel podras ver la diferencia de texto (*diff*), descargar la version anterior o fijar un hito formal.
5. Ve a la pestaña **Salud y Recuperacion**: podras comprobar el estado contra Dropbox Cloud y realizar la prueba guiada de alteracion y restauracion en 1 clic.

---

## 9. Ejecucion de Pruebas Unitarias

Para validar que todo el codigo, el backend y los servicios responden al 100%, puedes ejecutar la suite automatizada de pruebas:

```bash
python -m unittest discover tests
python -m unittest tests/test_documents.py
```

Deben completarse las **38 pruebas unitarias** exitosamente (0 errores).

---

## 10. Preguntas Frecuentes y Solucion de Problemas

### El puerto 5050 ya esta en uso
Si otra aplicacion utiliza el puerto 5050, puedes cambiarlo abriendo el archivo `.env` y agregando la siguiente linea:
```text
CBAS_BACKEND_PORT=5060
```
Reinicia `run_cbas.py` y abre `http://127.0.0.1:5060`.

### "No se puede reemplazar el archivo local" al restaurar
Si intentas restaurar un documento de Word que tienes abierto en Microsoft Word u otro editor, el sistema operativo bloquea el archivo contra escritura. Simplemente cierra el documento en Word y vuelve a presionar el boton de restauracion.

### Error de permisos de Dropbox
Si la consola muestra un error de autenticacion al subir archivos, verifica que en la consola de Dropbox Developers (pestaña **Permissions**) hayas marcado los 4 permisos (`account_info.read`, `files.metadata.read`, `files.content.read` y `files.content.write`) y hayas hecho clic en el boton **Submit** al pie de la pagina. Luego vuelve a ejecutar `python scripts/setup_oauth.py`.
