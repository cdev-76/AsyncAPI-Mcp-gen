"""
Run the streetlights log consumer. Subscribes to topics and logs each event.

Configuration is read from .env (consumer/.env takes precedence over the repo root .env).
Required variables:
  KAFKA_BOOTSTRAP_SERVERS  - default localhost:9095
  TOPICS                   - comma-separated list of topics (required)
  CONSUMER_GROUP_ID        - default streetlights-logger
  KAFKA_USERNAME, KAFKA_PASSWORD, KAFKA_SSL_CA_LOCATION - for SASL_SSL
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from kafka_consumer import MyConsumer

_consumer_dir = Path(__file__).resolve().parent
load_dotenv(_consumer_dir / ".env")
load_dotenv(_consumer_dir.parent / ".env")

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9095")
TOPICS_STR = os.getenv("TOPICS", "")
GROUP_ID = os.getenv("CONSUMER_GROUP_ID", "streetlights-logger")

KAFKA_USERNAME = os.getenv("KAFKA_USERNAME", "")
KAFKA_PASSWORD = os.getenv("KAFKA_PASSWORD", "")
KAFKA_SSL_CA_LOCATION = os.getenv("KAFKA_SSL_CA_LOCATION", "")
security_config = None
if KAFKA_USERNAME and KAFKA_PASSWORD:
    security_config = {
        "security.protocol": "SASL_SSL",
        "sasl.mechanism": "SCRAM-SHA-256",
        "sasl.username": KAFKA_USERNAME,
        "sasl.password": KAFKA_PASSWORD,
        "ssl.ca.location": KAFKA_SSL_CA_LOCATION,
    }

if not TOPICS_STR.strip():
    print("Set TOPICS in .env as a comma-separated list. Example:")
    print("  TOPICS=smartylighting.streetlights.1.0.action.home.turn.on,smartylighting.streetlights.1.0.action.home.turn.off")
    exit(1)

topics = [t.strip() for t in TOPICS_STR.split(",") if t.strip()]
bootstrap_servers = [s.strip() for s in KAFKA_BOOTSTRAP.split(",") if s.strip()]

consumer = MyConsumer(
    bootstrap_servers=bootstrap_servers,
    group_id=GROUP_ID,
    topics=topics,
    security_config=security_config,
)
consumer.consume_loop()
