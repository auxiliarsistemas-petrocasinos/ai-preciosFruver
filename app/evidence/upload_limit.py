"""Límite de cuerpo ASGI aplicado exclusivamente a uploads de evidencia."""

import re

from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.evidence.storage import MAX_FILE_SIZE

# Deja espacio acotado para boundary y los cuatro campos de texto del multipart (incluido CSRF).
MAX_UPLOAD_REQUEST_SIZE = MAX_FILE_SIZE + 64 * 1024

_UPLOAD_PATH = re.compile(
    r"^/purchase-needs/\d+/prospecting-records/\d+/(?:"
    r"evidence/files|commercial-offers/\d+/evidence/files)$"
)


class _RequestBodyTooLarge(Exception):
    pass


class EvidenceUploadBodyLimitMiddleware:
    """Rechaza por cabecera y por bytes reales sin afectar otras rutas."""

    def __init__(self, app: ASGIApp, max_body_size: int = MAX_UPLOAD_REQUEST_SIZE) -> None:
        self.app = app
        self.max_body_size = max_body_size

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] != "http"
            or scope.get("method") != "POST"
            or not _UPLOAD_PATH.fullmatch(scope.get("path", ""))
        ):
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        content_length = headers.get(b"content-length")
        if content_length is not None:
            try:
                declared_size = int(content_length)
            except ValueError:
                declared_size = 0
            if declared_size > self.max_body_size:
                await self._reject(scope, receive, send)
                return

        received_size = 0
        response_started = False

        async def limited_receive() -> Message:
            nonlocal received_size
            message = await receive()
            if message["type"] == "http.request":
                received_size += len(message.get("body", b""))
                if received_size > self.max_body_size:
                    raise _RequestBodyTooLarge
            return message

        async def tracked_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracked_send)
        except _RequestBodyTooLarge:
            if response_started:
                raise
            await self._reject(scope, receive, send)

    @staticmethod
    async def _reject(scope: Scope, receive: Receive, send: Send) -> None:
        response = PlainTextResponse("El cuerpo de la carga es demasiado grande.", status_code=413)
        await response(scope, receive, send)
