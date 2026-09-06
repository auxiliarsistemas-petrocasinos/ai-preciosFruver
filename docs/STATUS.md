# Estado del proyecto

## Definido

- MVP interno con usuarios de TI para administración y un pequeño grupo de compras para operación; compras evalúa y aprueba finalmente las alternativas.
- Registro de fuentes potenciales sin lista cerrada inicial.
- Investigación y captura manuales, asistidas y verificables durante el MVP.
- *Benchmark* inicial basado principalmente en compras históricas y cotizaciones existentes.
- Registro de metadatos y trazabilidad de evidencias: PDF, correos, conversaciones o capturas de WhatsApp, capturas de pantalla, URLs, páginas web y otros documentos relacionados.
- Monolito modular: Python, FastAPI, Jinja2, HTMX, PostgreSQL y Docker Compose; evidencias persistentes, autenticación local, roles simples y HTTPS mediante proxy inverso.
- Despliegue interno previsto en un servidor propio donde Docker funciona correctamente.

## Bootstrap técnico implementado

- Estructura inicial del monolito FastAPI, con rutas técnicas y de interfaz separadas, plantillas Jinja2 y una comprobación mínima mediante HTMX.
- Configuración por variables de entorno, Docker Compose con PostgreSQL y volúmenes persistentes separados para base de datos y evidencias.
- Ruta `GET /health` y pruebas/lint/formato mínimos para Python.
- Persistencia síncrona con SQLAlchemy 2.x, psycopg 3 y Alembic; incluye la primera migración y el registro y consulta de necesidades de compra en PostgreSQL.

## Pendiente de validación humana

- **Fórmula de landed cost:** debe ser validada, probablemente por un supervisor de bodega junto con compras.
- **Normalización/equivalencias:** productos, variedades, calidades y unidades.
- **Formato de datos históricos:** formato y mecanismo de obtención de compras históricas y cotizaciones existentes.
- **Fuentes iniciales:** cuáles fuentes potenciales se registrarán y usarán primero.
- **Especificaciones del servidor:** hardware, sistema operativo y condiciones de despliegue.
- **Política de backup/retención:** respaldo, recuperación y retención de datos y evidencias.
- Nombres y permisos concretos de los roles simples; vigencia de cotizaciones y criterios adicionales de evaluación.

## Fuera del MVP

- IA.
- *Scraping* universal.
- Conectores automáticos de proveedores.
- Agentes autónomos.
- Automatización completa de RFQ.
- Integración ERP.
- Órdenes de compra y pagos.
- Microservicios.
