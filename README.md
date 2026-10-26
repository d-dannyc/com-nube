# Cloud Backup & Audit System (CBAS)
## Sistema de Respaldo Descentralizado, Telemetría y Custodia de Archivos basado en Dropbox Cloud API v2

**Universidad Mayor de San Andrés (UMSA)**  
**Facultad de Ciencias Puras y Naturales - Carrera de Informática**  
**Materia:** Computación en la Nube (INF-318)  
**Docente:** Ph.D. Jose Maria Tapia Baltazar  
**Grupo N° 2:**
- Saul Mijael Choquehuanca Huanca
- Carlos Daniel Quispe Chambi
- Victor Bernardo Quispe Rojas
- Gabriel Yujra Machaca

---

## 1. Propósito y Principio de Computación en la Nube

CBAS es una solución de continuidad de negocio y custodia de información corporativa orientada a PYMEs. El sistema aplica el principio de **Desacoplamiento de Almacenamiento (Storage Decoupling)**:

- **Capa de Almacenamiento Masivo (Dropbox Cloud PaaS / STaaS):** Toda la redundancia multirregión, alta disponibilidad, cifrado en reposo AES-256 y versionado inmutable de archivos pesados (PDFs, hojas de cálculo, documentos Word, datos contables) se delega a la infraestructura de Dropbox mediante su API v2.
- **Capa de Lógica y Telemetría de Red (Backend y Consola Web):** Un servidor REST en Flask y base de datos relacional SQLite gestionan exclusivamente los metadatos de auditoría (usuario del sistema operativo, dirección IP local, nombre del equipo, código de revisión rev, hash de bloque SHA-256 y marcas de tiempo UTC).
- **Capa de Cliente Desatendida (Agente Local Watchdog):** Monitorea la carpeta corporativa asociada (directorio_pyme) en tiempo real, aplicando una ventana de debouncing de 1.0 segundo y verificación criptográfica por bloques de 4 MB para evitar transferencias redundantes.

---

## 2. Características Principales

1. **Respaldo Automático por Guardado:** Se activa de forma transparente al guardar cualquier documento en la carpeta corporativa, sin requerir intervención manual ni comandos técnicos.
2. **Consola Web con Sistema de Diseño Open Enterprise Tech:** Interfaz sobria, minimalista y legible, inspirada en las líneas de diseño técnico de Red Hat (paleta con acentos en rojo corporativo #EE0000, fondos neutros claros #FBF9F9 y tipografía IBM Plex Sans e IBM Plex Mono).
3. **Ficha Técnica y Gestión de Versiones en la Nube:** Permite inspeccionar cualquier versión histórica (v1, v2, v3...) con sus identificadores criptográficos y metadatos de origen.
4. **Doble Mecanismo de Recuperación:**
   - **Descarga directa:** Permite bajar cualquier revisión histórica al navegador sin alterar el archivo actual de la estación de trabajo.
   - **Restauración en un clic:** Revierte el archivo en la nube de Dropbox y lo restablece directamente en la carpeta local con protección anti-bucle infinito.
5. **Pista de Auditoría de Red (ISO/IEC 27001 A.12.4 & COBIT):** Registro inmutable de cada evento con usuario, dirección IP, tamaño transferido y código rev.

---

## 3. Estructura del Repositorio

```text
COM-NUBE/proyecto-dropbox/
├── .env                              # Credenciales OAuth 2.0 (App Key, Secret y Refresh Token permanente)
├── .env.example                      # Plantilla de variables de entorno
├── README.md                         # Documentación general de CBAS
├── Proyecto-CC.md                    # Informe académico completo del proyecto
├── requirements.txt                  # Dependencias de Python
├── run_cbas.py                       # Lanzador unificado (Agente Local + Servidor Web)
├── cbas/                             # Paquete modular CBAS
│   ├── __init__.py
│   ├── config.py                     # Detección de red local, IP, hostname y usuario SO
│   ├── hasher.py                     # Algoritmo Dropbox content_hash (bloques de 4 MB SHA-256)
│   ├── database.py                   # Persistencia relacional de versiones y metadatos
│   ├── dropbox_service.py            # SDK Dropbox API v2 (upload, download por rev, restore)
│   ├── agent.py                      # Agente reactivo Watchdog con debouncing de 1s
│   ├── backend.py                    # API REST Flask y servidor web de gestión
│   └── templates/
│       └── dashboard.html            # Consola Web corporativa (Open Enterprise Tech)
├── scripts/
│   └── setup_oauth.py                # Asistente de vinculación OAuth 2.0 (Offline Access)
├── directorio_pyme/                  # Carpeta corporativa monitoreada en la estación local
└── docs/                             # Guías operativas, diapositivas y capturas reales
    ├── guia_instalacion_y_uso.md
    ├── presentacion_diapositivas.md
    ├── plantilla_dropbox_paper.md
    ├── acta_conformidad_dropbox_sign.md
    └── capturas/
        ├── cbas_dashboard_general.png
        ├── cbas_alerta_ransomware.png
        ├── cbas_restauracion_exitosa.png
        └── cbas_acta_auditoria_sign.png
```

---

## 4. Puesta en Marcha Rápida

```bash
# 1. Activar entorno virtual
source venv/bin/activate

# 2. Iniciar servidor y agente de monitoreo
python3 run_cbas.py
```

Acceso al panel de administración: **http://127.0.0.1:5050**
