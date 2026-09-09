"""Rutas web para registrar y descargar evidencias URL o de archivo."""

from datetime import date
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import FormData, UploadFile
from starlette.exceptions import HTTPException

from app.commercial_offers.models import CommercialOffer
from app.db.session import get_session
from app.evidence.models import Evidence
from app.evidence.storage import (
    EvidenceFileError,
    EvidenceFileTooLarge,
    delete_stored_file,
    resolve_stored_file,
    store_upload,
    validate_original_filename,
)
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


def _file_form_response(
    request: Request,
    purchase_need: PurchaseNeed,
    prospecting_record: ProspectingRecord,
    action: str,
    commercial_offer: CommercialOffer | None,
    values: dict[str, str],
    errors: dict[str, str],
    status_code: int = status.HTTP_422_UNPROCESSABLE_CONTENT,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "evidence/new_file.html",
        _form_context(
            purchase_need,
            prospecting_record,
            action,
            commercial_offer,
            values,
            errors,
        ),
        status_code=status_code,
    )


def _text_field(form: FormData, name: str) -> str:
    value = form.get(name, "")
    return value if isinstance(value, str) else ""


def _validate_file_form(
    title: str,
    captured_on: str,
    upload: UploadFile | None,
) -> tuple[dict[str, str], str, date | None]:
    errors: dict[str, str] = {}
    cleaned_title = title.strip()
    if not cleaned_title:
        errors["title"] = "Este campo es obligatorio."

    try:
        parsed_captured_on = date.fromisoformat(captured_on)
    except ValueError:
        errors["captured_on"] = "Ingrese una fecha válida."
        parsed_captured_on = None

    if upload is None:
        errors["file"] = "Seleccione un archivo."
    else:
        try:
            validate_original_filename(upload.filename)
        except EvidenceFileError as exc:
            errors["file"] = str(exc)
    return errors, cleaned_title, parsed_captured_on


async def _create_file_evidence(
    request: Request,
    session: Session,
    purchase_need: PurchaseNeed,
    prospecting_record: ProspectingRecord,
    action: str,
    commercial_offer: CommercialOffer | None = None,
) -> Response:
    try:
        async with request.form(max_files=1, max_fields=3, max_part_size=64 * 1024) as form:
            title = _text_field(form, "title")
            captured_on = _text_field(form, "captured_on")
            notes = _text_field(form, "notes")
            values = {"title": title, "captured_on": captured_on, "notes": notes}
            file_value = form.get("file")
            upload = file_value if isinstance(file_value, UploadFile) else None
            errors, cleaned_title, parsed_captured_on = _validate_file_form(
                title, captured_on, upload
            )
            if errors:
                return _file_form_response(
                    request,
                    purchase_need,
                    prospecting_record,
                    action,
                    commercial_offer,
                    values,
                    errors,
                )

            assert upload is not None
            assert parsed_captured_on is not None
            try:
                stored = await run_in_threadpool(
                    store_upload,
                    request.app.state.evidence_storage_path,
                    upload.file,
                    upload.filename,
                )
            except EvidenceFileTooLarge as exc:
                return _file_form_response(
                    request,
                    purchase_need,
                    prospecting_record,
                    action,
                    commercial_offer,
                    values,
                    {"file": str(exc)},
                    status.HTTP_413_CONTENT_TOO_LARGE,
                )
            except EvidenceFileError as exc:
                return _file_form_response(
                    request,
                    purchase_need,
                    prospecting_record,
                    action,
                    commercial_offer,
                    values,
                    {"file": str(exc)},
                )
    except HTTPException as exc:
        if exc.status_code != status.HTTP_400_BAD_REQUEST:
            raise
        return _file_form_response(
            request,
            purchase_need,
            prospecting_record,
            action,
            commercial_offer,
            {},
            {"file": "Envíe exactamente un archivo y solo los campos del formulario."},
        )

    evidence = Evidence(
        prospecting_record_id=prospecting_record.id if commercial_offer is None else None,
        commercial_offer_id=commercial_offer.id if commercial_offer is not None else None,
        title=cleaned_title,
        url=None,
        storage_key=stored.storage_key,
        original_filename=stored.original_filename,
        media_type=stored.media_type,
        file_size=stored.file_size,
        captured_on=parsed_captured_on,
        notes=_optional_text(notes),
    )
    try:
        session.add(evidence)
        session.commit()
    except Exception:
        session.rollback()
        delete_stored_file(request.app.state.evidence_storage_path, stored.storage_key)
        raise
    return RedirectResponse(
        f"/purchase-needs/{purchase_need.id}", status_code=status.HTTP_303_SEE_OTHER
    )


def _evidence_not_found(
    request: Request, purchase_need: PurchaseNeed, evidence_id: int
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "evidence/not_found.html",
        {"purchase_need": purchase_need, "evidence_id": evidence_id},
        status_code=status.HTTP_404_NOT_FOUND,
    )


def _download_response(
    request: Request,
    purchase_need: PurchaseNeed,
    evidence: Evidence | None,
    evidence_id: int,
) -> Response:
    allowed_media_types = {"application/pdf", "image/png", "image/jpeg"}
    if (
        evidence is None
        or evidence.url is not None
        or evidence.storage_key is None
        or evidence.original_filename is None
        or evidence.media_type not in allowed_media_types
        or evidence.file_size is None
        or evidence.file_size <= 0
    ):
        return _evidence_not_found(request, purchase_need, evidence_id)
    try:
        _, _, expected_media_type = validate_original_filename(evidence.original_filename)
        if expected_media_type != evidence.media_type:
            return _evidence_not_found(request, purchase_need, evidence_id)
        path = resolve_stored_file(request.app.state.evidence_storage_path, evidence.storage_key)
    except EvidenceFileError:
        return _evidence_not_found(request, purchase_need, evidence_id)
    return FileResponse(
        path,
        media_type=evidence.media_type,
        filename=evidence.original_filename,
        content_disposition_type="attachment",
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


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


@router.get(
    "/purchase-needs/{purchase_need_id}/prospecting-records/{prospecting_record_id}/"
    "evidence/files/new",
    response_class=HTMLResponse,
)
def prospecting_file_evidence_new(
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
        f"/purchase-needs/{purchase_need.id}/prospecting-records/"
        f"{prospecting_record.id}/evidence/files"
    )
    return templates.TemplateResponse(
        request,
        "evidence/new_file.html",
        _form_context(purchase_need, prospecting_record, action),
    )


@router.post(
    "/purchase-needs/{purchase_need_id}/prospecting-records/{prospecting_record_id}/evidence/files",
    response_class=HTMLResponse,
)
async def prospecting_file_evidence_create(
    request: Request,
    purchase_need_id: int,
    prospecting_record_id: int,
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
        f"/purchase-needs/{purchase_need.id}/prospecting-records/"
        f"{prospecting_record.id}/evidence/files"
    )
    return await _create_file_evidence(request, session, purchase_need, prospecting_record, action)


@router.get(
    "/purchase-needs/{purchase_need_id}/prospecting-records/{prospecting_record_id}/"
    "commercial-offers/{commercial_offer_id}/evidence/files/new",
    response_class=HTMLResponse,
)
def commercial_offer_file_evidence_new(
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
        f"commercial-offers/{commercial_offer.id}/evidence/files"
    )
    return templates.TemplateResponse(
        request,
        "evidence/new_file.html",
        _form_context(purchase_need, prospecting_record, action, commercial_offer),
    )


@router.post(
    "/purchase-needs/{purchase_need_id}/prospecting-records/{prospecting_record_id}/"
    "commercial-offers/{commercial_offer_id}/evidence/files",
    response_class=HTMLResponse,
)
async def commercial_offer_file_evidence_create(
    request: Request,
    purchase_need_id: int,
    prospecting_record_id: int,
    commercial_offer_id: int,
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
        f"commercial-offers/{commercial_offer.id}/evidence/files"
    )
    return await _create_file_evidence(
        request,
        session,
        purchase_need,
        prospecting_record,
        action,
        commercial_offer,
    )


@router.get(
    "/purchase-needs/{purchase_need_id}/prospecting-records/{prospecting_record_id}/"
    "evidence/{evidence_id}/download"
)
def prospecting_file_evidence_download(
    request: Request,
    purchase_need_id: int,
    prospecting_record_id: int,
    evidence_id: int,
    session: Session = Depends(get_session),
) -> Response:
    purchase_need, prospecting_record, error_response = _resolve_prospecting_context(
        request, session, purchase_need_id, prospecting_record_id
    )
    if error_response is not None:
        return error_response
    assert purchase_need is not None
    assert prospecting_record is not None
    evidence = session.scalar(
        select(Evidence).where(
            Evidence.id == evidence_id,
            Evidence.prospecting_record_id == prospecting_record.id,
            Evidence.commercial_offer_id.is_(None),
        )
    )
    return _download_response(request, purchase_need, evidence, evidence_id)


@router.get(
    "/purchase-needs/{purchase_need_id}/prospecting-records/{prospecting_record_id}/"
    "commercial-offers/{commercial_offer_id}/evidence/{evidence_id}/download"
)
def commercial_offer_file_evidence_download(
    request: Request,
    purchase_need_id: int,
    prospecting_record_id: int,
    commercial_offer_id: int,
    evidence_id: int,
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
    evidence = session.scalar(
        select(Evidence).where(
            Evidence.id == evidence_id,
            Evidence.commercial_offer_id == commercial_offer.id,
            Evidence.prospecting_record_id.is_(None),
        )
    )
    return _download_response(request, purchase_need, evidence, evidence_id)
