# Especificación del Proyecto: ai-preciosFruver

## 1. Declaración del Problema

La empresa requiere reducir los costos de adquisición de materias primas y productos que compra habitualmente (enfocados en el sector fruver / agropecuario y afines). Actualmente, los proveedores existentes tienen precios fijados que no bajan más, lo que genera la necesidad de:

1. Salir al mercado a buscar de forma activa y continua nuevos proveedores a nivel nacional.
2. Evaluar no únicamente el precio por unidad del producto, sino el **costo total puesto en la puerta de la bodega** (precio de materia prima + costo de flete/transporte hasta la ubicación requerida).
3. Agilizar el proceso de cotización y centralizar la toma de decisiones del equipo de compras.

---

## 2. Usuarios y Perfiles

- **Destinatarios:** Personal de TI para administración y un pequeño grupo del área de compras como usuarios operativos. Compras evalúa y aprueba finalmente las alternativas.
- **Volumen inicial:** Aproximadamente 5 usuarios iniciales. La concurrencia esperada no se ha definido.
- **Control de acceso:** Sistema con autenticación y roles diferenciados (por ejemplo: roles con capacidad de solicitar/cotizar y roles con capacidad de aprobar o administrar usuarios y proveedores).

---

## 3. Variables de Entrada de una Solicitud de Compra

Para iniciar un proceso de búsqueda y cotización, el sistema debe capturar como mínimo:

- **Nombre del producto / materia prima:** (ej. Tomate chonto, Papa pastusa, Cebolla junca).
- **Variedad y estándar de calidad:** (ej. Primera, Segunda, industrial, calibre específico).
- **Cantidad requerida y volumen:** (número de unidades o masa total).
- **Unidad de medida:** (ej. kilogramo [kg], bulto, canastilla, tonelada).
- **Fecha requerida de entrega:** (cuándo debe estar físicamente en la empresa).
- **Ciudad y ubicación exacta de la bodega destino:** (factor indispensable para calcular o cotizar el flete).

---

## 4. Fuentes de Datos y Estrategia de Prospección

El sistema permitirá registrar distintas fuentes potenciales de proveedores, sin partir de una lista cerrada. En el MVP, la investigación y captura de información será manual, asistida y verificable; no incluirá *scraping* ni conectores automáticos.

El **benchmark** inicial se construirá principalmente con compras históricas y cotizaciones existentes. El formato y el mecanismo para obtener estos datos siguen pendientes de confirmación.

---

## 5. Dinámica de Cotización

1. **Captura asistida y verificable:** El usuario registra las alternativas y sus evidencias; las fuentes pueden incluir sitios web, cotizaciones y comunicaciones con proveedores.
2. **Solicitudes de cotización (RFQ):** La automatización completa de preparación, envío y recepción no pertenece al MVP.
3. **Canales de comunicación:** Correo electrónico y WhatsApp son canales relevantes para evidencias y futuras interacciones, sin integración automática en el MVP.
4. **Decisión humana:** Compras evalúa, aprueba y decide finalmente la alternativa y la compra.

---

## 6. Almacenamiento y Gestión de Datos

Como capacidad objetivo del sistema, se debe persistir:

- **Historial de precios:** Registro de variaciones temporales por producto, variedad, proveedor y fecha para detectar estacionalidad y tendencias.
- **Ficha de proveedores:** Directorio comercial con contactos, canales de comunicación, calificación de servicio, confiabilidad y tiempos promedio de entrega.
- **Trazabilidad y auditoría de decisiones de compra:** Historial completo de solicitudes (quién solicitó, qué opciones arrojó la prospección, qué respuestas se obtuvieron y cuál fue la opción seleccionada). La emisión de órdenes de compra, pagos o integración contable no forma parte del alcance definido hasta ahora.
- **Evidencias:** Metadatos y trazabilidad de cotizaciones PDF, correos, conversaciones o capturas de WhatsApp, capturas de pantalla, URLs, páginas web y otros documentos relacionados.

---

## 7. Restricciones y Entorno Operativo

- **Presupuesto inicial (MVP):** $0 COP de gasto nuevo. Se usarán tecnologías libres y recursos internos disponibles; IA, *scraping* y conectores automáticos están fuera del MVP.
- **Entorno de desarrollo:** Máquina local del desarrollador.
- **Entorno de producción interna:** Servidor propio (*on-premise*) donde Docker funciona correctamente. Sus especificaciones de hardware y sistema operativo siguen pendientes de confirmación.
- **Interfaz de usuario:** Interfaz web empresarial limpia, sin fricción ni complejidades innecesarias para los operadores.

---

## 8. ❓ Preguntas Abiertas (Pendientes por Definir)

> [!IMPORTANT]
> Los siguientes puntos no han sido decididos y requieren definición técnica o validación posterior:

1. **Fórmula de landed cost:** Debe validarse con personal operativo, probablemente un supervisor de bodega junto con el área de compras; no debe ser inventada desde desarrollo.
2. **Normalización y equivalencias:** Falta definir el tratamiento de catálogo, nombres, variedades, calidades y unidades de medida.
3. **Formato de datos históricos:** Falta confirmar el formato y mecanismo de obtención de compras históricas y cotizaciones existentes.
4. **Fuentes iniciales:** Falta acordar cuáles fuentes potenciales se registrarán y utilizarán primero.
5. **Especificaciones del servidor:** Faltan hardware, sistema operativo y demás condiciones de despliegue.
6. **Política de backup/retención:** Falta definir respaldo, recuperación y retención de datos y evidencias.
7. **Matriz precisa de roles:** Faltan los nombres y capacidades exactas de los roles simples.
8. **Reglas de comparación:** Faltan vigencia de cotizaciones y criterios adicionales de evaluación y ordenamiento.
