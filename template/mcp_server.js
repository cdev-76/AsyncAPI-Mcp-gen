import { File } from '@asyncapi/generator-react-sdk';

export default function ({ asyncapi }) {

    // Temporary static //
    const serverHost = asyncapi.servers().all()[0].host();

    const mcpTools = asyncapi.operations().all().map(operation => {
        // Extract topic and operation payload
        const operationId = operation.id(); // Example: lightTurnOn
        const channelAddress = operation.channels().all()[0].address(); // Example: 'smartylighting.streetlights.1.0.action.{streetlightId}.turn.on'
        const payloadSchema = operation.messages().all()[0].payload(); // Schema object. Example: 'turnOnOffPayload'
        const properties = payloadSchema.properties(); // Example: { command: [Schema Object], sentAt: [Schema Object] }

        const propNames = Object.keys(properties); // Example: ['command','sentAt']
        const required = payloadSchema.required() || []; // Example: ['command']

        // Extract path params
        // Search for everything that is within brackets in channel's address
        const pathParamsMatch = channelAddress.match(/\{([^}]+)\}/g) || []; // Example: ['{streetlightId}']
        // Cleans brackets to get the variable's name
        const pathParams = pathParamsMatch.map(param => param.replace(/[{}]/g, ''));

        // Combine path parameters and payload properties to search for a potential key
        const potentialKeyFields = [...pathParams, ...propNames]; // Example: ['streetlightId','command','sentAt']
        
        // Check for explicit x-kafka-key extension on the operation first
        // Example in YAML: x-kafka-key: streetlightId
        const explicitKey = operation.extensions().get('x-kafka-key')?.value();

        // Otherwise, auto-detect by checking if the parameter name matches or ends with our target words
        // Example: 'streetlightId' will match because it ends with 'id' (lowercased)
        const detectedKey = potentialKeyFields.find(prop => {
            const lowerProp = prop.toLowerCase();
            return ['id', 'username', 'userid', 'email', 'name'].some(
                keyword => lowerProp === keyword || lowerProp.endsWith(keyword)
            );
        });

        // Priority: explicit extension > auto-detected > None (Kafka round-robins across partitions)
        const keyField = explicitKey || detectedKey;
        const pythonKey = keyField ? `str(${keyField})` : 'None'; // Example: 'str(streetlightId)'

        // 1. Build function params. Example: streetlightId: str, command: str, sentAt: str
        const getPythonType = (asyncApiType) => {
            const typeMap = {
                'string': 'str',
                'integer': 'int',
                'number': 'float',
                'boolean': 'bool',
                'array': 'list',
                'object': 'dict'
            };
            return typeMap[asyncApiType] || 'str'; // If there is no type, we asume str
        };

        const payloadParams = propNames.map(propName => {
            const prop = properties[propName];
            // Extract each property type (if exists), if not: format to string
            const propType = prop.type() ? String(prop.type()) : 'string';
            const pyType = getPythonType(propType);
            // Non-required fields become Optional with a None default
            const isOptional = !required.includes(propName);
            return isOptional ? `${propName}: Optional[${pyType}] = None` : `${propName}: ${pyType}`;
        }); // Example: ['command: str', 'sentAt: Optional[str] = None']

        // Asume that URL params always enter as str
        const pathParamDefs = pathParams.map(param => `${param}: str`); // Example: ['streetlightId: str']
        const funcParams = [...pathParamDefs, ...payloadParams].join(', '); // Example: 'streetlightId: str, command: str, sentAt: str'

        // 2. Build data dictionary to send to kafka
        const dictEntries = Object.keys(properties).map(propName => `"${propName}": ${propName}`).join(',\n        ');
        // example: '"command": command,\n        "sentAt": sentAt'

        const operationSummary = operation.summary() || `Sends an event to the ${channelAddress} topic.`;
        // example: 'Sends an event to the smartylighting.streetlights.1.0.action.{streetlightId}.turn.on topic.'
        const operationDesc = operation.description() || ''; // For the example given, there is no description in the specification file

        let docstring = `"""\n    ${operationSummary}`;
        if (operationDesc) {
            docstring += `\n    ${operationDesc}`;
        }

        if (pathParams.length > 0 || propNames.length > 0) {
            docstring += `\n\n    Args:\n`;
            pathParams.forEach(param => {
                docstring += `        ${param}: Parameter extracted from the topic path.\n`;
            });
            propNames.forEach(propName => {
                const prop = properties[propName];
                // Take the current description from YAML file, if none, put a generic one 
                const propDesc = prop.description() ? String(prop.description()).replace(/\n/g, ' ') : `The ${propName} parameter.`;
                docstring += `        ${propName}: ${propDesc}\n`;
            });
        }
        docstring += `    """`;
        // example (final docstring): 
        // """
        //     Sends an event to the smartylighting.streetlights.1.0.action.{streetlightId}.turn.on topic.
        //
        //     Args:
        //         streetlightId: Parameter extracted from the topic path.
        //         command: Whether to turn on or off the light.
        //         sentAt: Date and time when the message was sent.
        //     """
        return `
@mcp.tool
def ${operationId}(${funcParams}) -> str:
    ${docstring}
    
    if kafka_client is None:
        return "Error: Kafka service is not available"
    
    user_data = {
        ${dictEntries}
    }

    try:
        kafka_client.send_event(
            topic=f'${channelAddress}', # 'f' injects topic variables
            message=user_data,
            key=${pythonKey}
        )
        return f"Event successfully sent to ${channelAddress}."
    except Exception as e:
        return f"Error: failed when trying to send event: {e}"
`;
    }).join('\n'); // Join each generated function

    return (
        <File name="mcp_server.py">
            {`from typing import Optional
from fastmcp import FastMCP
from kafka_producer import MyProducer

mcp = FastMCP("AsyncAPI-Kafka-Server")

try:
    kafka_client = MyProducer(['${serverHost}'])
    print("Kafka connection established")
except Exception as e:
    print(f"Error: Couldn't connect to Kafka. {e}")
    kafka_client = None
${mcpTools}

if __name__ == "__main__":
    mcp.run()
`}
        </File>
    );
}