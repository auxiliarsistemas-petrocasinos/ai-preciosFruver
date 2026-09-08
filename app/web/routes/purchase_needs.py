"""Rutas web para registrar y consultar necesidades de compra."""

from datetime import date
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.commercial_offers.models import CommercialOffer
from app.db.session import get_session
from app.prospecting.models import ProspectingRecord
from app.providers.models import Provider
from app.purchase_needs.models import PurchaseNeed
from app.sources.models import Source

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory="app/templates")


def _required_text(value: str) -> str | None:
    return value.strip() or None


def _optional_text(value: str) -> str | None:
    return value.strip() or None


def _form_context(values: dict[str, str], errors: dict[str, str]) -> dict[str, object]:
    return {"values": values, "errors": errors}


def _purchase_need_with_prospecting(session: Session, purchase_need_id: int) -> PurchaseNeed | None:
    return session.scalar(
        select(PurchaseNeed)
        .where(PurchaseNeed.id == purchase_need_id)
        .options(
            selectinload(PurchaseNeed.prospecting_records).selectinload(ProspectingRecord.source),
            selectinload(PurchaseNeed.prospecting_records).selectinload(ProspectingRecord.provider),
            selectinload(PurchaseNeed.prospecting_records).selectinload(
                ProspectingRecord.evidence_items
            ),
            selectinload(PurchaseNeed.prospecting_records)
            .selectinload(ProspectingRecord.commercial_offers)
            .selectinload(CommercialOffer.evidence_items),
        )
    )


def _detail_context(
    session: Session,
    purchase_need: PurchaseNeed,
    values: dict[str, str] | None = None,
    errors: dict[str, str] | None = None,
) -> dict[str, object]:
    sources = session.scalars(select(Source).order_by(Source.name, Source.id)).all()
    providers = session.scalars(select(Provider).order_by(Provider.name, Provider.id)).all()
    return {
        "purchase_need": purchase_need,
        "sources": sources,
        "providers": providers,
        "prospecting_values": values or {},
        "prospecting_errors": errors or {},
    }


def _selected_id(value: str) -> int | None:
    try:
        selected_id = int(value)
    except ValueError:
        return None
    return selected_id if selected_id > 0 else None


@router.get("/purchase-needs", response_class=HTMLResponse)
def purchase_need_list(request: Request, session: Session = Depends(get_session)) -> HTMLResponse:
    purchase_needs = session.scalars(
        select(PurchaseNeed).order_by(PurchaseNeed.created_at.desc(), PurchaseNeed.id.desc())
    ).all()
    return templates.TemplateResponse(
        request, "purchase_needs/list.html", {"purchase_needs": purchase_needs}
    )


@router.get("/purchase-needs/new", response_class=HTMLResponse)
def purchase_need_new(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "purchase_needs/new.html", _form_context({}, {}))


@router.post("/purchase-needs", response_class=HTMLResponse)
def purchase_need_create(
    request: Request,
    product_name: str = Form(""),
    variety: str = Form(""),
    quality_standard: str = Form(""),
    quantity: str = Form(""),
    unit_of_measure: str = Form(""),
    required_delivery_date: str = Form(""),
    destination_city: str = Form(""),
    destination_location: str = Form(""),
    session: Session = Depends(get_session),
) -> Response:
    values = {
        "product_name": product_name,
        "variety": variety,
        "quality_standard": quality_standard,
        "quantity": quantity,
        "unit_of_measure": unit_of_measure,
        "required_delivery_date": required_delivery_date,
        "destination_city": destination_city,
        "destination_location": destination_location,
    }
    errors: dict[str, str] = {}
    required_fields = {
        "product_name": product_name,
        "unit_of_measure": unit_of_measure,
        "required_delivery_date": required_delivery_date,
        "destination_city": destination_city,
        "destination_location": destination_location,
    }
    cleaned_fields = {name: _required_text(value) for name, value in required_fields.items()}
    for field_name, value in cleaned_fields.items():
        if value is None:
            errors[field_name] = "Este campo es obligatorio."

    try:
        parsed_quantity = Decimal(quantity)
        if not parsed_quantity.is_finite() or parsed_quantity <= 0:
            raise InvalidOperation
    except InvalidOperation:
        errors["quantity"] = "Ingrese una cantidad numérica mayor que cero."
        parsed_quantity = None

    try:
        parsed_delivery_date = date.fromisoformat(required_delivery_date)
    except ValueError:
        errors["required_delivery_date"] = "Ingrese una fecha válida."
        parsed_delivery_date = None

    if errors:
        return templates.TemplateResponse(
            request,
            "purchase_needs/new.html",
            _form_context(values, errors),
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    purchase_need = PurchaseNeed(
        product_name=cleaned_fields["product_name"],
        variety=_optional_text(variety),
        quality_standard=_optional_text(quality_standard),
        quantity=parsed_quantity,
        unit_of_measure=cleaned_fields["unit_of_measure"],
        required_delivery_date=parsed_delivery_date,
        destination_city=cleaned_fields["destination_city"],
        destination_location=cleaned_fields["destination_location"],
    )
    session.add(purchase_need)
    session.commit()
    session.refresh(purchase_need)
    return RedirectResponse(
        f"/purchase-needs/{purchase_need.id}", status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/purchase-needs/{purchase_need_id}", response_class=HTMLResponse)
def purchase_need_detail(
    request: Request, purchase_need_id: int, session: Session = Depends(get_session)
) -> HTMLResponse:
    purchase_need = _purchase_need_with_prospecting(session, purchase_need_id)
    if purchase_need is None:
        return templates.TemplateResponse(
            request,
            "purchase_needs/not_found.html",
            {"purchase_need_id": purchase_need_id},
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return templates.TemplateResponse(
        request, "purchase_needs/detail.html", _detail_context(session, purchase_need)
    )


@router.post("/purchase-needs/{purchase_need_id}/prospecting-records", response_class=HTMLResponse)
def prospecting_record_create(
    request: Request,
    purchase_need_id: int,
    source_id: str = Form(""),
    provider_id: str = Form(""),
    notes: str = Form(""),
    session: Session = Depends(get_session),
) -> Response:
    purchase_need = _purchase_need_with_prospecting(session, purchase_need_id)
    if purchase_need is None:
        return templates.TemplateResponse(
            request,
            "purchase_needs/not_found.html",
            {"purchase_need_id": purchase_need_id},
            status_code=status.HTTP_404_NOT_FOUND,
        )

    values = {"source_id": source_id, "provider_id": provider_id, "notes": notes}
    errors: dict[str, str] = {}
    parsed_source_id = _selected_id(source_id)
    parsed_provider_id = _selected_id(provider_id)

    source = session.get(Source, parsed_source_id) if parsed_source_id is not None else None
    if source is None:
        errors["source_id"] = "Seleccione una fuente existente."

    provider = session.get(Provider, parsed_provider_id) if parsed_provider_id is not None else None
    if provider_id.strip() and provider is None:
        errors["provider_id"] = "Seleccione un proveedor existente o deje el campo vacío."

    if errors:
        return templates.TemplateResponse(
            request,
            "purchase_needs/detail.html",
            _detail_context(session, purchase_need, values, errors),
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    prospecting_record = ProspectingRecord(
        purchase_need_id=purchase_need.id,
        source_id=source.id,
        provider_id=provider.id if provider is not None else None,
        notes=_optional_text(notes),
    )
    session.add(prospecting_record)
    session.commit()
    return RedirectResponse(
        f"/purchase-needs/{purchase_need.id}", status_code=status.HTTP_303_SEE_OTHER
    )
