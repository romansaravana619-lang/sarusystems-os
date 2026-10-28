from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.documents.router import TRANSITIONS
from app.documents.schemas import CATEGORIES, STATUSES, VISIBILITIES, DocumentCreate, DocumentUpdate


def test_document_schema_covers_knowledge_categories_and_workflow_values():
    doc=DocumentCreate(document_key="DOC-001",title="Founder SOP",category="sop",document_type="policy",status="draft",visibility="internal")
    assert doc.category == "sop"
    assert {"company","policy","sop","agreement","sales","client","project","freelancer","product","template","brand_asset"} <= set(CATEGORIES)
    assert {"draft","in_review","approved","published","archived","superseded"} == set(STATUSES)
    assert {"private","internal","restricted","shared"} == set(VISIBILITIES)


def test_document_schema_rejects_invalid_select_values():
    with pytest.raises(ValidationError): DocumentCreate(document_key="DOC-2",title="Bad",category="unknown")
    with pytest.raises(ValidationError): DocumentCreate(document_key="DOC-3",title="Bad",status="live")
    with pytest.raises(ValidationError): DocumentCreate(document_key="DOC-4",title="Bad",visibility="public")
    with pytest.raises(ValidationError): DocumentUpdate(status="live")


def test_document_workflow_is_explicit_and_terminal():
    assert TRANSITIONS["draft"] == {"in_review","archived"}
    assert "approved" in TRANSITIONS["in_review"]
    assert TRANSITIONS["archived"] == set()
    assert TRANSITIONS["superseded"] == {"archived"}
