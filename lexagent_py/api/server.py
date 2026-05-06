"""API REST para LexAgent (FastAPI). Expone el motor Python al frontend Java."""
from __future__ import annotations

import os
import sys
from typing import Any

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr, Field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lexagent import ai, db, export, knowledge_loader  # noqa: E402

db.init_db()

app = FastAPI(title="LexAgent API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------- Auth helpers --------------------
def current_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Falta token")
    token = authorization.split(" ", 1)[1].strip()
    user = db.user_for_token(token)
    if not user:
        raise HTTPException(401, "Sesión inválida")
    return user


# -------------------- Modelos --------------------
class FormField(BaseModel):
    name: str
    label: str
    type: str = "text"
    options: list[str] | None = None
    required: bool = False


class AgentPayload(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    doc_type: str = Field(min_length=1, max_length=80)
    system_prompt: str = Field(min_length=1)
    form_fields: list[FormField] = []
    knowledge_base: str = ""


class RunRequest(BaseModel):
    form_data: dict[str, Any]


class ExportRequest(BaseModel):
    markdown: str
    filename: str = "documento"
    format: str = "pdf"


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# -------------------- Endpoints públicos --------------------
@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/signup")
def signup(payload: SignupRequest):
    if db.get_user_by_email(payload.email):
        raise HTTPException(409, "Email ya registrado")
    uid = db.create_user(payload.email, payload.password)
    token = db.create_session(uid)
    return {"token": token, "email": payload.email}


@app.post("/auth/login")
def login(payload: LoginRequest):
    user = db.get_user_by_email(payload.email)
    if not user or not db.verify_password(user, payload.password):
        raise HTTPException(401, "Credenciales inválidas")
    token = db.create_session(user["id"])
    return {"token": token, "email": user["email"]}


@app.post("/auth/logout")
def logout(user=Depends(current_user), authorization: str | None = Header(default=None)):
    if authorization:
        db.delete_session(authorization.split(" ", 1)[1].strip())
    return {"ok": True}


@app.get("/auth/me")
def me(user=Depends(current_user)):
    return {"id": user["id"], "email": user["email"]}


# -------------------- Agentes (autenticados) --------------------
@app.get("/agents")
def list_agents(user=Depends(current_user),
                search: str = Query(default=""),
                page: int = Query(default=1, ge=1),
                page_size: int = Query(default=20, ge=1, le=100)):
    return db.list_agents(user_id=user["id"], search=search,
                          offset=(page - 1) * page_size, limit=page_size)


@app.get("/agents/{agent_id}")
def get_agent(agent_id: str, user=Depends(current_user)):
    a = db.get_agent(agent_id, user_id=user["id"])
    if not a:
        raise HTTPException(404, "Agente no encontrado")
    return a


@app.post("/agents")
def create_agent(payload: AgentPayload, user=Depends(current_user)):
    aid = db.create_agent(
        user_id=user["id"],
        name=payload.name, description=payload.description,
        doc_type=payload.doc_type, system_prompt=payload.system_prompt,
        form_fields=[f.model_dump() for f in payload.form_fields],
        knowledge_base=payload.knowledge_base,
    )
    return {"id": aid}


@app.put("/agents/{agent_id}")
def update_agent(agent_id: str, payload: AgentPayload, user=Depends(current_user)):
    ok = db.update_agent(
        agent_id=agent_id, user_id=user["id"],
        name=payload.name, description=payload.description,
        doc_type=payload.doc_type, system_prompt=payload.system_prompt,
        form_fields=[f.model_dump() for f in payload.form_fields],
        knowledge_base=payload.knowledge_base,
    )
    if not ok:
        raise HTTPException(404, "Agente no encontrado")
    return {"ok": True}


@app.delete("/agents/{agent_id}")
def delete_agent(agent_id: str, user=Depends(current_user)):
    if not db.delete_agent(agent_id, user_id=user["id"]):
        raise HTTPException(404, "Agente no encontrado")
    return {"ok": True}


@app.post("/agents/{agent_id}/run")
def run_agent(agent_id: str, payload: RunRequest, user=Depends(current_user)):
    a = db.get_agent(agent_id, user_id=user["id"])
    if not a:
        raise HTTPException(404, "Agente no encontrado")
    try:
        result = ai.run_agent(
            system_prompt=a["system_prompt"],
            knowledge_base=a["knowledge_base"],
            form_data=payload.form_data,
            agent_name=a["name"],
            doc_type=a["doc_type"],
        )
    except Exception as e:
        raise HTTPException(500, str(e))
    vid = db.save_validation(
        agent_id=agent_id, form_data=payload.form_data,
        report_md=result.get("report", ""), document_md=result.get("document", ""),
    )
    return {"validation_id": vid, **result}


@app.get("/agents/{agent_id}/validations")
def list_validations(agent_id: str, user=Depends(current_user)):
    a = db.get_agent(agent_id, user_id=user["id"])
    if not a:
        raise HTTPException(404)
    return db.list_validations(agent_id)


@app.get("/validations/{vid}")
def get_validation(vid: str, user=Depends(current_user)):
    v = db.get_validation(vid)
    if not v:
        raise HTTPException(404)
    a = db.get_agent(v["agent_id"], user_id=user["id"])
    if not a:
        raise HTTPException(404)
    return v


@app.post("/export")
def export_doc(payload: ExportRequest, user=Depends(current_user)):
    if payload.format == "pdf":
        data = export.md_to_pdf(payload.markdown, title=payload.filename)
        media = "application/pdf"
        ext = "pdf"
    elif payload.format == "docx":
        data = export.md_to_docx(payload.markdown, title=payload.filename)
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ext = "docx"
    else:
        raise HTTPException(400, "Formato no soportado")
    return Response(content=data, media_type=media,
                    headers={"Content-Disposition": f'attachment; filename="{payload.filename}.{ext}"'})


@app.post("/knowledge/extract")
async def extract_knowledge(file: UploadFile = File(...), user=Depends(current_user)):
    raw = await file.read()
    try:
        text = knowledge_loader.load_bytes(file.filename or "archivo.txt", raw)
    except Exception as e:
        raise HTTPException(400, f"No se pudo extraer texto: {e}")
    return {"text": text}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
