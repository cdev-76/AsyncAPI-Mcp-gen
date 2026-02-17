from kafka import KafkaProducer
import json

# Producer object that conects to the kafka broker
producer = KafkaProducer(bootstrap_servers=['localhost:9092'],
                         value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                         key_serializer=str.encode)

def send(topic:str, message:dict, key:str):
    '''
    Docstring for send
    
    :param topic: Kafka topic where the package is sent
    :type topic: str
    :param message: Content of the message in .JSON format
    :type message: dict
    :param key: Key that identifies the package in order to be sent
    :type key: str
    '''
    producer.send(topic,key=key,value=message)


if __name__ == "__main__":
    datos_user1 = {'name':'Jorge','surname':'Fernandez'}
    send('prueba-tfg',datos_user1,'user1')
    
    # Forces the sending of the package, even if it is too small to be sent
    producer.flush() 
    
    print("Sent!")