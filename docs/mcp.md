# HBntory - Product MCP Server

## Role

The Product MCP Server is the bridge between the AI agent and the data of HBntory.

- The AI agent never calls the Product API or the database directly. It can only use the tools exposed by this server.
- The server gives access to two sources:
  - the external **Product API**, for product information (name, price, description...);
  - the Backoffice **SQLite database**, for stock quantities in each branch.
- The server is implemented in Python with the official MCP SDK (`FastMCP`), in `product_mcp_server/server.py`.
- It uses the **stdio** transport: the AI Query Service starts it as a subprocess and talks to it through standard input and output. No network port is opened.
- It is **read-only**: no tool can create, modify or delete data.

Settings (environment variables):

| Variable | Default | Purpose |
| --- | --- | --- |
| `PRODUCT_API_URL` | `http://localhost:5001` | Address of the Product API |
| `HBNTORY_DB` | `data/hbntory.db` (at the root of the repository) | Path of the Backoffice database |

Every call to the Product API uses a **5 second timeout**, so the agent is never blocked by a slow or frozen API.

The default database path is built from the location of `server.py`, not from the folder where the program is started. This way the server finds the database whether it is started from `product_mcp_server/` (manual tests) or by the AI Query Service from `ai_service/`.

## Tool definitions

### Product tools (Product API)

| Tool | Input | Output on success | Possible errors |
| --- | --- | --- | --- |
| `list_products` | `search` (string, optional): a word to search, for example `"mouse"`. Empty = all products. | `{"ok": true, "products": [{"sku", "name", "category", "unit_price", "currency"}]}` | `product_api_unavailable` |
| `get_product` | `sku` (string, required): a SKU such as `"HB-LAP-1001"`, or a product name. | `{"ok": true, "product": {"sku", "name", "description", "category", "brand", "unit_price", "currency", "status"}}` | `invalid_input`, `product_not_found`, `product_api_unavailable` |

`status` is `"active"` or `"discontinued"`. `list_products` does not show discontinued products (this is the default of the Product API), but `get_product` finds them.

### Stock tools (database, read-only)

| Tool | Input | Output on success | Possible errors |
| --- | --- | --- | --- |
| `get_product_stock` | `sku` (string, required): a SKU or a product name. | `{"ok": true, "sku", "name", "in_stock", "total", "branches": [{"branch", "quantity"}]}` | `invalid_input`, `product_not_found`, `database_unavailable` |
| `get_branch_stock` | `branch` (string, required): the branch name, for example `"Main Campus"`. Upper and lower case are ignored. | `{"ok": true, "branch", "products": [{"sku", "name", "quantity"}]}` | `branch_not_found`, `database_unavailable` |
| `check_shopping_list` | `items` (list, required): for example `[{"sku": "HB-MON-2102", "quantity": 2}, {"sku": "27 inch Lab Monitor", "quantity": 1}]`. `sku` can be a SKU or a name. | `{"ok": true, "can_be_satisfied", "single_branch", "missing", "unknown_products", "products", "plan"}` (see below) | `invalid_input`, `unknown_product`, `database_unavailable` |

Why these five tools:

- `list_products` returns only the fields needed to recognize a product. The full details are returned by `get_product`, for one product at a time. The less data the model has to read, the fewer mistakes it makes.
- Each stock tool answers one type of supported question:
  - "Where can I find this product?" → `get_product_stock`
  - "What is available in this branch?" → `get_branch_stock`
  - "Which branches should I visit for my shopping list?" → `check_shopping_list`

The description of each tool (its docstring) and the type of its parameters are what the AI model reads to decide which tool to call and how.

### Finding a product from its name

Customers talk about product names, but products are identified by their SKU. At first the agent had to search the SKU with `list_products` before calling another tool. In our tests the model did not always do it and invented SKUs. So `get_product`, `get_product_stock` and `check_shopping_list` find the product themselves (`resolve_product`):

1. the text is an existing SKU;
2. or it is exactly a product name;
3. or all its words appear in only one product name, in any order ("Compact Monitor 24" finds "24 inch Compact Monitor").

If several products match, the error message lists them. If the Product API is down, `get_product_stock` and `check_shopping_list` use the text as a SKU.

### Details of the stock tools

- `get_product_stock` and `get_branch_stock` only return quantities **greater than zero**.
- `get_branch_stock` adds the product **names** from the Product API, because the database only stores SKUs. If the Product API is down, the quantities are still returned, with `"name": null`. When the branch is unknown, the error message lists the existing branches.
- `check_shopping_list` does the comparison **in Python**, not in the AI model. The result contains:
  - `can_be_satisfied`: `true` if every item exists and can be bought;
  - `single_branch`: the branches where all the known products can be bought in one visit;
  - `missing`: the products that no branch has in sufficient quantity, with the quantity requested and the quantity of each branch (`by_branch`);
  - `unknown_products`: the items that were not found in the catalog. The rest of the result is about the other items;
  - `products`: the name of each SKU of the list;
  - `plan` (only when nothing is in `missing`): the smallest group of branches to visit, and what to buy in each one.
- The quantity of one product must be available in **one** branch, it is never split between two branches. Example: 15 monitors are requested, Main Campus has 12 and North Campus has 7. The total is enough, but no branch alone has 15, so the product is in `missing` with the two quantities. We chose this rule to keep the plan simple.

## Error format

Every tool returns the same structure when something goes wrong:

```json
{
  "ok": false,
  "error": "product_not_found",
  "message": "'HB-DOES-NOT-EXIST' matches no product of the catalog"
}
```

- `ok` tells the agent immediately whether the call worked.
- `error` is a short, stable code that the code can test.
- `message` is a clear sentence that helps the AI model write its answer.

| Error code | When |
| --- | --- |
| `invalid_input` | A required input is empty, the shopping list is empty, or an item has no SKU or a quantity lower than 1. |
| `product_not_found` | `get_product` or `get_product_stock`: no product matches the text, or several products match it. |
| `unknown_product` | `check_shopping_list`: none of the items was found. |
| `product_api_unavailable` | The Product API cannot be reached (connection refused or timeout), or it answered with an unexpected status. The message tells the two situations apart. |
| `branch_not_found` | No branch has this name. The message lists the existing branches. |
| `database_unavailable` | The database file does not exist or cannot be read. |

## Error handling

The server handles the four cases required for the Product API:

| Case | What happens | What the tool returns |
| --- | --- | --- |
| Successful product listing | `200`, products in `results` | `ok: true` and the product list |
| Product detail retrieval | `200`, one product | `ok: true` and the product |
| Product not found | no product matches, or `404` | `ok: false`, `product_not_found` |
| Product API connection error | no answer or error status | `ok: false`, `product_api_unavailable` |

How it works:

- All calls to the Product API go through one function, `call_product_api(path, params)`. It sends the request with `requests.get(..., timeout=5)` and returns either the data or an error in the format above.
- All reads of the database go through one function, `query_db(sql, params)`. It first checks that the file exists, then opens the database in **read-only mode** (`?mode=ro`): even a wrong SQL query could not modify the stock. Any SQLite error becomes `database_unavailable`. The values (SKU, branch id) are passed as SQL parameters (`?`), never glued into the query text, to prevent SQL injection.

Limits:

- If an argument has the wrong type (for example a list of texts instead of a list of objects), the MCP library refuses the call with its own technical error.
- A successful answer of the Product API with an unexpected content is not handled.
- A quantity with decimals such as `2.9` is cut to `2`.

The server must never use `print()`. With the stdio transport, standard output carries the MCP messages, and a `print` would break the communication.

## What we do not expose

We only expose what the supported questions need: no price, supplier or category filters, no sorting or pagination, no testing parameters (`force_error`, `simulate_delay_ms`) from the Product API, and no users, password hashes or sessions from the database. Fewer tools and fewer parameters make the agent more reliable and easier to test.

## Manual tests

`product_mcp_server/test_client.py` starts the server, lists its tools and calls the product tools:

```bash
cd product_mcp_server
python3 test_client.py
```

The Product API must be running and the database must exist (see the README).

The tables below were checked on 25/11/2026 on a freshly initialized database, by calling the tools through MCP. The script in the repository only contains some of the product calls for now.

### Product tools

| Test | Call | Result |
| --- | --- | --- |
| Product listing | `list_products(search="keyboard")` | ✅ `ok: true`, 2 keyboards |
| Detail by SKU | `get_product(sku="HB-LAP-1001")` | ✅ Holberton Student Laptop 14, `status: "active"` |
| Detail by name | `get_product(sku="Compact Keyboard ES")` | ✅ `HB-KBD-4102` |
| Discontinued product | `get_product(sku="HB-OLD-1301")` | ✅ `status: "discontinued"` |
| Unknown product | `get_product(sku="HB-DOES-NOT-EXIST")` | ✅ `product_not_found` |
| Empty identifier | `get_product(sku="")` | ✅ `invalid_input` |
| Product API stopped | `list_products`, `get_product` | ✅ `product_api_unavailable` |

### Stock tools

| Test | Call | Result |
| --- | --- | --- |
| Product in two branches | `get_product_stock(sku="HB-MON-2102")` | ✅ Main Campus 12, North Campus 7, total 19 |
| Name with words in another order | `get_product_stock(sku="Compact Monitor 24")` | ✅ same result |
| Product in no branch | `get_product_stock(sku="HB-KBD-4101")` | ✅ `in_stock: false`, empty list |
| Vague name | `get_product_stock(sku="monitor")` | ✅ `product_not_found`, lists the 2 monitors |
| Branch stock, lower case | `get_branch_stock(branch="main campus")` | ✅ 8 products with their names |
| Unknown branch | `get_branch_stock(branch="Paris")` | ✅ `branch_not_found`, lists the branches |
| List possible in one branch | 2 × `HB-MON-2102`, 1 × `HB-MON-2101` | ✅ `single_branch: ["Main Campus"]` and a plan |
| Quantity too high | 30 × `HB-MON-2102` | ✅ in `missing`, `by_branch` 12 and 7 |
| Stock split between branches | 15 × `HB-MON-2102` | ✅ in `missing`, `by_branch` 12 and 7 |
| One unknown product | 2 × "Flying Carpet", 1 × `HB-MON-2102` | ✅ `unknown_products`, plan for the monitor |
| Only unknown products | 2 × "Flying Carpet" | ✅ `unknown_product` |
| Invalid quantity | quantity `0` | ✅ `invalid_input` |
| Database missing | stock tools with `HBNTORY_DB=/tmp/nothing.db` | ✅ `database_unavailable` |
| Product API stopped | `get_branch_stock(branch="North Campus")` | ✅ quantities with `"name": null` |

### Example output: shopping list (25/11/2026)

```text
>>> check_shopping_list {"items": [{"sku": "HB-MON-2102", "quantity": 30}]}
{
  "ok": true,
  "can_be_satisfied": false,
  "single_branch": [],
  "missing": [
    {
      "sku": "HB-MON-2102",
      "name": "24 inch Compact Monitor",
      "requested": 30,
      "by_branch": {"Main Campus": 12, "North Campus": 7},
      "note": "No single branch has the requested quantity."
    }
  ],
  "unknown_products": [],
  "products": {"HB-MON-2102": "24 inch Compact Monitor"}
}
```
