"""
Script para comprobar que la validación del mensaje frente al schema funciona.
Ejecutar desde generated-code con: uv run python test_validation.py

Al lanzar payloads inválidos, debe aparecer jsonschema.ValidationError y no se envía a Kafka.
"""
import sys
import jsonschema

# Al importar, se crea kafka_client y se registran los schemas
from mcp_server import kafka_client, SCHEMA_TURNON, SCHEMA_DIMLIGHT, SCHEMA_RECEIVELIGHTMEASUREMENT

SUBJECT_TURNON = "smartylighting.streetlights.1.0.action.{streetlightId}.turn.on"
SUBJECT_DIM = "smartylighting.streetlights.1.0.action.{streetlightId}.dim"
SUBJECT_MEASURED = "smartylighting.streetlights.1.0.event.{streetlightId}.lighting.measured"


def test_turnon_command_wrong_type():
    """command debe ser string; pasamos int → ValidationError."""
    print("Test 1: turnOn con command como número (debe fallar validación)...")
    try:
        kafka_client.send_event(
            topic="smartylighting.streetlights.1.0.action.test.turn.on",
            message={"command": 12345},
            key="test",
            schema_str=SCHEMA_TURNON,
            subject_topic=SUBJECT_TURNON,
        )
        print("  ERROR: se esperaba ValidationError")
        return False
    except jsonschema.ValidationError as e:
        print(f"  OK - ValidationError: {getattr(e, 'message', str(e))}")
        return True
    except Exception as e:
        print(f"  Otro error: {e}")
        return False


def test_dim_percentage_wrong_type():
    """percentage debe ser integer; pasamos string → ValidationError."""
    print("Test 2: dimLight con percentage como string (debe fallar validación)...")
    try:
        kafka_client.send_event(
            topic="smartylighting.streetlights.1.0.action.test.dim",
            message={"percentage": "no-soy-numero"},
            key="test",
            schema_str=SCHEMA_DIMLIGHT,
            subject_topic=SUBJECT_DIM,
        )
        print("  ERROR: se esperaba ValidationError")
        return False
    except jsonschema.ValidationError as e:
        print(f"  OK - ValidationError: {getattr(e, 'message', str(e))}")
        return True
    except Exception as e:
        print(f"  Otro error: {e}")
        return False


def test_lumens_wrong_type():
    """lumens debe ser integer; pasamos string → ValidationError."""
    print("Test 3: receiveLightMeasurement con lumens como string (debe fallar validación)...")
    try:
        kafka_client.send_event(
            topic="smartylighting.streetlights.1.0.event.test.lighting.measured",
            message={"lumens": "muchos"},
            key="test",
            schema_str=SCHEMA_RECEIVELIGHTMEASUREMENT,
            subject_topic=SUBJECT_MEASURED,
        )
        print("  ERROR: se esperaba ValidationError")
        return False
    except jsonschema.ValidationError as e:
        print(f"  OK - ValidationError: {getattr(e, 'message', str(e))}")
        return True
    except Exception as e:
        print(f"  Otro error: {e}")
        return False


if __name__ == "__main__":
    if kafka_client is None:
        print("Kafka client no disponible (revisa .env y conexión).")
        sys.exit(1)

    ok = 0
    ok += test_turnon_command_wrong_type()
    ok += test_dim_percentage_wrong_type()
    ok += test_lumens_wrong_type()

    print(f"\nResumen: {ok}/3 tests de validación correctos.")
    sys.exit(0 if ok == 3 else 1)
