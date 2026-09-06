# Hoja de Ruta (Roadmap): ai-preciosFruver

Este documento propone una secuencia de evolución en tres horizontes (**Now**, **Next**, **Later**). Es una guía de alcance, no una decisión de arquitectura ni un compromiso de fechas; los elementos marcados como pendientes requieren validación antes de incorporarse. El objetivo de $0 COP aplica a gasto nuevo del MVP y depende de recursos internos disponibles y de la viabilidad de servicios externos gratuitos.

---

## 🟢 Now (Fase 1: MVP Funcional)

**Objetivo:** Validar el flujo de captura de necesidades, prospección inicial y comparación de precios con la menor fricción y sin gasto nuevo.

- [ ] **Módulo de Solicitud de Insumos:**
  - Formulario web intuitivo para capturar parámetros de compra (producto, variedad, cantidad, unidad, fecha requerida, bodega destino).
- [ ] **Base de Proveedores y Línea Base (*Benchmark*):**
  - Registro interno de proveedores actuales y sus precios de referencia para medir el ahorro potencial frente a nuevas opciones.
- [ ] **Motor de Prospección Inicial:**
  - Búsqueda en las fuentes públicas y directorios que se aprueben para identificar nuevos distribuidores y mayoristas a nivel nacional.
  - Extracción de precios públicos visibles cuando estén disponibles.
- [ ] **Tablero Comparativo y Decisión:**
  - Vista comparativa de opciones encontradas frente a la línea base actual.
  - Registro de la decisión tomada por el comprador.
- [ ] **Control de Acceso Básico:**
  - Autenticación simple y segregación inicial de permisos para el equipo de ~5 usuarios.

---

## 🟡 Next (Fase 2: Agente de Contacto y Cotización Automatizada)

**Objetivo:** Automatizar la interacción con proveedores para obtener precios exactos con entrega puesta en bodega cuando no son públicos.

- [ ] **Generador Inteligente de Solicitudes de Cotización (RFQ):**
  - Redacción automática de solicitudes estandarizadas con todos los requerimientos técnicos y logísticos.
- [ ] **Canal de Correo Electrónico:**
  - Capacidad prevista para enviar solicitudes de cotización vía email y procesar respuestas, sujeta a definir proveedor, credenciales, costos y el nivel de automatización permitido.
- [ ] **Canal de WhatsApp:**
  - Integración o asistencia para el envío de solicitudes de cotización hacia proveedores vía WhatsApp, sujeta a definir viabilidad técnica, costos y condiciones de uso.
- [ ] **Consolidación de Ofertas Recibidas:**
  - Estandarización de precios, fletes y plazos de entrega reportados por los proveedores.
- [ ] **Historial de Precios y Fichas de Proveedor:**
  - Ampliación y explotación del registro histórico de cotizaciones por producto y temporalidad. El registro mínimo necesario para comparar opciones debe existir desde el MVP.
  - Evaluación de fiabilidad y tiempos de respuesta de proveedores.

---

## 🔵 Later (Fase 3: Optimización, Analítica y Escala)

**Objetivo:** Incorporar analítica predictiva, automatizaciones avanzadas e integración con sistemas contables/ERP de la empresa.

- [ ] **Alertas y Tendencias de Mercado:**
  - Notificaciones automáticas sobre caídas o alzas estacionales de precios en productos clave.
- [ ] **Integración ERP / Contabilidad:**
  - Posible sincronización de órdenes de compra con el sistema de inventario o facturación de la empresa, una vez se confirmen los sistemas objetivo y su disponibilidad de integración.
- [ ] **Interfaz Conversacional Avanzada:**
  - Asistente tipo bot interno para que los usuarios puedan consultar precios o solicitar cotizaciones desde herramientas de chat (Slack, Teams, WhatsApp interno).
- [ ] **Negociación Asistida:**
  - Sugerencias automáticas de contraoferta basadas en precios históricos y volumen solicitado.

---

## ❓ Preguntas Abiertas del Roadmap

> [!NOTE]
> Puntos a resolver antes de iniciar la implementación de cada fase:

1. **Alcance del MVP en WhatsApp:** ¿Para la fase **Now** bastará con generar enlaces directos de contacto (`wa.me`) con el mensaje preformateado para envío con un clic, o se requiere automatización total desde el inicio?
2. **Fuentes iniciales de datos para el MVP:** ¿Cuáles son los primeros 3 a 5 sitios o directorios clave que el proceso de prospección debería consultar en la fase **Now**?
3. **Métrica de éxito del MVP:** ¿Qué porcentaje o monto de ahorro frente a proveedores actuales validará el éxito del MVP para solicitar presupuesto posterior?
4. **Cálculo y criterios de comparación:** ¿Cómo se calculará el costo puesto en bodega y qué criterios, además de este costo, determinarán el orden de las ofertas?
5. **Condiciones operativas:** ¿Qué fuentes están autorizadas y qué proveedor de correo, credenciales, consentimiento o revisión humana se requerirá antes de enviar contactos?
