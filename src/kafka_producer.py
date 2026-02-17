from kafka import KafkaProducer

# Objeto productor que se conecta al broker de kafka
producer = KafkaProducer(bootstrap_servers=['localhost:9092'])

if __name__ == "__main__":

    # Método que manda el paquete de bytes al topic prueba-tfg
    producer.send('prueba-tfg',b'world')
    
    # El método flush fuerza el envio de paquetes al broker
    producer.flush() 
    
    print("Enviado!")