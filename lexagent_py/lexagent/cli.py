"""Interfaz CLI: crear / listar / ejecutar agentes."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from lexagent import ai, db, export, knowledge_loader


def _cmd_list(_: argparse.Namespace) -> int:
    db.init_db()
    for a in db.list_agents():
        print(f"{a['id']}  {a['name']}  ({a['doc_type']})")
    return 0


def _cmd_create(args: argparse.Namespace) -> int:
    db.init_db()
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))

    kb_parts = []
    for n in spec.get("builtin_knowledge", []):
        kb_parts.append(f"### {n}\n" + knowledge_loader.load_builtin(n))
    for path in spec.get("knowledge_files", []):
        p = Path(path)
        kb_parts.append(f"### {p.name}\n" + knowledge_loader.load_bytes(p.name, p.read_bytes()))

    aid = db.create_agent(
        name=spec["name"],
        description=spec.get("description", ""),
        doc_type=spec.get("doc_type", "otro"),
        system_prompt=spec["system_prompt"],
        form_fields=spec.get("form_fields", []),
        knowledge_base="\n\n".join(kb_parts),
    )
    print(f"Agente creado: {aid}")
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    db.init_db()
    agent = db.get_agent(args.agent_id)
    if not agent:
        print("Agente no encontrado", file=sys.stderr)
        return 1

    form_data = json.loads(Path(args.data).read_text(encoding="utf-8"))
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Ejecutando agente...")
    result = ai.run_agent(
        system_prompt=agent["system_prompt"],
        knowledge_base=agent["knowledge_base"],
        form_data=form_data,
        agent_name=agent["name"],
        doc_type=agent["doc_type"],
    )

    (out_dir / "report.md").write_text(result["report"], encoding="utf-8")
    (out_dir / "document.md").write_text(result["document"], encoding="utf-8")
    (out_dir / "report.pdf").write_bytes(export.md_to_pdf(result["report"], "Informe"))
    (out_dir / "document.pdf").write_bytes(export.md_to_pdf(result["document"], "Documento"))
    (out_dir / "report.docx").write_bytes(export.md_to_docx(result["report"], "Informe"))
    (out_dir / "document.docx").write_bytes(export.md_to_docx(result["document"], "Documento"))

    db.save_validation(
        agent_id=agent["id"],
        form_data=form_data,
        report_md=result["report"],
        document_md=result["document"],
    )
    print(f"OK. Salida en {out_dir.resolve()}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="lexagent")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="Lista los agentes").set_defaults(func=_cmd_list)

    pc = sub.add_parser("create", help="Crea un agente desde un JSON")
    pc.add_argument("spec", help="Ruta al JSON de definición del agente")
    pc.set_defaults(func=_cmd_create)

    pr = sub.add_parser("run", help="Ejecuta un agente")
    pr.add_argument("agent_id")
    pr.add_argument("--data", required=True, help="JSON con datos del formulario")
    pr.add_argument("--out", default="./salida", help="Carpeta de salida")
    pr.set_defaults(func=_cmd_run)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
