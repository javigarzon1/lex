"""Interfaz Streamlit de LexAgent."""
from __future__ import annotations

import json
from typing import Any

import streamlit as st

from lexagent import ai, db, export, knowledge_loader

st.set_page_config(page_title="LexAgent", page_icon="⚖️", layout="wide")
db.init_db()

# ---------- estado ----------
if "view" not in st.session_state:
    st.session_state.view = "list"
if "current_agent_id" not in st.session_state:
    st.session_state.current_agent_id = None
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "field_count" not in st.session_state:
    st.session_state.field_count = 3


def go(view: str, agent_id: str | None = None) -> None:
    st.session_state.view = view
    st.session_state.current_agent_id = agent_id
    st.session_state.last_result = None


# ---------- sidebar ----------
with st.sidebar:
    st.title("⚖️ LexAgent")
    st.caption("Agentes IA para documentos jurídicos")
    if st.button("📋 Mis agentes", use_container_width=True):
        go("list")
    if st.button("➕ Crear agente", use_container_width=True):
        go("create")
    st.divider()
    st.caption(f"Modelo: `{ai.DEFAULT_MODEL}`")


# ---------- vista: lista ----------
def view_list() -> None:
    st.header("Mis agentes")
    agents = db.list_agents()
    if not agents:
        st.info("Aún no tienes agentes. Crea el primero con el botón de la barra lateral.")
        return
    for a in agents:
        with st.container(border=True):
            c1, c2, c3 = st.columns([5, 1, 1])
            with c1:
                st.markdown(f"**{a['name']}**  \n*{a['doc_type']}*")
                if a["description"]:
                    st.caption(a["description"])
            with c2:
                if st.button("Abrir", key=f"open_{a['id']}", use_container_width=True):
                    go("agent", a["id"])
                    st.rerun()
            with c3:
                if st.button("🗑", key=f"del_{a['id']}", use_container_width=True):
                    db.delete_agent(a["id"])
                    st.rerun()


# ---------- vista: crear ----------
def view_create() -> None:
    st.header("Crear agente")

    name = st.text_input("Nombre del agente *", placeholder="Validador de avales internacionales")
    description = st.text_area("Descripción", placeholder="Para qué sirve este agente")
    doc_type = st.selectbox(
        "Tipo de documento",
        ["aval_internacional", "contragarantia", "contrato", "carta_juridica", "informe", "otro"],
    )
    system_prompt = st.text_area(
        "Prompt de sistema *",
        height=180,
        value=(
            "Eres un asistente jurídico experto en garantías y avales bancarios "
            "internacionales. Analiza los datos del caso, identifica posición de la "
            "entidad (garantía directa / contragarantía emitida / recibida), detecta "
            "reservas aplicables conforme a la base de conocimiento aportada, propone "
            "modificaciones de texto y redacta el documento solicitado en español "
            "jurídico claro y preciso."
        ),
    )

    st.subheader("Campos del formulario dinámico")
    st.caption("Define qué datos pedirás al usuario al ejecutar el agente.")

    cols = st.columns([1, 1])
    if cols[0].button("➕ Añadir campo"):
        st.session_state.field_count += 1
    if cols[1].button("➖ Quitar campo") and st.session_state.field_count > 1:
        st.session_state.field_count -= 1

    fields: list[dict[str, Any]] = []
    for i in range(st.session_state.field_count):
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 2, 1])
            label = c1.text_input("Etiqueta", key=f"flabel_{i}", value=_default_label(i))
            ftype = c2.selectbox(
                "Tipo",
                ["text", "textarea", "number", "date", "select"],
                key=f"ftype_{i}",
                index=_default_type_index(i),
            )
            required = c3.checkbox("Obligatorio", key=f"freq_{i}", value=True)
            options = ""
            if ftype == "select":
                options = st.text_input(
                    "Opciones (separadas por coma)",
                    key=f"fopt_{i}",
                    value="Garantía directa,Contragarantía emitida,Contragarantía recibida",
                )
            if label.strip():
                fields.append(
                    {
                        "key": _slug(label),
                        "label": label.strip(),
                        "type": ftype,
                        "required": required,
                        "options": [o.strip() for o in options.split(",") if o.strip()],
                    }
                )

    st.subheader("Base de conocimiento")
    builtin = knowledge_loader.list_builtin()
    selected_builtin = st.multiselect(
        "Manuales incluidos", builtin, default=builtin[:1] if builtin else []
    )
    uploads = st.file_uploader(
        "Sube tus propios documentos (PDF / DOCX / TXT)",
        type=["pdf", "docx", "txt", "md"],
        accept_multiple_files=True,
    )

    if st.button("✅ Crear agente", type="primary"):
        if not name.strip() or not system_prompt.strip():
            st.error("Nombre y prompt son obligatorios.")
            return
        kb_parts = []
        for n in selected_builtin:
            kb_parts.append(f"### {n}\n" + knowledge_loader.load_builtin(n))
        for f in uploads or []:
            try:
                kb_parts.append(f"### {f.name}\n" + knowledge_loader.load_bytes(f.name, f.read()))
            except Exception as e:  # noqa: BLE001
                st.warning(f"No se pudo procesar {f.name}: {e}")
        kb = "\n\n".join(kb_parts)

        aid = db.create_agent(
            name=name.strip(),
            description=description.strip(),
            doc_type=doc_type,
            system_prompt=system_prompt.strip(),
            form_fields=fields,
            knowledge_base=kb,
        )
        st.success("Agente creado.")
        go("agent", aid)
        st.rerun()


def _default_label(i: int) -> str:
    defaults = [
        "Posición de la entidad",
        "Importe garantizado",
        "Beneficiario",
        "Legislación aplicable",
        "Plazo / vencimiento",
    ]
    return defaults[i] if i < len(defaults) else ""


def _default_type_index(i: int) -> int:
    if i == 0:
        return 4  # select
    if i == 1:
        return 0  # text
    return 0


def _slug(s: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_") or "field"


# ---------- vista: agente / ejecución ----------
def view_agent() -> None:
    agent = db.get_agent(st.session_state.current_agent_id or "")
    if not agent:
        st.error("Agente no encontrado.")
        return

    st.header(agent["name"])
    if agent["description"]:
        st.caption(agent["description"])

    tab_run, tab_history, tab_info = st.tabs(["▶️ Ejecutar", "🕘 Historial", "ℹ️ Configuración"])

    with tab_run:
        st.subheader("Datos del caso")
        form_data: dict[str, Any] = {}
        with st.form(key="run_form"):
            for f in agent["form_fields"]:
                key = f"in_{f['key']}"
                if f["type"] == "textarea":
                    form_data[f["label"]] = st.text_area(f["label"], key=key)
                elif f["type"] == "number":
                    form_data[f["label"]] = st.number_input(f["label"], key=key, step=1.0)
                elif f["type"] == "date":
                    d = st.date_input(f["label"], key=key)
                    form_data[f["label"]] = d.isoformat() if d else ""
                elif f["type"] == "select":
                    form_data[f["label"]] = st.selectbox(f["label"], f["options"] or [""], key=key)
                else:
                    form_data[f["label"]] = st.text_input(f["label"], key=key)
            submitted = st.form_submit_button("🚀 Ejecutar agente", type="primary")

        if submitted:
            missing = [
                f["label"]
                for f in agent["form_fields"]
                if f["required"] and not str(form_data.get(f["label"], "")).strip()
            ]
            if missing:
                st.error("Faltan campos obligatorios: " + ", ".join(missing))
            else:
                with st.spinner("Generando con IA..."):
                    try:
                        result = ai.run_agent(
                            system_prompt=agent["system_prompt"],
                            knowledge_base=agent["knowledge_base"],
                            form_data=form_data,
                            agent_name=agent["name"],
                            doc_type=agent["doc_type"],
                        )
                        db.save_validation(
                            agent_id=agent["id"],
                            form_data=form_data,
                            report_md=result["report"],
                            document_md=result["document"],
                        )
                        st.session_state.last_result = result
                    except Exception as e:  # noqa: BLE001
                        st.error(str(e))

        if st.session_state.last_result:
            _render_result(st.session_state.last_result, agent["name"])

    with tab_history:
        items = db.list_validations(agent["id"])
        if not items:
            st.info("Sin ejecuciones todavía.")
        for it in items:
            with st.expander(f"Ejecución del {it['created_at']}"):
                v = db.get_validation(it["id"])
                if v:
                    st.json(v["form_data"])
                    _render_result({"report": v["report_md"], "document": v["document_md"]}, agent["name"])

    with tab_info:
        st.markdown("**Tipo:** " + agent["doc_type"])
        st.markdown("**Prompt de sistema:**")
        st.code(agent["system_prompt"])
        st.markdown(f"**Campos:** {len(agent['form_fields'])}")
        st.json(agent["form_fields"])
        st.markdown(f"**Tamaño base de conocimiento:** {len(agent['knowledge_base'])} caracteres")


def _render_result(result: dict[str, str], agent_name: str) -> None:
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📋 Informe de validación")
        st.markdown(result.get("report") or "_(vacío)_")
        if result.get("report"):
            st.download_button(
                "⬇️ PDF informe",
                data=export.md_to_pdf(result["report"], f"Informe — {agent_name}"),
                file_name="informe.pdf",
                mime="application/pdf",
            )
            st.download_button(
                "⬇️ DOCX informe",
                data=export.md_to_docx(result["report"], f"Informe — {agent_name}"),
                file_name="informe.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
    with c2:
        st.subheader("📄 Documento jurídico")
        st.markdown(result.get("document") or "_(vacío)_")
        if result.get("document"):
            st.download_button(
                "⬇️ PDF documento",
                data=export.md_to_pdf(result["document"], f"Documento — {agent_name}"),
                file_name="documento.pdf",
                mime="application/pdf",
            )
            st.download_button(
                "⬇️ DOCX documento",
                data=export.md_to_docx(result["document"], f"Documento — {agent_name}"),
                file_name="documento.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )


# ---------- router ----------
view = st.session_state.view
if view == "list":
    view_list()
elif view == "create":
    view_create()
elif view == "agent":
    view_agent()
