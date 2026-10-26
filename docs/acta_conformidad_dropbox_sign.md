# ACTA DE AUDITORIA DE RESPALDO Y CONTROL DE VERSIONES EN LA NUBE (CBAS)

## 1. Datos Institucionales y de Gobernanza TI
- **Universidad:** Universidad Mayor de San Andres (UMSA) - Carrera de Informatica
- **Asignatura:** Computacion en la Nube (Docente: Ph.D. Jose Maria Tapia Baltazar)
- **Sistema Evaluado:** Cloud Backup and Audit System (CBAS v2.0) - Grupo N° 2
- **Fecha de Emision del Reporte (UTC):** 2026-10-26 15:11:49 UTC
- **Estacion de Trabajo Auditada:** carloos-odann (IP: 192.168.21.78 | Usuario: carloos-odann)
- **Marcos de Cumplimiento:** ISO/IEC 27001 (Control A.12.4 Logging and Monitoring), ISO/IEC 38500 y COBIT 2019 (DSS05 / MEA01)

## 2. Resumen Ejecutivo de Estado en Dropbox Cloud API
- **Total de Activos PYME Protegidos:** 4
- **Total de Eventos de Versionado Registrados:** 11
- **Total de Restauraciones Exitosas (Viaje en el Tiempo):** 1
- **Archivos con Alerta Pendiente:** 0

## 3. Inventario de Archivos Monitoreados y Revision Activa en Dropbox

| Archivo PYME | Ruta Dropbox | Revision Activa (rev) | Content Hash (SHA-256 4MB) | Estado | Ultimo Editor |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Balance_Contable_2026.csv | /CBAS_Pyme_Vault/Balance_Contable_2026.csv | 0165ebfac881f970000000332488fd1 | 9a60ff8824af645f8ff5... | INTEGRO | carloos-odann (192.168.21.78) |
| Configuracion_ERP_Pyme.json | /CBAS_Pyme_Vault/Configuracion_ERP_Pyme.json | 0165ebe65e172e70000000332488fd1 | fb96aef53b8422bde0c9... | INTEGRO | carloos-odann (192.168.21.78) |
| Contratos_Proveedores_2026.md | /CBAS_Pyme_Vault/Contratos_Proveedores_2026.md | 0165ebfbdd000f70000000332488fd1 | 8d8932e62fd8af1c4595... | INTEGRO | carloos-odann (192.168.21.78) |
| Planilla_Sueldos_RRHH.csv | /CBAS_Pyme_Vault/Planilla_Sueldos_RRHH.csv | 0165ebe651e32910000000332488fd1 | 2fbc3d1686d29d4b6346... | INTEGRO | carloos-odann (192.168.21.78) |

## 4. Pista de Auditoria Reciente (Ultimos Eventos Registrados)

| ID | Fecha UTC | Archivo | Evento | Revision (rev) | Usuario / IP | Detalle |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| #11 | 2026-10-26 15:11:17 UTC | Contratos_Proveedores_2026.md | MODIFICACION_ARCHIVO | 0165ebfbdd000f70000000332488fd1 | carloos-odann (192.168.21.78) | Actualizacion detectada en tiempo real por Agente Watchdog sobre Contratos_Proveedores_2026.md (sincronizacion diferencial por bloques). |
| #10 | 2026-10-26 15:11:16 UTC | Contratos_Proveedores_2026.md | MODIFICACION_ARCHIVO | 0165ebfbdd000f70000000332488fd1 | contador_vquispe (192.168.21.78) | Modificacion operativa legitima realizada por contador_vquispe sobre Contratos_Proveedores_2026.md. |
| #9 | 2026-10-26 15:06:27 UTC | Balance_Contable_2026.csv | MODIFICACION_ARCHIVO | 0165ebfac881f970000000332488fd1 | carloos-odann (192.168.21.78) | Actualizacion detectada en tiempo real por Agente Watchdog sobre Balance_Contable_2026.csv (sincronizacion diferencial por bloques). |
| #8 | 2026-10-26 15:06:26 UTC | Balance_Contable_2026.csv | MODIFICACION_ARCHIVO | 0165ebfac881f970000000332488fd1 | contador_vquispe (192.168.21.78) | Modificacion operativa legitima realizada por contador_vquispe sobre Balance_Contable_2026.csv. |
| #7 | 2026-10-26 13:35:09 UTC | Configuracion_ERP_Pyme.json | RESTAURACION_VIAJE_TIEMPO | 0165ebe65e172e70000000332488fd1 | carloos-odann (192.168.21.78) | Viaje en el Tiempo completado: Se restauro Configuracion_ERP_Pyme.json desde la revision 0165ebe65352bde0000000332488fd1 generando la nueva revision activa 0165ebe65e172e70000000332488fd1. Motivo: Restauracion de version integra autorizada desde el Panel Web Admin. |
| #6 | 2026-10-26 13:35:02 UTC | Configuracion_ERP_Pyme.json | INCIDENTE_RANSOMWARE | 0165ebe65a5b28b0000000332488fd1 | proceso_externo_no_autorizado (192.168.21.78) | ALERTA CRITICA: Se detecto corrupcion o secuestro de datos sobre Configuracion_ERP_Pyme.json. Se requiere restauracion inmediata a una version anterior integra. |
| #5 | 2026-10-26 13:35:00 UTC | Balance_Contable_2026.csv | MODIFICACION_ARCHIVO | 0165ebe658b14ba0000000332488fd1 | contador_vquispe (192.168.21.78) | Modificacion operativa legitima realizada por contador_vquispe sobre Balance_Contable_2026.csv. |
| #4 | 2026-10-26 13:34:57 UTC | Contratos_Proveedores_2026.md | CREACION_INICIAL | 0165ebe655506600000000332488fd1 | carloos-odann (192.168.21.78) | Ingesta y respaldo inicial del activo empresarial Contratos_Proveedores_2026.md en Dropbox Core Storage. |
| #3 | 2026-10-26 13:34:55 UTC | Configuracion_ERP_Pyme.json | CREACION_INICIAL | 0165ebe65352bde0000000332488fd1 | carloos-odann (192.168.21.78) | Ingesta y respaldo inicial del activo empresarial Configuracion_ERP_Pyme.json en Dropbox Core Storage. |
| #2 | 2026-10-26 13:34:53 UTC | Planilla_Sueldos_RRHH.csv | CREACION_INICIAL | 0165ebe651e32910000000332488fd1 | carloos-odann (192.168.21.78) | Ingesta y respaldo inicial del activo empresarial Planilla_Sueldos_RRHH.csv en Dropbox Core Storage. |

## 5. Suscripcion y Firma Electronica Legal (Dropbox Sign)
Por medio de la presente acta, los responsables de infraestructura y auditoria TI certifican que las pruebas de respaldo desacoplado en tiempo real y recuperacion de versiones mediante Dropbox API v2 se ejecutaron satisfactoriamente, garantizando la integridad de los datos de la organizacion.

- **Responsable de Infraestructura Cloud (Grupo 2):** ___________________________
- **Coordinador de Seguridad y Auditoria TI (Grupo 2):** ___________________________
