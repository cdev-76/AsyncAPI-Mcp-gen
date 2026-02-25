# /// script
# dependencies = [
#     "fastmcp",
#     "kafka-python",
# ]
# ///

from fastmcp import FastMCP
from kafka_producer import MyProducer

mcp = FastMCP("Test-Server")

try:
    kafka_client = MyProducer(['localhost:9092'])
    print("Kafka connection established")
except Exception as e:
    print(f"Error: Couldn't connect to Kafka. {e}")
    kafka_client = None

@mcp.tool
def register_login(name:str, surname:str) -> str:

    if kafka_client is None:
        return "Error: Kafka service is not available"
    
    # Prepare data payload
    user_data = {
        "event": "USER_LOGIN",
        "name" : name,
        "surname" : surname,
        "status" : "active"
    }

    try:
        kafka_client.send_event(
            topic='test-system',
            message=user_data,
            key=name
        )
        return f"Login successfull for {name} {surname}."
    except Exception as e:
        return f"Error: failed when trying to send event"

if __name__ == "__main__":
    mcp.run()