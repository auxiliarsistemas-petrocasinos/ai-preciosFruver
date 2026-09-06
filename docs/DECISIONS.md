# Registro de Decisiones de Arquitectura y Negocio (ADRs)

Este documento registra **únicamente las decisiones acordadas formalmente**. No incluye suposiciones de arquitectura o tecnología que no hayan sido validadas.

---

## Decisiones Aceptadas

### ADR-001: Propósito de Negocio y Enfoque en Costo Puesto en Bodega (*Landed Cost*)
- **Estado:** Aceptada.
- **Contexto:** La empresa requiere reducir costos de materias primas e insumos (sector fruver). Los proveedores actuales tienen tarifas rígidas que no disminuyen.
- **Decisión:** El sistema evaluará el costo total del producto **puesto en la puerta de la bodega destino** (precio base + flete/logística), comparando ofertas a nivel nacional contra la línea base de los proveedores actuales.

### ADR-002: Audiencia y Control de Acceso
- **Estado:** Aceptada.
- **Contexto:** La herramienta será para uso interno exclusivo del departamento de compras de la empresa.
- **Decisión:** El sistema estará diseñado para un grupo inicial de aproximadamente **5 usuarios**, requiriendo autenticación y segregación de permisos por roles.

### ADR-003: Estrategia de Búsqueda y Fuentes de Datos
- **Estado:** Aceptada.
- **Contexto:** Depender de los proveedores existentes impide conseguir mejores tarifas.
- **Decisión:** La prospección priorizará portales web públicos, *marketplaces* y búsqueda abierta en internet a nivel nacional. La base de datos de proveedores internos se mantendrá como punto de referencia de precio (*benchmark*) y podrá considerarse si no se identifica una alternativa conveniente.

### ADR-004: Modelo Híbrido de Cotización con Decisión Humana
- **Estado:** Aceptada.
- **Contexto:** En el sector agropecuario, muchos precios no están publicados en páginas web o dependen directamente del volumen y la distancia del flete.
- **Decisión:** El sistema operará bajo un modelo dual:
  1. Extraerá precios públicos cuando existan.
  2. Permitirá preparar solicitudes de cotización cuando no haya precio visible. La automatización de envío y recepción, así como su fase exacta de incorporación, siguen pendientes de definición.
  3. **Supervisión humana:** El sistema presentará las opciones filtradas y ordenadas; la decisión final de adjudicación y compra siempre recaerá en el usuario humano.

### ADR-005: Canales de Contacto con Proveedores
- **Estado:** Aceptada.
- **Contexto:** Algunos distribuidores mayoristas manejan canales formales (correo) mientras que productores y comercializadores locales operan primordialmente vía mensajería instantánea.
- **Decisión:** El sistema contemplará tanto **Correo Electrónico** como **WhatsApp** como canales válidos de comunicación y solicitud de cotizaciones.

### ADR-006: Atributos Mínimos de Solicitud de Compra
- **Estado:** Aceptada.
- **Decisión:** Toda solicitud deberá capturar obligatoriamente: nombre del producto, variedad/calidad, cantidad/volumen, unidad de medida (kg, bulto, canastilla, etc.), fecha requerida y bodega destino.

### ADR-007: Entidades de Persistencia Requeridas
- **Estado:** Aceptada.
- **Decisión:** Como capacidad objetivo del sistema, se debe registrar y conservar:
  1. Historial de precios y variaciones temporales.
  2. Ficha y directorio de proveedores (contactos, calificaciones, tiempos).
  3. Trazabilidad completa de solicitudes y compras (quién pidió, qué cotizaciones llegaron, qué opción se eligió).

### ADR-008: Presupuesto del MVP ($0 COP)
- **Estado:** Aceptada.
- **Contexto:** Se busca validar el modelo antes de que la empresa asigne presupuesto formal de infraestructura o APIs.
- **Decisión:** La primera versión funcional (MVP) se construirá con un presupuesto de **$0 COP de gasto nuevo**, utilizando librerías de código abierto (*open source*) y, si resultan viables, capas gratuitas de servicios de búsqueda e inteligencia artificial. La disponibilidad, límites y condiciones de dichos servicios no están decididos.

### ADR-009: Entornos de Ejecución
- **Estado:** Aceptada.
- **Decisión:**
  - **Fase de desarrollo y pruebas:** Máquina local del desarrollador.
  - **Fase de despliegue interno:** Servidor propio (*on-premise*) de la empresa.

### ADR-010: Tipo de Interfaz de Usuario
- **Estado:** Aceptada.
- **Decisión:** Interfaz web enfocada en entorno empresarial, priorizando la facilidad de uso sin fricciones para los 5 operadores internos.

---

## ❓ Preguntas Abiertas y Decisiones Pendientes

Las siguientes decisiones de arquitectura e implementación técnica **no han sido tomadas todavía** y están explícitamente pendientes:

1. **[Pendiente] Stack Tecnológico Definitivo:**
   - Si bien se cuenta con conocimientos previos en Python, TypeScript, React, Next.js, FastAPI, PostgreSQL y Docker, aún no se ha decidido la arquitectura técnica concreta (¿Monolito en Next.js? ¿Backend desacoplado en FastAPI + Frontend en Next.js? ¿PostgreSQL con qué ORM?).
2. **[Pendiente] Motor de Búsqueda y Scraping a Costo Cero:**
   - ¿Qué herramientas o librerías específicas se utilizarán para la búsqueda web sin agotar cuotas de pago (p. ej. DuckDuckGo Search, Playwright, BeautifulSoup, SearXNG)?
3. **[Pendiente] Integración Técnica de WhatsApp a Costo Cero:**
   - Al tener presupuesto \$0 COP para el MVP, se debe decidir si se utilizará generación de enlaces directos `wa.me`, librerías web de automatización de WhatsApp, o si se priorizará el canal de correo en el MVP mientras se evalúa presupuesto.
4. **[Pendiente] Modelo de IA y Proveedor:**
   - Elección de modelos para extracción de datos y redacción de correos dentro de las capas gratuitas (ej. Gemini API free tier, Ollama en local, etc.).
5. **[Pendiente] Mecanismo de Autenticación y Sesiones:**
   - Definición del método de autenticación para los 5 usuarios (autenticación local con hashing seguro, JWT, sesiones en base de datos).
6. **[Pendiente] Reglas de negocio de cotización:**
   - Catálogo y normalización de productos, vigencia de las cotizaciones, cálculo del costo puesto en bodega y criterios/pesos para ordenar ofertas.
7. **[Pendiente] Alcance operativo y de contacto del MVP:**
   - Determinar qué parte del flujo será manual, asistida o automatizada en la primera versión, incluido correo y WhatsApp; también las fuentes autorizadas, frecuencia de consulta y condiciones internas para contactar proveedores.
