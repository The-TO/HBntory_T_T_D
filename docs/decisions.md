# HBntory – Decision Record

## Backoffice: Server-Side Rendering (SSR)

**Benefits:**
- It is an all-in-one application, instead of REST + HTML/CSS/JS, which would require at least two separate projects (backend and frontend).
- Server-side authentication is easier to implement.

**Trade-off:**
- The interface is less dynamic, and the page needs to reload each time something changes.

## Client Web to AI Query Service: REST

**Benefits:**
- Each question is independent and no conversation history is needed, so a simple request/response is enough.
- It is simple to implement and to test.

**Trade-off:**
- The user has to wait for the complete answer, since there is no streaming.

## AI Query Service to MCP tools: STDIO

**Benefits:**
- No extra port and nothing to secure on the network, since it is the simplest transport.

**Trade-off:**
- One MCP process is started per question (about one second slower), and the MCP server must run on the same machine as the AI service.
