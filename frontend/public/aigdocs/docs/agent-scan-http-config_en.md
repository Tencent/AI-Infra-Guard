# HTTP Interface Configuration Guide

The HTTP interface configuration allows you to connect to any custom HTTP conversation endpoint, making it suitable for self-hosted Agent services or third-party non-standard interfaces.

## Configuration Entry

**Path**: `Settings` → `Agent Configuration` → `Add` → Select `HTTP Endpoint`

## Basic Settings (Required)

- **Agent Name**: A unique custom name for the Agent, used for identification and management.
- **URL**: The full address of the target HTTP endpoint, e.g., `https://api.example.com/chat`.
- **HTTP Method**: Select the request method. Supports POST, GET, PUT, PATCH, DELETE. Default is `POST`.

## Advanced Settings (Optional)

### Request Headers

- **Format**: HTTP request headers in JSON format.
- **Default**: `{"Content-Type": "application/json"}`
- **Example**:
  ```json
  {
    "Content-Type": "application/json",
    "Authorization": "Bearer your-token-here",
    "X-Custom-Header": "xxxxx"
  }
  ```
- **Note**: If authentication is required, add headers like `Authorization` here.

### Request Body

- **Format**: Request body template, supports text or JSON format.
- **Placeholder**: Use `{{prompt}}` as the placeholder for test input. It will be automatically replaced with the actual test prompt during scanning.
- **Default**: `{"message": "{{prompt}}"}`
- **Example**:
  ```json
  {
    "query": "{{prompt}}",
    "user_id": "agent-user",
    "stream": false
  }
  ```
- **Note**: Fill in according to the actual request format of the target interface, ensuring the `{{prompt}}` placeholder is in the correct position.

### Response Parser

The Response Parser is used to extract the Agent's actual reply content from the HTTP response.

- **Format**: JSONPath expression or JavaScript expression.
- **Configuration Methods**:
  - **JSON Response**: Use JSONPath expressions to extract nested fields.
    - Example: Response is `{"reply": "content"}`, configure as `json.reply`.
    - Example: Response is `{"data": {"message": "content"}}`, configure as `json.data.message`.
  - **Text Response**: Leave blank or use `response`.
    - Example: Response is directly text `"Agent reply content"`, leave the parser blank.
- **How to Determine**: Use the "Agent Connection Verification" feature to test first and view the actual response structure before configuring.

### Timeout (ms)

- **Default**: `30000` (30 seconds).
- **Note**: Request timeout duration. If no response is received within this time, it will be treated as a failure.

## Configuration Examples

### Example 1: Standard JSON API

Assuming the target interface is `POST https://api.example.com/chat`, and the request format is:
```json
{
  "message": "User input content",
  "user_id": "user123"
}
```

The response format is:
```json
{
  "status": "success",
  "data": {
    "reply": "Agent reply content"
  }
}
```

**Configuration**:
- **URL**: `https://api.example.com/chat`
- **HTTP Method**: `POST`
- **Request Headers**: `{"Content-Type": "application/json", "Authorization": "Bearer your-token"}`
- **Request Body**: `{"message": "{{prompt}}", "user_id": "agent-user"}`
- **Response Parser**: `json.data.reply`

### Example 2: Simple Text Interface

Assuming the target interface is `POST https://api.example.com/simple`, the request body is direct text, and the response is also text.

**Configuration**:
- **URL**: `https://api.example.com/simple`
- **HTTP Method**: `POST`
- **Request Headers**: `{"Content-Type": "text/plain"}`
- **Request Body**: `{{prompt}}`
- **Response Parser**: Leave blank or fill in `response`

## Connection Verification

After configuration, it is recommended to use the "Agent Connection Verification" feature for a quick test. For details, please refer to the [Agent Configuration - Connection Verification](?menu=agent-scan#agent-connection-verification) section.

For HTTP interfaces, please pay special attention to:
- If extraction fails, check if the Response Parser configuration is correct.
- If connectivity check fails, check if the URL, request format, response parser, etc., are correct.

## FAQ

**Q: How do I configure the Response Parser?**
A: First use the "Agent Connection Verification" feature to view the actual response structure, then configure the corresponding JSONPath based on the response format.

**Q: Is streaming response supported?**
A: Streaming delivery is supported. If parsing fails, try switching to non-streaming. It is recommended to prioritize [Synchronous Requests (blocking mode)].

**Q: Must the request body contain `{{prompt}}`?**
A: Yes, `{{prompt}}` is a required placeholder, which will be replaced by the actual test prompt during scanning.

**Q: Is file upload supported?**
A: The current version does not support file upload; only text conversation is supported.

**Q: How do I know the interface parameters and response format?**
A: You can obtain interface information through the following methods:

1.  **Check Interface Documentation**: View the API documentation provided by the target Agent service to understand the request format (URL, method, headers, body structure) and response format.
2.  **Use "Agent Connection Verification"**: After configuring basic information, use the "Agent Connection Verification" feature in the interface to send a test request and view the actual returned response structure:
    - Enter a test prompt in "Prompt Input".
    - Click "Run Test".
    - View the returned raw response (if the response parser is incorrect, you can see the full response structure).
3.  **Use Browser Developer Tools**: If the target interface has a Web interface, you can:
    - Open Browser Developer Tools (F12).
    - Switch to the "Network" tab.
    - Send a message in the Web interface.
    - View the corresponding HTTP request and response to understand the format.
4.  **Use curl or Postman**: Use command-line tools or API testing tools to directly call the interface and observe the request and response formats.
5.  **View Response Parser Examples**: Configure the response parser based on common response formats:
    - If the response is `{"reply": "content"}`, use `json.reply`.
    - If the response is `{"data": {"message": "content"}}`, use `json.data.message`.
    - If the response is OpenAI format `{"choices": [{"message": {"content": "content"}}]}`, use `json.choices[0].message.content`.
