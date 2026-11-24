"""Mailing workspace for CONCEDE V3 with workspace-scoped contact and draft persistence."""
from __future__ import annotations

import os
import re
import uuid

import pandas as pd
import streamlit as st

from mailing_auth import render_mail_auth
from denue_enrichment import DenueEnrichmentError, fetch_denue_ficha
from website_contact_enrichment import find_public_business_emails
from mailing_service import (
    APPROVED_SENDER_MAILBOX,
    MailDeliveryError,
    read_mail_config,
    send_graph_mail,
)
from mailing_store import (
    ensure_schema,
    get_latest_draft,
    list_contacts,
    list_enrichment_records,
    list_public_emails,
    mark_accepted,
    save_draft,
    upsert_contacts,
    upsert_enrichment_records,
    upsert_public_emails,
    validate_campaign_recipients,
)

_TRUE = {"SI", "SÍ", "TRUE", "1", "AUTORIZADO", "YES", "Y"}
_CONTACT_COLUMNS = ["empresa", "correo", "contacto", "fuente", "autorizado", "correo_valido", "apto"]


def _read_contacts(uploaded):
    try:
        try:
            frame = pd.read_csv(uploaded, encoding="utf-8-sig", dtype=str).fillna("")
        except UnicodeDecodeError:
            uploaded.seek(0)
            frame = pd.read_csv(uploaded, encoding="latin1", dtype=str).fillna("")
    except Exception as exc:
        raise ValueError(f"No se pudo leer el CSV: {exc}") from exc

    aliases = {
        "empresa": ["empresa", "razon social", "razón social", "company", "nombre empresa"],
        "correo": ["correo", "email", "e-mail", "correo electronico", "correo electrónico"],
        "contacto": ["contacto", "nombre", "contact name", "persona"],
        "fuente": ["fuente", "source", "origen del correo"],
        "autorizado": ["autorizado", "consentimiento", "permiso", "authorization"],
    }
    normalized = {str(c).strip().casefold(): c for c in frame.columns}
    mapping = {
        key: next((normalized[name] for name in names if name in normalized), None)
        for key, names in aliases.items()
    }
    missing = [key for key, column in mapping.items() if column is None]
    if missing:
        raise ValueError("Faltan columnas obligatorias: " + ", ".join(missing))

    result = pd.DataFrame({
        key: frame[column].astype(str).str.strip()
        for key, column in mapping.items()
    })
    result["correo"] = result["correo"].str.lower()
    result["correo_valido"] = result["correo"].map(
        lambda value: bool(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value))
    )
    result["autorizado"] = result["autorizado"].str.upper().isin(_TRUE)
    result["apto"] = (
        result["correo_valido"]
        & result["autorizado"]
        & result["fuente"].ne("")
    )
    return result.drop_duplicates(subset=["correo"]).reset_index(drop=True)


def _initialize_store(mail_config):
    """Initialize Neon using the same DATABASE_URL setting as Radar."""
    try:
        database_url = st.secrets.get("DATABASE_URL", "")
    except Exception:
        database_url = ""
    if database_url and not os.getenv("DATABASE_URL"):
        os.environ["DATABASE_URL"] = str(database_url)

    ensure_schema()
    workspace_id = mail_config["workspace_id"]
    contacts = pd.DataFrame(list_contacts(workspace_id), columns=_CONTACT_COLUMNS)
    draft = get_latest_draft(workspace_id)
    return contacts, draft, bool(os.getenv("DATABASE_URL"))


def render_mailing_ui(result_df=None, metrics=None, config=None):
    st.markdown("### Mailing · Activación comercial")
    st.caption(
        "Prospección empresarial: localización de correos públicos, trazabilidad y campañas "
        "revisadas desde Microsoft 365."
    )

    if isinstance(result_df, pd.DataFrame) and not result_df.empty:
        candidates = result_df
        if "Candidato_Comercial" in candidates.columns:
            candidates = candidates[candidates["Candidato_Comercial"].fillna(False)]
        st.metric("Candidatos comerciales en la corrida activa", f"{len(candidates):,}")
        if not candidates.empty:
            st.download_button(
                "Exportar candidatos de CONCEDE (CSV)",
                candidates.to_csv(index=False).encode("utf-8-sig"),
                "concede_candidatos_para_activacion.csv",
                "text/csv",
            )
        st.caption(
            "La exportación conserva la fuente de cada registro para revisión comercial y trazabilidad."
        )

    mail_config, missing = read_mail_config(st.secrets)
    workspace_id = mail_config["workspace_id"]
    storage_error = None
    persistent_neon = False

    if not st.session_state.get("concede_mail_store_loaded", False):
        try:
            contacts, draft, persistent_neon = _initialize_store(mail_config)
            st.session_state["concede_mail_contacts"] = contacts
            st.session_state["concede_mail_draft"] = draft
            st.session_state["concede_mail_store_loaded"] = True
        except Exception as exc:
            storage_error = str(exc)
            st.session_state["concede_mail_contacts"] = pd.DataFrame(columns=_CONTACT_COLUMNS)
            st.session_state["concede_mail_draft"] = None
            st.session_state["concede_mail_store_loaded"] = False
    else:
        persistent_neon = bool(os.getenv("DATABASE_URL")) and bool(
            st.session_state.get("concede_mail_store_loaded", False)
        )

    if storage_error:
        st.error(
            "No se pudo inicializar la persistencia de Mailing. "
            "No se guardarán contactos ni borradores: " + storage_error
        )
    elif not persistent_neon:
        st.warning(
            "Neon no está configurado mediante DATABASE_URL. La base local de esta "
            "instancia no garantiza persistencia compartida entre despliegues."
        )
    else:
        st.caption(f"Persistencia Neon activa · Workspace: {workspace_id}")

    if "concede_mail_contacts" not in st.session_state:
        st.session_state["concede_mail_contacts"] = pd.DataFrame(columns=_CONTACT_COLUMNS)
    if "concede_mail_draft" not in st.session_state:
        st.session_state["concede_mail_draft"] = None

    contacts_tab, enrichment_tab, campaign_tab, m365_tab, send_tab = st.tabs(
        ["Contactos", "Enriquecimiento DENUE", "Campañas", "Microsoft 365", "Aprobación y envío"]
    )

    with contacts_tab:
        st.markdown("**Base compartida de contactos autorizados**")
        st.write(
            "CSV requerido: empresa, correo, contacto, fuente y autorizado. "
            "Solo correos válidos con fuente y autorización afirmativa pueden "
            "entrar a una campaña."
        )
        sample = pd.DataFrame([{
            "empresa": "Empresa ejemplo",
            "correo": "contacto@empresa.com",
            "contacto": "Nombre del contacto",
            "fuente": "URL o referencia de origen",
            "autorizado": "SI",
        }])
        st.download_button(
            "Descargar plantilla CSV",
            sample.to_csv(index=False).encode("utf-8-sig"),
            "plantilla_contactos_concede.csv",
            "text/csv",
        )
        upload = st.file_uploader(
            "Importar contactos (CSV)", type=["csv"], key="concede_mail_contacts_upload"
        )
        if upload is not None and st.button(
            "Validar e importar contactos", type="primary", disabled=not persistent_neon
        ):
            try:
                parsed = _read_contacts(upload)
                upsert_contacts(workspace_id, parsed.to_dict("records"))
                st.session_state["concede_mail_contacts"] = pd.DataFrame(
                    list_contacts(workspace_id), columns=_CONTACT_COLUMNS
                )
                st.success(
                    f"Contactos guardados: {len(parsed):,} · "
                    f"aptos para campaña: {int(parsed['apto'].sum()):,}"
                )
            except Exception as exc:
                st.error(f"No se guardaron los contactos: {exc}")

        contacts = st.session_state["concede_mail_contacts"]
        if not contacts.empty:
            st.dataframe(
                contacts[_CONTACT_COLUMNS],
                use_container_width=True,
                hide_index=True,
            )
            st.caption(
                "Los contactos no aptos se conservan para corrección, pero no "
                "pueden seleccionarse para envío."
            )

    with enrichment_tab:
        st.markdown("**Localización de correos y canales empresariales desde la ficha oficial DENUE**")
        st.write(
            "La consulta recupera únicamente los datos publicados por INEGI: correo, sitio web y teléfono. "
            "Un correo publicado no se considera autorizado para campañas."
        )
        st.caption("Fuente oficial: https://www.inegi.org.mx/servicios/api-denue/")
        # DENUE and the INEGI Indicators API are distinct services. Never
        # reuse a generic [mailing].token: it may belong to another INEGI API.
        # Accept only an explicitly named top-level or [denue] secret.
        denue_token = ""
        denue_token_source = ""
        denue_secret_error = ""
        secret_key_names = []
        nested_denue_key_names = []
        nested_mailing_key_names = []
        mailing_generic_token_present = False
        try:
            secret_values = dict(st.secrets)
            secret_key_names = sorted(str(key) for key in secret_values.keys())
            raw_token = secret_values.get("DENUE_API_TOKEN", "")
            if raw_token:
                denue_token = str(raw_token).strip()
                denue_token_source = "DENUE_API_TOKEN"
            else:
                section = secret_values.get("denue", {})
                if hasattr(section, "keys"):
                    nested_denue_key_names = sorted(str(key) for key in section.keys())
                    raw_token = (
                        section.get("DENUE_API_TOKEN", "")
                        or section.get("denue_api_token", "")
                        or section.get("api_token", "")
                        or section.get("token", "")
                    )
                    if raw_token:
                        denue_token = str(raw_token).strip()
                        denue_token_source = "[denue] token"
                mailing_section = secret_values.get("mailing", {})
                if hasattr(mailing_section, "keys"):
                    nested_mailing_key_names = sorted(str(key) for key in mailing_section.keys())
                    mailing_generic_token_present = bool(mailing_section.get("token", ""))
        except Exception as exc:
            denue_secret_error = type(exc).__name__

        if denue_token:
            st.success(f"Token DENUE configurado en Secrets ({denue_token_source}). La clave no se muestra.")
        elif mailing_generic_token_present:
            st.error(
                "Se detectó [mailing].token, pero no se utilizará para DENUE: "
                "puede pertenecer a otra API de INEGI. Configura una clave específica "
                "en DENUE_API_TOKEN o en [denue].api_token."
            )
        else:
            st.warning(
                "Falta una clave específica para la API DENUE. Configura "
                "DENUE_API_TOKEN o [denue].api_token en los Secrets de esta aplicación."
            )
            st.code('DENUE_API_TOKEN = "TOKEN_ESPECIFICO_DENUE"', language="toml")
            st.caption(
                "Usa una clave emitida para la API DENUE; no reutilices la clave de la API de Indicadores. "
                "No compartas el token ni lo guardes en GitHub."
            )
            if denue_secret_error:
                st.caption(f"Streamlit no pudo leer Secrets ({denue_secret_error}). Revisa el formato TOML.")
            elif secret_key_names:
                st.caption("Claves de Secrets visibles para esta app (solo nombres, nunca valores): " + ", ".join(secret_key_names))
                if "denue" in secret_values:
                    st.caption("Claves dentro de [denue]: " + (", ".join(nested_denue_key_names) or "ninguna"))
                if "mailing" in secret_values:
                    st.caption("Claves dentro de [mailing]: " + (", ".join(nested_mailing_key_names) or "ninguna"))

        if not persistent_neon:
            st.warning("El enriquecimiento queda bloqueado hasta confirmar persistencia Neon activa.")
        candidate_rows = pd.DataFrame()
        if isinstance(result_df, pd.DataFrame) and not result_df.empty:
            # Enrichment is a data-acquisition step, not a commercial-score gate.
            # Keep every row with a real DENUE establishment ID; prioritize
            # commercial candidates and higher Score V3 without excluding others.
            candidate_rows = result_df.copy()
            id_col = next(
                (
                    c for c in candidate_rows.columns
                    if str(c).strip().casefold().replace(" ", "_")
                    in {"id", "id_establecimiento", "id_denue", "denue_id"}
                ),
                None,
            )
            name_col = next(
                (
                    c for c in candidate_rows.columns
                    if str(c).strip().casefold().replace(" ", "_")
                    in {"nom_estab", "nombre", "empresa", "nombre_establecimiento"}
                ),
                None,
            )
            entity_col = next(
                (
                    c for c in candidate_rows.columns
                    if str(c).strip().casefold().replace(" ", "_")
                    in {"entidad", "estado", "nombre_entidad"}
                ),
                None,
            )
            municipality_col = next(
                (
                    c for c in candidate_rows.columns
                    if str(c).strip().casefold().replace(" ", "_")
                    in {"municipio", "nombre_municipio"}
                ),
                None,
            )
            score_col = "Score_V3" if "Score_V3" in candidate_rows.columns else None
            if id_col:
                candidate_rows[id_col] = candidate_rows[id_col].astype(str).str.strip()
                candidate_rows = candidate_rows[candidate_rows[id_col].str.fullmatch(r"\d+", na=False)]
                sort_cols = []
                ascending = []
                if "Candidato_Comercial" in candidate_rows.columns:
                    candidate_rows["_prioridad_enriquecimiento"] = candidate_rows["Candidato_Comercial"].fillna(False).astype(bool)
                    sort_cols.append("_prioridad_enriquecimiento")
                    ascending.append(False)
                if score_col:
                    sort_cols.append(score_col)
                    ascending.append(False)
                if sort_cols:
                    candidate_rows = candidate_rows.sort_values(sort_cols, ascending=ascending)
                candidate_rows = candidate_rows.drop_duplicates(subset=[id_col]).head(100)
                st.caption(
                    f"{len(candidate_rows):,} establecimientos con ID DENUE disponibles. "
                    "Se priorizan candidatos comerciales y Score V3, sin excluir otros registros."
                )
                options = {}
                for _, row in candidate_rows.iterrows():
                    label_name = str(row.get(name_col, "Establecimiento")) if name_col else "Establecimiento"
                    options[f"{label_name} · DENUE {row[id_col]}"] = row[id_col]
                selected_labels = st.multiselect(
                    "Selecciona establecimientos para consultar su ficha (máximo 25 por corrida)",
                    list(options),
                    key="concede_denue_selected",
                )
                if len(selected_labels) > 25:
                    st.warning("Selecciona como máximo 25 establecimientos por consulta.")
                if st.button(
                    "Consultar fichas oficiales INEGI",
                    type="primary",
                    disabled=(not denue_token or not persistent_neon or not selected_labels or len(selected_labels) > 25),
                ):
                    found = []
                    failures = []
                    progress = st.progress(0)
                    for index, label in enumerate(selected_labels, start=1):
                        denue_id = options[label]
                        source_row = candidate_rows.loc[candidate_rows[id_col].eq(denue_id)].iloc[0]
                        source_name = (
                            str(source_row.get(name_col, "")).strip() if name_col else label.split(" · DENUE ")[0]
                        )
                        source_entity = (
                            str(source_row.get(entity_col, "")).strip() if entity_col else ""
                        )
                        source_municipality = (
                            str(source_row.get(municipality_col, "")).strip() if municipality_col else ""
                        )
                        try:
                            record = fetch_denue_ficha(
                                denue_id,
                                denue_token,
                                establishment_name=source_name,
                                entity=source_entity,
                                municipality=source_municipality,
                            )
                            record["empresa"] = record["empresa"] or source_name
                            public_emails = []
                            if record.get("correo"):
                                public_emails.append({
                                    "correo": record["correo"],
                                    "fuente": record.get("fuente", "https://www.inegi.org.mx/servicios/api-denue/"),
                                    "tipo_fuente": "INEGI_DENUE_FICHA",
                                })
                            elif record.get("sitio_web"):
                                public_emails = find_public_business_emails(record["sitio_web"])
                            record["correos_publicos"] = public_emails
                            found.append(record)
                        except DenueEnrichmentError as exc:
                            failures.append(f"{denue_id}: {exc}")
                        progress.progress(index / len(selected_labels))
                    if found:
                        try:
                            saved = upsert_enrichment_records(workspace_id, found)
                            email_rows = []
                            for record in found:
                                for email_record in record.get("correos_publicos", []):
                                    email_rows.append({
                                        **email_record,
                                        "denue_id": record["denue_id"],
                                        "empresa": record.get("empresa", ""),
                                    })
                            saved_emails = upsert_public_emails(workspace_id, email_rows) if email_rows else 0
                            st.success(
                                f"Fichas guardadas en Neon: {saved:,} · "
                                f"correos públicos localizados: {saved_emails:,}."
                            )
                        except Exception as exc:
                            st.error(f"Las consultas se realizaron, pero no se guardaron en Neon: {exc}")
                    if failures:
                        st.warning("Consultas con incidencias: " + " · ".join(failures[:10]))
            else:
                st.info("La base activa no contiene la columna Id de establecimiento DENUE. No se harán búsquedas por nombre para evitar asociar fichas equivocadas.")
        else:
            st.info("Ejecuta primero una corrida con la base DENUE para seleccionar prospectos.")
        try:
            enriched = pd.DataFrame(list_enrichment_records(workspace_id)) if persistent_neon else pd.DataFrame()
        except Exception as exc:
            enriched = pd.DataFrame()
            st.error(f"No se pudo consultar el historial de enriquecimiento en Neon: {exc}")
        if not enriched.empty:
            st.markdown("**Historial de enriquecimiento**")
            st.dataframe(enriched, use_container_width=True, hide_index=True)
            public_emails = pd.DataFrame(list_public_emails(workspace_id)) if persistent_neon else pd.DataFrame()
            if not public_emails.empty:
                st.markdown("**Correos empresariales públicos localizados**")
                st.caption("Cada correo conserva la página exacta donde fue publicado. Revisa la pertinencia del contacto antes de incorporarlo a una campaña.")
                st.dataframe(public_emails, use_container_width=True, hide_index=True)
                st.download_button(
                    "Exportar directorio de correos públicos (CSV)",
                    public_emails.to_csv(index=False).encode("utf-8-sig"),
                    "concede_directorio_correos_publicos.csv",
                    "text/csv",
                )
                st.caption("La publicación de un correo permite consultarlo y documentar su origen; no sustituye la revisión de las reglas aplicables a cada campaña.")
            else:
                st.info("Todavía no hay correos públicos localizados. Al consultar fichas, Mailing revisará también las páginas de contacto de los sitios empresariales disponibles.")


    with campaign_tab:
        contacts = st.session_state["concede_mail_contacts"]
        if contacts.empty or not contacts["apto"].any():
            st.info(
                "Primero importa contactos con correo válido, fuente y autorización "
                "documentada."
            )
        else:
            eligible = contacts[contacts["apto"]]
            options = {
                f"{row.empresa} · {row.correo}": row.correo
                for row in eligible.itertuples(index=False)
            }
            selected = st.multiselect("Destinatarios", list(options), key="concede_mail_selected")
            campaign_name = st.text_input(
                "Nombre de campaña",
                "CONCEDE · Activación comercial",
                key="concede_mail_campaign_name",
            )
            subject = st.text_input("Asunto", key="concede_mail_subject")
            body = st.text_area("Mensaje", height=230, key="concede_mail_body")
            if selected:
                selected_rows = eligible[
                    eligible["correo"].isin([options[item] for item in selected])
                ]
                st.markdown("**Destinatarios seleccionados**")
                st.dataframe(
                    selected_rows[["empresa", "contacto", "correo", "fuente"]],
                    use_container_width=True,
                    hide_index=True,
                )
            if st.button("Guardar borrador", type="primary", disabled=not persistent_neon):
                if not selected:
                    st.error("Selecciona al menos un destinatario.")
                elif not subject.strip() or not body.strip():
                    st.error("El asunto y el mensaje son obligatorios.")
                else:
                    draft = {
                        "id": str(uuid.uuid4()),
                        "name": campaign_name.strip(),
                        "subject": subject.strip(),
                        "body": body.strip(),
                        "recipients": [options[item] for item in selected],
                    }
                    try:
                        save_draft(workspace_id, draft)
                        st.session_state["concede_mail_draft"] = draft
                        st.success("Borrador guardado en Neon. No se ha enviado ningún correo.")
                    except Exception as exc:
                        st.error(f"No se pudo guardar el borrador: {exc}")

        draft = st.session_state.get("concede_mail_draft")
        if draft:
            st.info(f"Borrador actual: {draft['name']} · {len(draft['recipients'])} destinatario(s)")

    with m365_tab:
        st.markdown("**Buzón institucional autorizado**")
        st.write(f"Remitente permitido: **{APPROVED_SENDER_MAILBOX}**")
        if missing:
            st.warning("Falta configurar en Streamlit Secrets: " + ", ".join(missing))
            st.code(
                '[mailing]\ntenant_id = "..."\nclient_id = "..."\n'
                'client_secret = "..."\nsender_mailbox = "C@4msfts.com"\n'
                'workspace_id = "4msfts"',
                language="toml",
            )
        else:
            render_mail_auth(mail_config)

    with send_tab:
        draft = st.session_state.get("concede_mail_draft")
        if not draft:
            st.info("No hay un borrador listo para aprobación.")
        else:
            st.markdown(f"**{draft['name']}**")
            st.write(
                f"Remitente: {APPROVED_SENDER_MAILBOX} · "
                f"Destinatarios: {len(draft['recipients'])}"
            )
            st.dataframe(
                st.session_state["concede_mail_contacts"].loc[
                    st.session_state["concede_mail_contacts"]["correo"].isin(
                        draft["recipients"]
                    ),
                    ["empresa", "contacto", "correo", "fuente"],
                ],
                use_container_width=True,
                hide_index=True,
            )
            st.text(f"Asunto: {draft['subject']}\n\n{draft['body']}")
            st.warning(
                "El envío ocurre solo al pulsar el botón final. "
                "Los destinatarios se envían en copia oculta (BCC)."
            )
            if not persistent_neon:
                st.error(
                    "Envío bloqueado: Mailing requiere persistencia Neon activa. "
                    "No se permite operar campañas desde la base SQLite local."
                )
            approved = st.checkbox(
                "Apruebo expresamente el contenido y la lista completa de destinatarios "
                "para enviar desde C@4msfts.com.",
                key=f"concede_mail_explicit_approval_{draft['id']}",
            )
            token = st.session_state.get("concede_mail_access_token")
            if not token:
                st.info("Conecta Microsoft 365 en la pestaña correspondiente antes de enviar.")
            if st.button(
                "Enviar campaña aprobada",
                type="primary",
                disabled=(not approved or not token or not persistent_neon),
            ):
                try:
                    allowed, blocked = validate_campaign_recipients(
                        workspace_id, draft["recipients"]
                    )
                    if blocked or len(allowed) != len(draft["recipients"]):
                        raise MailDeliveryError(
                            "Envío bloqueado: hay destinatarios sin autorización vigente "
                            "o que ya no pertenecen a la base apta. Revisa la campaña antes de continuar."
                        )
                    outcome = send_graph_mail(
                        mail_config,
                        draft["recipients"],
                        draft["subject"],
                        draft["body"],
                        access_token=token,
                    )
                    st.session_state["concede_mail_last_send"] = {
                        "campaign": draft["name"],
                        "recipient_count": outcome["recipient_count"],
                        "status": "ACEPTADO_POR_GRAPH",
                    }
                    st.session_state["concede_mail_draft"] = None
                    try:
                        mark_accepted(workspace_id, draft["id"])
                        st.success(
                            f"Microsoft Graph aceptó el envío a {outcome['recipient_count']} "
                            "destinatario(s). HTTP 202 confirma aceptación, no entrega final."
                        )
                    except Exception as exc:
                        st.warning(
                            "Microsoft Graph aceptó el envío, pero no se pudo actualizar "
                            f"el historial de Neon: {exc}. No reenvíes sin revisar Elementos enviados."
                        )
                except MailDeliveryError as exc:
                    st.error(str(exc))
