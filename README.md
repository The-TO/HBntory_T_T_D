# HBntory

HBntory is our school project: an inventory system for a company that has several branches.

There are two sides:

- the **Backoffice**, for employees. A normal user manages the stock of their branch, the admin manages the users.
- an **assistant** open to everyone, where you ask questions about products and stock in plain English.

The product information (name, price, description...) comes from the Product API given with the project. We don't copy it in our database, we only keep the product SKU and the quantity.

## Team

- Dylan (GitHub: RebornLPB)
- Theo (GitHub: The-TO)
- Theo (GitHub: GitGolik)

## How it works

| Part | Folder | Port |
| --- | --- | --- |
| Product API (not ours) | separate repository | 5001 |
| Backoffice (Flask) | `backoffice/` | 5002 |
| AI service (Flask + agent) | `ai_service/` | 5003 |
| Web page for the assistant | `web_client/` | 8080 |
| MCP server | `product_mcp_server/` | no port (stdio) |
| Ollama (language model) | installed on the computer | 11434 |
| Database (SQLite) | `data/hbntory.db` | |

When you ask a question, the web page sends it to the AI service. The model chooses which tool it needs, the AI service runs it on our MCP server, and the MCP server reads the Product API or the database (read only). Then the model writes the answer.

The diagrams are in [docs/architecture.md](docs/architecture.md).

## Installation

You need Python 3.12, Git, Docker and [Ollama](https://ollama.com).

1. Get the project and install the dependencies:

```bash
git clone https://github.com/The-TO/HBntory_T_T_D.git
cd HBntory_T_T_D
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Start the Product API. Put it **next to** our project, not inside:

```bash
cd ..
git clone https://github.com/hbtn-edu/hbntory-products-api.git
cd hbntory-products-api
docker compose up --build -d
cd ../HBntory_T_T_D
```

To check that it works:

```bash
curl http://localhost:5001/health
```

3. Download the model:

```bash
ollama pull qwen3:8b
```

## Create the database

Start the Product API first, because the test stock uses real products.

```bash
cd backoffice
HBNTORY_ADMIN_PASSWORD='choose-a-password' python3 init_db.py
cd ..
```

It creates two branches (Main Campus and North Campus), the `admin` account and some stock. The password is saved hashed. You can run it twice, nothing is duplicated. If you want to start over, delete `data/hbntory.db`.

## Run the project

Open one terminal per service. In each one, go to the project folder and activate the environment with `source .venv/bin/activate`.

Terminal 1, the Backoffice:

```bash
cd backoffice
python3 app.py
```

Terminal 2, the AI service:

```bash
cd ai_service
python3 api.py
```

If you use another model, give its name like this: `AI_MODEL=llama3.1:8b python3 api.py`

Terminal 3, the web page:

```bash
cd web_client
python3 -m http.server 8080
```

You don't have to start the MCP server, the AI service does it by itself.

## Using the Backoffice

Go to http://localhost:5002.

1. Log in with `admin` and the password you chose.
2. Create a user: a name, a password (8 characters minimum) and a branch.
3. Log out and log in with this new user.
4. You are on the stock page of the branch. You can add, remove or check a product with its SKU, for example `HB-LAP-1001`. The field suggests the products.

What each role can do:

- **admin**: list, create, edit and delete users (soft delete), change their password or branch. No access to the stock.
- **user**: add, remove and see the stock of their own branch only. No access to the user management.

## Using the assistant

Go to http://localhost:8080 and ask a question. Some examples:

- Give me details about the Holberton Student Laptop 14.
- Which branch has the 24 inch Compact Monitor in stock?
- What products can I find in Main Campus?
- I want 2 Breadboard Pack and 1 Compact Student Desk. Which branches should I visit?

It also works in the terminal. With `--debug` you can see which tools are called:

```bash
cd ai_service
python3 ask.py --debug "Which branch has the 24 inch Compact Monitor in stock?"
```

The first answer can be slow, the model has to load.

## Settings

These are environment variables. Only the admin password is required, the others have a default value.

| Variable | Default |
| --- | --- |
| `HBNTORY_ADMIN_PASSWORD` | none |
| `PRODUCT_API_URL` | `http://localhost:5001` |
| `DATABASE_URL` (Backoffice) | `data/hbntory.db` (SQLite) |
| `HBNTORY_DB` (MCP server) | `data/hbntory.db` |
| `SECRET_KEY` | a development key |
| `OLLAMA_URL` | `http://localhost:11434` |
| `AI_MODEL` | `qwen3:8b` |
| `OLLAMA_NUM_CTX` | `8192` |
| `MODEL_TIMEOUT` | `180` (seconds) |

If you move the database, change `DATABASE_URL` and `HBNTORY_DB` together.

## Tests

Backoffice (roles, products and stock rules):

```bash
cd backoffice
python3 -m pytest tests
```

Agent, with a fake model so Ollama is not needed:

```bash
cd ai_service
python3 -m pytest test_agent.py
```

MCP server (the Product API must run and the database must exist):

```bash
cd product_mcp_server
python3 test_client.py
```

Our test results are in [docs/mcp.md](docs/mcp.md) and [docs/ai_questions.md](docs/ai_questions.md).

## Our main choices

- The Backoffice pages are rendered by the server (Flask + Jinja), so there is no separate frontend.
- The web page talks to the AI service with a simple REST request, because every question is independent.
- We made our own MCP server. The stock tools can only read.
- SQLAlchemy with SQLite.
- Passwords are hashed with bcrypt, and sessions are kept on the server.
- The model runs locally with Ollama, so there is no API key to pay.

We explain why, and what we lose with each choice, in [docs/decisions.md](docs/decisions.md).

## Known limitations

- The assistant is not perfect. A small local model can choose the wrong tool or write something wrong, and it can be slow.
- In a shopping list, one product must be fully available in one branch.
- One stock operation is limited to 999 units.
- Two stock changes at exactly the same moment could overlap.
- Usernames are case sensitive (`Bob` and `bob` are two accounts).
- No HTTPS and no CSRF protection.
- Only the first 100 products of the catalog are loaded.
- The services run in Flask development mode.

## Extras we added

- Product names and suggestions on the stock page.
- The assistant understands product names, not only SKUs.
- The answer of the API also says which tools were used.
- `ask.py` to try the assistant from the terminal.

## Documentation

- [Architecture](docs/architecture.md)
- [Decisions](docs/decisions.md)
- [MVP](docs/mvp.md)
- [Database](docs/database.md)
- [Authentication](docs/auth.md)
- [Authorization](docs/authorization.md)
- [MCP server](docs/mcp.md)
- [Assistant questions and tests](docs/ai_questions.md)
