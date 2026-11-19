# HBntory – Decision Record

## Backoffice: Server-Side Rendering (SSR)

**Benefits:**
- It is an all-in-one application, instead of REST + HTML/CSS/JS, which would require at least two separate projects (backend and frontend).
- Server-side authentication is easier to implement.

**Trade-off:**
- The interface is less dynamic, and the page needs to reload each time something changes.

**How the Backoffice is organized:**
- Flask renders every page with Jinja templates (`backoffice/templates/`).
- Pages are grouped by role in two Blueprints: `stock_routes.py` (`/stock/...`, common users) and `routes_admin.py` (`/admin/...`, admin only). Login and logout are in `app.py`.
- Every route starts by checking the role on the server with `permissions.py` (`require_role`, `current_branch_id`). Hiding a button in the page is never the protection.
- For stock operations, the branch always comes from the logged-in user, never from the form.
- Routes do not contain the business rules: they call `stock_service.py` and `user_service.py`, which validate the data (positive quantity, enough stock, existing branch, password length...).
- Each form is sent with POST. The route shows a success or error message with `flash`, then redirects to the page, so refreshing the page never sends the form twice.
- Product information is never stored locally: it is read from the Product API through `product_client.py`.

The stock page shows the product names next to the SKUs and suggests products while typing. If the Product API is down, the page still works and shows a warning.

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

## Stock access for the AI: our own MCP server (read-only)

**Benefits:**
- Only one MCP server to build and run, and the agent can only use the stock queries we expose (no free access to the database).
- No third-party tool (such as MCP Toolbox for Databases) to configure.

**Trade-off:**
- We have to write and maintain the stock tools ourselves.

## Database access: SQLAlchemy alone (no Flask-SQLAlchemy)

**Benefits:**
- The models do not depend on Flask, so the Backoffice and the other services can use the same database without importing the web framework.

**Trade-off:**
- We have to create and manage the engine and the sessions ourselves.

## Database engine: SQLite

**Benefits:**
- A simple file, no server to install or configure.

**Trade-off:**
- The file is shared between the Backoffice and the MCP server, and SQLite handles concurrent writes less well than PostgreSQL.

## Product identifier: the SKU

**Benefits:**
- The SKU is a readable identifier, and it is what the Product API uses to return the details of one product. We store it as `product_id` and check it against the API.

**Trade-off:**
- Our stock depends on SKUs staying unchanged in the Product API, and we store them as text.

## Authentication: server-side session

**Benefits:**
- Fits the server-side rendered Backoffice and is simple to implement.

**Trade-off:**
- The server has to keep the session state, unlike a stateless token.
