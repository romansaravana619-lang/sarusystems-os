from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator

CATEGORIES=["company","policy","sop","agreement","sales","client","project","freelancer","product","template","brand_asset","operations","engineering","delivery","other"]
STATUSES=["draft","in_review","approved","published","archived","superseded"]
VISIBILITIES=["private","internal","restricted","shared"]

class DocumentBase(BaseModel):
    document_key:str=Field(min_length=1,max_length=100); title:str=Field(min_length=1,max_length=240); category:str="company"; document_type:str="general"; status:str="draft"; visibility:str="internal"; version:str="1.0"; description:str|None=None; content:str|None=None; external_url:str|None=None; file_url:str|None=None; owner_user_id:UUID|None=None; reviewer_user_id:UUID|None=None; review_notes:str|None=None; tags:str|None=None; is_template:bool=False; template_key:str|None=None; client_id:UUID|None=None; project_id:UUID|None=None; freelancer_id:UUID|None=None; product_id:UUID|None=None; notes:str|None=None
    @field_validator("category")
    @classmethod
    def category_ok(cls,v):
        if v not in CATEGORIES: raise ValueError("Invalid document category")
        return v
    @field_validator("status")
    @classmethod
    def status_ok(cls,v):
        if v not in STATUSES: raise ValueError("Invalid document status")
        return v
    @field_validator("visibility")
    @classmethod
    def visibility_ok(cls,v):
        if v not in VISIBILITIES: raise ValueError("Invalid document visibility")
        return v

class DocumentCreate(DocumentBase): pass
class DocumentUpdate(BaseModel):
    title:str|None=None; category:str|None=None; document_type:str|None=None; status:str|None=None; visibility:str|None=None; version:str|None=None; description:str|None=None; content:str|None=None; external_url:str|None=None; file_url:str|None=None; owner_user_id:UUID|None=None; reviewer_user_id:UUID|None=None; review_notes:str|None=None; tags:str|None=None; is_template:bool|None=None; template_key:str|None=None; client_id:UUID|None=None; project_id:UUID|None=None; freelancer_id:UUID|None=None; product_id:UUID|None=None; notes:str|None=None
    @field_validator("category")
    @classmethod
    def category_ok(cls,v):
        if v is not None and v not in CATEGORIES: raise ValueError("Invalid document category")
        return v
    @field_validator("status")
    @classmethod
    def status_ok(cls,v):
        if v is not None and v not in STATUSES: raise ValueError("Invalid document status")
        return v
    @field_validator("visibility")
    @classmethod
    def visibility_ok(cls,v):
        if v is not None and v not in VISIBILITIES: raise ValueError("Invalid document visibility")
        return v

class DocumentResponse(DocumentBase):
    model_config=ConfigDict(from_attributes=True)
    id:UUID; company_id:UUID; approved_by_user_id:UUID|None; approved_at:datetime|None; created_at:datetime; updated_at:datetime
class DocumentDashboardResponse(BaseModel):
    total_documents:int; draft_documents:int; review_documents:int; approved_documents:int; templates:int; recent_documents:list[DocumentResponse]
