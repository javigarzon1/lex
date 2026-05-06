# LexAgent — Frontend Java (Spring Boot + Thymeleaf)

Este módulo es un frontend web en Java que consume la API REST (FastAPI) del motor LexAgent en Python.

## Arquitectura

```
Navegador  →  Frontend Java (Spring Boot, puerto 8080)
                    │  REST/JSON
                    ▼
              API Python (FastAPI, puerto 8000)
                    │
                    ▼
              Motor LexAgent (SQLite + Lovable AI Gateway)
```

## Requisitos

- **Python ≥ 3.9** (para la API)
- **Java ≥ 17** y **Maven ≥ 3.8** (para el frontend)
- Variable `LOVABLE_API_KEY` configurada

## Ejecución

### 1. Arranca la API Python (terminal 1)

```bash
./run-api.sh           # Linux/macOS
run-api.bat            # Windows
```
La API queda en `http://localhost:8000` (docs interactivas en `/docs`).

### 2. Arranca el frontend Java (terminal 2)

```bash
./run-frontend.sh      # Linux/macOS
run-frontend.bat       # Windows
```
La web queda en `http://localhost:8080`.

> Para apuntar el frontend a otra URL: `LEXAGENT_API_URL=http://otra-host:8000 mvn spring-boot:run`

## Endpoints REST de la API

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET    | `/agents` | Lista agentes |
| POST   | `/agents` | Crea agente |
| GET    | `/agents/{id}` | Detalle del agente |
| DELETE | `/agents/{id}` | Borra agente |
| POST   | `/agents/{id}/run` | Ejecuta el agente con `form_data` |
| POST   | `/export` | Exporta markdown a PDF/DOCX |
| POST   | `/knowledge/extract` | Extrae texto de un PDF/DOCX/TXT subido |

## Pantallas del frontend

- `/` — Listado de agentes
- `/agents/new` — Crear agente (con campos dinámicos y subida de PDF)
- `/agents/{id}` — Formulario dinámico para ejecutar el agente
- Vista de resultado con descarga PDF / DOCX

Sigue funcionando el modo **Streamlit** (`streamlit run lexagent/app.py`) y la **CLI** original.
