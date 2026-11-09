# AGENTS.md — Reglas, Guía de Desarrollo y Ciclo de Iteración para Agentes en CBAS

> **Proyecto:** CBAS (Cloud Backup & Storage Governance) — Versión PYME Enterprise  
> **Ámbito:** UMSA - Grupo 2  
> **Repositorio:** `com-nube`

Este documento define la arquitectura, las directrices de codificación, las reglas de seguridad, la especificación de tokens de diseño y el **flujo iterativo obligatorio** de habilidades (*skills*) que cualquier agente de IA o desarrollador debe ejecutar al trabajar en este proyecto.

---

## 1. Visión y Arquitectura del Sistema

CBAS es un sistema descentralizado de gobierno documental, control de versiones, auditoría forense y ciberresiliencia diseñado para Pequeñas y Medianas Empresas (PYMEs).

### Principios Fundamentales
1. **Desacoplamiento de Almacenamiento (*Storage Decoupling*):**
   - **Plano de Datos (Binarios):** Los archivos reales (Word, CSV, JSON, PDF) se transmiten directamente a la infraestructura de Dropbox Cloud API v2 (Magic Pocket / cifrado AES-256).
   - **Plano de Control (Metadatos):** El servidor local hospeda únicamente telemetría ligera en SQLite (`cbas_audit.db`): hashes SHA-256 de bloques de 4 MB, identificadores `rev`, timestamps UTC, usuarios, IPs y pistas forenses ISO 27001.
2. **Eficiencia WAN (Delta Sync):**
   - Utiliza el algoritmo oficial `content_hash` de Dropbox basado en fragmentos de **4 MB (4,194,304 bytes)** para no reenviar archivos idénticos ni saturar el ancho de banda de la empresa.
3. **Cero Dependencias Pesadas (*Zero-Bloat Offline First*):**
   - **Backend:** Python 3.11+, Flask, Watchdog, SDK oficial de Dropbox y SQLite nativo.
   - **Frontend:** HTML5 semántico, CSS3 puro y Vanilla JavaScript nativo en [`cbas/static/`](file:///d:/PROJECTS/com-nube/cbas/static/). **No se permiten librerías externas por CDN** (el panel opera 100% desconectado a internet en la red LAN).
4. **Lenguaje Estrictamente Técnico, Fáctico y Profesional (Sin Emojis ni Metáforas):**
   - **Prohibición de Emojis:** Queda terminantemente prohibido el uso de emojis tanto en la interfaz de usuario (HTML/JS), como en el código fuente, commits, documentación y respuestas del agente. La interfaz debe utilizar exclusivamente etiquetas de texto sobrias o iconos SVG monocromáticos estándar.
   - **Prohibición de Metáforas y Alucinaciones:** Queda prohibido recurrir a metáforas ("viaje en el tiempo", "bóveda mágica", "resurrección de archivos") o analogías de la IA con la vida real.
   - **Claridad Fáctica:** Las explicaciones y textos de la UI deben describir exactamente el funcionamiento del software: directorio monitoreado en disco local, sincronización con Dropbox Cloud API, cálculo de hashes SHA-256 por bloques de 4 MB, historial correlativo de revisiones y restauración de copias anteriores.
5. **Regla Estricta: Cero Commits Automáticos por el Agente:**
   - El agente tiene **estrictamente prohibido ejecutar `git commit` por su cuenta**.
   - Toda creación de commits queda exclusivamente bajo la potestad del desarrollador humano.
   - Al finalizar un hito relevante de implementación o refactorización, el agente debe únicamente sugerir los comandos exactos bajo el formato de *Conventional Commits*:
     ```bash
     git add <archivos_relevantes>
     git commit -m "<tipo>(<alcance>): <descripción técnica fáctica>"
     ```
     Tipos estándar permitidos: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`.

---

## 2. Sistema de Diseño y Paleta de Colores Adaptable

La paleta de color del proyecto está modelada como un sistema desacoplado de **Design Tokens Semánticos** mediante variables CSS en [`cbas/static/dashboard.css`](file:///d:/PROJECTS/com-nube/cbas/static/dashboard.css). Esto permite que la identidad visual pueda personalizarse o reconfigurarse en cualquier momento modificando únicamente el bloque `:root`, sin alterar la estructura HTML ni la lógica JavaScript.

### Tokens de Color Base (Propuesta Corporativa de Alta Visibilidad)

| Token CSS | Valor Hex / Fallback | Rol Semántico en la Interfaz |
| :--- | :--- | :--- |
| `--brand` | `#ee0000` | Identidad de marca, logotipo y acentos principales |
| `--accent` | `#c40000` | Acciones interactivas primarias, botones destacados y estados activos |
| `--accent-dark` | `#a30000` | Estado *hover* y foco de botones principales |
| `--accent-soft` | `#fff0ef` | Superficie tenue para filas de archivos seleccionadas o alertas suaves |
| `--canvas` | `#fbf9f9` | Fondo general del espacio de trabajo (tono cálido de baja fatiga visual) |
| `--card` / Superficie | `#ffffff` | Superficie de lectura de documentos, tarjetas y modales |
| `--ink` | `#151515` | Texto principal de alto contraste y títulos |
| `--muted` | `#626262` | Texto secundario, etiquetas de telemetría y metadatos |
| `--line` | `#e5dfde` | Bordes limpios, divisores de paneles y líneas de tabla |
| `--green` | `#257353` | Estado exitoso, conexión activa, respaldos completados y rollback mitigado |
| `--amber` | `#87561a` | Estado de advertencia, sesiones de edición activas y alertas no críticas |
| `--danger` / Crítico | `#c40000` | Alertas forenses críticas (cifrado ransomware, alteración de archivos congelados) |

> **Regla de Adaptabilidad:** Cualquier cambio futuro de color (ej. cambio a azul corporativo, esmeralda o pizarra) debe realizarse exclusivamente a nivel de tokens en CSS. Ningún componente o script debe acoplarse a nombres comerciales de colores.

---

## 3. Ciclo de Iteración Obligatorio para Agentes (*Iteration Workflow*)

En cada ciclo de trabajo o iteración de desarrollo, el agente debe invocar y seguir las siguientes *skills* en orden estricto:

```text
[Requerimiento] 
       ↓
1. Análisis y Planificación     → skills/brainstorming & skills/writing-plans
       ↓
2. Criterio Senior Pragmático   → skills/ponytail (YAGNI, mínimo código, cero bloat)
       ↓
3. Desarrollo Guiado por Tests  → skills/test-driven-development (TDD)
       ↓
4. Diagnóstico (si hay fallos)  → skills/systematic-debugging
       ↓
5. Interfaz y Tokens (si aplica)→ skills/impeccable
       ↓
6. Verificación de Cierre       → skills/verification-before-completion (unittest OK)
       ↓
7. Revisión y Seguridad         → skills/requesting-code-review & skills/receiving-code-review
       ↓
[Entrega Lista]
```

### Detalle de Skills a usar en cada fase:

#### Fase 1: Análisis y Planificación
- **`skills/brainstorming`**: Utilízala antes de implementar funciones creativas o cambios arquitectónicos. Evalúa alternativas y valida supuestos.
- **`skills/writing-plans`**: Utilízala para desglosar tareas multi-paso en planes ejecutables antes de tocar código.
- **`skills/using-superpowers`**: Orquestador del flujo; establece las pautas de invocación antes de responder.

#### Fase 2: Implementación con Criterio Senior Pragmático
- **`skills/ponytail`**: **Filosofía rectora permanente.** Resuelve el problema con la menor cantidad de código nuevo posible.
  - Prohibido agregar dependencias externas para resolver lo que ya hace la biblioteca estándar de Python (`csv`, `json`, `difflib`, `hashlib`, `xml.etree`).
  - Prohibido crear código "por si acaso" o abstracciones innecesarias.

#### Fase 3: Pruebas Unitarias y TDD
- **`skills/test-driven-development`**: Escribe o actualiza las pruebas en [`tests/`](file:///d:/PROJECTS/com-nube/tests/) antes o en paralelo con la lógica.
  - Comprueba que la prueba falle por la razón esperada antes de implementar la solución en el backend.

#### Fase 4: Depuración Sistemática
- **`skills/systematic-debugging`**: Si se produce un error en Watchdog, SQLite, Dropbox o en el renderizado:
  - No intentes parches aleatorios ni cambios a ciegas.
  - Sigue las 4 fases: Reproducir → Aislar causa raíz → Corregir en el origen → Verificar que no haya regresiones.

#### Fase 5: Experiencia de Usuario y Frontend
- **`skills/impeccable`**: Gobierna el **Modo Operate** de [DESIGN.md](file:///d:/PROJECTS/com-nube/DESIGN.md):
  - Prioriza la densidad informativa y el escaneo rápido sobre la ornamentación.
  - Emplea fuentes del sistema operativo y respeta la jerarquía de tres columnas.

#### Fase 6: Verificación Obligatoria de Cierre
- **`skills/verification-before-completion`**: **Regla de oro no negociable.**
  - Antes de afirmar que una tarea está resuelta o hacer commit, debes ejecutar:
    ```powershell
    .\.venv\Scripts\python.exe -m unittest discover tests
    ```
  - Todos los tests (38 tests mínimos) deben resultar en `OK`.

#### Fase 7: Revisión de Código y Resistencia
- **`skills/requesting-code-review`** & **`skills/receiving-code-review`**:
  - Revisa que todo archivo esté protegido contra *path traversal* con `validar_nombre`.
  - Revisa que las operaciones de archivo empleen `with bloqueo_archivo(nombre_archivo):`.
  - Verifica que cada evento registre telemetría forense (IP, usuario, equipo, hash de 4 MB y UTC).
- **`skills/finishing-a-development-branch`**: Concluye el ciclo integrando y verificando que la rama de trabajo esté limpia.

---

## 4. Estructura de Directorios del Proyecto

```text
com-nube/
├── cbas/                       # Paquete central del backend y frontend
│   ├── agent.py                # Agente Watchdog local (debounce, locks y sesiones)
│   ├── backend.py              # Servidor Flask, API REST y endpoints de auditoría
│   ├── config.py               # Configuración de entorno y telemetría de estación
│   ├── database.py             # Capa SQLite (migraciones, diffs, hitos, poda y riesgos)
│   ├── documents.py            # Extracción segura de texto Word .docx sin Word instalado
│   ├── dropbox_service.py      # Cliente Dropbox API v2 (OAuth Refresh Token permanente)
│   ├── hasher.py               # Algoritmo content_hash de bloques de 4 MB de Dropbox
│   ├── validation.py           # Validadores estrictos de rutas departamentales y revisiones
│   ├── static/                 # dashboard.css y dashboard.js (Vanilla, sin CDNs)
│   └── templates/              # dashboard.html (interfaz unificada responsive)
├── directorio_pyme/            # Carpeta local monitoreada en tiempo real
│   ├── Contabilidad/           # Balances, comprobantes, facturas (.csv, .xlsx)
│   ├── Recursos_Humanos/       # Planillas de sueldos, nóminas (.csv)
│   ├── Legal/                  # Contratos con proveedores, licencias (.md, .docx)
│   ├── Sistemas_TI/            # Configuraciones ERP, scripts (.json, .sql)
│   ├── General/                # Documentos generales de la empresa
│   └── .cbas_recovery/         # Buffer de contingencia ante apagones (oculto, no sincronizado)
├── tests/                      # Suite de pruebas automatizadas
│   ├── test_cbas.py            # Pruebas integrales de API, auditoría, poda y resiliencia
│   └── test_documents.py       # Pruebas de extracción y diff para archivos Word
├── scripts/
│   └── setup_oauth.py          # Asistente interactivo para vincular Dropbox con Refresh Token
├── .agents/skills/             # Catálogo de habilidades del agente
├── PRODUCT.md                  # Especificación del producto según Impeccable
├── DESIGN.md                   # Sistema de diseño (Modo Operate, tokens semánticos)
└── run_cbas.py                 # Lanzador unificado (Backend + Watchdog)
```

---

## 5. Comandos Frecuentes de la Estación

```powershell
# 1. Ejecutar el servidor central (Backend Flask + Agente Watchdog)
.\.venv\Scripts\python.exe run_cbas.py

# 2. Correr la suite de pruebas unitarias
.\.venv\Scripts\python.exe -m unittest discover tests

# 3. Asistente de vinculación de credenciales permanentes de Dropbox
.\.venv\Scripts\python.exe scripts\setup_oauth.py
```
