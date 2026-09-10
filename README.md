# ai-preciosFruver

Sistema inteligente de búsqueda, prospección y cotización de materias primas y productos agrícolas/fruver para optimización de costos de compra empresarial.

---

## 🎯 Objetivo

Reducir los costos de materias primas e insumos adquiridos por la empresa, apoyando la investigación, captura y comparación verificable de alternativas de proveedores a nivel nacional. La comparación contempla el concepto de **producto entregado en la puerta de la bodega** (*landed cost*), cuya fórmula permanece pendiente de validación operativa.

---

## 🏢 Contexto y Alcance

- **Uso:** Interno empresarial.
- **Usuarios iniciales:** ~5 personas (equipo de compras y administración). El número de usuarios concurrentes aún no se ha definido.
- **Entorno de ejecución:** Desarrollo en máquina local; versión productiva/presentable en servidor propio (*on-premise*) de la empresa.
- **Presupuesto inicial:** $0 COP de gasto nuevo para la fase de MVP. Esto presupone el uso de recursos locales o internos ya disponibles; la viabilidad y condiciones de las capas gratuitas externas siguen por validar.

---

## 📂 Documentación del Proyecto

El diseño y alcance del sistema se encuentra detallado en la carpeta [`docs/`](docs/):

- **[`docs/PROJECT.md`](docs/PROJECT.md):** Definición completa del problema, requerimientos de negocio, variables logísticas, datos requeridos y preguntas abiertas.
- **[`docs/ROADMAP.md`](docs/ROADMAP.md):** Plan de evolución organizado en **Now** (MVP), **Next** (Fase 2) y **Later** (Fase 3).
- **[`docs/DECISIONS.md`](docs/DECISIONS.md):** Registro de decisiones tomadas explícitamente y decisiones pendientes por resolver.
- **[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md):** Arquitectura técnica aceptada para el MVP.
- **[`docs/STATUS.md`](docs/STATUS.md):** Estado de definición, validaciones humanas pendientes y exclusiones del MVP.

---

## 📌 Estado Actual

Existe un incremento funcional del monolito: FastAPI, Jinja2, HTMX, configuración por entorno, Docker Compose con PostgreSQL y almacenamiento persistente de evidencias. Incluye persistencia síncrona y migraciones Alembic para registrar y consultar necesidades de compra, fuentes y proveedores, asociar prospecciones manuales a cada necesidad con proveedor opcional, capturar múltiples ofertas comerciales cuando la prospección identifica un proveedor y registrar evidencias URL o archivos PDF, PNG y JPEG para una prospección o una oferta. Toda capacidad no pública está protegida por autenticación local, sesión revocable y CSRF.

## Ejecución local

Requiere Python 3.13 o superior.

1. Cree el archivo de entorno: `cp .env.example .env`.
2. En `.env`, sustituya `POSTGRES_PASSWORD` y mantenga `DATABASE_URL` coherente con esos valores.
3. Cree y active un entorno virtual, e instale las dependencias de desarrollo: `python3 -m venv .venv`, `source .venv/bin/activate` y `python -m pip install -e '.[dev]'`.
4. Cargue las variables: `set -a; source .env; set +a`.
5. Ejecute `python -m alembic upgrade head` y cree el primer usuario con `python -m app.auth.cli create-user <username>`; la contraseña y su confirmación se solicitan de forma oculta.
6. Inicie con `uvicorn app.main:app --reload`, abra `http://127.0.0.1:8000/` e inicie sesión. El estado técnico público está disponible en `http://127.0.0.1:8000/health`.

Para ejecutar los servicios en contenedores, después de crear `.env` use `docker compose up --build -d`, aplique migraciones con `docker compose exec app python -m alembic upgrade head` y cree el primer usuario con `docker compose exec app python -m app.auth.cli create-user <username>`. La aplicación quedará disponible en `http://127.0.0.1:8000/`. Docker Compose conserva PostgreSQL y los archivos de evidencia en volúmenes con nombre separados. El servicio monta `evidence_data` y entrega a la aplicación exactamente la misma ruta interna, `/var/lib/ai-precios-fruver/evidence`.

Cada carga admite un solo PDF, PNG, JPG o JPEG de máximo 20 MiB. El servidor valida la extensión y la firma inicial, deriva el tipo de medio del contenido, genera una clave opaca y copia por bloques antes de publicar el archivo sin sobrescritura. La descarga pasa por rutas controladas y siempre responde como adjunto con `nosniff` y sin caché privada reutilizable.

Un volumen persistente no es un backup. Las políticas de respaldo y retención, antivirus, checksum, previews, edición, reemplazo y eliminación continúan pendientes. La jerarquía de IDs de las rutas no es un control de acceso; la autenticación global debe ejecutarse antes de acceder a datos o archivos.

## Autenticación y operación segura

Los usernames se almacenan en minúsculas después de eliminar espacios exteriores y las contraseñas se guardan únicamente como Argon2id. La cookie `ai_pf_session` contiene un token opaco; PostgreSQL conserva solo su SHA-256, el token CSRF de la sesión y una expiración absoluta de ocho horas. El logout, el cambio administrativo de contraseña y la desactivación revocan las sesiones correspondientes. Todo usuario local activo autenticado puede acceder provisionalmente a todas las capacidades actuales; la matriz de roles todavía no está implementada.

La CLI administrativa disponible es:

```bash
python -m app.auth.cli create-user <username>
python -m app.auth.cli set-password <username>
python -m app.auth.cli deactivate-user <username>
python -m app.auth.cli activate-user <username>
```

`APP_ORIGIN` es el origen exacto permitido para el login. `SESSION_COOKIE_SECURE=false` solo se acepta con HTTP en `localhost`, `127.0.0.1` o `::1`. Cualquier acceso compartido o desde otro equipo exige `APP_ORIGIN=https://...`, `SESSION_COOKIE_SECURE=true` y un proxy HTTPS. La autenticación no convierte HTTP en un transporte seguro; el proxy/HTTPS productivo sigue pendiente.

## Migraciones y URL de PostgreSQL

La imagen de `app` incluye Alembic y los archivos de migración. Con Docker Compose activo, ejecute las migraciones desde ese mismo contexto de red:

```bash
docker compose exec app python -m alembic upgrade head
docker compose exec app python -m alembic current
```

Dentro de Docker Compose, el servicio `app` recibe automáticamente una `DATABASE_URL` con el dialecto de psycopg 3 y el host interno `db`:

```text
postgresql+psycopg://usuario:contraseña@db:5432/base_de_datos
```

Para ejecutar la aplicación o Alembic directamente desde WSL, use `localhost` porque el nombre `db` solo existe en la red de Compose. El puerto se publica mediante `POSTGRES_PORT` (por defecto `5432`):

```text
postgresql+psycopg://usuario:contraseña@localhost:5432/base_de_datos
```

Por ejemplo, después de cargar `.env`, puede ejecutar `python -m alembic upgrade head` desde WSL mientras los servicios de Compose estén activos.

## Validaciones

Tras instalar las dependencias de desarrollo:

```bash
ruff check .
ruff format --check .
pytest
```
