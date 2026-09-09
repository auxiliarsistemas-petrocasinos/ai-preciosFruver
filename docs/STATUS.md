# Estado del proyecto

## Definido

- MVP interno con usuarios de TI para administración y un pequeño grupo de compras para operación; compras evalúa y aprueba finalmente las alternativas.
- Registro de fuentes potenciales sin lista cerrada inicial.
- Investigación y captura manuales, asistidas y verificables durante el MVP.
- *Benchmark* inicial basado principalmente en compras históricas y cotizaciones existentes.
- Registro de metadatos y trazabilidad de evidencias: PDF, correos, conversaciones o capturas de WhatsApp, capturas de pantalla, URLs, páginas web y otros documentos relacionados.
- Monolito modular: Python, FastAPI, Jinja2, HTMX, PostgreSQL y Docker Compose; evidencias persistentes, autenticación local, roles simples y HTTPS mediante proxy inverso.
- Despliegue interno previsto en un servidor propio donde Docker funciona correctamente.

## Capacidades implementadas

- Estructura inicial del monolito FastAPI, con rutas técnicas y de interfaz separadas, plantillas Jinja2 y una comprobación mínima mediante HTMX.
- Configuración por variables de entorno, Docker Compose con PostgreSQL y volúmenes persistentes separados para base de datos y evidencias.
- Ruta `GET /health` y pruebas/lint/formato mínimos para Python.
- Persistencia síncrona con SQLAlchemy 2.x, psycopg 3 y Alembic.
- Registro, listado y detalle de necesidades de compra.
- Registro, listado y detalle de fuentes reutilizables y proveedores reutilizables, sin reglas de aprobación ni unicidad por nombre.
- Registro manual de prospecciones desde una necesidad de compra mediante una fuente existente y, opcionalmente, un proveedor existente. Las prospecciones quedan visibles en el detalle de la necesidad.
- Registro manual de múltiples ofertas comerciales por prospección con proveedor. Cada oferta conserva precio, unidad de precio y moneda sin normalización, fecha de obtención, descripción opcional y condiciones opcionales de texto libre.
- Registro manual de referencias URL HTTP/HTTPS como evidencias de una prospección o de una oferta comercial. Cada evidencia pertenece exactamente a uno de esos destinos y conserva título, URL, fecha de captura o consulta y notas opcionales.
- Carga manual de un archivo PDF, PNG o JPEG por envío, de máximo 20 MiB, como representación alternativa de `Evidence`. Conserva nombre original solo como metadata, MIME derivado de firma, tamaño real y clave opaca única; el archivo se publica atómicamente en filesystem local bajo `EVIDENCE_STORAGE_PATH`.
- Descarga contextual controlada, siempre como adjunto, con `X-Content-Type-Options: nosniff` y `Cache-Control: private, no-store`. Los archivos viven en el volumen `evidence_data`, cuya persistencia no constituye backup.
- Migraciones para `purchase_needs`, `sources`, `providers`, `prospecting_records`, `commercial_offers` y `evidence_items`, con sus claves foráneas, restricciones e índices de relación. `Evidence` conserva intacto el XOR de destino y añade un XOR entre URL y archivo completo.

Una fuente representa el origen, canal o lugar consultado; no representa una evidencia concreta. Una oferta comercial es la alternativa candidata estructurada dentro de una necesidad, no el documento o comunicación que la sustenta. Las evidencias URL y los archivos PDF/PNG/JPEG están implementados. Otros formatos, antivirus, checksum, previews, backup, retención y corrección de archivos erróneos mediante edición, reemplazo o eliminación continúan pendientes.

La aplicación aún no tiene autenticación ni autorización. La carga y descarga de archivos son aptas para desarrollo o una red interna restringida, no para exposición pública; conocer o recorrer la jerarquía de IDs no concede autorización. HTTPS/proxy inverso también sigue pendiente según el despliegue.

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
