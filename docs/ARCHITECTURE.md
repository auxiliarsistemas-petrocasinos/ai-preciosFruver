# Arquitectura del MVP

## Decisión arquitectónica

El MVP será un **monolito modular** desplegable con Docker Compose. No se divide en microservicios.

## Componentes decididos

| Componente | Decisión |
| --- | --- |
| Aplicación | Python con FastAPI |
| Interfaz web | Plantillas Jinja2 y HTMX |
| Base de datos | PostgreSQL |
| Persistencia y migraciones | SQLAlchemy 2.x síncrono, psycopg 3 y Alembic |
| Empaquetado y ejecución | Docker Compose |
| Evidencias | URLs y archivos PDF/PNG/JPEG en filesystem local persistente |
| Acceso | Autenticación local y roles simples |
| Exposición segura | HTTPS mediante proxy inverso |

## Límites del MVP

La aplicación respalda un flujo manual, asistido y verificable de registro de fuentes potenciales, alternativas, cotizaciones, decisiones y evidencias. Compras conserva la evaluación y aprobación final.

No forman parte de esta arquitectura del MVP la IA, el *scraping* universal, conectores automáticos de proveedores, agentes autónomos, automatización completa de RFQ, integración ERP, órdenes de compra, pagos ni microservicios.

## Módulos persistentes implementados

- `purchase_needs`: necesidades de compra y su interfaz web de creación y consulta.
- `sources`: fuentes reutilizables que representan el origen, canal o lugar consultado durante la prospección.
- `providers`: contrapartes comerciales reutilizables; para su registro solo es obligatorio el nombre.
- `prospecting`: registros contextuales que vinculan una necesidad con una fuente y, opcionalmente, con un proveedor.
- `commercial_offers`: ofertas comerciales capturadas manualmente para una prospección con proveedor; representan alternativas candidatas dentro de la necesidad.
- `evidence`: referencias URL o archivos persistidos que sustentan una prospección o una oferta comercial.

Las relaciones implementadas son `PurchaseNeed 1 -> N ProspectingRecord`, `Source 1 -> N ProspectingRecord`, `Provider 1 -> N ProspectingRecord`, `ProspectingRecord 1 -> N CommercialOffer`, `ProspectingRecord 1 -> N Evidence` y `CommercialOffer 1 -> N Evidence`, con proveedor opcional en cada prospección. Una oferta solo puede registrarse mediante la aplicación cuando la prospección tiene proveedor. `CommercialOffer` deriva necesidad, fuente y proveedor de su prospección y no duplica esas relaciones. Cada evidencia pertenece a una prospección o a una oferta, nunca a ambas ni a ninguna, mediante dos claves foráneas y una restricción XOR. Un segundo XOR exige que su representación sea exactamente una URL o un archivo con toda su metadata. No existe una relación global directa entre fuentes y proveedores.

Una fuente no es la referencia concreta que sustenta un hallazgo y una oferta comercial no es su soporte. `Evidence` conserva URLs HTTP/HTTPS registradas manualmente sin acceder a ellas desde el servidor, o un archivo PDF/PNG/JPEG de hasta 20 MiB. Los archivos se copian por chunks, se validan por extensión y firma, y se publican atómicamente bajo una clave UUID opaca relativa a `EVIDENCE_STORAGE_PATH`. Docker Compose monta allí el volumen `evidence_data`; este volumen da persistencia, no backup.

Las descargas validan toda la jerarquía, el destino de `Evidence`, su representación y el containment del archivo regular; no usan `StaticFiles` y siempre fuerzan attachment. La capa ASGI que limita multipart se aplica solo a las rutas POST de archivo y controla tanto `Content-Length` como los bytes realmente recibidos. No existe aún autenticación/autorización, por lo que estas rutas son solo para desarrollo o red interna restringida y no deben publicarse. La jerarquía de IDs no equivale a autorización.

Los precios, unidades, monedas y condiciones se conservan como fueron capturados, sin conversiones, normalización, comparación ni cálculo de *landed cost*. Antivirus, checksum, otros formatos, previews, cloud storage, edición, reemplazo y eliminación de archivos no forman parte del incremento.

## Aspectos no definidos por esta arquitectura

Esta decisión no fija la fórmula de *landed cost*, las reglas de normalización/equivalencias, el formato de datos históricos, las fuentes iniciales, las especificaciones del servidor ni la política de backup/retención. Esos aspectos requieren validación humana.
