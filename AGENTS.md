# Guía para agentes — ai-preciosFruver

## Propósito del MVP

Aplicación interna para que compras registre necesidades, fuentes, proveedores, alternativas, cotizaciones y evidencias, y compare opciones frente a un *benchmark*. La captura es manual, asistida y verificable; compras conserva la evaluación y aprobación final. El objetivo es reducir costos de compra, considerando el concepto de *landed cost* sin asumir una fórmula todavía.

## Stack y arquitectura decididos

- Monolito modular: Python, FastAPI, Jinja2, HTMX y PostgreSQL.
- Docker Compose; almacenamiento persistente de evidencias; autenticación local, roles simples y HTTPS mediante proxy inverso.
- Desarrollo local y despliegue interno *on-premise*.

## Fuentes de verdad (en orden)

1. Código y configuración existentes, cuando existan.
2. Este `AGENTS.md`.
3. `docs/`.

## Reglas obligatorias

- Mantén el alcance del MVP manual, asistido, trazable y con decisión humana de compras.
- No inventes ni implementes como hechos las decisiones pendientes: fórmula de *landed cost*, normalización/equivalencias, datos históricos, fuentes iniciales, infraestructura, backup/retención, matriz de roles y reglas de evaluación.
- No añadas IA, *scraping* automático, conectores automáticos, agentes autónomos, ERP, pagos, órdenes de compra, automatización completa de RFQ ni microservicios sin una decisión explícita.
- No guardes secretos, credenciales ni archivos sensibles en Git.
- No inventes comandos de validación; usa solo los que existan en el repositorio o estén documentados.
- Cuando un cambio afecte de verdad su contenido, actualiza `docs/STATUS.md`, `docs/ARCHITECTURE.md`, `docs/DECISIONS.md` y `docs/ROADMAP.md`.

## Fuera del MVP

IA, *scraping* universal, automatizaciones y conectores de proveedores, agentes autónomos, RFQ completamente automatizada, ERP, órdenes de compra, pagos y microservicios.
