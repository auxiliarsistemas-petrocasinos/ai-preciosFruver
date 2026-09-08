# Registro de Decisiones de Arquitectura y Negocio (ADRs)

Este documento registra decisiones aceptadas y pendientes explícitos. No convierte una pregunta abierta en requisito.

---

## Decisiones aceptadas

### ADR-001: Propósito y comparación de alternativas

- **Estado:** Aceptada.
- **Decisión:** El sistema apoya la reducción de costos de compra de productos fruver y compara alternativas contra un *benchmark*. La comparación considera el concepto de costo puesto en la puerta de la bodega (*landed cost*); su fórmula exacta no está definida.

### ADR-002: Usuarios y decisión final

- **Estado:** Aceptada.
- **Decisión:** Los usuarios iniciales son personal de TI, para administración, y un pequeño grupo de compras, como usuarios operativos. El área de compras evalúa, aprueba y toma la decisión final sobre las alternativas.

### ADR-003: Fuentes y captura en el MVP

- **Estado:** Aceptada.
- **Decisión:** El sistema permite registrar distintas fuentes potenciales de proveedores, sin una lista cerrada inicial. En el MVP, la investigación y captura son manuales, asistidas y verificables. El *scraping* y los conectores automáticos quedan fuera del MVP y se evaluarán posteriormente fuente por fuente.

### ADR-004: Benchmark inicial

- **Estado:** Aceptada.
- **Decisión:** El *benchmark* inicial se construye principalmente con compras históricas y cotizaciones existentes. El formato y mecanismo exacto de obtención de esos datos permanecen pendientes.

### ADR-005: Evidencias y trazabilidad

- **Estado:** Aceptada.
- **Decisión:** El sistema conserva metadatos y trazabilidad de las evidencias asociadas a alternativas y cotizaciones. Las evidencias pueden ser cotizaciones PDF, correos, conversaciones o capturas de WhatsApp, capturas de pantalla, URLs, páginas web y otros documentos relacionados.

### ADR-006: Arquitectura técnica del MVP

- **Estado:** Aceptada.
- **Decisión:** El MVP se construirá como un monolito modular con Python, FastAPI, Jinja2, HTMX y PostgreSQL. Usará Docker Compose, almacenamiento persistente de evidencias, autenticación local, roles simples y HTTPS mediante proxy inverso.

### ADR-007: Entorno de despliegue

- **Estado:** Aceptada.
- **Decisión:** El desarrollo ocurre en la máquina local del desarrollador y el despliegue interno se realizará en un servidor propio donde Docker funciona correctamente. Las especificaciones del servidor siguen pendientes.

### ADR-008: Exclusiones del MVP

- **Estado:** Aceptada.
- **Decisión:** Quedan fuera del MVP: IA, *scraping* universal, conectores automáticos de proveedores, agentes autónomos, automatización completa de RFQ, integración ERP, órdenes de compra, pagos y microservicios.

### ADR-009: Persistencia relacional y migraciones

- **Estado:** Aceptada.
- **Decisión:** El MVP utiliza PostgreSQL con SQLAlchemy 2.x y psycopg 3 mediante acceso síncrono. Las migraciones de esquema se gestionan con Alembic. No se utiliza SQLAlchemy async.

### ADR-010: Fuentes, proveedores y registros de prospección

- **Estado:** Aceptada.
- **Decisión:** `Source` es una entidad reutilizable para el origen, canal o lugar consultado durante la prospección. Conserva nombre obligatorio, referencia opcional de texto libre, notas opcionales y fecha de creación. No representa la evidencia concreta.
- **Decisión:** `Provider` es una contraparte comercial reutilizable y es válida con solo un nombre. Puede conservar opcionalmente nombre de contacto, correo, teléfono, ubicación de texto libre y notas. No se impone unicidad por nombre.
- **Decisión:** `ProspectingRecord` registra en contexto que una necesidad consultó una fuente. La fuente y la necesidad son obligatorias; el proveedor y las notas son opcionales, de modo que se pueda registrar una consulta sin proveedor resultante.
- **Relaciones:** Una necesidad, una fuente o un proveedor pueden participar en múltiples registros de prospección. No existe una relación global directa entre fuente y proveedor.
- **Alcance actual:** Creación y consulta de fuentes y proveedores, y registro manual y visualización de prospecciones en una necesidad. Edición, eliminación, evidencias, cotizaciones, precios, evaluación y aprobación permanecen fuera de este incremento.

### ADR-011: Ofertas comerciales como alternativas candidatas

- **Estado:** Aceptada.
- **Decisión:** `CommercialOffer` representa una oferta comercial estructurada que funciona como alternativa candidata dentro de una necesidad. Puede registrar un precio público, información recibida informalmente, una respuesta de proveedor o los datos de una cotización formal. El artefacto que sustenta la información corresponde a evidencia y no forma parte de esta entidad.
- **Relación:** Una prospección puede tener múltiples ofertas comerciales. Cada oferta pertenece obligatoriamente a un `ProspectingRecord` y deriva de este la necesidad, fuente y proveedor, sin duplicar sus claves foráneas.
- **Regla:** La aplicación solo permite registrar ofertas cuando la prospección tiene proveedor asociado. Las prospecciones sin proveedor continúan representando consultas sin resultado comercial.
- **Captura:** Cada oferta conserva precio positivo, unidad del precio y moneda como texto libre, fecha de obtención, descripción opcional y condiciones opcionales de texto libre. No se asignan monedas por defecto, no se exige coincidencia de unidades y no se realizan normalizaciones, conversiones, comparaciones ni cálculos.
- **Alcance actual:** Creación y visualización contextual desde el detalle de la necesidad. Las referencias URL que sustentan ofertas se implementan como `Evidence`; los archivos de evidencia permanecen pendientes. Listado global, detalle independiente, edición, eliminación, benchmark, evaluación y decisión también permanecen pendientes.

### ADR-012: Referencias URL de evidencia

- **Estado:** Aceptada.
- **Decisión:** `Evidence` representa una referencia URL concreta y contextual que sustenta una prospección o una oferta comercial. No reemplaza a `Source`, que continúa representando el origen, canal o lugar reutilizable donde se investigó.
- **Relaciones:** Una prospección y una oferta comercial pueden tener múltiples evidencias. Cada evidencia pertenece exactamente a una prospección o a una oferta mediante dos claves foráneas opcionales y una restricción XOR; nunca pertenece a ambas ni queda sin destino. Una evidencia de oferta deriva la prospección, fuente, proveedor y necesidad por las relaciones existentes.
- **Captura:** Cada evidencia conserva título, URL absoluta HTTP/HTTPS, fecha de captura o consulta, notas opcionales y fecha de creación. Las URLs no son únicas y se presentan por fecha de captura y creación descendentes.
- **Seguridad:** El servidor valida sintaxis, esquema y host, pero no solicita, verifica, descarga ni previsualiza la URL.
- **Alcance actual:** Creación y visualización contextual dentro de la necesidad. Carga, almacenamiento y descarga de archivos, tipos de evidencia, edición, eliminación, backup y retención permanecen pendientes.

---

## Pendientes de validación humana

1. **Fórmula de landed cost:** Debe validarse con personal operativo, probablemente un supervisor de bodega junto con compras. Desarrollo no debe inventarla.
2. **Normalización/equivalencias:** Falta definir normalización de productos, variedades, calidades y equivalencias entre unidades de medida.
3. **Formato de datos históricos:** Falta confirmar el formato y mecanismo de obtención de compras históricas y cotizaciones existentes.
4. **Fuentes iniciales:** Falta acordar las fuentes potenciales que se registrarán y usarán primero.
5. **Especificaciones del servidor:** Faltan hardware, sistema operativo y condiciones concretas de despliegue.
6. **Política de backup/retención:** Falta definir respaldo, recuperación y retención de datos y evidencias.
7. **Roles simples:** Falta detallar los nombres y permisos de cada rol.
8. **Reglas de evaluación:** Faltan vigencia de cotizaciones y criterios adicionales para ordenar alternativas.
