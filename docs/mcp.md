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
| `list_products` | `search` (string, optional): a word of the product name, for example `"mouse"`. Empty = all products. | `{"ok": true, "products": [{"sku", "name", "category", "unit_price", "currency"}]}` | `product_api_unavailable` |
| `get_product` | `sku` (string, required): the product SKU, for example `"HB-LAP-1001"`. Spaces are removed and letters are put in upper case. | `{"ok": true, "product": {"sku", "name", "description", "category", "brand", "unit_price", "currency", "discontinued"}}` | `invalid_input`, `product_not_found`, `product_api_unavailable` |

### Stock tools (database, read-only)

| Tool | Input | Output on success | Possible errors |
| --- | --- | --- | --- |
| `get_product_stock` | `sku` (string, required): the product SKU, for example `"HB-MON-2102"`. | `{"ok": true, "sku", "in_stock": true/false, "total", "branches": [{"branch", "quantity"}]}` | `invalid_input`, `database_unavailable` |
| `get_branch_stock` | `branch` (string, required): the branch name, for example `"Main Campus"`. Upper and lower case are ignored. | `{"ok": true, "branch", "products": [{"sku", "name", "quantity"}]}` | `branch_not_found`, `database_unavailable` |
| `check_shopping_list` | `items` (list, required): for example `[{"sku": "HB-MON-2102", "quantity": 2}, {"sku": "HB-MON-2101", "quantity": 1}]`. | `{"ok": true, "can_be_satisfied", "single_branch", "missing", "plan"}` (see below) | `invalid_input`, `database_unavailable` |

Why these five tools:

- Customers talk about product **names** ("the wireless mouse"), but products are identified by their **SKU**. The agent first uses `list_products` with a word of the name to find the SKU, then the other tools with this SKU.
- `list_products` returns only the fields needed to recognize a product. The full details are returned by `get_product`, for one product at a time. The less data the model has to read, the fewer mistakes it makes.
- Each stock tool answers one type of supported question:
  - "Where can I find this product?" → `get_product_stock`
  - "What is available in this branch?" → `get_branch_stock`
  - "Which branches should I visit for my shopping list?" → `check_shopping_list`

The description of each tool (its docstring) and the type of its parameters are what the AI model reads to decide which tool to call and how. They are written in English and kept short.

### Details of the stock tools

- Only quantities **greater than zero** are returned. A product with a quantity of `0` is treated as "not in stock".
- `get_product_stock` does not check whether the SKU exists in the Product API. For an unknown SKU it simply returns `"in_stock": false`. This is why the agent always finds the SKU with `list_products` first.
- `get_branch_stock` adds the product **names** from the Product API, because the database only stores SKUs. If the Product API is down, the quantities are still returned, with `"name": null`. When the branch is unknown, the error message lists the existing branches, so the agent can tell the customer which ones exist.
- `check_shopping_list` does the comparison **in Python**, not in the AI model. A language model can make mistakes when comparing numbers, Python cannot. The result contains:
  - `can_be_satisfied`: `true` if every product of the list can be bought;
  - `single_branch`: the branches where the **whole** list can be bought in one visit;
  - `missing`: the products that no branch has in sufficient quantity, with the quantity requested and the total quantity in all branches;
  - `plan` (only when the list can be satisfied): the smallest group of branches to visit, and what to buy in each one.
- In `check_shopping_list`, the quantity of one product must be available in **one** branch: the quantity of a product is never split between two branches. Example: 15 monitors are requested, Main Campus has 12 and North Campus has 7. The total (19) is enough, but no branch alone has 15, so the product is in `missing` with `"total_available": 19`. The agent can then explain that the stock exists but is split between branches. We chose this rule to keep the plan simple for the customer and for the code.

## Error format

Every tool returns the same structure when something goes wrong:

```json
{
  "ok": false,
  "error": "product_not_found",
  "message": "No product matches this SKU"
}
```

- `ok` tells the agent immediately whether the call worked.
- `error` is a short, stable code that the code can test.
- `message` is a clear sentence that the AI model can use in its answer.

| Error code | When |
| --- | --- |
| `invalid_input` | A required input is missing or empty (for example an empty SKU), or a shopping list item has no SKU, or a quantity that is not a whole number greater than zero. |
| `product_not_found` | The Product API answered `404`: no product has this SKU. |
| `product_api_unavailable` | The Product API cannot be reached (connection refused or timeout), or it answered with an unexpected status (for example `503`). In both cases, the agent can only say that product information is unavailable, so one code is enough. The message tells the two situations apart. |
| `branch_not_found` | No branch has this name. The message lists the existing branches. |
| `database_unavailable` | The database file does not exist or cannot be read. |

## Error handling

The server handles the four cases required for the Product API:

| Case | What the Product API does | What the tool returns |
| --- | --- | --- |
| Successful product listing | `200`, products in `results` | `ok: true` and the product list |
| Product detail retrieval | `200`, one product | `ok: true` and the product |
| Product not found | `404` | `ok: false`, `product_not_found` |
| Product API connection error | no answer (exception) or error status | `ok: false`, `product_api_unavailable` |

How it works:

- All calls to the Product API go through one function, `call_product_api(path, params)`. It sends the request with `requests.get(..., timeout=5)` and returns either the data or an error in the format above.
- All reads of the database go through one function, `query_db(sql, params)`. It first checks that the file exists, then opens the database in **read-only mode** (`?mode=ro`): even a wrong SQL query could not modify the stock. Any SQLite error becomes `database_unavailable`. The values (SKU, branch id) are passed as SQL parameters (`?`), never glued into the query text, to prevent SQL injection.
- The tools only check whether an error came back, and return it as it is.

**The server never fails silently.** A tool never crashes and never returns an empty answer: it always returns either data or a clear error. This matters for the AI agent: when information is missing, a clear error lets the agent say "this information is unavailable" instead of inventing an answer.

Note: the server must never use `print()`. With the stdio transport, standard output carries the MCP messages, and a `print` would break the communication.

## What we do not expose

We deliberately expose only what the supported questions need: no price, supplier or category filters, no sorting or pagination, no testing parameters (`force_error`, `simulate_delay_ms`) from the Product API, and no users, password hashes or sessions from the database. Fewer tools and fewer parameters make the agent more reliable and easier to test.

## Manual tests

Before connecting the AI agent, the tools were tested by hand with `product_mcp_server/test_client.py`. The script starts the server, lists its tools, then calls them one by one and prints each result.

How to run it (the Product API must be running, and the database must exist: `python3 init_db.py` in `backoffice/`):

```bash
cd product_mcp_server
python3 test_client.py
```

To test a Product API failure, stop the Product API (or give the server an address where nothing answers, for example `PRODUCT_API_URL=http://localhost:5999 python3 test_client.py`) and run the script again.

To test a database failure, give the server a path where no database exists, for example `HBNTORY_DB=/tmp/nothing.db python3 test_client.py`.

### Product tools

| Test | Call | Expected result | Result |
| --- | --- | --- | --- |
| Product listing works | `list_products(search="keyboard")` | `ok: true`, a list of keyboards | ✅ 2 keyboards |
| Product detail works | `get_product(sku="HB-LAP-1001")` | `ok: true`, the Holberton Student Laptop 14 | ✅ |
| Invalid product identifier | `get_product(sku="HB-DOES-NOT-EXIST")` | `ok: false`, `product_not_found` | ✅ |
| Empty identifier | `get_product(sku="")` | `ok: false`, `invalid_input` | ✅ |
| Product API failure | all tools, with the Product API stopped | `ok: false`, `product_api_unavailable` | ✅ |

### Example output: product not found (20/11/2026)

```text
>>> get_product {'sku': 'HB-DOES-NOT-EXIST'}
{
  "ok": false,
  "error": "product_not_found",
  "message": "No product matches this SKU"
}
```

### Stock tools

| Test | Call | Expected result | Result |
| --- | --- | --- | --- |
| Product in two branches | `get_product_stock(sku="HB-MON-2102")` | `ok: true`, Main Campus 12, North Campus 7, total 19 | ✅ |
| Product in no branch | `get_product_stock(sku="HB-KBD-4101")` | `ok: true`, `in_stock: false`, empty list | ✅ |
| Branch stock, lower case name | `get_branch_stock(branch="main campus")` | `ok: true`, branch "Main Campus" with product names | ✅ 8 products |
| Unknown branch | `get_branch_stock(branch="Paris")` | `ok: false`, `branch_not_found`, list of branches | ✅ |
| Shopping list possible in one branch | `check_shopping_list` with 2 × HB-MON-2102 and 1 × HB-MON-2101 | `can_be_satisfied: true`, `single_branch: ["Main Campus"]`, a plan | ✅ |
| Quantity too high | `check_shopping_list` with 30 × HB-MON-2102 | `can_be_satisfied: false`, in `missing` with `total_available: 19` | ✅ |
| Stock split between branches | `check_shopping_list` with 15 × HB-MON-2102 | `can_be_satisfied: false`, `total_available: 19` | ✅ |
| Invalid quantity | `check_shopping_list` with a quantity of 0 | `ok: false`, `invalid_input` | ✅ |
| Database missing | all stock tools, with `HBNTORY_DB=/tmp/nothing.db` | `ok: false`, `database_unavailable` | ✅ |
| Product API stopped, database OK | `get_branch_stock(branch="North Campus")` | `ok: true`, quantities with `"name": null` | ✅ |

### Example output: shopping list (23/11/2026)

```text
>>> check_shopping_list {'items': [{'sku': 'HB-MON-2102', 'quantity': 30}]}
{
  "ok": true,
  "can_be_satisfied": false,
  "single_branch": [],
  "missing": [
    {
      "sku": "HB-MON-2102",
      "requested": 30,
      "total_available": 19
    }
  ]
}
```