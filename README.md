# 🚀 AsyncAPI MCP Kafka Generator

This project contains a custom AsyncAPI template that automatically generates a **Model Context Protocol (MCP)** server in Python.

The main goal is to allow Large Language Models (LLMs like Claude, Cursor, etc.) to understand a system's event architecture and send structured messages to a Kafka broker, using an AsyncAPI (v3) specification as the single source of truth.

## 📁 Project Structure

* **`src/`**: Contains the generator logic.
  * `template/`: Template files. Includes static code (`kafka_producer.py`) and dynamic React code (`mcp_server.js`) that processes the YAML.
  * `package.json`: Configuration for the AsyncAPI template engine (React SDK).
* **`yaml/`**: Directory for AsyncAPI specifications (e.g., `test-system.yaml`).
* **`generated-code/`**: Destination folder where the final, ready-to-run Python code is created.
