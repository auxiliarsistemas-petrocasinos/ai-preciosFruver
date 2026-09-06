# Arquitectura del MVP

## Decisión arquitectónica

El MVP será un **monolito modular** desplegable con Docker Compose. No se divide en microservicios.

## Componentes decididos

| Componente | Decisión |
| --- | --- |
| Aplicación | Python con FastAPI |
| Interfaz web | Plantillas Jinja2 y HTMX |
| Base de datos | PostgreSQL |
| Empaquetado y ejecución | Docker Compose |
| Evidencias | Almacenamiento persistente para archivos y documentos asociados |
| Acceso | Autenticación local y roles simples |
| Exposición segura | HTTPS mediante proxy inverso |

## Límites del MVP

La aplicación respalda un flujo manual, asistido y verificable de registro de fuentes potenciales, alternativas, cotizaciones, decisiones y evidencias. Compras conserva la evaluación y aprobación final.

No forman parte de esta arquitectura del MVP la IA, el *scraping* universal, conectores automáticos de proveedores, agentes autónomos, automatización completa de RFQ, integración ERP, órdenes de compra, pagos ni microservicios.

## Aspectos no definidos por esta arquitectura

Esta decisión no fija la fórmula de *landed cost*, las reglas de normalización/equivalencias, el formato de datos históricos, las fuentes iniciales, las especificaciones del servidor ni la política de backup/retención. Esos aspectos requieren validación humana.

