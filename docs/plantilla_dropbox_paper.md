# Bitacora de Ingenieria y Manual Operativo: Sistema CBAS (Grupo 2)

Documento estructurado para uso colaborativo en **Dropbox Paper** (https://paper.dropbox.com).

---

## 1. Ficha Tecnica del Proyecto

- **Universidad:** Universidad Mayor de San Andres (UMSA) - Carrera de Informatica
- **Materia:** Computacion en la Nube
- **Docente:** Ph.D. Jose Maria Tapia Baltazar
- **Sistema:** Cloud Backup and Audit System (CBAS v2.0)
- **Repositorio en Dropbox Core Storage:** /Aplicaciones/CloudBackup-UMSA-G2/CBAS_Pyme_Vault

---

## 2. Resumen de Arquitectura Desacoplada

El sistema CBAS separa el almacenamiento de objetos binarios del registro de auditoria:

| Componente | Tecnologia Utilizada | Funcion en el Sistema |
| :--- | :--- | :--- |
| **Agente Local PYME** | Python 3 + Watchdog + Hasher 4 MB | Monitorea en tiempo real la carpeta directorio_pyme, evita bucles infinitos mediante content_hash y sube cambios a Dropbox. |
| **Motor Cloud (IaaS/PaaS)** | Dropbox Core Storage + Version History | Almacena bloques cifrados con AES-256 en Magic Pocket y mantiene el arbol inmutable de revisiones (rev). |
| **Backend y Auditoria** | Flask REST API + SQLite | Registra metadatos forenses (usuario SO, IP, equipo, rev, content_hash y fecha UTC) conforme a ISO/IEC 27001 A.12.4. |
| **Panel Web Admin** | HTML5 + TailwindCSS + JS | Permite auditar quien modifico cada archivo y ejecutar el Viaje en el Tiempo (restauracion en un clic). |

---

## 3. Asignacion de Responsabilidades del Grupo N° 2

- [x] **Saul Mijael Choquehuanca Huanca:** Configuracion de Dropbox App Console, permisos Scoped Access y flujo OAuth 2.0 con Refresh Token.
- [x] **Carlos Daniel Quispe Chambi:** Desarrollo del Agente Local en tiempo real con Watchdog, calculo de content_hash de 4 MB y servicio Dropbox API v2.
- [x] **Victor Bernardo Quispe Rojas:** Desarrollo del Backend de Auditoria Desacoplada (SQLite + API REST) y Panel Web de Viaje en el Tiempo.
- [x] **Gabriel Yujra Machaca:** Pruebas de recuperacion ante incidentes (Ransomware), documentacion en Dropbox Paper y flujo de firma legal en Dropbox Sign.

---

## 4. Procedimiento Estandar de Recuperacion ante Incidentes (SOP)

1. Cuando el Panel Web de CBAS reporta un archivo en estado **ALERTA_CORRUPCION**, el Administrador de TI selecciona el archivo afectado en el catalogo principal.
2. En el panel derecho (**Viaje en el Tiempo**), verifica el usuario del sistema operativo, la direccion IP y el identificador rev de la version corrupta frente a la version inmediata anterior marcada como **INTEGRA**.
3. Presiona el boton **Restaurar esta Version**, disparando la llamada autenticada a files_restore y files_download_to_file.
4. Genera el Acta de Auditoria desde el boton superior del panel y la remite mediante **Dropbox Sign** para su firma electronica con pista de auditoria legal.
