#!/usr/bin/env python3
"""
LexAgent - Instalador automático.

Funciones:
  1. Verifica versión de Python (>=3.9).
  2. Crea un entorno virtual `.venv` si no existe.
  3. Instala las dependencias de requirements.txt dentro del venv.
  4. Comprueba la variable LOVABLE_API_KEY (la pide si falta y se guarda en .env).
  5. Lanza automáticamente la app Streamlit.

Uso:
    python install.py            # instala y arranca Streamlit
    python install.py --cli      # instala y abre la CLI
    python install.py --no-run   # solo instala
"""
from __future__ import annotations

import os
import sys
import subprocess
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".venv"
REQS = ROOT / "requirements.txt"
ENV_FILE = ROOT / ".env"
APP_FILE = ROOT / "lexagent" / "app.py"

MIN_PY = (3, 9)


def info(msg: str) -> None:
    print(f"\033[1;36m[LexAgent]\033[0m {msg}")


def warn(msg: str) -> None:
    print(f"\033[1;33m[!]\033[0m {msg}")


def err(msg: str) -> None:
    print(f"\033[1;31m[ERROR]\033[0m {msg}")


def check_python() -> None:
    if sys.version_info < MIN_PY:
        err(f"Se requiere Python {MIN_PY[0]}.{MIN_PY[1]}+ (tienes {sys.version.split()[0]}).")
        sys.exit(1)
    info(f"Python {sys.version.split()[0]} OK")


def venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def create_venv() -> None:
    if VENV_DIR.exists() and venv_python().exists():
        info(f"Entorno virtual ya existe en {VENV_DIR}")
        return
    info(f"Creando entorno virtual en {VENV_DIR} ...")
    venv.EnvBuilder(with_pip=True, clear=False, upgrade_deps=False).create(VENV_DIR)
    info("Entorno virtual creado.")


def pip_install() -> None:
    py = venv_python()
    if not py.exists():
        err("No se encuentra el Python del venv.")
        sys.exit(1)
    if not REQS.exists():
        err(f"No se encuentra {REQS}")
        sys.exit(1)
    info("Actualizando pip ...")
    subprocess.check_call([str(py), "-m", "pip", "install", "--quiet", "--upgrade", "pip"])
    info("Instalando dependencias (esto puede tardar) ...")
    subprocess.check_call([str(py), "-m", "pip", "install", "--quiet", "-r", str(REQS)])
    info("Dependencias instaladas.")


def smoke_test() -> None:
    py = venv_python()
    code = (
        "import streamlit, docx, fpdf, pypdf, markdown; "
        "print('imports ok')"
    )
    try:
        subprocess.check_call([str(py), "-c", code])
    except subprocess.CalledProcessError:
        err("Falló la verificación de imports.")
        sys.exit(1)


def ensure_api_key() -> dict:
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    key = os.environ.get("LOVABLE_API_KEY") or env.get("LOVABLE_API_KEY")
    if not key:
        warn("No se encontró LOVABLE_API_KEY.")
        try:
            key = input("Introduce tu LOVABLE_API_KEY (Enter para omitir): ").strip()
        except EOFError:
            key = ""
        if key:
            with ENV_FILE.open("a") as f:
                f.write(f"\nLOVABLE_API_KEY={key}\n")
            info(f"Clave guardada en {ENV_FILE}")
        else:
            warn("Continuando sin clave: la app fallará al llamar al modelo.")
    if key:
        env["LOVABLE_API_KEY"] = key
    return env


def run_streamlit(extra_env: dict) -> None:
    py = venv_python()
    if not APP_FILE.exists():
        err(f"No se encuentra {APP_FILE}")
        sys.exit(1)
    info("Lanzando Streamlit en http://localhost:8501 ...")
    new_env = os.environ.copy()
    new_env.update(extra_env)
    subprocess.call(
        [str(py), "-m", "streamlit", "run", str(APP_FILE)],
        env=new_env,
        cwd=str(ROOT),
    )


def run_cli(extra_env: dict) -> None:
    py = venv_python()
    new_env = os.environ.copy()
    new_env.update(extra_env)
    subprocess.call([str(py), "-m", "lexagent.cli", "--help"], env=new_env, cwd=str(ROOT))
    info("Para ejecutar comandos: source .venv/bin/activate && python -m lexagent.cli ...")


def main() -> None:
    args = set(sys.argv[1:])
    info("Iniciando instalación de LexAgent")
    check_python()
    create_venv()
    pip_install()
    smoke_test()
    extra_env = ensure_api_key()

    if "--no-run" in args:
        info("Instalación completa. Omitiendo arranque (--no-run).")
        return
    if "--cli" in args:
        run_cli(extra_env)
        return
    run_streamlit(extra_env)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        warn("Interrumpido por el usuario.")
        sys.exit(130)
