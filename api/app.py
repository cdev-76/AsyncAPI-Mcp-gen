from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import shutil
import os
import uuid

app = FastAPI(title="MCP Generator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4321"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

class GenerateRequest(BaseModel):
    yaml_content: str
    server: str

ROOT_PATH = os.path.abspath("..")

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
        # CORRECCIÓN: Indentado correctamente dentro del try
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

# CORRECCIÓN: Añadidos guiones bajos dobles e indentación
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)