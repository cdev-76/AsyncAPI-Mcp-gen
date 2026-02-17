from kafka import KafkaProducer
import json

class MyProducer:

    def __init__(self,bootstrap_servers: list):
        '''
        CONSTRUCTOR: Initializes the conection with kafka broker
        
        :param self: Self object
        :param bootstrap_servers: Kafka broker ip:port
        :type bootstrap_servers: list
        '''
        # Producer object that conects to the kafka broker
        self.producer = KafkaProducer(bootstrap_servers=bootstrap_servers,
                            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                            key_serializer=str.encode)
        print("Connection established")

    def send_event(self,topic:str, message:dict, key:str):
        '''
        Sends an event to kafka broker
        
        :param topic: Kafka topic where the package is sent
        :type topic: str
        :param message: Content of the message in .JSON format
        :type message: dict
        :param key: Key that identifies the package in order to be sent
        :type key: str
        '''
        try:
            self.producer.send(topic,key=key,value=message)
            self.producer.flush()    # Forces the sending of the package, even if it is too small to be sent
            print(f"Event sent to topic: '{topic}' with Key: '{key}'")
        except Exception as e:
            print(f"Error sending: {e}")
    
    def close(self):
        '''
        Closes conection with broker
        
        :param self: Self object
        '''
        self.producer.close()


if __name__ == "__main__":
    
    productor = MyProducer(['localhost:9092'])
    
    datos_user1 = {'name':'Jorge','surname':'Fernandez'}
    productor.send_event('test-system',datos_user1,'user1')
    
    productor.close() 
    
    print("Sent!")