# BIIP-SIH2026 Documents API
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime
import uuid
import os
import shutil

from app.core.database import get_session
from app.core.config import get_settings
from app.models.document import Document, DocumentType, DocumentStatus
from app.models.document_field import DocumentField
from app.models.case import Case
from app.schemas.document import DocumentRead, DocumentFieldRead, DocumentUpload, DocumentProcessRequest

from app.services.audit import create_audit_event
from app.models.audit import AuditEventType

router = APIRouter()
settings = get_settings()

# Ensure upload directory exists
UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/{case_id}/documents", response_model=DocumentRead, status_code=201)
async def upload_document(
    case_id: str,
    document_type: DocumentType = Form(...),
    document_subtype: Optional[str] = Form(None),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    """Upload a document for a case"""
    # Verify case exists
    case = session.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Save file
    file_ext = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
    file_id = str(uuid.uuid4())
    filename = f"{file_id}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(file_path)

    # Create document record
    document = Document(
        case_id=case_id,
        document_type=document_type,
        document_subtype=document_subtype,
        filename=file.filename or filename,
        file_path=file_path,
        file_size=file_size,
        mime_type=file.content_type or "application/octet-stream",
        status=DocumentStatus.UPLOADED,
    )

    session.add(document)
    session.commit()
    session.refresh(document)

    # Audit
    await create_audit_event(
        session=session,
        case_id=case_id,
        event_type=AuditEventType.DOCUMENT_ADDED,
        module="DOCUMENTS",
        details={
            "document_id": document.id,
            "document_type": document_type.value,
            "filename": file.filename,
        },
        actor_type="SYSTEM",
    )

    return document


@router.get("/{case_id}/documents", response_model=List[DocumentRead])
async def list_documents(case_id: str, session: Session = Depends(get_session)):
    """List all documents for a case"""
    case = session.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    documents = session.exec(
        select(Document).where(Document.case_id == case_id)
    ).all()

    # Load fields for each document
    result = []
    for doc in documents:
        fields = session.exec(
            select(DocumentField).where(DocumentField.document_id == doc.id)
        ).all()
        doc_read = DocumentRead.model_validate(doc)
        doc_read.fields = [DocumentFieldRead.model_validate(f) for f in fields]
        result.append(doc_read)

    return result


@router.get("/{case_id}/documents/{document_id}", response_model=DocumentRead)
async def get_document(case_id: str, document_id: str, session: Session = Depends(get_session)):
    """Get a specific document"""
    document = session.get(Document, document_id)
    if not document or document.case_id != case_id:
        raise HTTPException(status_code=404, detail="Document not found")

    fields = session.exec(
        select(DocumentField).where(DocumentField.document_id == document_id)
    ).all()

    doc_read = DocumentRead.model_validate(document)
    doc_read.fields = [DocumentFieldRead.model_validate(f) for f in fields]

    return doc_read


@router.post("/{case_id}/documents/{document_id}/process")
async def process_document(
    case_id: str,
    document_id: str,
    request: DocumentProcessRequest,
    session: Session = Depends(get_session),
):
    """Trigger document processing pipeline"""
    document = session.get(Document, document_id)
    if not document or document.case_id != case_id:
        raise HTTPException(status_code=404, detail="Document not found")

    # Update status
    document.status = DocumentStatus.PROCESSING
    session.add(document)
    session.commit()

    # TODO: Trigger actual processing via services
    # This would call OCR, MRZ, barcode, validation, tamper services

    return {"message": "Processing started", "document_id": document_id}