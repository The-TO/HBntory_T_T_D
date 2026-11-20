# HBntory - Product MCP Server

## Role

The Product MCP Server is the bridge between the AI agent and the external Product API.

- The AI agent never calls the Product API directly. It can only use the tools exposed by this server.
- The server is implemented in Python with the official MCP SDK (`FastMCP`), in `product_mcp_server/server.py`.
- It uses the **stdio** transport: the AI Query Service starts it as a subprocess and talks to it through standard input and output. No network port is opened.
- It is **read-only**: no tool can create, modify or delete data.

Settings (environment variables):

| Variable | Default | Purpose |
| --- | --- | --- |
| `PRODUCT_API_URL` | `http://localhost:5001` | Address of the Product API |

Every call to the Product API uses a **5 second timeout**, so the agent is never blocked by a slow or frozen API.

## Tool definitions

| Tool | Input | Output on success | Possible errors |
| --- | --- | --- | --- |
| `list_products` | `search` (string, optional): a word of the product name, for example `"mouse"`. Empty = all products. | `{"ok": true, "products": [{"sku", "name", "category", "unit_price", "currency"}]}` | `product_api_unavailable` |
| `get_product` | `sku` (string, required): the product SKU, for example `"HB-LAP-1001"`. Spaces are removed and letters are put in upper case. | `{"ok": true, "product": {"sku", "name", "description", "category", "brand", "unit_price", "currency", "discontinued"}}` | `invalid_input`, `product_not_found`, `product_api_unavailable` |

Why two tools only:

- Customers talk about product **names** ("the wireless mouse"), but products are identified by their **SKU**. The agent first uses `list_products` with a word of the name to find the SKU, then `get_product` for the details.
- `list_products` returns only the fields needed to recognize a product. The full details are returned by `get_product`, for one product at a time. The less data the model has to read, the fewer mistakes it makes.

The description of each tool (its docstring) and the type of its parameters are what the AI model reads to decide which tool to call and how. They are written in English, short, with an example value.

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
| `invalid_input` | A required input is missing or empty (for example an empty SKU). |
| `product_not_found` | The Product API answered `404`: no product has this SKU. |
| `product_api_unavailable` | The Product API cannot be reached (connection refused or timeout), or it answered with an unexpected status (for example `503`). In both cases, the agent can only say that product information is unavailable, so one code is enough. The message tells the two situations apart. |

## Error handling

The server handles the four cases required by the project:

| Case | What the Product API does | What the tool returns |
| --- | --- | --- |
| Successful product listing | `200`, products in `results` | `ok: true` and the product list |
| Product detail retrieval | `200`, one product | `ok: true` and the product |
| Product not found | `404` | `ok: false`, `product_not_found` |
| Product API connection error | no answer (exception) or error status | `ok: false`, `product_api_unavailable` |

How it works: all calls to the Product API go through one function, `call_product_api(path, params)`. It sends the request with `requests.get(..., timeout=5)` and returns either the data or an error in the format above. The tools only check whether an error came back, and return it as it is.

**The server never fails silently.** A tool never crashes and never returns an empty answer: it always returns either data or a clear error. This matters for the AI agent: when information is missing, a clear error lets the agent say "this information is unavailable" instead of inventing an answer.

Note: the server must never use `print()`. With the stdio transport, standard output carries the MCP messages, and a `print` would break the communication.

## What we do not expose

The Product API can do more than our tools show. We deliberately do not expose:

- price filters (`min_price`, `max_price`);
- supplier and category filters;
- sorting and pagination;
- the suppliers and categories endpoints;
- the testing parameters `force_error` and `simulate_delay_ms`.

The agent does not need them to answer the supported questions. Fewer tools and fewer parameters make the agent more reliable, and keep the server easier to test and to explain.

## Manual tests

Before connecting the AI agent, the tools were tested by hand with `product_mcp_server/test_client.py`. The script starts the server, lists its tools, then calls them one by one and prints each result.

How to run it (the Product API must be running):

```bash
cd product_mcp_server
python3 test_client.py
```

To test a Product API failure, stop the Product API (or give the server an address where nothing answers, for example `PRODUCT_API_URL=http://localhost:5999 python3 test_client.py`) and run the script again.

| Test | Call | Expected result | Result |
| --- | --- | --- | --- |
| Product listing works | `list_products(search="keyboard")` | `ok: true`, a list of keyboards | ✅ 2 keyboards |
| Product detail works | `get_product(sku="HB-LAP-1001")` | `ok: true`, the Holberton Student Laptop 14 | ✅ |
| Invalid product identifier | `get_product(sku="HB-DOES-NOT-EXIST")` | `ok: false`, `product_not_found` | ✅ |
| Empty identifier | `get_product(sku="")` | `ok: false`, `invalid_input` | ✅ |
| Product API failure | all tools, with the Product API stopped | `ok: false`, `product_api_unavailable` | ✅ |

### Test output with the Product API running (20/11/2026)

```text
TOOLS: ['list_products', 'get_product']

>>> list_products {'search': 'keyboard'}
{
  "ok": true,
  "products": [
    {
      "sku": "HB-KBD-4102",
      "name": "Compact Keyboard ES",
      "category": "Accessories",
      "unit_price": 49.99,
      "currency": "USD"
    },
    {
      "sku": "HB-KBD-4101",
      "name": "Mechanical Keyboard EN",
      "category": "Accessories",
      "unit_price": 74.0,
      "currency": "USD"
    }
  ]
}

>>> get_product {'sku': 'HB-LAP-1001'}
{
  "ok": true,
  "product": {
    "sku": "HB-LAP-1001",
    "name": "Holberton Student Laptop 14",
    "description": "Training catalog item for HBntory integration: holberton student laptop 14.",
    "category": "Laptops",
    "brand": "Holberton",
    "unit_price": 799.0,
    "currency": "USD",
    "discontinued": false
  }
}

>>> get_product {'sku': 'HB-DOES-NOT-EXIST'}
{
  "ok": false,
  "error": "product_not_found",
  "message": "No product matches this SKU"
}

>>> get_product {'sku': ''}
{
  "ok": false,
  "error": "invalid_input",
  "message": "A product SKU is required."
}
```

### Test output with the Product API stopped (20/11/2026)

```text
TOOLS: ['list_products', 'get_product']

>>> list_products {'search': 'keyboard'}
{
  "ok": false,
  "error": "product_api_unavailable",
  "message": "The Product API cannot be reached. Product information is unavailable right now."
}

>>> get_product {'sku': 'HB-LAP-1001'}
{
  "ok": false,
  "error": "product_api_unavailable",
  "message": "The Product API cannot be reached. Product information is unavailable right now."
}

>>> get_product {'sku': 'HB-DOES-NOT-EXIST'}
{
  "ok": false,
  "error": "product_api_unavailable",
  "message": "The Product API cannot be reached. Product information is unavailable right now."
}

>>> get_product {'sku': ''}
{
  "ok": false,
  "error": "invalid_input",
  "message": "A product SKU is required."
}
```

The empty SKU is refused before any call to the Product API, which is why it returns `invalid_input` in both runs.

## Planned for Task 5: stock tools

The AI agent will also need stock information. It will be added to this same server as read-only tools (`get_branch_stock`, `check_purchase_availability`, and a tool for the stock of one product across all branches). They will be documented in this file when they are implemented.