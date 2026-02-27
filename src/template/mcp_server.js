import { File } from '@asyncapi/generator-react-sdk';

export default function ({ asyncapi }) {

    // Temporary static //
    const serverHost = asyncapi.servers().all()[0].host();

    const mcpTools = asyncapi.operations().all().map(operation => {
        const operationId = operation.id();// Extract topic and operation payload
        const channelAddress = operation.channels().all()[0].address();
        const payloadSchema = operation.messages().all()[0].payload();
        const properties = payloadSchema.properties();

        const propNames = Object.keys(properties);

        // Extract path params
        // Search for everything that is within brackets in channel's address
        const pathParamsMatch = channelAddress.match(/\{([^}]+)\}/g) || [];
        // Cleans brackets to get the variable's name
        const pathParams = pathParamsMatch.map(param => param.replace(/[{}]/g, ''));

        const keyField = propNames.find(prop =>
            ['id', 'username', 'userid', 'email', 'name'].includes(prop.toLowerCase())
        );

        // If there is no regular KeyField, gives a default key value
        const pythonKey = keyField ? `str(${keyField})` : '"mcp_event"';

        // 1. Build function params (example: name:str, surname:str)
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
            // Extract each property tipe (if exists), if not: format to string
            const propType = prop.type() ? String(prop.type()) : 'string';
            const pyType = getPythonType(propType);
            return `${propName}: ${pyType}`;
        });

        // Asume that URL params always enter as str
        const pathParamDefs = pathParams.map(param => `${param}: str`);
        const funcParams = [...pathParamDefs, ...payloadParams].join(', ');

        // 2. Build data dictionary to send to kafka
        const dictEntries = Object.keys(properties).map(propName => `"${propName}": ${propName}`).join(',\n        ');

        const operationSummary = operation.summary() || `Sends an event to the ${channelAddress} topic.`;
        const operationDesc = operation.description() || '';

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
            topic=f'${channelAddress}', # 'f' inyects topic variables
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
            {`from fastmcp import FastMCP
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