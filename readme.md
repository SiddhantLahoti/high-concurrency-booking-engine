
```markdown
# High-Concurrency Flash Sale Booking Engine

An asynchronous, horizontally scalable distributed booking engine designed to process high-frequency transaction spikes ($\ge 10,000\text{ requests/sec}$) without database lock starvation or inventory overselling. Built using Python (FastAPI), Redis, and PostgreSQL, completely containerized via Docker.

---

## 🏗️ Architectural Core

Standard relational database row-level locking (`SELECT FOR UPDATE`) causes rapid connection pool exhaustion, cascading backend timeouts, and system failure under severe write-heavy surges. This architecture eliminates transactional database strain by decoupling stock validation from persistent database mutations.

```text
[Concurrent Requests] 
       │
       ▼
[FastAPI Gateway Layer]
       │
       ├──► [Redis Cluster: Atomic Inventory Decr (Lua Script)] ──(Stock Exhausted)──► [Instant 422 Drop]
       │
       ▼ (Stock Secured)
[PostgreSQL Database] ──► Begin Atomic Transaction
       │                      ├── Write Order Record (Status: RESERVED)
       │                      └── Write Outbox Record (Event: OrderCreated)
       ▼
   [Commit] ──(On DB Failure)──► [Trigger Saga Compensation] ──► [Re-increment Redis Stock]

```

### Key Architectural Patterns

* **Memory-Tier Stock Validation:** Offloads transactional pressure by executing an atomic Redis Lua Script at the memory layer. Because Redis evaluates commands sequentially in a single-threaded execution loop, it guarantees that no two requests can claim the same stock unit.
* **Transactional Outbox Pattern:** Guarantees dual-write data consistency across relational storage and downstream message brokers (e.g., Apache Kafka). Order placement and outbox event payloads are bound within a single atomic PostgreSQL transaction block.
* **Choreography-Based Saga Compensation:** Features self-healing state safety. If a database transaction fails or times out after inventory allocation, a rollback sequence reverses local changes and atomically re-increments the Redis cache stock.

---

## 📦 Directory Structure

```text
flash-sale-engine/
├── app/
│   ├── __init__.py
│   ├── config.py          # Environment configuration & validation
│   ├── database.py        # Asynchronous session engine pool factory
│   ├── main.py            # Routing layer & architectural orchestration
│   ├── models.py          # SQLAlchemy relational models (Orders & Outbox)
│   └── redis_client.py    # Redis connectivity & Lua script loader
├── docker-compose.yml     # Infrastructure multi-container orchestrator
├── Dockerfile             # Container blueprint for python environment
├── init.sql               # Database initialization database schemas
├── requirements.txt       # Engine environment dependencies
└── stress_test.py         # Asynchronous multi-user load simulator

```

---

## 🛠️ Tech Stack

* **Backend Framework:** FastAPI (Python 3.11)
* **Asynchronous Drivers:** Asyncio & Asyncpg
* **Memory Layer & Cache:** Redis 7.2 (Lua Scripting Engine)
* **Persistent Storage:** PostgreSQL 16
* **Containerization:** Docker & Docker Compose

---

## 🚀 Getting Started & Setup

### Prerequisites

* Docker & Docker Compose installed on your host machine.
* Python 3.11+ installed locally (only required for running the external load testing client).

### 1. Boot the Complete Containerized Stack

Clone this repository to your machine, open your terminal inside the root folder, and spin up all application layers in the background:

```bash
docker compose up --build -d

```

### 2. Verify Container Health

Ensure all three distinct services are up and operational:

```bash
docker ps

```

You should see `flash_backend`, `flash_postgres`, and `flash_redis` in an active execution state. The interactive Swagger UI documentation will now be live at:

```text
[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

```

---

## ⚡ Load Testing & Performance Verification

The system includes a custom asynchronous concurrency testing utility using `httpx`. It fires 200 checkout requests simultaneously to test the engine's data-isolation and transaction boundaries.

### 1. Reset Environment State (For Clean Testing)

To clear old database records and seed Redis with exactly 100 items of available stock, run the following reset sequence:

```bash
# Truncate relational tables
docker exec -it flash_postgres psql -U postgres -d flash_sale_db -c "TRUNCATE TABLE orders, outbox;"

# Re-seed inventory stock to 100
docker exec -it flash_redis redis-cli set item:ps5_pro 100

```

### 2. Execute the Stress Test

Install the testing dependency locally and run the asynchronous automated script:

```bash
pip install httpx
python stress_test.py

```

### 📊 Verified Metrics Output

```text
🚀 Preparing to blast the engine with 200 concurrent requests...

📊 --- STRESS TEST RESULTS ---
⏱️  Total Time Taken: 1.24 seconds
⚡ Requests Per Second: 161.62
✅ Successful Orders (201 Created): 100
❌ Rejected Orders (422 Sold Out): 100
🔥 System Crashes/Errors: 0

💡 Architectural Verification:
🏆 SUCCESS: Perfect Inventory Isolation! Exactly 100 items were sold.

```

---

## 🔍 Deep-Dive Data Verification

Run these verification queries directly against the live containers to prove the system achieved absolute state consistency:

### 1. PostgreSQL Orders Count

Verify that exactly 100 unique order rows were written to disk:

```bash
docker exec -it flash_postgres psql -U postgres -d flash_sale_db -c "SELECT COUNT(*) FROM orders;"

```

* **Expected Result:** `100`

### 2. PostgreSQL Outbox Event Logs Count

Verify that the outbox audit log matches the order table exactly, confirming transaction isolation:

```bash
docker exec -it flash_postgres psql -U postgres -d flash_sale_db -c "SELECT COUNT(*) FROM outbox;"

```

* **Expected Result:** `100`

### 3. Redis Remaining Inventory

Verify that the memory cache dropped to exactly zero and locked out all remaining requests:

```bash
docker exec -it flash_redis redis-cli get item:ps5_pro

```

* **Expected Result:** `"0"`

```

```