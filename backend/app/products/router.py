from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.products.models import (
    Product, ProductDocument, ProductFeature, ProductIssue, ProductRelease,
    ProductRequirement, ProductRoadmapItem, ProductVersion,
)
from app.products.schemas import (
    DOCUMENT_STATUSES, FEATURE_STATUSES, ISSUE_SEVERITIES, ISSUE_STATUSES,
    PRIORITIES, PRODUCT_STATUSES, PRODUCT_TYPES, RELEASE_STATUSES,
    REQUIREMENT_STATUSES, ROADMAP_CATEGORIES, ROADMAP_STATUSES, RETEST_RESULTS,
    VERSION_STATUSES, DocumentCreate, DocumentResponse, DocumentUpdate,
    FeatureCreate, FeatureResponse, FeatureUpdate, IssueCreate, IssueResponse,
    IssueUpdate, ProductCreate, ProductDashboardResponse, ProductResponse,
    ProductUpdate, ReleaseCreate, ReleaseResponse, ReleaseUpdate,
    RequirementCreate, RequirementResponse, RequirementUpdate, RoadmapItemCreate,
    RoadmapItemResponse, RoadmapItemUpdate, VersionCreate, VersionResponse, VersionUpdate,
)
from app.shared.models import AuditLog, User
from app.tasks.models import Task
from app.projects.models import Project
from app.tasks.router import _validate_owner


router = APIRouter(prefix="/products", tags=["products"])

PRODUCT_TRANSITIONS = {
    "discovery": {"planned", "active", "archived"},
    "planned": {"active", "discovery", "archived"},
    "active": {"maintenance", "deprecated", "archived"},
    "maintenance": {"active", "deprecated", "archived"},
    "deprecated": {"maintenance", "archived"},
    "archived": set(),
}
ROADMAP_TRANSITIONS = {
    "backlog": {"planned", "cancelled"},
    "planned": {"in_progress", "deferred", "cancelled"},
    "in_progress": {"blocked", "done", "deferred", "cancelled"},
    "blocked": {"in_progress", "deferred", "cancelled"},
    "done": set(),
    "deferred": {"backlog", "planned", "cancelled"},
    "cancelled": set(),
}
ISSUE_TRANSITIONS = {
    "open": {"assigned", "in_progress", "closed"},
    "assigned": {"in_progress", "closed"},
    "in_progress": {"fixed", "open"},
    "fixed": {"retest", "in_progress"},
    "retest": {"verified", "reopened", "in_progress"},
    "verified": {"closed", "reopened"},
    "reopened": {"assigned", "in_progress", "closed"},
    "closed": {"reopened"},
}
VERSION_TRANSITIONS = {
    "planned": {"in_development", "withdrawn"},
    "in_development": {"testing", "withdrawn"},
    "testing": {"ready", "in_development", "withdrawn"},
    "ready": {"released", "testing", "withdrawn"},
    "released": set(),
    "withdrawn": set(),
}
RELEASE_TRANSITIONS = {
    "planned": {"in_preparation", "cancelled"},
    "in_preparation": {"ready_for_approval", "cancelled"},
    "ready_for_approval": {"released", "in_preparation", "cancelled"},
    "released": {"rolled_back"},
    "rolled_back": set(),
    "cancelled": set(),
}


def _record(db: Session, model, company_id: UUID, record_id: UUID, label: str):
    obj = db.scalar(select(model).where(model.id == record_id, model.company_id == company_id))
    if obj is None:
        raise HTTPException(status_code=404, detail=f"{label} not found.")
    return obj


def _audit(db: Session, actor: User, action: str, entity: str, entity_id: UUID, details: str | None = None) -> None:
    db.add(AuditLog(actor_user_id=actor.id, action=action, entity_type=entity, entity_id=str(entity_id), details=details))


def _validate_owner_id(db: Session, company_id: UUID, owner_user_id: UUID | None) -> None:
    if owner_user_id is not None:
        owner = db.scalar(select(User.id).where(User.id == owner_user_id, User.company_id == company_id, User.is_active.is_(True)))
        if owner is None:
            raise HTTPException(status_code=400, detail="Owner must be an active user in this company.")


def _validate_related_task(db: Session, company_id: UUID, product_id: UUID, task_id: UUID | None) -> None:
    if task_id is None:
        return
    task = db.scalar(select(Task).where(Task.id == task_id, Task.company_id == company_id))
    if task is None:
        raise HTTPException(status_code=400, detail="Development task must belong to this company.")
    if task.project_id is not None:
        project = db.scalar(select(Project).where(Project.id == task.project_id, Project.company_id == company_id))
        if project is None:
            raise HTTPException(status_code=400, detail="Development task project must belong to this company.")
    task.notes = (task.notes or "")[:3500] + f"\n[Product link: {product_id}]"


def _validate_feature(db: Session, company_id: UUID, product_id: UUID, feature_id: UUID | None) -> None:
    if feature_id is not None and db.scalar(select(ProductFeature.id).where(
        ProductFeature.id == feature_id, ProductFeature.company_id == company_id, ProductFeature.product_id == product_id
    )) is None:
        raise HTTPException(status_code=400, detail="Feature must belong to the selected product and company.")


def _validate_requirement(db: Session, company_id: UUID, product_id: UUID, requirement_id: UUID | None) -> None:
    if requirement_id is not None and db.scalar(select(ProductRequirement.id).where(
        ProductRequirement.id == requirement_id, ProductRequirement.company_id == company_id, ProductRequirement.product_id == product_id
    )) is None:
        raise HTTPException(status_code=400, detail="Requirement must belong to the selected product and company.")


def _validate_roadmap(db: Session, company_id: UUID, product_id: UUID, item_id: UUID | None) -> None:
    if item_id is not None and db.scalar(select(ProductRoadmapItem.id).where(
        ProductRoadmapItem.id == item_id, ProductRoadmapItem.company_id == company_id, ProductRoadmapItem.product_id == product_id
    )) is None:
        raise HTTPException(status_code=400, detail="Roadmap item must belong to the selected product and company.")


def _validate_version(db: Session, company_id: UUID, product_id: UUID, version_id: UUID | None) -> None:
    if version_id is not None and db.scalar(select(ProductVersion.id).where(
        ProductVersion.id == version_id, ProductVersion.company_id == company_id, ProductVersion.product_id == product_id
    )) is None:
        raise HTTPException(status_code=400, detail="Version must belong to the selected product and company.")


def _validate_links(db: Session, company_id: UUID, product_id: UUID, feature_id: UUID | None = None, requirement_id: UUID | None = None, task_id: UUID | None = None, roadmap_item_id: UUID | None = None, version_id: UUID | None = None, assigned_user_id: UUID | None = None, owner_user_id: UUID | None = None) -> None:
    _validate_feature(db, company_id, product_id, feature_id)
    _validate_requirement(db, company_id, product_id, requirement_id)
    _validate_related_task(db, company_id, product_id, task_id)
    _validate_roadmap(db, company_id, product_id, roadmap_item_id)
    _validate_version(db, company_id, product_id, version_id)
    _validate_owner_id(db, company_id, assigned_user_id)
    _validate_owner_id(db, company_id, owner_user_id)


@router.get("/dashboard", response_model=ProductDashboardResponse)
def dashboard(current_user: User = Depends(require_permission("products.dashboard.view")), db: Session = Depends(get_db)):
    products = list(db.scalars(select(Product).where(Product.company_id == current_user.company_id).order_by(Product.created_at.desc())).all())
    product_ids = [p.id for p in products]
    if not product_ids:
        return ProductDashboardResponse(total_products=0, active_products=0, roadmap_items=0, open_issues=0, in_progress_features=0, released_versions=0, planned_releases=0, recent_products=[])
    count = lambda model, *criteria: db.scalar(select(func.count(model.id)).where(model.company_id == current_user.company_id, *criteria)) or 0
    return ProductDashboardResponse(
        total_products=len(products),
        active_products=sum(p.lifecycle_status in {"active", "maintenance"} for p in products),
        roadmap_items=count(ProductRoadmapItem),
        open_issues=db.scalar(select(func.count(ProductIssue.id)).where(ProductIssue.company_id == current_user.company_id, ProductIssue.status.not_in(["verified", "closed"]))) or 0,
        in_progress_features=count(ProductFeature, ProductFeature.status == "in_progress"),
        released_versions=count(ProductVersion, ProductVersion.status == "released"),
        planned_releases=count(ProductRelease, ProductRelease.status.not_in(["released", "cancelled", "rolled_back"])),
        recent_products=products[:8],
    )


@router.get("", response_model=list[ProductResponse])
def list_products(current_user: User = Depends(require_permission("products.view")), db: Session = Depends(get_db)):
    return list(db.scalars(select(Product).where(Product.company_id == current_user.company_id).order_by(Product.created_at.desc())).all())


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(p: ProductCreate, current_user: User = Depends(require_permission("products.create")), db: Session = Depends(get_db)):
    _validate_owner_id(db, current_user.company_id, p.owner_user_id)
    if db.scalar(select(Product.id).where(Product.company_id == current_user.company_id, Product.code == p.code)) is not None:
        raise HTTPException(status_code=409, detail="Product code already exists.")
    if db.scalar(select(Product.id).where(Product.company_id == current_user.company_id, Product.name == p.name)) is not None:
        raise HTTPException(status_code=409, detail="Product name already exists.")
    obj = Product(company_id=current_user.company_id, **p.model_dump())
    db.add(obj); db.flush(); _audit(db, current_user, "product.create", "Product", obj.id, obj.code); db.commit(); db.refresh(obj)
    return obj


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: UUID, current_user: User = Depends(require_permission("products.view")), db: Session = Depends(get_db)):
    return _record(db, Product, current_user.company_id, product_id, "Product")


@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(product_id: UUID, p: ProductUpdate, current_user: User = Depends(require_permission("products.edit")), db: Session = Depends(get_db)):
    obj = _record(db, Product, current_user.company_id, product_id, "Product")
    values = p.model_dump(exclude_unset=True)
    target = values.get("lifecycle_status", obj.lifecycle_status)
    if target != obj.lifecycle_status and target not in PRODUCT_TRANSITIONS[obj.lifecycle_status]:
        raise HTTPException(status_code=409, detail=f"Invalid product lifecycle transition: {obj.lifecycle_status} -> {target}.")
    _validate_owner_id(db, current_user.company_id, values.get("owner_user_id", obj.owner_user_id))
    if "name" in values and db.scalar(select(Product.id).where(Product.company_id == current_user.company_id, Product.name == values["name"], Product.id != obj.id)) is not None:
        raise HTTPException(status_code=409, detail="Product name already exists.")
    for k, v in values.items(): setattr(obj, k, v)
    _audit(db, current_user, "product.update", "Product", obj.id); db.commit(); db.refresh(obj); return obj


def _list_child(db, model, company_id, product_id):
    _record(db, Product, company_id, product_id, "Product")
    return list(db.scalars(select(model).where(model.company_id == company_id, model.product_id == product_id).order_by(model.created_at.desc())).all())


@router.get("/{product_id}/roadmap", response_model=list[RoadmapItemResponse])
def list_roadmap(product_id: UUID, current_user: User = Depends(require_permission("products.roadmap.view")), db: Session = Depends(get_db)):
    return _list_child(db, ProductRoadmapItem, current_user.company_id, product_id)


@router.post("/{product_id}/roadmap", response_model=RoadmapItemResponse, status_code=201)
def create_roadmap(product_id: UUID, p: RoadmapItemCreate, current_user: User = Depends(require_permission("products.roadmap.edit")), db: Session = Depends(get_db)):
    _record(db, Product, current_user.company_id, product_id, "Product")
    _validate_version(db, current_user.company_id, product_id, p.target_version_id); _validate_owner_id(db, current_user.company_id, p.owner_user_id)
    obj = ProductRoadmapItem(company_id=current_user.company_id, product_id=product_id, **p.model_dump())
    db.add(obj); db.flush(); _audit(db,current_user,"product.roadmap.create","ProductRoadmapItem",obj.id); db.commit(); db.refresh(obj); return obj


@router.patch("/{product_id}/roadmap/{item_id}", response_model=RoadmapItemResponse)
def update_roadmap(product_id: UUID, item_id: UUID, p: RoadmapItemUpdate, current_user: User = Depends(require_permission("products.roadmap.edit")), db: Session = Depends(get_db)):
    _record(db, Product, current_user.company_id, product_id, "Product")
    obj = db.scalar(select(ProductRoadmapItem).where(ProductRoadmapItem.id == item_id, ProductRoadmapItem.product_id == product_id, ProductRoadmapItem.company_id == current_user.company_id))
    if obj is None: raise HTTPException(404, detail="Roadmap item not found.")
    changes=p.model_dump(exclude_unset=True)
    target=changes.get("status",obj.status)
    if target != obj.status and target not in ROADMAP_TRANSITIONS[obj.status]: raise HTTPException(409,detail=f"Invalid roadmap transition: {obj.status} -> {target}.")
    _validate_version(db,current_user.company_id,product_id,changes.get("target_version_id",obj.target_version_id)); _validate_owner_id(db,current_user.company_id,changes.get("owner_user_id",obj.owner_user_id))
    for k,v in changes.items(): setattr(obj,k,v)
    _audit(db,current_user,"product.roadmap.update","ProductRoadmapItem",obj.id); db.commit(); db.refresh(obj); return obj


@router.get("/{product_id}/features", response_model=list[FeatureResponse])
def list_features(product_id: UUID, current_user: User = Depends(require_permission("products.features.view")), db: Session = Depends(get_db)):
    return _list_child(db, ProductFeature, current_user.company_id, product_id)


@router.post("/{product_id}/features", response_model=FeatureResponse, status_code=201)
def create_feature(product_id: UUID, p: FeatureCreate, current_user: User = Depends(require_permission("products.features.edit")), db: Session = Depends(get_db)):
    _record(db,Product,current_user.company_id,product_id,"Product")
    _validate_roadmap(db,current_user.company_id,product_id,p.roadmap_item_id); _validate_owner_id(db,current_user.company_id,p.owner_user_id)
    if db.scalar(select(ProductFeature.id).where(ProductFeature.product_id==product_id,ProductFeature.code==p.code)) is not None: raise HTTPException(409,detail="Feature code already exists for this product.")
    obj=ProductFeature(company_id=current_user.company_id,product_id=product_id,**p.model_dump()); db.add(obj); db.flush(); _audit(db,current_user,"product.feature.create","ProductFeature",obj.id,obj.code); db.commit(); db.refresh(obj); return obj


@router.patch("/{product_id}/features/{feature_id}", response_model=FeatureResponse)
def update_feature(product_id: UUID, feature_id: UUID, p: FeatureUpdate, current_user: User = Depends(require_permission("products.features.edit")), db: Session = Depends(get_db)):
    obj=db.scalar(select(ProductFeature).where(ProductFeature.id==feature_id,ProductFeature.product_id==product_id,ProductFeature.company_id==current_user.company_id))
    if obj is None: raise HTTPException(404,detail="Feature not found.")
    values=p.model_dump(exclude_unset=True); _validate_roadmap(db,current_user.company_id,product_id,values.get("roadmap_item_id",obj.roadmap_item_id)); _validate_owner_id(db,current_user.company_id,values.get("owner_user_id",obj.owner_user_id))
    for k,v in values.items(): setattr(obj,k,v)
    _audit(db,current_user,"product.feature.update","ProductFeature",obj.id); db.commit(); db.refresh(obj); return obj


@router.get("/{product_id}/requirements", response_model=list[RequirementResponse])
def list_requirements(product_id: UUID, current_user: User = Depends(require_permission("products.requirements.view")), db: Session = Depends(get_db)):
    return _list_child(db, ProductRequirement, current_user.company_id, product_id)


@router.post("/{product_id}/requirements", response_model=RequirementResponse, status_code=201)
def create_requirement(product_id: UUID, p: RequirementCreate, current_user: User = Depends(require_permission("products.requirements.edit")), db: Session = Depends(get_db)):
    _record(db,Product,current_user.company_id,product_id,"Product"); _validate_feature(db,current_user.company_id,product_id,p.feature_id)
    if db.scalar(select(ProductRequirement.id).where(ProductRequirement.product_id==product_id,ProductRequirement.requirement_key==p.requirement_key)) is not None: raise HTTPException(409,detail="Requirement key already exists for this product.")
    if p.status in {"approved","implemented"}: raise HTTPException(409,detail="Create requirements as draft or in review and use the approval workflow.")
    obj=ProductRequirement(company_id=current_user.company_id,product_id=product_id,**p.model_dump()); db.add(obj); db.flush(); _audit(db,current_user,"product.requirement.create","ProductRequirement",obj.id,obj.requirement_key); db.commit(); db.refresh(obj); return obj


@router.patch("/{product_id}/requirements/{requirement_id}", response_model=RequirementResponse)
def update_requirement(product_id: UUID, requirement_id: UUID, p: RequirementUpdate, current_user: User = Depends(require_permission("products.requirements.edit")), db: Session = Depends(get_db)):
    obj=db.scalar(select(ProductRequirement).where(ProductRequirement.id==requirement_id,ProductRequirement.product_id==product_id,ProductRequirement.company_id==current_user.company_id))
    if obj is None: raise HTTPException(404,detail="Requirement not found.")
    values=p.model_dump(exclude_unset=True)
    target=values.get("status",obj.status)
    if target != obj.status and target in {"approved","implemented"}: raise HTTPException(409,detail="Use the requirement approval endpoint before approval or implementation.")
    _validate_feature(db,current_user.company_id,product_id,values.get("feature_id",obj.feature_id))
    for k,v in values.items(): setattr(obj,k,v)
    _audit(db,current_user,"product.requirement.update","ProductRequirement",obj.id); db.commit(); db.refresh(obj); return obj


@router.post("/{product_id}/requirements/{requirement_id}/approve", response_model=RequirementResponse)
def approve_requirement(product_id: UUID, requirement_id: UUID, current_user: User = Depends(require_permission("products.requirements.approve")), db: Session = Depends(get_db)):
    obj=db.scalar(select(ProductRequirement).where(ProductRequirement.id==requirement_id,ProductRequirement.product_id==product_id,ProductRequirement.company_id==current_user.company_id))
    if obj is None: raise HTTPException(404,detail="Requirement not found.")
    if obj.status not in {"draft","in_review"}: raise HTTPException(409,detail="Only draft or in-review requirements can be approved.")
    obj.status="approved"; obj.approved_by_user_id=current_user.id; obj.approved_at=datetime.now(timezone.utc)
    _audit(db,current_user,"product.requirement.approve","ProductRequirement",obj.id); db.commit(); db.refresh(obj); return obj


@router.get("/{product_id}/issues", response_model=list[IssueResponse])
def list_issues(product_id: UUID, current_user: User = Depends(require_permission("products.issues.view")), db: Session = Depends(get_db)):
    return _list_child(db, ProductIssue, current_user.company_id, product_id)


@router.post("/{product_id}/issues", response_model=IssueResponse, status_code=201)
def create_issue(product_id: UUID, p: IssueCreate, current_user: User = Depends(require_permission("products.issues.create")), db: Session = Depends(get_db)):
    _record(db,Product,current_user.company_id,product_id,"Product")
    _validate_links(db,current_user.company_id,product_id,feature_id=p.feature_id,requirement_id=p.requirement_id,task_id=p.task_id,assigned_user_id=p.assigned_user_id)
    if db.scalar(select(ProductIssue.id).where(ProductIssue.product_id==product_id,ProductIssue.issue_key==p.issue_key)) is not None: raise HTTPException(409,detail="Issue key already exists for this product.")
    obj=ProductIssue(company_id=current_user.company_id,product_id=product_id,**p.model_dump()); db.add(obj); db.flush(); _audit(db,current_user,"product.issue.create","ProductIssue",obj.id,obj.issue_key); db.commit(); db.refresh(obj); return obj


@router.patch("/{product_id}/issues/{issue_id}", response_model=IssueResponse)
def update_issue(product_id: UUID, issue_id: UUID, p: IssueUpdate, current_user: User = Depends(require_permission("products.issues.edit")), db: Session = Depends(get_db)):
    obj=db.scalar(select(ProductIssue).where(ProductIssue.id==issue_id,ProductIssue.product_id==product_id,ProductIssue.company_id==current_user.company_id))
    if obj is None: raise HTTPException(404,detail="Product issue not found.")
    values=p.model_dump(exclude_unset=True)
    target=values.get("status",obj.status)
    if target != obj.status and target not in ISSUE_TRANSITIONS[obj.status]: raise HTTPException(409,detail=f"Invalid issue transition: {obj.status} -> {target}.")
    _validate_links(db,current_user.company_id,product_id,feature_id=values.get("feature_id",obj.feature_id),requirement_id=values.get("requirement_id",obj.requirement_id),task_id=values.get("task_id",obj.task_id),assigned_user_id=values.get("assigned_user_id",obj.assigned_user_id))
    if target == "fixed":
        values["fix_date"] = values.get("fix_date") or datetime.now(timezone.utc)
    if target == "verified" and values.get("retest_result",obj.retest_result) != "passed":
        raise HTTPException(409,detail="Issue can only be verified after a passed retest.")
    for k,v in values.items(): setattr(obj,k,v)
    _audit(db,current_user,"product.issue.update","ProductIssue",obj.id); db.commit(); db.refresh(obj); return obj


@router.post("/{product_id}/issues/{issue_id}/retest", response_model=IssueResponse)
def record_retest(product_id: UUID, issue_id: UUID, result: str, current_user: User = Depends(require_permission("products.issues.edit")), db: Session = Depends(get_db)):
    obj=db.scalar(select(ProductIssue).where(ProductIssue.id==issue_id,ProductIssue.product_id==product_id,ProductIssue.company_id==current_user.company_id))
    if obj is None: raise HTTPException(404,detail="Product issue not found.")
    if obj.status != "retest": raise HTTPException(409,detail="Only issues in retest can record a retest result.")
    if result not in RETEST_RESULTS: raise HTTPException(400,detail="Invalid retest result.")
    obj.retest_result=result; obj.status="verified" if result=="passed" else "reopened"
    _audit(db,current_user,"product.issue.retest","ProductIssue",obj.id,result); db.commit(); db.refresh(obj); return obj


@router.get("/{product_id}/versions", response_model=list[VersionResponse])
def list_versions(product_id: UUID, current_user: User = Depends(require_permission("products.versions.view")), db: Session = Depends(get_db)):
    return _list_child(db, ProductVersion, current_user.company_id, product_id)


@router.post("/{product_id}/versions", response_model=VersionResponse, status_code=201)
def create_version(product_id: UUID, p: VersionCreate, current_user: User = Depends(require_permission("products.versions.edit")), db: Session = Depends(get_db)):
    _record(db,Product,current_user.company_id,product_id,"Product")
    if db.scalar(select(ProductVersion.id).where(ProductVersion.product_id==product_id,ProductVersion.version==p.version)) is not None: raise HTTPException(409,detail="Version already exists for this product.")
    if p.status == "released": raise HTTPException(409,detail="Create versions as planned and use the release workflow.")
    obj=ProductVersion(company_id=current_user.company_id,product_id=product_id,**p.model_dump()); db.add(obj); db.flush(); _audit(db,current_user,"product.version.create","ProductVersion",obj.id,obj.version); db.commit(); db.refresh(obj); return obj


@router.patch("/{product_id}/versions/{version_id}", response_model=VersionResponse)
def update_version(product_id: UUID, version_id: UUID, p: VersionUpdate, current_user: User = Depends(require_permission("products.versions.edit")), db: Session = Depends(get_db)):
    obj=db.scalar(select(ProductVersion).where(ProductVersion.id==version_id,ProductVersion.product_id==product_id,ProductVersion.company_id==current_user.company_id))
    if obj is None: raise HTTPException(404,detail="Product version not found.")
    values=p.model_dump(exclude_unset=True); target=values.get("status",obj.status)
    if target != obj.status and target not in VERSION_TRANSITIONS[obj.status]: raise HTTPException(409,detail=f"Invalid version transition: {obj.status} -> {target}.")
    if target == "released": raise HTTPException(409,detail="Versions are released only through an approved release.")
    for k,v in values.items(): setattr(obj,k,v)
    _audit(db,current_user,"product.version.update","ProductVersion",obj.id); db.commit(); db.refresh(obj); return obj


@router.get("/{product_id}/releases", response_model=list[ReleaseResponse])
def list_releases(product_id: UUID, current_user: User = Depends(require_permission("products.releases.view")), db: Session = Depends(get_db)):
    return _list_child(db, ProductRelease, current_user.company_id, product_id)


@router.post("/{product_id}/releases", response_model=ReleaseResponse, status_code=201)
def create_release(product_id: UUID, p: ReleaseCreate, current_user: User = Depends(require_permission("products.releases.edit")), db: Session = Depends(get_db)):
    _record(db,Product,current_user.company_id,product_id,"Product")
    _validate_version(db,current_user.company_id,product_id,p.version_id)
    if db.scalar(select(ProductRelease.id).where(ProductRelease.product_id==product_id,ProductRelease.release_key==p.release_key)) is not None: raise HTTPException(409,detail="Release key already exists for this product.")
    if p.status in {"released","ready_for_approval"}: raise HTTPException(409,detail="A release must use the approval workflow before publication.")
    obj=ProductRelease(company_id=current_user.company_id,product_id=product_id,**p.model_dump()); db.add(obj); db.flush(); _audit(db,current_user,"product.release.create","ProductRelease",obj.id,obj.release_key); db.commit(); db.refresh(obj); return obj


@router.patch("/{product_id}/releases/{release_id}", response_model=ReleaseResponse)
def update_release(product_id: UUID, release_id: UUID, p: ReleaseUpdate, current_user: User = Depends(require_permission("products.releases.edit")), db: Session = Depends(get_db)):
    obj=db.scalar(select(ProductRelease).where(ProductRelease.id==release_id,ProductRelease.product_id==product_id,ProductRelease.company_id==current_user.company_id))
    if obj is None: raise HTTPException(404,detail="Release not found.")
    values=p.model_dump(exclude_unset=True); target=values.get("status",obj.status)
    if target != obj.status and target not in RELEASE_TRANSITIONS[obj.status]: raise HTTPException(409,detail=f"Invalid release transition: {obj.status} -> {target}.")
    if target == "released": raise HTTPException(409,detail="Use the release approval endpoint to release a version.")
    for k,v in values.items(): setattr(obj,k,v)
    _audit(db,current_user,"product.release.update","ProductRelease",obj.id); db.commit(); db.refresh(obj); return obj


@router.post("/{product_id}/releases/{release_id}/approve", response_model=ReleaseResponse)
def approve_release(product_id: UUID, release_id: UUID, current_user: User = Depends(require_permission("products.releases.approve")), db: Session = Depends(get_db)):
    obj=db.scalar(select(ProductRelease).where(ProductRelease.id==release_id,ProductRelease.product_id==product_id,ProductRelease.company_id==current_user.company_id))
    if obj is None: raise HTTPException(404,detail="Release not found.")
    if obj.status != "ready_for_approval": raise HTTPException(409,detail="Release must be ready for approval.")
    version=_record(db,ProductVersion,current_user.company_id,obj.version_id,"Version")
    open_issues=db.scalar(select(func.count(ProductIssue.id)).where(ProductIssue.company_id==current_user.company_id,ProductIssue.product_id==product_id,ProductIssue.status.not_in(["verified","closed"]),ProductIssue.severity.in_(["critical","high"]))) or 0
    if open_issues: raise HTTPException(409,detail="Critical/high open product issues must be verified or closed before release.")
    now=datetime.now(timezone.utc); obj.status="released"; obj.released_at=now; obj.approved_at=now; obj.approved_by_user_id=current_user.id
    version.status="released"; version.released_at=now
    product=_record(db,Product,current_user.company_id,product_id,"Product"); product.current_version=version.version
    _audit(db,current_user,"product.release.approve","ProductRelease",obj.id,version.version); _audit(db,current_user,"product.version.release","ProductVersion",version.id,version.version)
    db.commit(); db.refresh(obj); return obj


@router.get("/{product_id}/documents", response_model=list[DocumentResponse])
def list_documents(product_id: UUID, current_user: User = Depends(require_permission("products.documents.view")), db: Session = Depends(get_db)):
    return _list_child(db, ProductDocument, current_user.company_id, product_id)


@router.post("/{product_id}/documents", response_model=DocumentResponse, status_code=201)
def create_document(product_id: UUID, p: DocumentCreate, current_user: User = Depends(require_permission("products.documents.edit")), db: Session = Depends(get_db)):
    _record(db,Product,current_user.company_id,product_id,"Product")
    _validate_feature(db,current_user.company_id,product_id,p.feature_id); _validate_version(db,current_user.company_id,product_id,p.version_id); _validate_owner_id(db,current_user.company_id,p.owner_user_id)
    if p.status == "approved": raise HTTPException(409,detail="Use document approval workflow.")
    obj=ProductDocument(company_id=current_user.company_id,product_id=product_id,**p.model_dump()); db.add(obj); db.flush(); _audit(db,current_user,"product.document.create","ProductDocument",obj.id); db.commit(); db.refresh(obj); return obj


@router.patch("/{product_id}/documents/{document_id}", response_model=DocumentResponse)
def update_document(product_id: UUID, document_id: UUID, p: DocumentUpdate, current_user: User = Depends(require_permission("products.documents.edit")), db: Session = Depends(get_db)):
    obj=db.scalar(select(ProductDocument).where(ProductDocument.id==document_id,ProductDocument.product_id==product_id,ProductDocument.company_id==current_user.company_id))
    if obj is None: raise HTTPException(404,detail="Product document not found.")
    changes=p.model_dump(exclude_unset=True)
    if changes.get("status")=="approved": raise HTTPException(409,detail="Use document approval workflow.")
    _validate_feature(db,current_user.company_id,product_id,changes.get("feature_id",obj.feature_id)); _validate_version(db,current_user.company_id,product_id,changes.get("version_id",obj.version_id)); _validate_owner_id(db,current_user.company_id,changes.get("owner_user_id",obj.owner_user_id))
    for k,v in changes.items(): setattr(obj,k,v)
    _audit(db,current_user,"product.document.update","ProductDocument",obj.id); db.commit(); db.refresh(obj); return obj


@router.post("/{product_id}/documents/{document_id}/approve", response_model=DocumentResponse)
def approve_document(product_id: UUID, document_id: UUID, current_user: User = Depends(require_permission("products.documents.approve")), db: Session = Depends(get_db)):
    obj=db.scalar(select(ProductDocument).where(ProductDocument.id==document_id,ProductDocument.product_id==product_id,ProductDocument.company_id==current_user.company_id))
    if obj is None: raise HTTPException(404,detail="Product document not found.")
    if obj.status != "in_review": raise HTTPException(409,detail="Only in-review documents can be approved.")
    obj.status="approved"; _audit(db,current_user,"product.document.approve","ProductDocument",obj.id); db.commit(); db.refresh(obj); return obj
