## Database Schema

- Branches - id, name

- users - id, username, password hashed, role, isDeleted, branch_id

- Stock - id, branch, product_id, quantity

## Database Relations
- branches (1) ────< users (0..)
- branches (1) ────< stocks (0..)
- stocks (*) ────> external_product_id (Product API Reference)


```mermaid
erDiagram
   BRANCHES |o--o{ USERS : "has (except admin)"
   BRANCHES ||--o{ STOCK : holds
   BRANCHES {
       int id PK
       string name UK
       datetime created_at
   }
   USERS {
       int id PK
       string username UK
       string password_hash
       string role "admin or user"
       int branch_id FK "NULL for admin"
       datetime created_at
       datetime updated_at
       datetime deleted_at "NULL = active"
   }
   STOCK {
       int id PK
       int branch_id FK
       string product_id
       int quantity ">= 0"
       datetime updated_at
   }
```
