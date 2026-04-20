from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from anthropic import Anthropic
from dotenv import load_dotenv
import subprocess
import shutil
import os
import uuid
import json

load_dotenv()

app = FastAPI(title="MCP Generator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4321"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

#Deserialización del JSON
class GenerateRequest(BaseModel):
    yaml_content: str
    server: str

class ChatMessageIn(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    yaml_content: str
    messages: list[ChatMessageIn]


ASYNCAPI_SYSTEM_PROMPT = """Eres un experto en AsyncAPI 3.0. Ayudas a los usuarios a crear y modificar especificaciones YAML de AsyncAPI 3.0.

Reglas:
- Usa siempre el formato AsyncAPI 3.0.0 (no 2.x)
- Cuando generes o modifiques YAML, devuelve la especificación COMPLETA dentro de un bloque ```yaml
- En AsyncAPI 3.0 las operaciones referencian canales con $ref (no nombre directo)
- Los canales y mensajes son entidades separadas de las operaciones
- Sé conciso y enfocado en la petición del usuario

Nomenclatura de topics Kafka:
- Usa SOLO caracteres alfanuméricos, puntos (.), guiones (-) y guiones bajos (_)
- NUNCA uses barras (/) ni espacios en nombres de topics ni en el campo address
- Usa el punto como separador jerárquico: streetlights.turnon, usuarios.registrados
- El campo address del canal debe seguir la misma regla

Especificación YAML actual del usuario:

{yaml_content}"""


async def _stream_chat(yaml_content: str, messages: list[ChatMessageIn]):
    client = Anthropic()
    system = ASYNCAPI_SYSTEM_PROMPT.format(yaml_content=yaml_content)
    anthropic_messages = [{"role": m.role, "content": m.content} for m in messages]

    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=system,
        messages=anthropic_messages,
    ) as stream:
        for text in stream.text_stream:
            yield f"data: {json.dumps({'text': text})}\n\n"

    yield "data: [DONE]\n\n"

ROOT_PATH = os.path.abspath("..")


@app.post("/chat")
async def chat(request: ChatRequest):
    return StreamingResponse(
        _stream_chat(request.yaml_content, request.messages),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.post("/generate")
async def generate(data: GenerateRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    working_dir = f"/tmp/mcp_{job_id}"
    os.makedirs(working_dir, exist_ok=True)
    
    yaml_file = os.path.join(working_dir, "spec.yaml")
    output_dir = os.path.join(working_dir, "generated")
    zip_base_name = f"/tmp/mcp_project_{job_id}"
    full_zip_path = zip_base_name + ".zip"

    try:
        # Escritura de especificación YAML temporal
        with open(yaml_file, "w") as f:
            f.write(data.yaml_content)

        # Configuración de entorno para CLI de AsyncAPI
        env = os.environ.copy()
        env["NODE_ENV"] = "development" 
        env["SUPPRESS_NO_CONFIG_WARNING"] = "y"

        command = (
            f"asyncapi generate fromTemplate {yaml_file} {ROOT_PATH} "
            f"-o {output_dir} "
            f"-p server={data.server} "
            f"--force-write"
        )
        
        print(f"Ejecutando comando: {command}")

        process = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            env=env
        )

        if process.returncode != 0:
            error_msg = process.stderr if process.stderr else process.stdout
            print(f"ERROR CLI: {error_msg}")
            raise Exception(f"AsyncAPI CLI Error: {error_msg}")

        if not os.path.exists(output_dir):
            raise Exception("El generador no creó la carpeta de salida.")

        # Generación de entorno de proyecto UV
        project_name = f"mcp-server-{data.server or 'generated'}"

        pyproject_content = f"""[project]
name = "{project_name}"
version = "0.1.0"
description = "Servidor MCP generado automáticamente para {data.server}"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "confluent-kafka>=2.13.2",
    "fastmcp>=3.1.1",
    "orjson>=3.11.7",
]

[tool.uv]
managed = true
"""
        with open(os.path.join(output_dir, "pyproject.toml"), "w") as f:
            f.write(pyproject_content)

        readme_content = f"""# {project_name.upper()}

Proyecto generado con AsyncAPI.

## Requisitos
- [uv](https://docs.astral.sh/uv/)

## Ejecución
```bash
# 1. Instalar dependencias
uv sync

# 2. Iniciar servidor
uv run python mcp_server.py
"""
        # CORRECCIÓN: Indentado correctamente dentro del try
        with open(os.path.join(output_dir, "README.md"), "w") as f:
            f.write(readme_content)

        gitignore_content = """# Environments
.venv/
env/
venv/
ENV/

# Python
__pycache__/
*.py[cod]
*$py.class
.python-version
"""
        # Indentado correctamente dentro del try
        with open(os.path.join(output_dir, ".gitignore"), "w") as f:
            f.write(gitignore_content)

        # Compresión del directorio final
        shutil.make_archive(zip_base_name, 'zip', output_dir)

        # Limpieza de archivos temporales
        background_tasks.add_task(shutil.rmtree, working_dir)

        return FileResponse(
            full_zip_path, 
            media_type="application/zip", 
            filename=f"mcp-server-{data.server or 'generated'}.zip"
        )

    except Exception as e:
        if os.path.exists(working_dir):
            shutil.rmtree(working_dir)
        print(f"EXCEPTION: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)