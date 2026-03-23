import json
import os
import time
import requests
from confluent_kafka import Producer
from confluent_kafka.schema_registry import SchemaRegistryClient, Schema
from confluent_kafka.schema_registry.json_schema import JSONSerializer
from confluent_kafka.serialization import SerializationContext, MessageField
from typing import Optional, List, Tuple
import jsonschema


def fetch_oauth_token(config_str: str):
    '''
    OAuth2 client_credentials token callback for confluent-kafka OAUTHBEARER.
    Called automatically by the Kafka client when a token is needed or has expired.
    Reads OAUTH_TOKEN_URL, OAUTH_CLIENT_ID and OAUTH_CLIENT_SECRET from environment.

    :param config_str: Value of sasl.oauthbearer.config (unused, required by confluent-kafka callback signature)
    :returns: Tuple of (access_token, expiry_unix_timestamp_seconds)
    '''
    resp = requests.post(
        os.getenv('OAUTH_TOKEN_URL', ''),
        data={
            'grant_type': 'client_credentials',
            'client_id': os.getenv('OAUTH_CLIENT_ID', ''),
            'client_secret': os.getenv('OAUTH_CLIENT_SECRET', ''),
        },
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
    )
    resp.raise_for_status()
    data = resp.json()
    return data['access_token'], time.time() + float(data['expires_in'])


class MyProducer:

    def __init__(self, bootstrap_servers: list, schema_registry_url: str, security_config: dict = None):
        '''
        CONSTRUCTOR: Initializes the connection with the Kafka broker and Schema Registry.

        :param bootstrap_servers: Kafka broker ip:port list
        :type bootstrap_servers: list
        :param schema_registry_url: URL of the Confluent Schema Registry
        :type schema_registry_url: str
        :param security_config: Optional dict of confluent-kafka security settings (e.g. SASL/SSL)
        :type security_config: dict
        '''
        config = {'bootstrap.servers': ','.join(bootstrap_servers)}
        if security_config:
            config.update(security_config)
        self.producer = Producer(config)
        self.registry_client = SchemaRegistryClient({'url': schema_registry_url})
        self._serializers = {}  # Cache serializers by schema string to avoid re-registering
        print("Connection established")

    def register_schemas(self, topic_schemas: List[Tuple[str, str]]) -> None:
        '''
        Registers all schemas in the Schema Registry at startup (static loading).
        Subject for each topic is "{topic}-value", matching Confluent convention.
        Call this once after __init__ so schemas exist before any produce; the
        producer will then use the existing schema instead of registering on first send.

        :param topic_schemas: List of (topic, schema_str) for each event type
        :type topic_schemas: List[Tuple[str, str]]
        '''
        for topic, schema_str in topic_schemas:
            subject = f"{topic}-value"
            schema = Schema(schema_str=schema_str, schema_type="JSON")
            self.registry_client.register_schema(subject_name=subject, schema=schema)
            print(f"Schema registered for subject: {subject}")
        print("All schemas registered in Schema Registry")

    def send_event(self, topic: str, message: dict, key: Optional[str], schema_str: str,
                   subject_topic: str):
        '''
        Validates the message against the schema and sends it to the Kafka broker.
        Schemas must be registered beforehand via register_schemas() (static loading).
        Schema Registry is used only with the static subject (subject_topic); no dynamic registration.

        :param topic: Kafka topic where the message is sent (resolved, e.g. ...action.myhome.turn.on)
        :type topic: str
        :param message: Content of the message as a dict
        :type message: dict
        :param key: Key that identifies the message for partition routing
        :type key: Optional[str]
        :param schema_str: JSON Schema string for validation and serialization
        :type schema_str: str
        :param subject_topic: Topic name used for Schema Registry subject lookup (template form, e.g.
            ...action.{streetlightId}.turn.on). Required; ensures only pre-registered schemas are used.
        :type subject_topic: str
        '''
        schema_dict = json.loads(schema_str)
        message_clean = {k: v for k, v in message.items() if v is not None}
        jsonschema.validate(instance=message_clean, schema=schema_dict)

        if schema_str not in self._serializers:
            self._serializers[schema_str] = JSONSerializer(schema_str, self.registry_client)
        serializer = self._serializers[schema_str]

        serialized_value = serializer(
            message_clean, SerializationContext(subject_topic, MessageField.VALUE)
        )
        encoded_key = key.encode('utf-8') if key is not None else None

        delivery_error = []

        def on_delivery(err, msg):
            if err:
                delivery_error.append(err)

        self.producer.produce(topic=topic, key=encoded_key, value=serialized_value, on_delivery=on_delivery)
        self.producer.flush()

        if delivery_error:
            raise Exception(f"Delivery failed: {delivery_error[0]}")

        print(f"Event sent to topic: '{topic}' with key: '{key}'")

    def close(self):
        '''
        Flushes remaining messages and closes the connection with the broker.
        '''
        self.producer.flush()
