"""Rutas web para registrar ofertas comerciales de una prospección."""

from datetime import date
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth.security import validate_authenticated_csrf
from app.commercial_offers.models import CommercialOffer
from app.db.session import get_session
from app.prospecting.models import ProspectingRecord
from app.purchase_needs.models import PurchaseNeed

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory="app/templates")


def _optional_text(value: str) -> str | None:
    return value.strip() or None


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


def _context(
    purchase_need: PurchaseNeed,
    prospecting_record: ProspectingRecord,
    values: dict[str, str] | None = None,
    errors: dict[str, str] | None = None,
) -> dict[str, object]:
    return {
        "purchase_need": purchase_need,
        "prospecting_record": prospecting_record,
        "values": values or {},
        "errors": errors or {},
    }


def _resolve_context(
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

    if prospecting_record.provider is None:
        response = templates.TemplateResponse(
            request,
            "commercial_offers/provider_required.html",
            _context(purchase_need, prospecting_record),
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
        return purchase_need, prospecting_record, response

    return purchase_need, prospecting_record, None


@router.get(
    "/purchase-needs/{purchase_need_id}/prospecting-records/"
    "{prospecting_record_id}/commercial-offers/new",
    response_class=HTMLResponse,
)
def commercial_offer_new(
    request: Request,
    purchase_need_id: int,
    prospecting_record_id: int,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    purchase_need, prospecting_record, error_response = _resolve_context(
        request, session, purchase_need_id, prospecting_record_id
    )
    if error_response is not None:
        return error_response
    assert purchase_need is not None
    assert prospecting_record is not None
    return templates.TemplateResponse(
        request,
        "commercial_offers/new.html",
        _context(purchase_need, prospecting_record),
    )


@router.post(
    "/purchase-needs/{purchase_need_id}/prospecting-records/"
    "{prospecting_record_id}/commercial-offers",
    response_class=HTMLResponse,
)
def commercial_offer_create(
    request: Request,
    purchase_need_id: int,
    prospecting_record_id: int,
    price_amount: str = Form(""),
    price_unit: str = Form(""),
    currency: str = Form(""),
    obtained_on: str = Form(""),
    offered_description: str = Form(""),
    conditions: str = Form(""),
    csrf_token: str = Form("", alias="_csrf_token"),
    session: Session = Depends(get_session),
) -> Response:
    validate_authenticated_csrf(request, csrf_token)
    purchase_need, prospecting_record, error_response = _resolve_context(
        request, session, purchase_need_id, prospecting_record_id
    )
    if error_response is not None:
        return error_response
    assert purchase_need is not None
    assert prospecting_record is not None

    values = {
        "price_amount": price_amount,
        "price_unit": price_unit,
        "currency": currency,
        "obtained_on": obtained_on,
        "offered_description": offered_description,
        "conditions": conditions,
    }
    errors: dict[str, str] = {}

    try:
        parsed_price_amount = Decimal(price_amount)
        if not parsed_price_amount.is_finite() or parsed_price_amount <= 0:
            raise InvalidOperation
    except InvalidOperation:
        errors["price_amount"] = "Ingrese un precio numérico mayor que cero."
        parsed_price_amount = None

    cleaned_price_unit = price_unit.strip()
    if not cleaned_price_unit:
        errors["price_unit"] = "Este campo es obligatorio."

    cleaned_currency = currency.strip()
    if not cleaned_currency:
        errors["currency"] = "Este campo es obligatorio."

    try:
        parsed_obtained_on = date.fromisoformat(obtained_on)
    except ValueError:
        errors["obtained_on"] = "Ingrese una fecha válida."
        parsed_obtained_on = None

    if errors:
        return templates.TemplateResponse(
            request,
            "commercial_offers/new.html",
            _context(purchase_need, prospecting_record, values, errors),
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    commercial_offer = CommercialOffer(
        prospecting_record_id=prospecting_record.id,
        price_amount=parsed_price_amount,
        price_unit=cleaned_price_unit,
        currency=cleaned_currency,
        obtained_on=parsed_obtained_on,
        offered_description=_optional_text(offered_description),
        conditions=_optional_text(conditions),
    )
    session.add(commercial_offer)
    session.commit()
    return RedirectResponse(
        f"/purchase-needs/{purchase_need.id}", status_code=status.HTTP_303_SEE_OTHER
    )
