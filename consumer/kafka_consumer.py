"""
Simple Kafka consumer that subscribes to topics, deserializes Confluent JSON
(magic byte + schema id + JSON payload) and logs each event.
"""
import json
import logging
from typing import List, Optional

from confluent_kafka import Consumer, KafkaError

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Confluent JSON wire format: [0] magic byte, [1:5] schema id (4 bytes big endian), [5:] JSON
MAGIC_BYTE = 0


def _deserialize_confluent_json(value: bytes) -> Optional[dict]:
    """Deserialize Confluent JSON wire format (magic + schema_id + JSON). Returns dict or None."""
    if not value or len(value) < 5:
        return None
    if value[0] != MAGIC_BYTE:
        return None
    try:
        payload = value[5:].decode("utf-8") # Skips the magic byte, schema id and the JSON payload
        return json.loads(payload) # Returns the JSON payload as a dict
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


class MyConsumer:
    """
    Simple consumer: subscribes to a list of topics, polls and logs each message
    (topic, partition, offset, key, value as dict). Uses same security config as producer.
    """

    def __init__(
        self,
        bootstrap_servers: List[str],
        group_id: str,
        topics: List[str],
        security_config: Optional[dict] = None,
    ):
        config = {
            "bootstrap.servers": ",".join(bootstrap_servers), # Join the bootstrap servers with a comma
            "group.id": group_id, # Group id
            "auto.offset.reset": "earliest",
        }
        if security_config: # If security config is provided, update the config with the security config
            config.update(security_config) # Update the config with the security config
        self.consumer = Consumer(config) # Create a consumer
        self.topics = topics # List of topics to subscribe to
        self.consumer.subscribe(topics) # Subscribe to the topics
        logger.info("Consumer subscribed to %s", topics) # Log the topics

    def consume_loop(self) -> None:
        """Poll and log each message until KeyboardInterrupt.""" # Poll and log each message until KeyboardInterrupt
        try:
            while True:
                msg = self.consumer.poll(timeout=1.0) # Poll for a message every 1 second
                if msg is None: # If no message is found, continue
                    continue
                if msg.error(): # If an error is found, log the error
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue # If the error is a partition EOF, continue
                    logger.error("Consumer error: %s", msg.error())
                    continue
                key = msg.key().decode("utf-8") if msg.key() else None # If a key is found, decode it
                value = _deserialize_confluent_json(msg.value()) # Deserialize the value
                logger.info(
                    "event topic=%s partition=%s offset=%s key=%s value=%s",
                    msg.topic(), # Topic name
                    msg.partition(), # Partition number
                    msg.offset(), # Offset number (position inside the partition)
                    key,
                    value, # Value as a dict
                )
        except KeyboardInterrupt:
            logger.info("Stopping consumer")
        finally:
            self.consumer.close()

    def close(self) -> None:
        self.consumer.close()
