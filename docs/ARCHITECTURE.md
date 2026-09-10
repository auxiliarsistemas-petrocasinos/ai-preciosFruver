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
| Acceso | Autenticación local implementada; roles simples pendientes |
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
- `auth`: usuarios locales, credenciales Argon2id y sesiones server-side revocables.

Las relaciones implementadas son `PurchaseNeed 1 -> N ProspectingRecord`, `Source 1 -> N ProspectingRecord`, `Provider 1 -> N ProspectingRecord`, `ProspectingRecord 1 -> N CommercialOffer`, `ProspectingRecord 1 -> N Evidence` y `CommercialOffer 1 -> N Evidence`, con proveedor opcional en cada prospección. Una oferta solo puede registrarse mediante la aplicación cuando la prospección tiene proveedor. `CommercialOffer` deriva necesidad, fuente y proveedor de su prospección y no duplica esas relaciones. Cada evidencia pertenece a una prospección o a una oferta, nunca a ambas ni a ninguna, mediante dos claves foráneas y una restricción XOR. Un segundo XOR exige que su representación sea exactamente una URL o un archivo con toda su metadata. No existe una relación global directa entre fuentes y proveedores.

Una fuente no es la referencia concreta que sustenta un hallazgo y una oferta comercial no es su soporte. `Evidence` conserva URLs HTTP/HTTPS registradas manualmente sin acceder a ellas desde el servidor, o un archivo PDF/PNG/JPEG de hasta 20 MiB. Los archivos se copian por chunks, se validan por extensión y firma, y se publican atómicamente bajo una clave UUID opaca relativa a `EVIDENCE_STORAGE_PATH`. Docker Compose monta allí el volumen `evidence_data`; este volumen da persistencia, no backup.

Las descargas validan toda la jerarquía, el destino de `Evidence`, su representación y el containment del archivo regular; no usan `StaticFiles` y siempre fuerzan attachment. Un middleware global fail-closed resuelve primero la cookie opaca contra `UserSession` y `User`, expone una identidad separada de la sesión SQLAlchemy y solo permite anónimamente `GET/POST /login`, `GET /health` y los estáticos. Para HTMX anónimo devuelve `204` con `HX-Redirect`. Este middleware envuelve la capa ASGI que limita multipart, de modo que una carga anónima no consume el body; después se aplican el límite, el parsing y CSRF.

`User` contiene únicamente username canónico, hash de contraseña Argon2id, estado activo y fecha de creación. `UserSession` usa como clave el SHA-256 hexadecimal de un token opaco generado con CSPRNG; el token crudo solo se entrega en la cookie `ai_pf_session`. Cada sesión tiene su propio token CSRF y expiración absoluta de ocho horas. No hay JWT, sesión anónima, idle timeout ni remember-me. Logout revoca la sesión; cambiar contraseña o desactivar mediante CLI revoca todas las sesiones del usuario.

Todo formulario POST autenticado usa synchronizer token con comparación constante. El login, que todavía no tiene sesión, exige `Origin` exacto contra `APP_ORIGIN` o, si falta, el origen exacto de `Referer`. Los destinos `next` se limitan a paths internos seguros. La cookie es de sesión del navegador, `HttpOnly`, `SameSite=Lax`, `Path=/`, sin `Domain`, y adopta `Secure` desde configuración validada. La política provisional otorga el mismo acceso a todo usuario activo autenticado; esto no implementa roles ni auditoría por usuario.

La autenticación no cifra HTTP. `SESSION_COOKIE_SECURE=false` solo es válido para desarrollo HTTP en loopback; cualquier acceso compartido requiere HTTPS y cookie `Secure`. Proxy inverso/HTTPS, matriz de roles, administración web de usuarios, cambio propio/reset de contraseña, MFA, SSO/LDAP, rate limiting robusto, auditoría y `created_by` siguen pendientes.

Los precios, unidades, monedas y condiciones se conservan como fueron capturados, sin conversiones, normalización, comparación ni cálculo de *landed cost*. Antivirus, checksum, otros formatos, previews, cloud storage, edición, reemplazo y eliminación de archivos no forman parte del incremento.

## Aspectos no definidos por esta arquitectura

Esta decisión no fija la fórmula de *landed cost*, las reglas de normalización/equivalencias, el formato de datos históricos, las fuentes iniciales, las especificaciones del servidor ni la política de backup/retención. Esos aspectos requieren validación humana.
