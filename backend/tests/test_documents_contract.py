from app.documents.schemas import CATEGORIES, STATUSES, VISIBILITIES


def test_documents_knowledge_contract_lists_all_approved_categories():
    assert {
        "company",
        "policy",
        "sop",
        "agreement",
        "sales",
        "client",
        "project",
        "freelancer",
        "product",
        "template",
        "brand_asset",
        "operations",
        "engineering",
        "delivery",
        "other",
    } == set(CATEGORIES)


def test_documents_knowledge_contract_lists_lifecycle_and_visibility_values():
    assert {"draft", "in_review", "approved", "published", "archived", "superseded"} == set(STATUSES)
    assert {"private", "internal", "restricted", "shared"} == set(VISIBILITIES)
