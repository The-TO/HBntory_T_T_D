## Database Schema

- **branches**: id, name, created_at

- **users**: id, username, password_hash, role, branch_id, created_at, updated_at, deleted_at

- **stock**: id, branch_id, product_id, quantity, updated_at

## Database Relations

- branches (1) ────< users (0..*)

- branches (1) ────< stocks (0..*)

- stocks (*) ────> product_id (Product API Reference)

## Database Rules

- An common user has one branch.
- An Admin user has no branch.
- Users are soft deleted by setting a value in the 'deleted_at' row, instead of removing the entire row. A deleted user can't log in anymore and the stock of their branch is never deleted.
- A branch can have multiple stock lines.
- Each stock is always >= 0.
- Products details aren't stocked here, only in the Product API.


```mermaid
erDiagram
   BRANCHES |o--o{ USERS : "has (except admin)"
   BRANCHES ||--o{ STOCK : holds
   BRANCHES {
       int id PK
       string name UK "Name of branch"
       datetime created_at "Creation Date"
   }
   USERS {
       int id PK
       string username UK "Unique username"
       string password_hash "Hashed Password"
       string role "admin or common"
       int branch_id FK "NULL for admin"
       datetime created_at "Creation date"
       datetime deleted_at "NULL = active"
   }
   STOCK {
       int id PK
       int branch_id FK "Which branch"
       string product_id "Product API id"
       int quantity ">= 0"
       datetime updated_at "Last Updated"
   }
```
