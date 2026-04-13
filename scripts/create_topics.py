from kafka.admin import KafkaAdminClient, NewTopic

# Cambia esto a la dirección de tu broker local si no es localhost
KAFKA_BROKER = "localhost:9092"

# 1. Definimos los patrones exactos de tu YAML
TOPIC_PATTERNS = [
    "smartylighting.streetlights.1.0.event.{id}.lighting.measured",
    "smartylighting.streetlights.1.0.action.{id}.turn.on",
    "smartylighting.streetlights.1.0.action.{id}.turn.off",
    "smartylighting.streetlights.1.0.action.{id}.dim"
]

# 2. Definimos algunas farolas de prueba para crear sus topics
STREETLIGHT_IDS = ["farola-001", "farola-002"]

def main():
    try:
        # Conectamos con el broker
        admin_client = KafkaAdminClient(bootstrap_servers=KAFKA_BROKER)
        existing_topics = admin_client.list_topics()
        
        new_topics = []
        
        # 3. Generamos las combinaciones (4 topics x 2 farolas = 8 topics)
        for streetlight_id in STREETLIGHT_IDS:
            for pattern in TOPIC_PATTERNS:
                # Sustituimos la variable por el ID real
                real_topic_name = pattern.replace("{id}", streetlight_id)
                
                if real_topic_name not in existing_topics:
                    new_topics.append(
                        NewTopic(name=real_topic_name, num_partitions=1, replication_factor=1)
                    )
        
        # 4. Los creamos de golpe
        if new_topics:
            admin_client.create_topics(new_topics)
            print(f"✅ ¡Éxito! Se han creado {len(new_topics)} topics para tus farolas:")
            for t in new_topics:
                print(f"  💡 {t.name}")
        else:
            print("👌 Todos los topics de prueba ya existían en tu Kafka.")
            
    except Exception as e:
        print(f"❌ Error al conectar con Kafka: {e}")

if __name__ == "__main__":
    main()