# Guia de Instalacion, Configuracion y Uso Operativo de CBAS
## Cloud Backup & Audit System | Dropbox Platform API v2
### Universidad Mayor de San Andres (UMSA) - Computacion en la Nube (Grupo 2)

---

## 1. Descripcion General del Sistema

CBAS (Cloud Backup & Audit System) es una solucion de continuidad de negocio y custodia de archivos corporativos en la nube para PYMEs. Utiliza la infraestructura de Dropbox Cloud Platform (API v2) como motor de almacenamiento masivo y versionado inmutable, complementado con un backend de telemetria de red, metadatos y consola web de administracion bajo el sistema de diseno Open Enterprise Tech.

El sistema opera de forma desatendida: cuando un empleado guarda un documento en la carpeta corporativa asociada (directorio_pyme), el Agente Local calcula el hash SHA-256 por bloques de 4 MB y lo sincroniza de inmediato con Dropbox. Desde la consola web, el administrador puede examinar el historial de versiones, consultar la pista de auditoria de red, descargar copias directas de cualquier version o restaurar un archivo en la estacion de trabajo en un clic.

---

## 2. Requisitos Previos del Entorno

- Sistema Operativo: Linux (Ubuntu, Debian, Fedora), macOS o Windows 10/11.
- Python: Version 3.10 o superior (verificado con Python 3.12).
- Cuenta activa en Dropbox (Plan gratuito o comercial).
- Conexion a Internet para comunicarse con los endpoints de Dropbox Cloud API v2.

---

## 3. Instalacion y Puesta en Marcha

### Paso 1: Clonar o posicionarse en el directorio del proyecto

```bash
cd /home/carloos-odann/PROYECTOS/UNI-VERSALIDAD/COM-NUBE/proyecto-dropbox
```

### Paso 2: Crear y activar el entorno virtual de Python

```bash
python3 -m venv venv
source venv/bin/activate
```

### Paso 3: Instalar las dependencias oficiales

```bash
pip install -r requirements.txt
```

Las dependencias principales instaladas son:
- dropbox: SDK oficial de Python para Dropbox Cloud API v2.
- watchdog: Monitoreo reactivo de eventos del sistema de archivos en tiempo real.
- flask: Servidor web y API REST de telemetria y gestion.
- python-dotenv: Carga de variables de entorno y credenciales OAuth 2.0.
- requests: Cliente HTTP para verificaciones auxiliares.

### Paso 4: Variables de entorno (.env)

El archivo .env en la raiz contiene las credenciales de la aplicacion registrada en Dropbox Developers con alcance App Folder y permisos minimos (account_info.read, files.metadata.read, files.content.read, files.content.write):

```env
DROPBOX_APP_KEY=tu_app_key
DROPBOX_APP_SECRET=tu_app_secret
DROPBOX_REFRESH_TOKEN=tu_refresh_token_permanente
PORT=5050
```

---

## 4. Ejecucion del Sistema

Para iniciar simultaneamente el Agente Local en tiempo real y el Servidor Web de administracion, ejecute:

```bash
python3 run_cbas.py
```

Salida esperada en la consola:

```text
========================================================================
  CLOUD BACKUP & AUDIT SYSTEM (CBAS) - DROPBOX PLATFORM
  Universidad Mayor de San Andres | Computacion en la Nube - Grupo 2
========================================================================
  Cuenta Dropbox : Dan Y El o Carlos Chambi (dannyperseverante70v7@gmail.com)
  Carpeta local  : /home/carloos-odann/.../directorio_pyme
  Panel Web      : http://127.0.0.1:5050
========================================================================
```

Abra su navegador web en: **http://127.0.0.1:5050**

---

## 5. Como Operar y Verificar el Sistema

### 5.1 Boveda y Versiones

1. En la seccion **Boveda y Versiones**, la lista superior muestra todos los documentos monitoreados dentro de directorio_pyme (archivos de balance CSV, configuraciones JSON, documentos Markdown, contratos Word y reportes PDF).
2. Al hacer clic sobre cualquier archivo, se carga la ficha tecnica del documento junto con su linea de tiempo de versiones (v1, v2, v3...).
3. Cada tarjeta de version muestra:
   - Numero de version y tipo de evento (CREADO, MODIFICADO, RESTAURADO).
   - Codigo rev de Dropbox asignado por la nube.
   - Hash criptografico SHA-256 de bloques de 4 MB.
   - Usuario del sistema operativo y direccion IP de la estacion de trabajo.
   - Fecha y hora exacta en formato UTC.

### 5.2 Descarga Directa vs. Restauracion Local

- **Boton "Descargar copia de esta version":** Descarga inmediatamente al navegador el archivo exacto de esa version desde los servidores de Dropbox, sin alterar ni sobrescribir el archivo de trabajo en el disco local.
- **Boton "Restaurar en estacion de trabajo":** Invoca el endpoint files_restore de Dropbox API v2, actualiza la boveda en la nube y descarga el archivo a la carpeta directorio_pyme, registrando la nueva version con la etiqueta RESTAURADO sin producir bucles infinitos.

### 5.3 Pista de Auditoria y Telemetria

En la seccion **Registro de Auditoria**, el sistema ofrece una tabla cronologica completa conforme a las normas ISO/IEC 27001 (A.12.4) y COBIT, permitiendo filtrar por archivo y ver la trazabilidad de cada guardado con su IP y usuario de red.
