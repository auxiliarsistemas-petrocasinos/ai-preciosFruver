# Especificación del Proyecto: ai-preciosFruver

## 1. Declaración del Problema

La empresa requiere reducir los costos de adquisición de materias primas y productos que compra habitualmente (enfocados en el sector fruver / agropecuario y afines). Actualmente, los proveedores existentes tienen precios fijados que no bajan más, lo que genera la necesidad de:

1. Salir al mercado a buscar de forma activa y continua nuevos proveedores a nivel nacional.
2. Evaluar no únicamente el precio por unidad del producto, sino el **costo total puesto en la puerta de la bodega** (precio de materia prima + costo de flete/transporte hasta la ubicación requerida).
3. Agilizar el proceso de cotización y centralizar la toma de decisiones del equipo de compras.

---

## 2. Usuarios y Perfiles

- **Destinatarios:** Equipo interno de compras y abastecimiento de la empresa.
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

Para localizar opciones de abastecimiento, el sistema contemplará:

1. **Portales web públicos y marketplaces:** Sitios de comercio electrónico mayorista, listas públicas de precios y directorios comerciales agropecuarios.
2. **Búsqueda abierta en internet:** Identificación de distribuidores, cooperativas, fincas y mayoristas a nivel nacional mediante motores de búsqueda.
3. **Base de datos interna de proveedores existentes:** Utilizada como **línea base (*benchmark*)** para comparar alternativas. Puede considerarse para la compra solo si no se identifica una alternativa conveniente; no se define un umbral de precio único, pues la comparación considera el costo puesto en bodega y los criterios de selección pendientes.

---

## 5. Dinámica de Cotización

1. **Extracción directa:** Cuando el proveedor publique precios fijos y condiciones de envío en su sitio web, el sistema extraerá la información directamente.
2. **Generación de solicitudes de cotización (RFQ):** Cuando el precio no sea público o dependa del flete a bodega, el sistema deberá permitir preparar solicitudes de cotización para el proveedor. El envío y la recepción automatizados pertenecen al alcance previsto de fases posteriores; su forma técnica no está decidida.
3. **Canales de comunicación previstos:**
   - **Correo electrónico** (cotización formal detallada).
   - **WhatsApp** (contacto directo, canal preferido por distribuidores agropecuarios).
4. **Decisión humana:** El sistema recopila, filtra y ordena las alternativas encontradas; el usuario humano siempre conserva la decisión final de selección y compra.

---

## 6. Almacenamiento y Gestión de Datos

Como capacidad objetivo del sistema, se debe persistir:

- **Historial de precios:** Registro de variaciones temporales por producto, variedad, proveedor y fecha para detectar estacionalidad y tendencias.
- **Ficha de proveedores:** Directorio comercial con contactos, canales de comunicación, calificación de servicio, confiabilidad y tiempos promedio de entrega.
- **Trazabilidad y auditoría de decisiones de compra:** Historial completo de solicitudes (quién solicitó, qué opciones arrojó la prospección, qué respuestas se obtuvieron y cuál fue la opción seleccionada). La emisión de órdenes de compra, pagos o integración contable no forma parte del alcance definido hasta ahora.

---

## 7. Restricciones y Entorno Operativo

- **Presupuesto inicial (MVP):** $0 COP de gasto nuevo. Se debe maximizar el uso de tecnologías libres, librerías *open source* y, cuando sean viables, capas gratuitas de servicios de IA/búsqueda. No se ha confirmado qué servicios externos, credenciales o infraestructura ya están disponibles ni su permanencia sin costo.
- **Entorno de desarrollo:** Máquina local del desarrollador.
- **Entorno de producción interna:** Servidor propio (*on-premise*) de la empresa.
- **Interfaz de usuario:** Interfaz web empresarial limpia, sin fricción ni complejidades innecesarias para los operadores.

---

## 8. ❓ Preguntas Abiertas (Pendientes por Definir)

> [!IMPORTANT]
> Los siguientes puntos no han sido decididos y requieren definición técnica o validación posterior:

1. **Catálogo estandarizado de productos:** ¿Se manejará un catálogo maestro cerrado de productos con nombres y variedades normalizadas, o los usuarios podrán escribir términos libres al solicitar insumos?
2. **Mecanismo de automatización en WhatsApp a costo cero:** ¿Cómo se enviarán y recibirán los mensajes de WhatsApp sin incurrir en costos de API oficial (Meta Cloud API / Twilio) manteniendo estabilidad (p. ej. puente Web, mensajes semiautomatizados mediante enlaces `wa.me`, o comenzar con correos y simulación)?
3. **Definición precisa de la matriz de roles:** ¿Cuáles serán los nombres exactos y capacidades de cada rol (ej. `Administrador`, `Comprador`, `Aprobador`)?
4. **Tolerancia y caducidad de cotizaciones:** ¿Durante cuánto tiempo se considera válida una cotización recibida de un proveedor antes de requerir actualización?
5. **Criterios de ordenamiento de ofertas:** Además del precio final puesto en bodega, ¿qué peso tendrán factores como tiempo de entrega, reputación del proveedor o condiciones de pago (crédito vs. contado)?
6. **Cálculo de costo puesto en bodega:** ¿Qué conceptos, además de precio base y flete, se incluirán o excluirán (impuestos, cargue/descargue, seguros, mínimos de pedido y otros cargos), y quién validará el dato de flete cuando no esté confirmado por el proveedor?
7. **Alcance verificable del MVP:** ¿La primera versión solo registrará y comparará opciones públicas, o incluirá preparación de RFQ, envío por correo, enlaces de WhatsApp y/o lectura de respuestas? La hoja de ruta plantea una secuencia, pero no sustituye esta definición de alcance.
8. **Uso de fuentes y contacto de proveedores:** ¿Qué fuentes pueden consultarse y con qué frecuencia, y qué consentimiento, revisión humana o políticas internas se exigirán antes de contactar proveedores por correo o WhatsApp?
