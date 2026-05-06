"""Carga de ficheros para la base de conocimiento (TXT, PDF, DOCX)."""
from __future__ import annotations

import io
import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).parent
BUILTIN_DIR = PACKAGE_DIR / "knowledge"


def list_builtin() -> list[str]:
    if not BUILTIN_DIR.exists():
        return []
    return sorted(p.name for p in BUILTIN_DIR.iterdir() if p.is_file())


def load_builtin(name: str) -> str:
    path = BUILTIN_DIR / name
    return path.read_text(encoding="utf-8")


def load_bytes(filename: str, raw: bytes) -> str:
    """Extrae texto de un fichero subido (TXT/MD, PDF o DOCX)."""
    ext = os.path.splitext(filename)[1].lower()
    if ext in {".txt", ".md"}:
        return raw.decode("utf-8", errors="replace")
    if ext == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(raw))
        return "\n\n".join((page.extract_text() or "") for page in reader.pages)
    if ext == ".docx":
        from docx import Document

        doc = Document(io.BytesIO(raw))
        return "\n".join(p.text for p in doc.paragraphs)
    raise ValueError(f"Formato no soportado: {ext}")
