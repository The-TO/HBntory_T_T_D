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

## Backoffice code organisation: one blueprint per feature

**Benefits:**
- Each feature (`stock_routes.py` for the stock pages, `routes_admin.py` for user management) lives in its own file, so team members do not edit the same file and conflicts stay rare.

**Trade-off:**
- A few more files to follow, and each blueprint has to be registered in `app.py`.

## Stock pages: the branch comes from the logged-in user

**Benefits:**
- Every stock route starts with `permissions.current_branch_id()`. The branch is never read from the URL or a form, so a common user cannot act on another branch, even by editing the request. The admin gets a 403 on these routes.

**Trade-off:**
- Each new route has to call it by hand: forgetting it would leave the route open.

## Stock pages: Post/Redirect/Get with flash messages

**Benefits:**
- After each POST the route redirects to the stock page, so refreshing the page does not repeat the action. The result (success or error such as invalid quantity, unknown product, not enough stock, Product API unavailable) is shown with a flash message, using only server-side templates.

**Trade-off:**
- The page reloads after each action.

## Product API Integration in the Backoffice

- The stock page now shows which product a user is working on. Product names come from the external Product API, never from our own database. The local database still stores only the product SKU and the quantity.

- **Product suggestions:** when a user types in a SKU field (Add, Remove, Check), the browser suggests existing SKUs together with their product names.
- **Name column:** the "Products in stock" table shows the product name next to the SKU and the quantity.
- **Server-side check unchanged:** adding stock still verifies the SKU against the Product API, so the suggestions are only a typing aid.

### Benefits

- **No duplicated data:** a renamed product shows its new name immediately, with no synchronization.
- **Efficient:** one API call per page load instead of one per table row.
- **Resilient display:** if the API is down, the page still loads, with a warning and `-` in place of names.
- **Safe input:** every SKU is still validated on the server before stock is added.

### Trade-offs

- **Dependency on the API:** while it is down, names are not shown and adding stock is refused, because the SKU cannot be verified.
- **No cache:** names are always fresh, but each page load makes an extra request to the API.
- **No pagination:** at most 100 products are loaded. A larger catalog would need paging.
- **Free typing allowed:** the SKU field is not a strict dropdown, so a wrong SKU can be typed. It is rejected on submit, not while typing.


### How it works

1. `products_by_sku()` in `product_client.py` calls the Product API once and returns a dictionary `{sku: product}`.
2. The `index` route in `stock_routes.py` loads this dictionary and passes it to the template. If the API is unreachable, it passes an empty dictionary and shows a warning.
3. `stock.html` uses the dictionary to fill the suggestion list and the Name column. A product that is not found in the API response is shown as `-`.

##### How to test

1. Start the Product API container (port 5001).
2. Run `init_db.py`, then `python3 app.py` from `backoffice/`.
3. Log in as a common user and open `/stock/`. Check that the table shows a Name column and that the SKU fields suggest products.
4. Stop the Product API and reload `/stock/`. The page should still load, with a warning and `-` in the Name column.
5. Run `pytest -v` from `backoffice/` for the automatic tests.

## AI model: a local model with Ollama (`qwen3:8b`)

**Benefits:**
- It runs on our own machines: no API key, no cost per question, and the questions are not sent to an external service.
- It can call tools, which is what our agent needs. Another model can be used with the `AI_MODEL` environment variable.

**Trade-off:**
- It needs enough memory (a graphics card helps), answers can be slow, and a small model sometimes picks the wrong tool or adds information. This is why several checks are done in Python.

## Assistant tools accept product names

**Benefits:**
- In our tests with a small model (`llama3.1:8b`), the model sometimes invented a SKU instead of searching for it, then told the customer that the product did not exist. The tools now find the product from its name in Python, so the model only has to copy what the customer wrote.

**Trade-off:**
- A vague name such as "monitor" matches several products: the tool returns an error that lists them. Names are compared word by word, so a spelling mistake is not found.
