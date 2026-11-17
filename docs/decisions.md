# HBntory - Decision record


## Backoffice: Server-side-rendering: 
   		Benefits:
- Because it’s an all in one program instead than REST + html/css/js. There’s a need of at least 2 projects.
-The server side authentication is easier.
			Trade-off:
-The interface is less dynamic and the page needs a reload each time there’s a change.

## Client Web: REST:
			Benefits
-Because there is no need for an extended conversation for an FAQ.
			Trade-off:
pros there is a bit of wait for the response of the server before any other action can be done

## Ai Query Service to MCP tools: STDIO:
			Benefits
-No extra port, nothing to secure on the network, the simplest transport.
			Trade-off:
-One MCP process is started per question (about one second slower) , and the MCP server must be on the same machine as the AI service.