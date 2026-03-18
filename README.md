# AsyncAPI MCP Kafka Generator

Custom AsyncAPI generator template that automatically produces a **Model Context Protocol (MCP)** server in Python from an AsyncAPI v3 specification.

The goal is to let LLMs (Claude, Cursor, etc.) interact with a Kafka-based event architecture using the AsyncAPI spec as the single source of truth.

---

## How it works

```
AsyncAPI spec (.yaml)
        │
        ▼
AsyncAPI Generator + template/
        │
        ▼
generated-code/
  ├── mcp_server.py   ← FastMCP server with one @mcp.tool per operation
  └── kafka_producer.py  ← Confluent Kafka producer with Schema Registry
```

For each `send` operation defined in the spec, the generator creates a typed Python function decorated with `@mcp.tool`. The function validates and serializes the payload against a JSON Schema extracted from the spec, then produces the message to the corresponding Kafka topic.

---

## Project structure

```
.
├── template/
│   ├── mcp_server.js       # Dynamic template (AsyncAPI React SDK) — generates mcp_server.py
│   └── kafka_producer.py   # Static file — copied as-is to generated-code/
├── yaml/                   # AsyncAPI v3 spec examples
│   ├── streets-lights.yaml
│   ├── temperature.yaml
│   └── ...
├── generated-code/         # Output of the generator (gitignored, regenerate as needed)
│   ├── mcp_server.py
│   └── kafka_producer.py
├── consumer/               # Standalone Kafka consumer (for testing / observability)
│   ├── kafka_consumer.py
│   └── run_consumer.py
├── docker/                 # Local dev environment
│   ├── docker-compose.yml  # Kafka (SASL_SSL + PLAINTEXT) + Schema Registry + kafka-ui
│   ├── gen-certs.sh        # Generates SSL certs for SASL_SSL listener
│   ├── kafka-init.sh       # Creates SCRAM users at broker startup
│   └── launch.sh
├── scripts/
│   └── create_topics.py    # Helper to pre-create Kafka topics
├── package.json            # AsyncAPI generator template config
└── pyproject.toml          # Python dependencies (uv)
```

---

## Prerequisites

- **Node.js** (for the AsyncAPI generator)
- **Python ≥ 3.13** + **uv**
- **Docker + Docker Compose** (for the local Kafka stack)

Install the AsyncAPI generator and Python dependencies:

```bash
npm install
uv sync
```

---

## Generating the MCP server

```bash
npx asyncapi generate fromTemplate <spec.yaml> . --output generated-code/
```

If the spec defines multiple servers, select one with the `server` parameter:

```bash
npx asyncapi generate fromTemplate yaml/streets-lights.yaml . \
  --output generated-code/ \
  --param server=scram-connections
```

The `server` parameter controls which broker host and security scheme are embedded in the generated code.

---

## Local development environment

The `docker/` directory provides a ready-to-use Kafka stack:

| Service | Port | Description |
|---------|------|-------------|
| Kafka (PLAINTEXT) | 9092 | For Schema Registry and internal use |
| Kafka (SASL_SSL) | 9095 | Authenticated external clients |
| Confluent Schema Registry | 8081 | JSON Schema validation and serialization |
| kafka-ui | 8080 | Web UI for topic/message inspection |

**Start the stack:**

```bash
cd docker/
bash gen-certs.sh   # only needed once — generates SSL certs
docker compose up -d
```

---

## Running the generated MCP server

1. Copy `.env.example` to `generated-code/.env` (or set variables in your environment):

```env
SCHEMA_REGISTRY_URL=http://localhost:8081

# For SASL_SSL (scramSha256 / scramSha512 / plain)
KAFKA_USERNAME=testuser
KAFKA_PASSWORD=testpassword
KAFKA_SSL_CA_LOCATION=docker/certs/ca.crt

# For mTLS (X509)
# KAFKA_SSL_CERTIFICATE_LOCATION=...
# KAFKA_SSL_KEY_LOCATION=...
# KAFKA_SSL_CA_LOCATION=...
```

2. Run the server from `generated-code/`:

```bash
cd generated-code/
uv run mcp_server.py
```

---

## Security support

Security configuration is read automatically from the spec's `servers[].security` field.

| AsyncAPI scheme | Kafka protocol | Generated config |
|-----------------|---------------|-----------------|
| `plain` | SASL_SSL | PLAIN mechanism |
| `scramSha256` | SASL_SSL | SCRAM-SHA-256 |
| `scramSha512` | SASL_SSL | SCRAM-SHA-512 |
| `X509` | SSL | mTLS (cert + key + CA) |
| _(none)_ | PLAINTEXT | No auth |

---

## AsyncAPI spec features used

### Path parameters

Channel address parameters (e.g. `{streetlightId}`) are extracted and exposed as function arguments. The first path param is used as the Kafka partition key by default.

### Custom partition key (`x-kafka-key`)

Override the partition key field with the `x-kafka-key` extension on an operation:

```yaml
operations:
  sendReading:
    action: send
    x-kafka-key: sensorId
    channel:
      $ref: '#/channels/readingsChannel'
```

### Optional fields

Payload properties not listed under `required` are generated as `Optional[T] = None` and filtered out before sending.

### Docstrings

Generated tool functions include docstrings built from `summary`, `description`, and property `description` fields in the spec.

---

## Consuming events (observability)

A simple consumer is provided for testing. Configure it via `consumer/.env`:

```env
KAFKA_BOOTSTRAP_SERVERS=localhost:9095
TOPICS=smartylighting.streetlights.1.0.action.home.turn.on,smartylighting.streetlights.1.0.action.home.turn.off
CONSUMER_GROUP_ID=streetlights-logger
KAFKA_USERNAME=testuser
KAFKA_PASSWORD=testpassword
KAFKA_SSL_CA_LOCATION=../docker/certs/ca.crt
```

```bash
cd consumer/
uv run run_consumer.py
```

---

## Example specs

| File | Description |
|------|-------------|
| `yaml/streets-lights.yaml` | Streetlights API with SCRAM-SHA-256 and mTLS servers, path params |
| `yaml/temperature.yaml` | IoT temperature sensors, no auth, required fields |
| `yaml/test-system.yaml` | Generic test spec |
| `yaml/test-system-more-tools.yaml` | Multi-tool test spec |
