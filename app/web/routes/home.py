"""Página técnica mínima de la interfaz web."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html")


@router.get("/ui/health-status", response_class=HTMLResponse)
async def health_status(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "partials/health-status.html")
