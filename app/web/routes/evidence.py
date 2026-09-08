"""Rutas web para registrar referencias de evidencia."""

from datetime import date
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.commercial_offers.models import CommercialOffer
from app.db.session import get_session
from app.evidence.models import Evidence
from app.prospecting.models import ProspectingRecord
from app.purchase_needs.models import PurchaseNeed

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory="app/templates")


def _optional_text(value: str) -> str | None:
    return value.strip() or None


def _valid_http_url(value: str) -> bool:
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme.lower() in {"http", "https"}
        and hostname is not None
        and not any(character.isspace() for character in parsed.netloc)
    )


def _prospecting_record(
    session: Session, purchase_need_id: int, prospecting_record_id: int
) -> ProspectingRecord | None:
    return session.scalar(
        select(ProspectingRecord)
        .where(
            ProspectingRecord.id == prospecting_record_id,
            ProspectingRecord.purchase_need_id == purchase_need_id,
        )
        .options(
            selectinload(ProspectingRecord.source),
            selectinload(ProspectingRecord.provider),
        )
    )


def _resolve_prospecting_context(
    request: Request,
    session: Session,
    purchase_need_id: int,
    prospecting_record_id: int,
) -> tuple[PurchaseNeed | None, ProspectingRecord | None, HTMLResponse | None]:
    purchase_need = session.get(PurchaseNeed, purchase_need_id)
    if purchase_need is None:
        response = templates.TemplateResponse(
            request,
            "purchase_needs/not_found.html",
            {"purchase_need_id": purchase_need_id},
            status_code=status.HTTP_404_NOT_FOUND,
        )
        return None, None, response

    prospecting_record = _prospecting_record(session, purchase_need_id, prospecting_record_id)
    if prospecting_record is None:
        response = templates.TemplateResponse(
            request,
            "commercial_offers/prospecting_not_found.html",
            {
                "purchase_need": purchase_need,
                "prospecting_record_id": prospecting_record_id,
            },
            status_code=status.HTTP_404_NOT_FOUND,
        )
        return purchase_need, None, response

    return purchase_need, prospecting_record, None


def _resolve_offer_context(
    request: Request,
    session: Session,
    purchase_need_id: int,
    prospecting_record_id: int,
    commercial_offer_id: int,
) -> tuple[
    PurchaseNeed | None,
    ProspectingRecord | None,
    CommercialOffer | None,
    HTMLResponse | None,
]:
    purchase_need, prospecting_record, error_response = _resolve_prospecting_context(
        request, session, purchase_need_id, prospecting_record_id
    )
    if error_response is not None:
        return purchase_need, prospecting_record, None, error_response
    assert purchase_need is not None
    assert prospecting_record is not None

    commercial_offer = session.scalar(
        select(CommercialOffer).where(
            CommercialOffer.id == commercial_offer_id,
            CommercialOffer.prospecting_record_id == prospecting_record.id,
        )
    )
    if commercial_offer is None:
        response = templates.TemplateResponse(
            request,
            "evidence/commercial_offer_not_found.html",
            {
                "purchase_need": purchase_need,
                "commercial_offer_id": commercial_offer_id,
            },
            status_code=status.HTTP_404_NOT_FOUND,
        )
        return purchase_need, prospecting_record, None, response

    return purchase_need, prospecting_record, commercial_offer, None


def _form_context(
    purchase_need: PurchaseNeed,
    prospecting_record: ProspectingRecord,
    action: str,
    commercial_offer: CommercialOffer | None = None,
    values: dict[str, str] | None = None,
    errors: dict[str, str] | None = None,
) -> dict[str, object]:
    return {
        "purchase_need": purchase_need,
        "prospecting_record": prospecting_record,
        "commercial_offer": commercial_offer,
        "action": action,
        "values": values or {},
        "errors": errors or {},
    }


def _create_evidence(
    request: Request,
    session: Session,
    purchase_need: PurchaseNeed,
    prospecting_record: ProspectingRecord,
    action: str,
    title: str,
    url: str,
    captured_on: str,
    notes: str,
    commercial_offer: CommercialOffer | None = None,
) -> Response:
    values = {
        "title": title,
        "url": url,
        "captured_on": captured_on,
        "notes": notes,
    }
    errors: dict[str, str] = {}

    cleaned_title = title.strip()
    if not cleaned_title:
        errors["title"] = "Este campo es obligatorio."

    cleaned_url = url.strip()
    if not cleaned_url:
        errors["url"] = "Este campo es obligatorio."
    elif not _valid_http_url(cleaned_url):
        errors["url"] = "Ingrese una URL absoluta con esquema http o https y un host válido."

    try:
        parsed_captured_on = date.fromisoformat(captured_on)
    except ValueError:
        errors["captured_on"] = "Ingrese una fecha válida."
        parsed_captured_on = None

    if errors:
        return templates.TemplateResponse(
            request,
            "evidence/new.html",
            _form_context(
                purchase_need,
                prospecting_record,
                action,
                commercial_offer,
                values,
                errors,
            ),
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    evidence = Evidence(
        prospecting_record_id=prospecting_record.id if commercial_offer is None else None,
        commercial_offer_id=commercial_offer.id if commercial_offer is not None else None,
        title=cleaned_title,
        url=cleaned_url,
        captured_on=parsed_captured_on,
        notes=_optional_text(notes),
    )
    session.add(evidence)
    session.commit()
    return RedirectResponse(
        f"/purchase-needs/{purchase_need.id}", status_code=status.HTTP_303_SEE_OTHER
    )


@router.get(
    "/purchase-needs/{purchase_need_id}/prospecting-records/{prospecting_record_id}/evidence/new",
    response_class=HTMLResponse,
)
def prospecting_evidence_new(
    request: Request,
    purchase_need_id: int,
    prospecting_record_id: int,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    purchase_need, prospecting_record, error_response = _resolve_prospecting_context(
        request, session, purchase_need_id, prospecting_record_id
    )
    if error_response is not None:
        return error_response
    assert purchase_need is not None
    assert prospecting_record is not None
    action = (
        f"/purchase-needs/{purchase_need.id}/prospecting-records/{prospecting_record.id}/evidence"
    )
    return templates.TemplateResponse(
        request,
        "evidence/new.html",
        _form_context(purchase_need, prospecting_record, action),
    )


@router.post(
    "/purchase-needs/{purchase_need_id}/prospecting-records/{prospecting_record_id}/evidence",
    response_class=HTMLResponse,
)
def prospecting_evidence_create(
    request: Request,
    purchase_need_id: int,
    prospecting_record_id: int,
    title: str = Form(""),
    url: str = Form(""),
    captured_on: str = Form(""),
    notes: str = Form(""),
    session: Session = Depends(get_session),
) -> Response:
    purchase_need, prospecting_record, error_response = _resolve_prospecting_context(
        request, session, purchase_need_id, prospecting_record_id
    )
    if error_response is not None:
        return error_response
    assert purchase_need is not None
    assert prospecting_record is not None
    action = (
        f"/purchase-needs/{purchase_need.id}/prospecting-records/{prospecting_record.id}/evidence"
    )
    return _create_evidence(
        request,
        session,
        purchase_need,
        prospecting_record,
        action,
        title,
        url,
        captured_on,
        notes,
    )


@router.get(
    "/purchase-needs/{purchase_need_id}/prospecting-records/{prospecting_record_id}/"
    "commercial-offers/{commercial_offer_id}/evidence/new",
    response_class=HTMLResponse,
)
def commercial_offer_evidence_new(
    request: Request,
    purchase_need_id: int,
    prospecting_record_id: int,
    commercial_offer_id: int,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    purchase_need, prospecting_record, commercial_offer, error_response = _resolve_offer_context(
        request,
        session,
        purchase_need_id,
        prospecting_record_id,
        commercial_offer_id,
    )
    if error_response is not None:
        return error_response
    assert purchase_need is not None
    assert prospecting_record is not None
    assert commercial_offer is not None
    action = (
        f"/purchase-needs/{purchase_need.id}/prospecting-records/{prospecting_record.id}/"
        f"commercial-offers/{commercial_offer.id}/evidence"
    )
    return templates.TemplateResponse(
        request,
        "evidence/new.html",
        _form_context(purchase_need, prospecting_record, action, commercial_offer),
    )


@router.post(
    "/purchase-needs/{purchase_need_id}/prospecting-records/{prospecting_record_id}/"
    "commercial-offers/{commercial_offer_id}/evidence",
    response_class=HTMLResponse,
)
def commercial_offer_evidence_create(
    request: Request,
    purchase_need_id: int,
    prospecting_record_id: int,
    commercial_offer_id: int,
    title: str = Form(""),
    url: str = Form(""),
    captured_on: str = Form(""),
    notes: str = Form(""),
    session: Session = Depends(get_session),
) -> Response:
    purchase_need, prospecting_record, commercial_offer, error_response = _resolve_offer_context(
        request,
        session,
        purchase_need_id,
        prospecting_record_id,
        commercial_offer_id,
    )
    if error_response is not None:
        return error_response
    assert purchase_need is not None
    assert prospecting_record is not None
    assert commercial_offer is not None
    action = (
        f"/purchase-needs/{purchase_need.id}/prospecting-records/{prospecting_record.id}/"
        f"commercial-offers/{commercial_offer.id}/evidence"
    )
    return _create_evidence(
        request,
        session,
        purchase_need,
        prospecting_record,
        action,
        title,
        url,
        captured_on,
        notes,
        commercial_offer,
    )
