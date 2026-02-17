from kafka import KafkaProducer
import json

# Objeto productor que se conecta al broker de kafka
producer = KafkaProducer(bootstrap_servers=['localhost:9092'],
                         value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                         key_serializer=str.encode)

if __name__ == "__main__":

    # Método que manda el paquete de bytes al topic prueba-tfg
    producer.send('prueba-tfg',key='usuario1',value={'nombre':'Pepito','apellidos':'Pepitez'})
    
    # El método flush fuerza el envio de paquetes al broker
    producer.flush() 
    
    print("Enviado!")