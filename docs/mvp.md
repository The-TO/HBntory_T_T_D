# HBntory - MVP definition

## First (mandatory, in this order)

- Product API running in Docker.
- Database schema, SQLAlchemy models, initialization script.
- Login and logout, password hashing, role assignment (common user and admin) and their routes.
- MCP Server: `list_products` and `get_product`, tested manually.
- Stock tools in the MCP Server.
- AI Service query with one REST endpoint.
- README.

## To leave for later

- Frontend improvements.
- Non-critical bug fixes and extra tests (the critical scenarios are tested in the MVP).
- Styled error pages (basic error messages are still handled in the MVP).

## Only if we have time

- Design improvements.
- Switching to PostgreSQL.
- Conversation history for the Client Web (with WebSocket).

## Why this MVP is realistic

- It avoids unnecessary extra features.
- We have clearly focused on the main objective: all the mandatory requirements.
