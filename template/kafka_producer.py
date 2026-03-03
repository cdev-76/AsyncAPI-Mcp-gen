from confluent_kafka import Producer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.json_schema import JSONSerializer
from confluent_kafka.serialization import SerializationContext, MessageField
from typing import Optional


class MyProducer:

    def __init__(self, bootstrap_servers: list, schema_registry_url: str):
        '''
        CONSTRUCTOR: Initializes the connection with the Kafka broker and Schema Registry.

        :param bootstrap_servers: Kafka broker ip:port list
        :type bootstrap_servers: list
        :param schema_registry_url: URL of the Confluent Schema Registry
        :type schema_registry_url: str
        '''
        self.producer = Producer({'bootstrap.servers': ','.join(bootstrap_servers)})
        self.registry_client = SchemaRegistryClient({'url': schema_registry_url})
        self._serializers = {}  # Cache serializers by schema string to avoid re-registering
        print("Connection established")

    def send_event(self, topic: str, message: dict, key: Optional[str], schema_str: str):
        '''
        Validates the message against the schema, registers it with the Schema Registry
        if needed, and sends it to the Kafka broker.

        :param topic: Kafka topic where the message is sent
        :type topic: str
        :param message: Content of the message as a dict
        :type message: dict
        :param key: Key that identifies the message for partition routing
        :type key: Optional[str]
        :param schema_str: JSON Schema string for validation and registration
        :type schema_str: str
        '''
        if schema_str not in self._serializers:
            self._serializers[schema_str] = JSONSerializer(schema_str, self.registry_client)
        serializer = self._serializers[schema_str]

        serialized_value = serializer(message, SerializationContext(topic, MessageField.VALUE))
        encoded_key = key.encode('utf-8') if key is not None else None

        self.producer.produce(topic=topic, key=encoded_key, value=serialized_value)
        self.producer.flush()
        print(f"Event sent to topic: '{topic}' with key: '{key}'")

    def close(self):
        '''
        Flushes remaining messages and closes the connection with the broker.
        '''
        self.producer.flush()
