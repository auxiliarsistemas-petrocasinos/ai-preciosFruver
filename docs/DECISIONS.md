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
