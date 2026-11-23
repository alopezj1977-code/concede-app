from mailing_store import (
    ensure_schema,
    get_latest_draft,
    list_contacts,
    mark_accepted,
    save_draft,
    upsert_contacts,
    validate_campaign_recipients,
)


def test_contacts_are_workspace_scoped_and_revalidated(tmp_path):
    db = tmp_path / "mailing.sqlite3"
    ensure_schema(db)
    upsert_contacts(
        "workspace-a",
        [{
            "empresa": "Empresa Uno",
            "correo": "contacto@example.com",
            "contacto": "Contacto",
            "fuente": "Autorización documentada",
            "autorizado": True,
            "correo_valido": True,
            "apto": True,
        }],
        db_path=db,
    )

    allowed, blocked = validate_campaign_recipients(
        "workspace-a",
        ["contacto@example.com", "otro@example.com"],
        db_path=db,
    )
    assert allowed == ["contacto@example.com"]
    assert blocked == ["otro@example.com"]
    assert list_contacts("workspace-b", db_path=db) == []


def test_campaign_draft_lifecycle_is_workspace_scoped(tmp_path):
    db = tmp_path / "mailing.sqlite3"
    ensure_schema(db)
    draft = {
        "id": "campaign-001",
        "name": "Prueba controlada",
        "subject": "Asunto de prueba",
        "body": "Mensaje de prueba",
        "recipients": ["contacto@example.com"],
    }

    assert save_draft("workspace-a", draft, db_path=db) == "campaign-001"
    assert get_latest_draft("workspace-a", db_path=db) == draft
    assert get_latest_draft("workspace-b", db_path=db) is None

    mark_accepted("workspace-a", "campaign-001", db_path=db)
    assert get_latest_draft("workspace-a", db_path=db) is None
