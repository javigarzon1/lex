# LexAgent — Agentes IA para documentos jurídicos (Python)

Aplicación 100% Python para crear y ejecutar **agentes de IA especializados en
documentos jurídicos** (avales internacionales, contragarantías, contratos,
etc.). Incluye:

- Interfaz web con **Streamlit** (formulario para crear agentes y ejecutarlos).
- **CLI** (`python -m lexagent.cli`) para ejecutar agentes desde terminal.
- **Base de conocimiento** propia: usa el manual de avales preinstalado o sube
  tus propios PDF/TXT/DOCX.
- **Salida**: en pantalla (markdown) **y** descargable en PDF y DOCX.
- Persistencia local en SQLite (`lexagent.db`).
- Conexión al modelo IA vía la API que prefieras: por defecto usa
  **Lovable AI Gateway** (compatible OpenAI), también funciona con OpenAI o
  cualquier endpoint compatible.

## Instalación

```bash
cd lexagent_py
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Configuración

Define la API key del proveedor de IA. Recomendado: Lovable AI Gateway.

```bash
export LOVABLE_API_KEY="tu_clave"
# o, si prefieres OpenAI:
# export OPENAI_API_KEY="tu_clave"
# export LEXAGENT_BASE_URL="https://api.openai.com/v1"
# export LEXAGENT_MODEL="gpt-4o-mini"
```

Variables opcionales:

| Variable | Por defecto |
|---|---|
| `LEXAGENT_BASE_URL` | `https://ai.gateway.lovable.dev/v1` |
| `LEXAGENT_MODEL` | `google/gemini-2.5-flash` |
| `LEXAGENT_DB` | `./lexagent.db` |

## Uso — Interfaz web

```bash
streamlit run lexagent/app.py
```

Se abre en `http://localhost:8501`. Desde la UI puedes:

1. **Crear agente**: nombre, descripción, prompt de sistema, tipo de documento,
   campos del formulario (dinámicos) y base de conocimiento (manual incluido o
   ficheros propios).
2. **Ejecutar agente**: rellenas el formulario que has definido y obtienes:
   - Informe de validación (markdown).
   - Documento jurídico borrador (markdown).
   - Botones de descarga **PDF** y **DOCX** para ambos.
3. **Historial**: cada ejecución se guarda en SQLite.

## Uso — CLI

```bash
# Listar agentes
python -m lexagent.cli list

# Crear un agente desde un fichero JSON
python -m lexagent.cli create ejemplo_agente.json

# Ejecutar un agente con datos del formulario
python -m lexagent.cli run <agent_id> --data datos.json --out ./salida
```

`datos.json` es un diccionario con los campos del formulario.
Genera en `./salida`: `report.md`, `report.pdf`, `document.md`, `document.docx`.

## Estructura

```
lexagent_py/
├── lexagent/
│   ├── __init__.py
│   ├── app.py              # Streamlit UI
│   ├── cli.py              # Interfaz línea de comandos
│   ├── ai.py               # Cliente IA (Lovable / OpenAI compatible)
│   ├── db.py               # Persistencia SQLite
│   ├── export.py           # Exportación a PDF y DOCX
│   ├── knowledge_loader.py # Carga PDF/TXT/DOCX
│   └── knowledge/
│       └── avales_internacionales.txt
├── ejemplo_agente.json
├── requirements.txt
└── README.md
```
