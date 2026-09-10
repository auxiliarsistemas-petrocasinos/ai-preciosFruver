"""Rutas web para registrar y consultar fuentes de prospección."""

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import validate_authenticated_csrf
from app.db.session import get_session
from app.sources.models import Source

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory="app/templates")


def _optional_text(value: str) -> str | None:
    return value.strip() or None


@router.get("/sources", response_class=HTMLResponse)
def source_list(request: Request, session: Session = Depends(get_session)) -> HTMLResponse:
    sources = session.scalars(
        select(Source).order_by(Source.created_at.desc(), Source.id.desc())
    ).all()
    return templates.TemplateResponse(request, "sources/list.html", {"sources": sources})


@router.get("/sources/new", response_class=HTMLResponse)
def source_new(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "sources/new.html", {"values": {}, "errors": {}})


@router.post("/sources", response_class=HTMLResponse)
def source_create(
    request: Request,
    name: str = Form(""),
    reference: str = Form(""),
    notes: str = Form(""),
    csrf_token: str = Form("", alias="_csrf_token"),
    session: Session = Depends(get_session),
) -> Response:
    validate_authenticated_csrf(request, csrf_token)
    values = {"name": name, "reference": reference, "notes": notes}
    cleaned_name = name.strip()
    if not cleaned_name:
        return templates.TemplateResponse(
            request,
            "sources/new.html",
            {"values": values, "errors": {"name": "Este campo es obligatorio."}},
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    source = Source(
        name=cleaned_name,
        reference=_optional_text(reference),
        notes=_optional_text(notes),
    )
    session.add(source)
    session.commit()
    session.refresh(source)
    return RedirectResponse(f"/sources/{source.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/sources/{source_id}", response_class=HTMLResponse)
def source_detail(
    request: Request, source_id: int, session: Session = Depends(get_session)
) -> HTMLResponse:
    source = session.get(Source, source_id)
    if source is None:
        return templates.TemplateResponse(
            request,
            "sources/not_found.html",
            {"source_id": source_id},
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return templates.TemplateResponse(request, "sources/detail.html", {"source": source})
