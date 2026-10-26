**UNIVERSIDAD MAYOR DE SAN ANDRÉS**  
**FACULTAD DE CIENCIAS PURAS Y NATURALES**  
**CARRERA DE INFORMÁTICA**  
![][image1]

**Materia: Computación en la Nube**

**Proyecto Cloud Computing: Ecosistema Dropbox**

## ***"CLOUD BACKUP AND AUDIT SYSTEM (CBAS): SISTEMA DE RESPALDO DESCENTRALIZADO Y CONTROL DE VERSIONES PARA PYMES BASADO EN DROPBOX CLOUD API"***

**INTEGRANTES (GRUPO N° 2):**  
1\. Univ. Choquehuanca Huanca Saul Mijael  
2\. Univ. Quispe Chambi Carlos Daniel  
3\. Univ. Quispe Rojas Victor Bernardo  
4\. Univ. Yujra Machaca Gabriel

**DOCENTE:** Ph.D. JOSE MARIA TAPIA BALTAZAR  
**FECHA:** Octubre de 2026

**La Paz \- Bolivia**  
**2026**

---

# **I. PRIMERA PARTE: FUNDAMENTACIÓN TEÓRICA Y PROBLEMÁTICA (30%)**

# **1\. INTRODUCCIÓN**

En el entorno empresarial contemporáneo, las Pequeñas y Medianas Empresas (PYMEs) enfrentan dos desafíos críticos respecto a la seguridad y continuidad de sus activos de información: la **pérdida de datos** ocasionada por errores humanos involuntarios o ataques de secuestro de información (*ransomware*), y la **ausencia de trazabilidad (auditoría)** sobre quién modifica los documentos críticos del negocio, desde qué terminal y en qué instante exacto.

Las herramientas tradicionales de control de versiones procedentes de la ingeniería de software (como Git) resultan excesivamente complejas y ajenas para usuarios de áreas operativas no técnicas, tales como contadores, administradores financieros, analistas de recursos humanos o gestores de contratos. En el extremo opuesto, diseñar e implementar desde cero una arquitectura de almacenamiento masivo, redundante y seguro sobre infraestructuras de nube pura (como Amazon AWS S3 o Microsoft Azure Blob Storage) exige configuraciones avanzadas de políticas de identidad (IAM), reglas de ciclo de vida y costos de administración técnica que superan el presupuesto operativo de una PYME.

Frente a esta realidad, es indispensable comprender que **Dropbox** no es un simple disco duro virtual para guardar archivos manualmente ni un sustituto pasivo de herramientas ofimáticas como Google Drive. Dropbox constituye una plataforma tecnológica integral de **Computación en la Nube (SaaS y PaaS)** respaldada por su propia infraestructura física distribuida a escala de exabytes (**Magic Pocket**), un motor de sincronización diferencial a nivel de bloques de 4 MB (**Delta Sync**), un libro mayor transaccional e inmutable de historial de versiones (**Version History**) y un ecosistema empresarial que abarca colaboración en tiempo real (**Dropbox Paper**), firma electrónica con validez jurídica (**Dropbox Sign**) y búsqueda universal asistida por inteligencia artificial (**Dropbox Dash**).

El presente proyecto desarrolla e implementa **Cloud Backup and Audit System (CBAS)**, un sistema de respaldo automatizado en tiempo real y auditoría forense de versiones orientado a PYMEs. CBAS resuelve la problemática planteada mediante una **arquitectura híbrida y desacoplada (*Storage Decoupling*)**: utiliza la infraestructura de **Dropbox Cloud API v2** como motor central de almacenamiento binario y control de versiones nativo, mientras que un servidor backend independiente con su propia base de datos relacional gestiona exclusivamente los metadatos de auditoría (usuario del sistema operativo, dirección IP, nombre del equipo, fecha UTC, hash criptográfico de bloques e identificador de revisión). De este modo, las organizaciones pueden "viajar en el tiempo" desde un panel web intuitivo para auditar modificaciones y restaurar archivos corrompidos en un solo clic, optimizando drásticamente el consumo de ancho de banda y los costos de almacenamiento en la nube.

---

# **2\. MARCO TEÓRICO**

## **2.1 Qué es Dropbox: Definición, Origen y Propósito General**

Dropbox es una plataforma pionera de computación en la nube diseñada para el almacenamiento seguro de objetos, la sincronización automática de archivos multiplataforma, el control transaccional de versiones y la colaboración documental empresarial. Fue fundada en el año 2007 en Boston, Estados Unidos, por Drew Houston y Arash Ferdowsi, entonces estudiantes de ingeniería del Instituto Tecnológico de Massachusetts (MIT).

El propósito original de Dropbox nació para resolver una limitación cotidiana de la informática personal y corporativa de mediados de la década de 2000: la dependencia de memorias flash USB físicas o del envío reiterado de archivos adjuntos por correo electrónico para trabajar en distintas computadoras. Aquel método tradicional provocaba frecuentes pérdidas de información por extravío o daño de dispositivos, desfasaje entre versiones de un mismo documento y falta de disponibilidad fuera de la oficina.

La innovación fundamental de Dropbox consistió en integrar una carpeta local dentro del sistema de archivos nativo del sistema operativo que se sincroniza de manera transparente, silenciosa y en segundo plano con centros de datos en la nube. En la actualidad, Dropbox atiende a más de 700 millones de usuarios registrados y más de 575,000 equipos empresariales a nivel global, operando sobre clientes para Windows, Linux, macOS, Android, iOS, interfaz web e integraciones programáticas vía API REST.

## **2.2 Evolución Tecnológica de Dropbox: De Almacenamiento Básico a Ecosistema Cloud**

A lo largo de casi dos décadas de ingeniería, Dropbox atravesó cuatro etapas evolutivas que explican por qué hoy no debe analizarse como una herramienta aislada de almacenamiento, sino como un ecosistema completo de servicios en la nube:

1. **Etapa 1 \- Sincronización Diferencial y Almacenamiento en la Nube (2007–2014):** Consolidación del protocolo de sincronización por bloques (*Delta Sync*), recuperación de versiones previas y compartición segura mediante enlaces. En esta etapa inicial, Dropbox gestionaba internamente el catálogo de metadatos en sus propios servidores mientras delegaba el almacenamiento físico de bloques binarios a Amazon Simple Storage Service (AWS S3).
2. **Etapa 2 \- Infraestructura Propia Magic Pocket y Colaboración en Tiempo Real (2015–2018):** Con el fin de optimizar el rendimiento de red, reducir costos operativos y ejercer soberanía tecnológica sobre cientos de petabytes de datos, Dropbox diseñó y construyó su propia infraestructura de almacenamiento distribuido denominada **Magic Pocket**, conservando una integración híbrida con AWS para redundancia geográfica en determinadas regiones. En este mismo periodo lanzó **Dropbox Paper**, un entorno colaborativo de edición simultánea de documentos técnicos y gestión de proyectos.
3. **Etapa 3 \- Flujos Documentales Empresariales, Firma Legal y Resiliencia (2019–2022):** Expansión hacia la gobernanza empresarial y la continuidad del negocio mediante adquisiciones estratégicas y nuevos servicios:
   * **Dropbox Sign (adquisición de HelloSign en 2019):** Plataforma de firma electrónica legalmente vinculante bajo estándares internacionales (ESIGN, UETA y eIDAS) que incorpora una pista de auditoría criptográfica (*Audit Trail*).
   * **DocSend (adquirida en 2021):** Envío seguro de documentos corporativos con analítica de lectura en tiempo real y salas de datos virtuales.
   * **Dropbox Backup y Dropbox Rewind:** Soluciones especializadas para respaldar estaciones de trabajo completas y revertir masivamente carpetas o cuentas enteras a un punto temporal previo ante infecciones de *ransomware*.
   * **Dropbox Replay y Dropbox Transfer:** Herramientas para revisión colaborativa de video/audio y entrega de paquetes de archivos de hasta 100 GB.
4. **Etapa 4 \- Plataforma como Servicio (API v2 Scoped Access) e Inteligencia Artificial (2023–Actualidad):** Consolidación de **Dropbox Platform (API v2)** bajo permisos granulares y tokens de actualización continua, junto con el lanzamiento de **Dropbox Dash**, un buscador universal impulsado por inteligencia artificial que indexa y conecta contenidos de Dropbox con herramientas externas (Microsoft 365, Google Workspace, Slack, GitHub y Jira).

## **2.3 Fundamentos de Computación en la Nube (NIST) Aplicados al Proyecto**

Tomando como base la definición oficial del **Instituto Nacional de Estándares y Tecnología (NIST SP 800-145)** estudiada en el Capítulo 1 de la asignatura, la computación en la nube provee acceso ubicuo, conveniente y bajo demanda a un conjunto compartido de recursos informáticos configurables. El sistema **CBAS** y el ecosistema **Dropbox** materializan las cinco características esenciales del NIST de la siguiente manera:

* **Autoservicio bajo demanda (*On-demand self-service*):** La organización aprovisiona aplicaciones en Dropbox App Console, genera credenciales OAuth 2.0, habilita espacios de almacenamiento y ejecuta restauraciones desde el Panel Web de CBAS de forma inmediata y sin requerir la intervención manual de operadores del proveedor.
* **Acceso amplio a la red (*Broad network access*):** Los archivos respaldados por el agente local y los metadatos de auditoría se transmiten y consultan a través de la red utilizando protocolos estándar HTTPS/TLS 1.3 desde estaciones de trabajo Linux/Windows, navegadores web y dispositivos móviles.
* **Agrupación de recursos (*Resource pooling* y *Multi-tenancy*):** Dropbox emplea una arquitectura multi-inquilino sobre sus centros de datos donde múltiples empresas comparten dinámicamente la infraestructura física de discos y red, manteniendo el aislamiento lógico estricto de cada cuenta y carpeta de aplicación (*App Folder*) mediante cifrado y control de acceso.
* **Elasticidad rápida (*Rapid elasticity*):** A medida que la PYME incrementa su volumen de hojas contables, contratos y revisiones históricas, la plataforma escala transparentemente su capacidad de almacenamiento y tasa de transferencia sin que la empresa deba adquirir servidores ni discos físicos.
* **Servicio medido (*Measured service*):** Tanto Dropbox Platform como el Panel Web de CBAS supervisan y cuantifican en tiempo real el consumo de bytes por archivo, el número total de versiones almacenadas, las llamadas a los endpoints de la API y los eventos de auditoría registrados.

## **2.4 Principios Arquitectónicos en la Nube Aplicados en CBAS**

El diseño de **Cloud Backup and Audit System (CBAS)** introduce dos patrones de arquitectura en la nube de nivel industrial que superan el enfoque de un respaldo tradicional:

### **A. Desacoplamiento de Almacenamiento (*Storage Decoupling*)**

En una arquitectura monolítica convencional, el servidor de la aplicación recibe, procesa y guarda los archivos pesados dentro de su propio disco duro o base de datos, lo que encarece el hospedaje del servidor, satura el ancho de banda y crea un punto único de fallo.

CBAS aplica una separación estricta de responsabilidades:
1. **Plano de Datos Binarios (Dropbox Cloud API):** Los archivos reales de la PYME (tablas contables, bases de datos, documentos y configuraciones) viajan directamente desde la estación de trabajo hacia la nube de Dropbox. El servidor backend del proyecto **jamás almacena archivos binarios pesados**.
2. **Plano de Control y Metadatos (Servidor Backend y Base de Datos CBAS):** Nuestro servidor recibe y almacena únicamente *datos sobre los datos* (metadatos livianos de pocos bytes en formato JSON/SQL: nombre del archivo, identificador *rev* de Dropbox, hash criptográfico, usuario del sistema operativo, dirección IP y marca de tiempo UTC). Esto permite desplegar el backend en infraestructuras sumamente económicas o capas gratuitas en la nube con un rendimiento instantáneo.

### **B. Arquitectura Orientada a Eventos (*Event-Driven Architecture*)**

En lugar de depender de tareas programadas rígidas que se ejecutan una vez al día (dejando una ventana de pérdida de datos de hasta 24 horas), CBAS opera bajo un modelo reactivo dirigido por eventos del sistema operativo:
* El **Agente Local** suscribe un observador de bajo nivel (*inotify* en Linux / *ReadDirectoryChangesW* en Windows a través de la librería Python Watchdog) sobre el directorio crítico de la PYME.
* Cualquier creación o guardado de archivo dispara un evento asíncrono en milisegundos, activa un temporizador de estabilización (*debounce*) para esperar el cierre de escritura en disco, verifica la huella criptográfica del archivo y ejecuta la ingesta hacia la nube de forma completamente desatendida.

## **2.5 Modelos de Servicio (SaaS, PaaS, IaaS) y Modelo de Nube Híbrida**

Dentro de la pirámide de niveles de servicio en la nube (Capítulo 2 de la materia), el proyecto articula las tres capas de abstracción:

| Modelo Cloud | Nivel de Abstracción | Componentes en el Proyecto CBAS y Dropbox | Responsabilidad del Grupo 2 / Administrador TI |
| :--- | :--- | :--- | :--- |
| **SaaS** (*Software as a Service*) | Aplicaciones listas para el usuario final accesibles vía web o escritorio. | Interfaz Web de Dropbox, **Dropbox Paper**, **Dropbox Sign**, **Dropbox Dash**, Cliente de Escritorio y **Panel Web Admin de CBAS**. | Gestión de usuarios, revisión de líneas de tiempo de auditoría, restauración en un clic y firma de actas. |
| **PaaS** (*Platform as a Service* / API) | Entornos de ejecución, SDKs, APIs REST y motores de bases de datos para desarrollar software propio. | **Dropbox Platform (API v2)**, flujo **OAuth 2.0**, SDK oficial de Python, framework web **Flask** y motor relacional **SQLite**. | Codificación del Agente Local (agent.py), del Servidor Backend (backend.py), esquema de base de datos y control de tokens. |
| **IaaS** (*Infrastructure as a Service*) | Infraestructura física subyacente: servidores de bloques, redes de fibra y centros de datos. | **Dropbox Magic Pocket** y **AWS S3** (administrados internamente por Dropbox de forma transparente para el cliente). | Ninguna sobre los centros de datos en la nube; únicamente administración básica de la estación de trabajo local de la PYME. |

Asimismo, respecto a los **modelos de despliegue en la nube**, CBAS constituye un **Modelo de Nube Híbrida**:
* **Entorno Local (*On-Premises*):** La red interna y las estaciones de trabajo de la PYME donde los empleados crean y editan la información operativa, y donde reside el Agente Local de monitoreo.
* **Entorno de Nube Pública:** La infraestructura global de Dropbox (donde se resguardan los bloques cifrados y el árbol de revisiones) junto con los servicios SaaS de gobernanza documental.
* **Canal de Orquestación Híbrida:** La comunicación autenticada vía HTTPS/TLS 1.3 y API REST que sincroniza el estado entre el entorno local y la nube pública.

## **2.6 Arquitectura Interna de Dropbox: Magic Pocket, Delta Sync y Base Atlas**

Para fundamentar técnicamente por qué Dropbox es idóneo como motor de respaldo y control de versiones para PYMEs, se detallan sus tres pilares internos de ingeniería:

1. **Almacenamiento Distribuido Magic Pocket:** Infraestructura propietaria desarrollada en lenguajes Rust y Go sobre discos de grabación magnética superpuesta (SMR) con codificación de borrado (*erasure coding*) y replicación geográfica. Ofrece una durabilidad anual de objetos del **99.999999999% (11 nueves)**, una disponibilidad superior al **99.9%** y cifrado en reposo mediante el algoritmo **AES de 256 bits**.
2. **Sincronización Diferencial por Bloques (*Delta Sync*) y Algoritmo Content Hash:** A diferencia de servicios que retransmiten el archivo completo ante cualquier cambio menor, Dropbox divide cada archivo en bloques secuenciales de exactamente **4 MB ($4 \times 1024 \times 1024 = 4,194,304$ bytes)**:
   * A cada bloque de 4 MB se le calcula su resumen criptográfico **SHA-256** binario (32 bytes).
   * Los resúmenes binarios de todos los bloques se concatenan y se les aplica un segundo cálculo **SHA-256** para obtener el atributo hexadecimal de 64 caracteres denominado **content\_hash**.
   * Cuando un archivo grande se modifica, solo se transfieren los bloques de 4 MB cuyo hash cambió. Además, en nuestro sistema CBAS, el Agente Local implementa este mismo algoritmo de bloques de 4 MB para comparar el archivo en disco con la última versión sincronizada, evitando subidas redundantes y previniendo bucles infinitos durante las restauraciones.
3. **Separación de Metadatos en Atlas e Historial de Versiones Inmutable (*Version History*):** Dropbox separa el almacenamiento físico de bloques (Magic Pocket) de su base de datos transaccional distribuida de metadatos (**Atlas**). Cada vez que un archivo se actualiza mediante el modo de sobrescritura controlada, Atlas genera un puntero único e inmutable llamado **identificador de revisión (*rev*)**. Los bloques de las versiones anteriores no se eliminan ni consumen espacio adicional de la cuota contratada, permitiendo revertir cualquier archivo al instante durante la ventana de retención (30 días en cuentas Basic y de 180 días a 1 año en cuentas corporativas).

## **2.7 Gobierno de TI, Auditoría Forense y Gestión de Riesgos en la Nube (Capítulos 5 y 6\)**

El diseño de CBAS se alinea rigurosamente con los marcos internacionales de **Gobierno de TI y Seguridad en la Nube** abordados en los Capítulos 5 y 6 de la materia:

| Norma / Marco Internacional | Propósito en Gobierno y Seguridad TI | Implementación Concreta en el Sistema CBAS |
| :--- | :--- | :--- |
| **ISO/IEC 27001 (Anexo A.12.4 / Control 8.15 y 8.17)** | Registro de eventos (*Logging and Monitoring*), protección de registros de auditoría y sincronización de relojes. | La base de datos de CBAS registra en cada evento el usuario del sistema operativo, dirección IP, hostname, tipo de evento, tamaño, *rev* de Dropbox, *content\_hash* y marca de tiempo estandarizada en UTC. |
| **COBIT 2019 (Objetivos DSS05 y MEA01)** | Gestión de servicios de seguridad, continuidad operativa y monitoreo del cumplimiento de controles internos. | Trazabilidad completa del ciclo de vida del archivo desde su creación hasta su restauración ante incidentes, respaldada por el Panel Web de Auditoría. |
| **ISO/IEC 38500** | Gobierno corporativo de tecnologías de la información (Evaluar, Dirigir y Monitorear). | Generación automática del Acta de Conformidad y Auditoría Forense desde el Panel Web de CBAS y formalización mediante firma electrónica con validez legal en **Dropbox Sign**. |
| **ISO/IEC 27036 y CSA Guidance** | Seguridad en las relaciones con proveedores de servicios en la nube y Acuerdos de Nivel de Servicio (ANS/SLA). | Aplicación del modelo de responsabilidad compartida y uso de credenciales OAuth 2.0 confinadas mediante permisos mínimos (*Scoped Apps*). |

De igual forma, se presenta la **Matriz de Mitigación de Riesgos Cloud** implementada en el proyecto:

| Amenaza / Riesgo en la Nube (Capítulo 6\) | Impacto en la PYME | Mecanismo Técnico de Mitigación en CBAS |
| :--- | :--- | :--- |
| **Secuestro de Datos (*Ransomware*) o Borrado Accidental** | Paralización operativa de contabilidad/RRHH y pérdida financiera. | Historial inmutable de revisiones (*rev*) en Dropbox y módulo de **Viaje en el Tiempo** en el Panel Web para restaurar la versión limpia en un clic. |
| **Falta de Trazabilidad y Amenaza Interna (*Insider Threat*)** | Imposibilidad de identificar qué empleado o terminal alteró un balance o contrato. | Registro forense automático en el Backend CBAS capturando usuario del sistema operativo, IP privada, nombre de red del equipo y hora exacta UTC. |
| **Exposición o Robo de Credenciales de la Nube** | Compromiso total de la cuenta corporativa de almacenamiento. | Uso del estándar **OAuth 2.0 con Refresh Tokens** en archivo .env protegido y confinamiento de tipo **App Folder** (aislado en /Aplicaciones/CloudBackup-UMSA-G2). |
| **Interceptación de Datos en Tránsito o en Reposo** | Fuga de información financiera o salarial confidencial. | Transporte cifrado bajo **HTTPS/TLS 1.3**, almacenamiento en reposo con **AES-256** y verificación de integridad mediante hash SHA-256 por bloques de 4 MB. |
| **Repudio en Procesos de Auditoría de Sistemas** | Desconocimiento de responsabilidades tras la recuperación de un incidente. | Emisión de reporte forense con hashes criptográficos y firma digital vinculante con certificado *Audit Trail* en **Dropbox Sign**. |

---

# **3\. PROBLEMÁTICA Y OBJETIVOS**

## **3.1 Identificación del Problema Puntual**

En las Pequeñas y Medianas Empresas (PYMEs), los departamentos administrativos, contables y de recursos humanos almacenan y modifican diariamente archivos críticos del negocio (balances financieros, planillas de sueldos, configuraciones de sistemas ERP y contratos con proveedores) directamente en carpetas locales de sus estaciones de trabajo. Esta forma de operación expone a las PYMEs a dos problemas críticos: la **pérdida súbita de información** ante errores humanos de sobrescritura o ataques de *ransomware*, y la **ausencia total de trazabilidad (auditoría)** para determinar quién modificó un archivo, desde qué equipo y en qué fecha.

Al buscar soluciones, las PYMEs se encuentran con una barrera estructural: los sistemas de control de versiones como **Git** son demasiado complejos para personal no técnico, mientras que construir y administrar desde cero una infraestructura de almacenamiento seguro en **AWS S3 o Azure Blob Storage** implica costos financieros y conocimientos de ingeniería en la nube inaccesibles para una pequeña empresa.

## **3.2 Problemas Específicos**

1. **Dependencia de respaldos manuales:** Los empleados olvidan realizar copias de seguridad periódicas, dejando brechas críticas de tiempo donde cualquier fallo o edición errónea provoca la pérdida irreversible del trabajo reciente.
2. **Desperdicio de ancho de banda y riesgo de bucles de sincronización:** Los scripts básicos que reenvían archivos completos o carecen de verificación criptográfica por bloques saturan la conexión a internet de la oficina y pueden generar subidas repetitivas innecesarias.
3. **Carencia de auditoría centralizada de metadatos:** Las carpetas compartidas convencionales muestran únicamente el último archivo guardado, sin mantener una base de datos consultable que vincule cada versión con el usuario del sistema operativo, la dirección IP local y el terminal que originó el cambio.
4. **Complejidad en la recuperación ante desastres o *ransomware*:** Cuando un archivo crítico resulta corrompido o cifrado maliciosamente, el administrador carece de un panel visual unificado que le permita inspeccionar la línea de tiempo histórica, restaurar una versión íntegra en segundos y emitir un acta formal de auditoría.

## **3.3 Objetivos del Proyecto (Relación Directa Problema \- Objetivo)**

### **Objetivo General**

Desarrollar e implementar el sistema **Cloud Backup and Audit System (CBAS)** orientado a PYMEs, utilizando **Dropbox Cloud API v2** como infraestructura desacoplada de almacenamiento masivo y control de versiones nativo, articulado con un agente local en tiempo real y un panel web centralizado de auditoría y recuperación ante desastres.

### **Objetivos Específicos**

1. **Implementar un Agente Local automatizado en tiempo real** en Python (basado en la librería Watchdog) que monitoree continuamente los directorios críticos de la PYME y respalde cada creación o modificación sin intervención del usuario.
2. **Optimizar el uso del ancho de banda, almacenamiento y estabilidad del sistema** mediante la sincronización diferencial por bloques de 4 MB de Dropbox y la implementación local del algoritmo *content\_hash* (SHA-256) para evitar transferencias redundantes y bucles infinitos.
3. **Diseñar un Servidor Backend y una Base de Datos de Metadatos desacoplada** que registre la pista de auditoría forense de cada modificación (usuario del sistema operativo, dirección IP, nombre del equipo, fecha UTC, tamaño e identificador de revisión *rev*), cumpliendo con el control A.12.4 de la norma ISO/IEC 27001.
4. **Proveer un Panel Web de Administración con funcionalidad de "Viaje en el Tiempo"** que permita visualizar la línea de tiempo histórica de cada archivo, restaurar versiones íntegras en un solo clic ante ataques de *ransomware* e integrar la gobernanza documental con **Dropbox Paper** y **Dropbox Sign**.

---

# **4\. LISTA DE SERVICIOS DEL ECOSISTEMA DROPBOX Y SU DESCRIPCIÓN**

En cumplimiento de la directriz académica de abarcar el **conjunto integral de herramientas de la plataforma** y demostrar su articulación práctica, el proyecto emplea y documenta los siguientes servicios del ecosistema Dropbox:

| N° | Servicio del Ecosistema | Categoría Cloud | Descripción Técnica y Capacidades | Rol Específico en el Sistema CBAS |
| :--- | :--- | :--- | :--- | :--- |
| **1** | **Dropbox Core Storage** | SaaS / IaaS | Almacenamiento de objetos en la nube sobre arquitectura *Magic Pocket* con cifrado AES-256 en reposo, TLS 1.3 en tránsito y sincronización diferencial en bloques de 4 MB. | Bóveda central desacoplada (/CBAS\_Pyme\_Vault) donde residen físicamente los archivos binarios críticos de la PYME. |
| **2** | **Dropbox Platform (API v2 y SDK Python)** | PaaS | Plataforma para desarrolladores con endpoints HTTP REST, permisos granulares (*Scoped Access*), aislamiento por carpeta (*App Folder*) y flujo OAuth 2.0 con *Refresh Token*. | Motor programático consumido por el Agente Local y el Backend de CBAS para autenticar, subir archivos, listar revisiones y ejecutar restauraciones. |
| **3** | **Dropbox Version History y Rewind** | SaaS / PaaS | Motor transaccional inmutable que conserva cada estado histórico de un archivo bajo un código hexadecimal *rev* sin consumir cuota adicional del usuario. | Base del módulo de **Viaje en el Tiempo** de CBAS para revertir archivos corrompidos o secuestrados por *ransomware* a una versión limpia. |
| **4** | **Dropbox Desktop Client y Archivos Solo en Línea** | SaaS Híbrido | Aplicación de escritorio para Windows, macOS y Linux con función de *Archivos solo en línea* (evolución de *Smart Sync*), que muestra archivos de la nube sin ocupar disco local hasta abrirlos. | Verificación multiplataforma de la bóveda de respaldos sin saturar el almacenamiento físico de las computadoras de la empresa. |
| **5** | **Dropbox Backup** | SaaS | Servicio nativo de copia de seguridad continua para carpetas del sistema operativo (Escritorio, Documentos, Descargas) y unidades externas. | Punto de referencia técnico en el marco teórico frente a la arquitectura desacoplada con auditoría personalizada construida en CBAS. |
| **6** | **Dropbox Paper** | SaaS Colaborativo | Espacio de trabajo documental colaborativo en tiempo real con soporte para Markdown, tablas, bloques de código con sintaxis resaltada y listas de tareas con responsables. | Alojamiento de la Bitácora de Ingeniería del Grupo 2 y del Manual de Procedimientos Operativos Estándar (SOP) ante incidentes. |
| **7** | **Dropbox Sign (antes HelloSign)** | SaaS (LegalTech) | Plataforma de firma electrónica legalmente vinculante que adjunta automáticamente un certificado de pista de auditoría (*Audit Trail*) con IP, fecha UTC y hash del documento. | Formalización del Gobierno TI: suscripción digital del **Acta de Conformidad y Auditoría Forense** generada directamente desde el Panel Web de CBAS. |
| **8** | **Dropbox Dash, DocSend, Replay y Transfer** | SaaS + IA | Buscador universal con inteligencia artificial (Dash), control analítico de documentos compartidos (DocSend), revisión multimedia (Replay) y entrega de hasta 100 GB (Transfer). | Indexación inteligente y localización rápida de actas de auditoría, manuales y respaldos históricos dentro del ecosistema corporativo. |

---

# **II. SEGUNDA PARTE: DESARROLLO PRÁCTICO DE CADA APLICACIÓN Y SERVICIO (70%)**

# **1\. ARQUITECTURA DESACOPLADA DEL SISTEMA CBAS**

El producto desarrollado (**Cloud Backup and Audit System \- CBAS v2.0**) se estructura en tres capas independientes pero estrechamente coordinadas que demuestran el principio de **Desacoplamiento de Almacenamiento (*Storage Decoupling*)**:

1. **Capa de Cliente \- Agente Local en Estación PYME (cbas/agent.py y cbas/hasher.py):** Un servicio liviano en Python que corre en segundo plano vigilando el directorio de trabajo de la empresa (directorio\_pyme/). Actúa como puente reactivo de ingesta: detecta cambios del sistema operativo, calcula el hash criptográfico por bloques de 4 MB, sube el archivo binario a Dropbox y envía el reporte de metadatos al backend.
2. **Capa de Almacenamiento Masivo y Versionado \- Dropbox Cloud API (cbas/dropbox\_service.py):** Recibe y resguarda los archivos binarios reales dentro del contenedor aislado /Aplicaciones/CloudBackup-UMSA-G2/CBAS\_Pyme\_Vault. Gestiona la deduplicación por bloques, el cifrado AES-256 y la generación de identificadores únicos de versión (*rev*).
3. **Capa de Lógica, Metadatos y Panel Web (cbas/backend.py, cbas/database.py y dashboard.html):** Una API REST desarrollada en Flask junto a una base de datos SQLite (cbas\_auditoria.db) que registra las versiones creadas por guardado, calcula diferencias línea por línea y sirve el Panel Web organizado en pestañas.

```mermaid
flowchart TB
    subgraph EstacionPYME["1. CAPA DE CLIENTE (Estación de Trabajo PYME)"]
        Carpeta["Directorio Corporativo Asociado\n(directorio_pyme/)"]
        Agente["Agente Local CBAS (cbas/agent.py)\nWatchdog + Debounce 1s + Hasher 4 MB"]
        Carpeta -->|"Guardado de archivo\n(Creación / Modificación)"| Agente
    end

    subgraph NubeDropbox["2. CAPA DE ALMACENAMIENTO Y VERSIONADO (Dropbox Cloud PaaS/SaaS)"]
        Core["Dropbox Core Storage\n(Magic Pocket AES-256 / Delta Sync)"]
        Revs["Dropbox Version History\n(Árbol de códigos rev)"]
        Gobernanza["Gobernanza SaaS\n(Dropbox Paper y Dropbox Sign)"]
        Core --> Revs
    end

    subgraph ServidorCBAS["3. CAPA DE LÓGICA, TELEMETRÍA Y ADMINISTRACIÓN (Servidor Backend CBAS)"]
        API["Servidor Backend REST API\n(cbas/backend.py - Flask)"]
        BD[("Base de Datos de Versiones y Auditoría\n(SQLite: cbas_auditoria.db)")]
        Web["Consola Web Empresarial Open Enterprise\n(cbas/templates/dashboard.html)"]
        API --> BD
        Web <-->|"Consulta Ficha Técnica y Métricas /\nOrdena Descarga o Restauración"| API
    end

    Agente -->|"Paso A1: Sube archivo por bloques\n(/files/upload WriteMode.overwrite)"| Core
    Core -->|"Paso A2: Retorna ID de versión (rev)\ny content_hash SHA-256"| Agente
    Agente -->|"Paso A3: Registra versión y telemetría de red\n(Usuario SO, IP, Equipo, rev, Hash, Fecha UTC)"| API
    API -->|"Paso B1: Descarga directa (/files/download)\no Restauración (/files/restore)"| Revs
    Revs -->|"Paso B2: Restablece archivo en estación de trabajo\nsin bucle infinito"| Carpeta
    API -.->|"Paso B3: Registro de auditoría y gobernanza"| Gobernanza
```

---

# **2\. FLUJOS DE TRABAJO DEL SISTEMA (WORKFLOWS)**

## **2.1 Flujo de Trabajo A: Respaldo por Guardado y Telemetría en Tiempo Real**

Este flujo se ejecuta de forma automática cada vez que un usuario de la PYME guarda un archivo nuevo o modificado dentro de la carpeta asociada (directorio\_pyme):

1. **Guardado en la Carpeta Asociada:** Un usuario edita y guarda un archivo en directorio\_pyme (hojas de cálculo, documentos Word, balances CSV, reportes PDF o configuraciones JSON).
2. **Detección por Eventos y Estabilización (*Debouncing*):** El Agente Local ([agent.py](file:///home/carloos-odann/PROYECTOS/UNI-VERSALIDAD/COM-NUBE/proyecto-dropbox/cbas/agent.py)) detecta la señal del sistema operativo mediante Watchdog, ignora archivos temporales de edición y espera 1.0 segundo de inactividad para asegurar que el archivo haya terminado de escribirse en disco.
3. **Verificación Criptográfica por Bloques de 4 MB:** El módulo [hasher.py](file:///home/carloos-odann/PROYECTOS/UNI-VERSALIDAD/COM-NUBE/proyecto-dropbox/cbas/hasher.py) divide el archivo en bloques de 4 MB y calcula localmente el *content\_hash* SHA-256 idéntico al de Dropbox. Si el hash coincide con la última versión registrada (por ejemplo, si se presionó guardar sin modificar datos), no se duplican versiones; si el hash cambió, se procede con el respaldo.
4. **Subida con Versionado a Dropbox Core Storage:** El agente transmite el archivo hacia el endpoint /files/upload de Dropbox API v2 utilizando WriteMode.overwrite. Dropbox almacena la nueva revisión y devuelve un objeto FileMetadata con el identificador único de versión (**rev**), la marca temporal del servidor (**server\_modified**) y el **content\_hash** verificado.
5. **Registro de Metadatos y Auditoría en el Backend:** El backend registra la nueva versión correlativa (v1, v2, v3...) en la base de datos SQLite ([database.py](file:///home/carloos-odann/PROYECTOS/UNI-VERSALIDAD/COM-NUBE/proyecto-dropbox/cbas/database.py)) junto con el usuario del sistema operativo, dirección IP y equipo, consolidando la trazabilidad de red.

```mermaid
sequenceDiagram
    autonumber
    participant Empleado as Usuario PYME (Disco Local)
    participant Agente as Agente Local CBAS (Watchdog)
    participant Dropbox as Dropbox Cloud API v2
    participant Backend as Backend CBAS y BD SQLite

    Empleado->>Agente: Guarda documento en directorio_pyme/
    Agente->>Agente: Filtra temporales + Debounce (1.0 s) + Calcula Hash 4 MB
    Agente->>Dropbox: files_upload(ruta, WriteMode.overwrite) con OAuth 2.0
    Dropbox-->>Agente: Retorna FileMetadata (rev, content_hash, server_modified)
    Agente->>Backend: Registra nueva versión, tamaño, IP local y usuario SO
    Backend-->>Agente: Actualiza catálogo de custodia y registro de auditoría
```

## **2.2 Flujo de Trabajo B: Consulta de Ficha Técnica, Descarga Directa y Restauración**

Cuando un administrador necesita auditar un documento, obtener una copia de una versión histórica o recuperar un archivo ante un error humano o corrupción local, utiliza la consola web de CBAS:

1. **Selección Instantánea de Archivo y Versión:** En la sección **Bóveda y Versiones** de la consola web (http://127.0.0.1:5050), el usuario selecciona cualquier documento y hace clic sobre cualquiera de sus tarjetas de versión histórica (v1, v2, v3...).
2. **Inspección de la Ficha Técnica de Nube:** La consola despliega de inmediato la ficha con el tipo de documento, tamaño, fecha de registro UTC, usuario de origen, IP de la estación, código *rev* de Dropbox y firma criptográfica SHA-256.
3. **Opción 1 \- Descarga Directa al Navegador (Sin Alterar Estación de Trabajo):** Si el usuario solo desea obtener una copia de consulta o verificación de esa versión histórica, presiona el botón **Descargar copia de esta versión**. El servidor solicita el archivo a Dropbox mediante files\_download(ruta\_nube, rev=rev) y lo entrega al navegador.
4. **Opción 2 \- Restauración en la Estación de Trabajo:** Si se desea restablecer el documento de trabajo en la computadora de la empresa, el usuario presiona **Restaurar en estación de trabajo**. El backend ejecuta files\_restore(path, rev) en Dropbox y descarga el contenido limpio a directorio\_pyme.
5. **Prevención de Bucle Infinito y Registro de Restauración:** Antes de escribir el archivo en disco, el backend registra el *content\_hash* recuperado en el Agente Local para que no lo vuelva a subir, y anota el evento RESTAURADO en la base de datos de auditoría.

```mermaid
sequenceDiagram
    autonumber
    participant Admin as Administrador TI (Consola Web)
    participant Backend as Servidor Backend CBAS
    participant Dropbox as Dropbox API v2 (Version History)
    participant Disco as Estación de Trabajo (directorio_pyme)

    Admin->>Backend: Selecciona documento y hace clic en versión histórica
    Backend-->>Admin: Despliega Ficha Técnica (rev, SHA-256, IP, Usuario, Tamaño)
    alt Opción 1: Descargar copia histórica
        Admin->>Backend: Clic en "Descargar copia de esta versión"
        Backend->>Dropbox: files_download(ruta_nube, rev=rev)
        Dropbox-->>Admin: Descarga directa al navegador
    else Opción 2: Restaurar en la estación de trabajo
        Admin->>Backend: Clic en "Restaurar en estación de trabajo"
        Backend->>Dropbox: files_restore(ruta, rev) + files_download_to_file
        Dropbox-->>Disco: Restablece el documento en directorio_pyme/
        Backend->>Backend: Actualiza hash anti-bucle y registra auditoría
        Backend-->>Admin: Confirma restauración exitosa
    end
```

---

# **3\. ESTRUCTURA DEL PROYECTO E IMPLEMENTACIÓN POR SERVICIO DEL ECOSISTEMA**

## **3.1 Organización Modular del Código Fuente**

Se estructuró el proyecto bajo una arquitectura limpia de paquetes en Python, documentada con su archivo [README.md](file:///home/carloos-odann/PROYECTOS/UNI-VERSALIDAD/COM-NUBE/proyecto-dropbox/README.md) y su guía operativa en [guia\_instalacion\_y\_uso.md](file:///home/carloos-odann/PROYECTOS/UNI-VERSALIDAD/COM-NUBE/proyecto-dropbox/docs/guia_instalacion_y_uso.md):

```text
COM-NUBE/proyecto-dropbox/
├── .env                              # Credenciales OAuth 2.0 reales (App Key, Secret y Refresh Token)
├── .env.example                      # Plantilla de configuración de variables de entorno
├── README.md                         # Documentación general del repositorio CBAS
├── Proyecto-CC.md                    # Informe académico integral del proyecto
├── requirements.txt                  # Dependencias: dropbox, python-dotenv, watchdog, flask, requests
├── run_cbas.py                       # Lanzador unificado (Agente Local Watchdog + Servidor Backend Web)
├── cbas/                             # Paquete principal del sistema CBAS
│   ├── __init__.py
│   ├── config.py                     # Configuración centralizada y detección de red/usuario SO
│   ├── hasher.py                     # Algoritmo oficial Dropbox content_hash (bloques de 4 MB SHA-256)
│   ├── database.py                   # Persistencia relacional SQLite (cbas_auditoria.db) y telemetría
│   ├── dropbox_service.py            # Cliente Dropbox API v2 (upload, download por rev, restore)
│   ├── agent.py                      # Agente Watchdog en tiempo real con debounce de 1s y anti-bucle
│   ├── backend.py                    # API REST Flask de versiones, telemetría y descarga/restauración
│   └── templates/
│       └── dashboard.html            # Consola Web corporativa bajo diseño Open Enterprise Tech
├── scripts/
│   └── setup_oauth.py                # Asistente interactivo de vinculación OAuth 2.0 (Offline Access)
├── directorio_pyme/                  # Carpeta asociada monitoreada en tiempo real (texto y binarios)
│   ├── Balance_Contable_2026.csv
│   ├── Planilla_Sueldos_RRHH.csv
│   ├── Configuracion_ERP_Pyme.json
│   └── Contratos_Proveedores_2026.md
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

## **3.2 Servicio 1 y 2: Dropbox Platform (API v2 OAuth 2.0) y Dropbox Core Storage**

Aplicando el **principio de privilegio mínimo**, se registró en el portal oficial Dropbox Developers la aplicación **CloudBackup-UMSA-G2 (App ID: 8806881)** bajo modalidad *Scoped Access* y confinamiento *App Folder*, habilitando exclusivamente los permisos account\_info.read, files.metadata.read, files.content.read y files.content.write.

El módulo [dropbox\_service.py](file:///home/carloos-odann/PROYECTOS/UNI-VERSALIDAD/COM-NUBE/proyecto-dropbox/cbas/dropbox_service.py) encapsula la comunicación con **Dropbox Core Storage** y **Dropbox Version History** utilizando el *Refresh Token* permanente para subir nuevas versiones, descargar cualquier revisión histórica específica por su código *rev* o restaurarla en la carpeta local:

```python
def descargar_bytes_version(nombre_archivo: str, rev: str | None = None) -> tuple[bytes, dict]:
    """
    Descarga desde Dropbox el contenido binario exacto de una version especifica (rev)
    sin modificar ni sobrescribir el archivo en la carpeta local monitoreada.
    """
    ruta_nube = construir_ruta_dropbox(nombre_archivo)
    dbx = obtener_cliente_dropbox()

    if rev:
        metadata, response = dbx.files_download(ruta_nube, rev=rev)
    else:
        metadata, response = dbx.files_download(ruta_nube)

    contenido = response.content
    return contenido, {
        "nombre_archivo": metadata.name,
        "rev": metadata.rev,
        "tamano_bytes": metadata.size,
        "content_hash": metadata.content_hash,
    }
```

## **3.3 Servicio 3: Verificación por Bloques de 4 MB y Agente en Tiempo Real (Watchdog)**

El módulo [hasher.py](file:///home/carloos-odann/PROYECTOS/UNI-VERSALIDAD/COM-NUBE/proyecto-dropbox/cbas/hasher.py) implementa la especificación criptográfica exacta de Dropbox (bloques de 4 MB con SHA-256), utilizada por el Agente Local ([agent.py](file:///home/carloos-odann/PROYECTOS/UNI-VERSALIDAD/COM-NUBE/proyecto-dropbox/cbas/agent.py)) para comprobar si el contenido de un archivo guardado realmente cambió y evitar bucles infinitos al restaurar versiones:

```python
DROPBOX_BLOCK_SIZE = 4 * 1024 * 1024  # 4 MB exactos (4,194,304 bytes)

def calcular_content_hash_dropbox(ruta_archivo: str | Path) -> str:
    hashes_bloques = bytearray()
    with open(ruta_archivo, "rb") as archivo:
        while True:
            bloque = archivo.read(DROPBOX_BLOCK_SIZE)
            if not bloque:
                break
            hashes_bloques.extend(hashlib.sha256(bloque).digest())
    return hashlib.sha256(hashes_bloques).hexdigest()
```

## **3.4 Servicio 4: Dropbox Version History, Telemetría y Restauración Local**

Cuando el usuario selecciona un archivo en la Consola Web ([dashboard.html](file:///home/carloos-odann/PROYECTOS/UNI-VERSALIDAD/COM-NUBE/proyecto-dropbox/cbas/templates/dashboard.html)), el backend recupera la telemetría de auditoría almacenada en SQLite y el servicio [dropbox\_service.py](file:///home/carloos-odann/PROYECTOS/UNI-VERSALIDAD/COM-NUBE/proyecto-dropbox/cbas/dropbox_service.py) permite descargar o restaurar cualquier código *rev* en la estación de trabajo:

```python
def restaurar_version_en_carpeta(nombre_archivo: str, rev_objetivo: str) -> dict:
    ruta_nube = construir_ruta_dropbox(nombre_archivo)
    ruta_local_destino = MONITORED_DIR / nombre_archivo
    dbx = obtener_cliente_dropbox()

    # 1. Reversion transaccional en Dropbox Version History
    restaurado_meta = dbx.files_restore(ruta_nube, rev_objetivo)

    # 2. Descarga inmediata de la version seleccionada hacia la carpeta local asociada
    MONITORED_DIR.mkdir(parents=True, exist_ok=True)
    dbx.files_download_to_file(str(ruta_local_destino), ruta_nube)

    return {
        "nombre_archivo": nombre_archivo,
        "rev_solicitada": rev_objetivo,
        "nueva_rev_activa": restaurado_meta.rev,
        "content_hash": restaurado_meta.content_hash,
        "tamano_bytes": restaurado_meta.size,
    }
```

## **3.5 Servicios 5, 6 y 7: Gobernanza Documental con Dropbox Paper, Dropbox Sign y Dash**

Para complementar la gestión documental del proyecto dentro del ecosistema Dropbox:
* **Dropbox Paper:** Se elaboró la Bitácora Operativa y Procedimiento Estándar de Recuperación del Grupo 2 ([plantilla\_dropbox\_paper.md](file:///home/carloos-odann/PROYECTOS/UNI-VERSALIDAD/COM-NUBE/proyecto-dropbox/docs/plantilla_dropbox_paper.md)), documentando los roles del equipo y el flujo de respaldo y restauración.
* **Dropbox Sign:** A partir de la tabla de actividad del sistema (que registra cada versión, usuario del sistema operativo, dirección IP, código *rev* y hash SHA-256), se estructura el acta de conformidad técnica ([acta\_conformidad\_dropbox\_sign.md](file:///home/carloos-odann/PROYECTOS/UNI-VERSALIDAD/COM-NUBE/proyecto-dropbox/docs/acta_conformidad_dropbox_sign.md)) para su firma electrónica con validez de auditoría.
* **Dropbox Desktop Client y Dropbox Dash:** Permiten consultar los archivos sincronizados bajo modalidad *Archivos solo en línea* y localizar rápidamente versiones o reportes mediante búsqueda unificada.

---

# **4\. DEMOSTRACIÓN DEL PRODUCTO ENTREGABLE Y EVIDENCIAS REALES (100%)**

## **4.1 Trazas Reales de Ejecución y Verificación contra Dropbox Cloud API v2**

A continuación se presenta la salida real de consola al ejecutar el sistema CBAS conectado con la cuenta activa de Dropbox del Grupo 2, mostrando la indexación de los archivos reales presentes en la carpeta asociada (tanto archivos de texto como documentos binarios PDF y Word), la detección de cambios al guardar modificaciones, la descarga directa de una versión histórica y la restauración en la carpeta local:

```text
========================================================================
  CLOUD BACKUP & AUDIT SYSTEM (CBAS) - DROPBOX PLATFORM
  Universidad Mayor de San Andres | Computacion en la Nube - Grupo 2
========================================================================
  Cuenta Dropbox : Dan Y El o Carlos Chambi (dannyperseverante70v7@gmail.com)
  Carpeta local  : /home/carloos-odann/PROYECTOS/UNI-VERSALIDAD/COM-NUBE/proyecto-dropbox/directorio_pyme
  Panel Web      : http://127.0.0.1:5050
========================================================================

1. Sincronizacion inicial de archivos reales en directorio_pyme/:
   - Balance_Contable_2026.csv     -> v1 (CREADO: Respaldo inicial | rev: 0165ec03f1088500000000332488fd1)
   - Configuracion_ERP_Pyme.json   -> v1 (CREADO: Respaldo inicial | rev: 0165ec03f88fc830000000332488fd1)
   - Contratos_Proveedores_2026.md -> v1 (CREADO: Respaldo inicial | rev: 0165ec03fa52abd0000000332488fd1)
   - Planilla_Sueldos_RRHH.csv     -> v1 (CREADO: Respaldo inicial | rev: 0165ec03fc6da550000000332488fd1)
   - Computacion en la Nube.docx   -> v1 (CREADO: Documento Word 1.03 MB)
   - Computacion en la Nube.pdf    -> v1 (CREADO: Documento PDF 1.21 MB)
   - RBenPagos-1.pdf               -> v1 (CREADO: Documento PDF 10.5 KB)

2. Guardado de modificacion contable en Balance_Contable_2026.csv:
   [CBAS Agent] Balance_Contable_2026.csv -> v2 (MODIFICADO: 614 bytes | rev: 0165ec03ff550000000000332488fd1)

3. Guardado con alteracion de parametros en Configuracion_ERP_Pyme.json:
   [CBAS Agent] Configuracion_ERP_Pyme.json -> v2 (MODIFICADO: 89 bytes | rev: 0165ec0401043400000000332488fd1)

4. Descarga directa de la Version v1 desde Dropbox sin sobrescribir carpeta local:
   GET /api/files/Configuracion_ERP_Pyme.json/versions/0165ec03f88fc830000000332488fd1/download -> HTTP 200 (232 bytes)

5. Restauracion de la Version v1 en la carpeta local (/api/restore):
   POST /api/restore -> Version v3 creada (RESTAURADO: 232 bytes | rev: 0165ec0404ef7390000000332488fd1)
```

## **4.2 Evidencias Visuales del Producto Entregable (Consola Web CBAS Open Enterprise)**

A continuación se presentan las capturas reales de la consola web de **CBAS**, diseñada bajo los lineamientos visuales de **Open Enterprise Tech** (fondos limpios #FBF9F9, tipografía IBM Plex Sans e IBM Plex Mono, acentos en rojo #EE0000 y navegación estructurada por secciones):

### **Figura 1: Consola Principal CBAS \- Bóveda de Documentos y Ficha Técnica de Versiones**

En la siguiente captura se observa la consola corporativa conectada a Dropbox Cloud API. En la parte superior se exhiben las métricas globales de almacenamiento (4.72 MB en custodia, 8 archivos y 11 versiones). En la columna izquierda se disponen las secciones de navegación y la tarjeta del principio *Storage Decoupling*. En el panel central se lista el inventario de documentos con sus etiquetas de formato (CSV, Word, PDF, JSON), la línea de tiempo de versiones y la ficha técnica del archivo contable Balance\_Contable\_2026.csv (Versión v2 en disco local):

![Consola Principal CBAS Open Enterprise](docs/capturas/cbas_dashboard_general.png)

### **Figura 2: Inspección de Versión Histórica y Telemetría de Origen en Configuracion\_ERP\_Pyme.json**

Al seleccionar el archivo Configuracion\_ERP\_Pyme.json y pulsar sobre la tarjeta **Versión v2**, la consola despliega la ficha técnica de esa versión histórica en la nube: código *rev* 0165ec04010434..., hash criptográfico SHA-256 de bloques, dirección IP de la estación (192.168.21.78) y usuario carloos-odann. Desde esta vista el administrador dispone de los botones para **Descargar copia de esta versión** o **Restaurar v2 en estación local**:

![Inspección de Versión Histórica y Telemetría](docs/capturas/cbas_alerta_ransomware.png)

### **Figura 3: Restauración Completada en la Estación de Trabajo (Versión v3 Recuperada desde v1)**

Tras ordenar la recuperación de la **Versión v1** del archivo Configuracion\_ERP\_Pyme.json mediante el endpoint /api/restore, Dropbox revierte transaccionalmente el archivo y el sistema genera la **Versión v3 (RESTAURADO)**. El visor confirma que los parámetros corporativos originales de la empresa han sido restablecidos en disco local con su nueva firma criptográfica de bloques y sin producir bucles de sincronización:

![Restauración Exitosa de Documento en Estación Local](docs/capturas/cbas_restauracion_exitosa.png)

### **Figura 4: Pista de Auditoría de Red y Cumplimiento Normativo (ISO/IEC 27001 A.12.4 & COBIT)**

En la sección **Registro de Auditoría** se visualiza la tabla cronológica con todos los eventos capturados en la red (CREADO, MODIFICADO y RESTAURADO), detallando fecha y hora UTC, documento, número de versión, tipo de operación, usuario del sistema operativo (carloos-odann), dirección IP local (192.168.21.78), código de revisión *rev* de Dropbox y botón directo para examinar la ficha técnica de cada versión:

![Pista de Auditoría y Telemetría de Red](docs/capturas/cbas_acta_auditoria_sign.png)

---

# **5\. CONCLUSIONES Y VIABILIDAD**

1. **Demostración del Potencial de Dropbox como Plataforma Cloud (PaaS):** Se comprobó en la práctica que Dropbox trasciende el almacenamiento manual de archivos, proveyendo mediante su API v2 un motor transaccional de versionado por identificadores *rev* y sincronización diferencial por bloques de 4 MB capaz de respaldar aplicaciones empresariales de auditoría y continuidad de negocio.
2. **Eficiencia de la Arquitectura Desacoplada (*Storage Decoupling*):** Al delegar el almacenamiento de archivos binarios y documentos a Dropbox Core Storage y conservar en el servidor local únicamente la telemetría de red y firmas criptográficas (SQLite), CBAS ofrece respuestas instantáneas al explorar versiones sin sobrecargar el servidor de la empresa.
3. **Continuidad del Negocio y Cumplimiento de Gobierno TI (Capítulos 5 y 6\):** La captura automática del usuario del sistema operativo, dirección IP, nombre del equipo, código *rev* y *content\_hash* SHA-256 cumple los controles de trazabilidad de ISO/IEC 27001 (A.12.4) y COBIT, brindando a usuarios no técnicos una consola corporativa clara donde cualquier documento puede descargarse o restaurarse en su estación de trabajo en cuestión de segundos.

[image1]: <data:image/png;base64,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>
