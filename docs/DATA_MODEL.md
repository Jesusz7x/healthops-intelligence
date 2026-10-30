# Data model

All example records are synthetic. SQLite constraints reject negative stock, impossible ages, duplicate codes/emails, unsupported states, and dangling relationships.

```mermaid
erDiagram
  USERS ||--o{ SESSIONS : authenticates
  USERS ||--o{ AUDIT : performs
  USERS ||--o{ STOCK_MOVEMENTS : records
  PATIENTS ||--o{ APPOINTMENTS : scheduled_for
  STAFF ||--o{ APPOINTMENTS : assigned_to
  INVENTORY ||--o{ STOCK_MOVEMENTS : changes
  USERS { int id PK string email UK string role bool active string password_hash }
  SESSIONS { string token_hash PK int user_id FK datetime expires_at }
  PATIENTS { int id PK string code UK string full_name string email int age string status }
  STAFF { int id PK string code UK string full_name string role string department bool active }
  APPOINTMENTS { int id PK int patient_id FK int staff_id FK datetime starts_at string status }
  INVENTORY { int id PK string sku UK string name int quantity int reorder_level string unit }
  STOCK_MOVEMENTS { int id PK int inventory_id FK int actor_id FK int delta string reason datetime created_at }
  AUDIT { int id PK int actor_id FK string action string entity string entity_id string detail datetime created_at }
  SETTINGS { string key PK string value datetime updated_at }
```

Sessions store SHA-256 token digests rather than bearer tokens. Passwords use a random 16-byte salt and PBKDF2-HMAC-SHA256 (240,000 rounds). Audit detail avoids patient name/email fields. The schema does not contain real medical-record, diagnosis, medication, or treatment data.
