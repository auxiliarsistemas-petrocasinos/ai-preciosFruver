"""Rutas web para registrar y consultar proveedores."""

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import validate_authenticated_csrf
from app.db.session import get_session
from app.providers.models import Provider

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory="app/templates")


def _optional_text(value: str) -> str | None:
    return value.strip() or None


@router.get("/providers", response_class=HTMLResponse)
def provider_list(request: Request, session: Session = Depends(get_session)) -> HTMLResponse:
    providers = session.scalars(
        select(Provider).order_by(Provider.created_at.desc(), Provider.id.desc())
    ).all()
    return templates.TemplateResponse(request, "providers/list.html", {"providers": providers})


@router.get("/providers/new", response_class=HTMLResponse)
def provider_new(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "providers/new.html", {"values": {}, "errors": {}})


@router.post("/providers", response_class=HTMLResponse)
def provider_create(
    request: Request,
    name: str = Form(""),
    contact_name: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    location: str = Form(""),
    notes: str = Form(""),
    csrf_token: str = Form("", alias="_csrf_token"),
    session: Session = Depends(get_session),
) -> Response:
    validate_authenticated_csrf(request, csrf_token)
    values = {
        "name": name,
        "contact_name": contact_name,
        "email": email,
        "phone": phone,
        "location": location,
        "notes": notes,
    }
    cleaned_name = name.strip()
    if not cleaned_name:
        return templates.TemplateResponse(
            request,
            "providers/new.html",
            {"values": values, "errors": {"name": "Este campo es obligatorio."}},
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    provider = Provider(
        name=cleaned_name,
        contact_name=_optional_text(contact_name),
        email=_optional_text(email),
        phone=_optional_text(phone),
        location=_optional_text(location),
        notes=_optional_text(notes),
    )
    session.add(provider)
    session.commit()
    session.refresh(provider)
    return RedirectResponse(f"/providers/{provider.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/providers/{provider_id}", response_class=HTMLResponse)
def provider_detail(
    request: Request, provider_id: int, session: Session = Depends(get_session)
) -> HTMLResponse:
    provider = session.get(Provider, provider_id)
    if provider is None:
        return templates.TemplateResponse(
            request,
            "providers/not_found.html",
            {"provider_id": provider_id},
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return templates.TemplateResponse(request, "providers/detail.html", {"provider": provider})
