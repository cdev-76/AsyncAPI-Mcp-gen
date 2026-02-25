import { File } from '@asyncapi/generator-react-sdk';

export default function({ asyncapi }) {

  const serverHost = asyncapi.servers().all()[0].host();
  const channelAddress = asyncapi.channels().all()[0].address();

  return (
    <File name="mcp_server.py">
      {`# /// script
# dependencies = [
#     "fastmcp",
#     "kafka-python",
# ]
# ///

from fastmcp import FastMCP
from kafka_producer import MyProducer

mcp = FastMCP("Test-Server")

try:
    kafka_client = MyProducer(['${serverHost}'])
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
            topic='${channelAddress}',
            message=user_data,
            key=name
        )
        return f"Login successfull for {name} {surname}."
    except Exception as e:
        return f"Error: failed when trying to send event"

if __name__ == "__main__":
    mcp.run()
`}
    </File>
  );
}