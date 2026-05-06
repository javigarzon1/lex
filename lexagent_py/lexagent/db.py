"""Persistencia local con SQLite."""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
import uuid
from datetime import datetime
from typing import Any

DB_PATH = os.environ.get("LEXAGENT_DB", "lexagent.db")


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                name TEXT NOT NULL,
                description TEXT,
                doc_type TEXT NOT NULL,
                system_prompt TEXT NOT NULL,
                form_fields TEXT NOT NULL,
                knowledge_base TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS validations (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                form_data TEXT NOT NULL,
                report_md TEXT,
                document_md TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE
            );
            """
        )
        # Migración suave: añadir columnas si faltan en BBDD antiguas
        cols = {r[1] for r in c.execute("PRAGMA table_info(agents)").fetchall()}
        if "user_id" not in cols:
            c.execute("ALTER TABLE agents ADD COLUMN user_id TEXT")
        if "updated_at" not in cols:
            c.execute("ALTER TABLE agents ADD COLUMN updated_at TEXT")
            c.execute("UPDATE agents SET updated_at = created_at WHERE updated_at IS NULL")


# -------------------- Users / Sessions --------------------
def _hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()


def create_user(email: str, password: str) -> str:
    uid = str(uuid.uuid4())
    salt = secrets.token_hex(16)
    with _conn() as c:
        c.execute(
            "INSERT INTO users VALUES (?,?,?,?,?)",
            (uid, email.lower().strip(), _hash(password, salt), salt, datetime.utcnow().isoformat()),
        )
    return uid


def get_user_by_email(email: str) -> dict[str, Any] | None:
    with _conn() as c:
        r = c.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),)).fetchone()
    return dict(r) if r else None


def verify_password(user: dict[str, Any], password: str) -> bool:
    return _hash(password, user["salt"]) == user["password_hash"]


def create_session(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    with _conn() as c:
        c.execute(
            "INSERT INTO sessions VALUES (?,?,?)",
            (token, user_id, datetime.utcnow().isoformat()),
        )
    return token


def user_for_token(token: str) -> dict[str, Any] | None:
    with _conn() as c:
        r = c.execute(
            "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token = ?",
            (token,),
        ).fetchone()
    return dict(r) if r else None


def delete_session(token: str) -> None:
    with _conn() as c:
        c.execute("DELETE FROM sessions WHERE token = ?", (token,))


# -------------------- Agents --------------------
def create_agent(*, user_id: str, name: str, description: str, doc_type: str,
                 system_prompt: str, form_fields: list[dict[str, Any]],
                 knowledge_base: str) -> str:
    aid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    with _conn() as c:
        c.execute(
            "INSERT INTO agents (id,user_id,name,description,doc_type,system_prompt,form_fields,knowledge_base,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (aid, user_id, name, description, doc_type, system_prompt,
             json.dumps(form_fields, ensure_ascii=False), knowledge_base, now, now),
        )
    return aid


def update_agent(*, agent_id: str, user_id: str, name: str, description: str,
                 doc_type: str, system_prompt: str,
                 form_fields: list[dict[str, Any]], knowledge_base: str) -> bool:
    with _conn() as c:
        cur = c.execute(
            "UPDATE agents SET name=?, description=?, doc_type=?, system_prompt=?, "
            "form_fields=?, knowledge_base=?, updated_at=? "
            "WHERE id=? AND user_id=?",
            (name, description, doc_type, system_prompt,
             json.dumps(form_fields, ensure_ascii=False), knowledge_base,
             datetime.utcnow().isoformat(), agent_id, user_id),
        )
        return cur.rowcount > 0


def list_agents(*, user_id: str, search: str = "", offset: int = 0,
                limit: int = 20) -> dict[str, Any]:
    q = "%" + (search or "").lower() + "%"
    with _conn() as c:
        total = c.execute(
            "SELECT COUNT(*) FROM agents WHERE user_id=? AND LOWER(name) LIKE ?",
            (user_id, q),
        ).fetchone()[0]
        rows = c.execute(
            "SELECT id, name, description, doc_type, created_at, updated_at "
            "FROM agents WHERE user_id=? AND LOWER(name) LIKE ? "
            "ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (user_id, q, limit, offset),
        ).fetchall()
    return {"total": total, "items": [dict(r) for r in rows]}


def get_agent(agent_id: str, user_id: str | None = None) -> dict[str, Any] | None:
    with _conn() as c:
        if user_id:
            row = c.execute("SELECT * FROM agents WHERE id=? AND user_id=?",
                            (agent_id, user_id)).fetchone()
        else:
            row = c.execute("SELECT * FROM agents WHERE id=?", (agent_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    d["form_fields"] = json.loads(d["form_fields"])
    return d


def delete_agent(agent_id: str, user_id: str) -> bool:
    with _conn() as c:
        cur = c.execute("DELETE FROM agents WHERE id=? AND user_id=?", (agent_id, user_id))
        return cur.rowcount > 0


def save_validation(*, agent_id: str, form_data: dict[str, Any],
                    report_md: str, document_md: str) -> str:
    vid = str(uuid.uuid4())
    with _conn() as c:
        c.execute(
            "INSERT INTO validations VALUES (?,?,?,?,?,?)",
            (vid, agent_id, json.dumps(form_data, ensure_ascii=False),
             report_md, document_md, datetime.utcnow().isoformat()),
        )
    return vid


def list_validations(agent_id: str) -> list[dict[str, Any]]:
    with _conn() as c:
        rows = c.execute(
            "SELECT id, created_at FROM validations WHERE agent_id=? ORDER BY created_at DESC",
            (agent_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_validation(vid: str) -> dict[str, Any] | None:
    with _conn() as c:
        row = c.execute("SELECT * FROM validations WHERE id=?", (vid,)).fetchone()
    if not row:
        return None
    d = dict(row)
    d["form_data"] = json.loads(d["form_data"])
    return d
