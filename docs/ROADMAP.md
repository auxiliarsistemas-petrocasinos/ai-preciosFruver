# Hoja de Ruta (Roadmap): ai-preciosFruver

Este documento propone una secuencia de evolución en tres horizontes (**Now**, **Next**, **Later**). Es una guía de alcance, no una decisión de arquitectura ni un compromiso de fechas; los elementos marcados como pendientes requieren validación antes de incorporarse. El objetivo de $0 COP aplica a gasto nuevo del MVP y depende de recursos internos disponibles y de la viabilidad de servicios externos gratuitos.

---

## 🟢 Now (Fase 1: MVP Funcional)

**Objetivo:** Validar el flujo de captura de necesidades, prospección inicial y comparación de precios con la menor fricción y sin gasto nuevo.

- [x] **Módulo de Solicitud de Insumos:**
  - Formulario web intuitivo para capturar parámetros de compra (producto, variedad, cantidad, unidad, fecha requerida, bodega destino).
- [ ] **Base de Proveedores, Fuentes y Línea Base (*Benchmark*):**
  - [x] Registro y consulta de fuentes y proveedores reutilizables, sin lista cerrada inicial, y registro manual de prospecciones por necesidad con proveedor opcional.
  - [ ] Construcción inicial del *benchmark* principalmente con compras históricas y cotizaciones existentes; su formato y mecanismo de obtención están pendientes de confirmar.
- [ ] **Captura Manual Asistida y Verificable:**
  - [x] Registro por usuarios de ofertas comerciales que funcionan como alternativas candidatas, con precios y condiciones de texto libre encontradas en las fuentes registradas.
  - [x] Asociación manual de referencias URL HTTP/HTTPS como evidencia de una prospección o de una oferta comercial.
  - [x] Carga y persistencia local de archivos PDF, PNG y JPEG de hasta 20 MiB, con descarga controlada exclusivamente como adjunto.
  - [ ] Ampliación a otros formatos de evidencia, antivirus, checksum, previews, edición/eliminación y políticas operativas de backup y retención.
- [ ] **Tablero Comparativo y Decisión:**
  - Vista comparativa de opciones encontradas frente a la línea base actual.
  - Registro de la decisión tomada por el comprador.
- [ ] **Control de Acceso Básico:**
  - [x] Autenticación local, sesiones server-side revocables, CSRF, protección global de rutas y CLI administrativa mínima.
  - [ ] Matriz y roles simples para TI administradora y el pequeño grupo operativo de compras; hasta definirlos, todos los usuarios activos autenticados comparten acceso.
  - [ ] Hardening de despliegue: HTTPS/proxy, rate limiting robusto, auditoría, autoservicio/reset de contraseña y evaluación posterior de MFA o SSO/LDAP.

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

1. **Fuentes iniciales de datos para el MVP:** ¿Cuáles fuentes potenciales se registrarán y utilizarán primero en la captura manual asistida?
3. **Métrica de éxito del MVP:** ¿Qué porcentaje o monto de ahorro frente a proveedores actuales validará el éxito del MVP para solicitar presupuesto posterior?
4. **Cálculo y criterios de comparación:** La fórmula de costo puesto en bodega debe validarse con bodega y compras; también faltan los criterios de ordenamiento y las equivalencias/normalización.
5. **Condiciones operativas:** ¿Qué fuentes están autorizadas y qué proveedor de correo, credenciales, consentimiento o revisión humana se requerirá antes de enviar contactos?
6. **Datos e infraestructura:** ¿Cuál será el formato y mecanismo para obtener datos históricos, las especificaciones del servidor y la política de backup/retención?
7. **Autorización y hardening:** ¿Cuál será la matriz de roles y qué proxy, terminación HTTPS, rate limiting y mecanismos adicionales de identidad exige el despliegue?
