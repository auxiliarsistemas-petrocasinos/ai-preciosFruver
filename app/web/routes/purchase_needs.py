"""Rutas web para registrar y consultar necesidades de compra."""

from datetime import date
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.purchase_needs.models import PurchaseNeed

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory="app/templates")


def _required_text(value: str) -> str | None:
    return value.strip() or None


def _optional_text(value: str) -> str | None:
    return value.strip() or None


def _form_context(values: dict[str, str], errors: dict[str, str]) -> dict[str, object]:
    return {"values": values, "errors": errors}


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
    purchase_need = session.get(PurchaseNeed, purchase_need_id)
    if purchase_need is None:
        return templates.TemplateResponse(
            request,
            "purchase_needs/not_found.html",
            {"purchase_need_id": purchase_need_id},
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return templates.TemplateResponse(
        request, "purchase_needs/detail.html", {"purchase_need": purchase_need}
    )
