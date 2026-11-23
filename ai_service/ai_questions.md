# HBntory - AI Query Service

## Supported questions

| Type | Example | Tools the agent should use |
| --- | --- | --- |
| Product details | "Give me details about the Holberton Student Laptop 14." | `list_products`, then `get_product` |
| Where is a product | "Which branch has the Wireless Mouse in stock?" | `list_products`, then `get_product_stock` |
| What a branch has | "What products can I find in the Paris branch?" | `get_branch_stock` |
| Shopping list | "I want 2 Holberton Student Laptop 14 and 10 Wireless Mouse. Which branches should I visit?" | `list_products`, then `check_shopping_list` |

## Out of scope

Anything not about HBntory products, stock or branches (weather, opening hours, orders...). The assistant says it can only help with products and stock.

## How we avoid invented answers (hallucination)

- The model gets no product or stock data in its instructions: everything comes from the tools.
- Every tool error has the same shape: `{"ok": false, "error": "...", "message": "..."}`.
- The instructions tell the model to say the information is unavailable instead of guessing.
- The shopping-list comparison is done in Python by `check_shopping_list`, not by the model.
- Temperature 0, and at most 6 steps.
- Every tool call is printed in the terminal of the AI service (`TOOL CALL ...`), and the answer lists `tools_used`.

## Endpoint

- `POST /api/ask` with `{"question": "..."}`.
- Success: `{"answer": "...", "tools_used": [...]}`.
- Errors: `400` (empty or too long question), `503` (model or tools unavailable), with `{"error": "..."}`.