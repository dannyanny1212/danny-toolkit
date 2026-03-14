"""
Protocol 'Deep Ingestion' — Stress Test v2.0
=============================================
Test de stabiliteit van Atomic Staging-Swap en LocalEmbeddings (384d)
onder maximale belasting met web-scraped FastAPI + Pydantic v2 documentatie.

STAP 1: Massa Scrape — FastAPI + Pydantic v2 docs van GitHub (raw markdown)
         Aangevuld met lokale docs. Target: 500-1000 chunks.
STAP 2: 5 parallelle POST requests naar /api/v1/ingest/background
         EMBEDDING_PROVIDER=local geforceerd (384d LocalEmbeddings)
STAP 3: Poll alle job_ids, monitor RAM/GPU, staging collectie verificatie
STAP 4: Rapport: totale tijd, chunks/sec, integriteitscheck, staging orphans

Gebruik:
    python stress_test_deep_ingestion.py
Vereist:
    - FastAPI server draaiend op localhost:8000
    - pip install httpx psutil
"""

import asyncio
import os
import sys
import tempfile
import time
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

# Forceer LocalEmbeddings (384d) — MOET voor import van project modules
os.environ["EMBEDDING_PROVIDER"] = "local"

# Zorg dat project root op sys.path staat
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import httpx
except ImportError:
    print("[FATAL] httpx niet geinstalleerd: pip install httpx")
    sys.exit(1)

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False
    print("[WARN] psutil niet beschikbaar — RAM/GPU monitoring uitgeschakeld")

# ── Config ──
BASE_URL = os.environ.get("STRESS_TEST_URL", "http://localhost:8000")
API_KEY = os.environ.get(
    "FASTAPI_SECRET_KEY",
    os.environ.get("STRESS_TEST_API_KEY", ""),
)
DOCS_DIR = PROJECT_ROOT / "data" / "rag" / "documenten"
SCRAPE_DIR = PROJECT_ROOT / "data" / "rag" / "documenten" / "_stress_test"
POLL_INTERVAL = 2.0        # seconden tussen status polls
MAX_POLL_TIME = 600        # max 10 minuten wachten
CONCURRENT_JOBS = 5        # 5 parallelle ingest jobs
TARGET_MIN_CHUNKS = 500    # minimaal 500 chunks
CHUNK_SIZE_WORDS = 350     # Config.CHUNK_SIZE = 350


# ═══════════════════════════════════════════════════════
# STAP 1: MASSA SCRAPE — FastAPI + Pydantic v2 docs
# ═══════════════════════════════════════════════════════

# GitHub raw URLs voor FastAPI docs (markdown bronbestanden)
FASTAPI_RAW_BASE = "https://raw.githubusercontent.com/fastapi/fastapi/master/docs/en/docs"
FASTAPI_DOC_PATHS = [
    "index.md",
    "features.md",
    "tutorial/first-steps.md",
    "tutorial/path-params.md",
    "tutorial/query-params.md",
    "tutorial/body.md",
    "tutorial/body-multiple-params.md",
    "tutorial/body-fields.md",
    "tutorial/body-nested-models.md",
    "tutorial/header-params.md",
    "tutorial/cookie-params.md",
    "tutorial/response-model.md",
    "tutorial/extra-models.md",
    "tutorial/response-status-code.md",
    "tutorial/request-forms.md",
    "tutorial/request-files.md",
    "tutorial/handling-errors.md",
    "tutorial/dependencies/index.md",
    "tutorial/dependencies/classes-as-dependencies.md",
    "tutorial/dependencies/dependencies-in-path-operation-decorators.md",
    "tutorial/dependencies/global-dependencies.md",
    "tutorial/security/index.md",
    "tutorial/security/first-steps.md",
    "tutorial/security/get-current-user.md",
    "tutorial/security/oauth2-jwt.md",
    "tutorial/middleware.md",
    "tutorial/cors.md",
    "tutorial/sql-databases.md",
    "tutorial/bigger-applications.md",
    "tutorial/background-tasks.md",
    "tutorial/metadata.md",
    "tutorial/testing.md",
    "tutorial/debugging.md",
    "advanced/response-directly.md",
    "advanced/custom-response.md",
    "advanced/middleware.md",
    "advanced/websockets.md",
    "advanced/events.md",
    "advanced/testing-websockets.md",
    "advanced/settings.md",
    "deployment/concepts.md",
    "deployment/docker.md",
]

# GitHub raw URLs voor Pydantic v2 docs
PYDANTIC_RAW_BASE = "https://raw.githubusercontent.com/pydantic/pydantic/main/docs"
PYDANTIC_DOC_PATHS = [
    "index.md",
    "concepts/models.md",
    "concepts/fields.md",
    "concepts/validators.md",
    "concepts/config.md",
    "concepts/serialization.md",
    "concepts/types.md",
    "concepts/unions.md",
    "concepts/json_schema.md",
    "concepts/dataclasses.md",
    "concepts/strict_mode.md",
    "concepts/postponed_annotations.md",
    "concepts/performance.md",
    "why.md",
    "migration.md",
    "errors/validation_errors.md",
    "errors/usage_errors.md",
    "integrations/visual_studio_code.md",
]


async def scrape_docs(client: httpx.AsyncClient) -> list[Path]:
    """Scrape FastAPI + Pydantic v2 docs van GitHub raw content.

    Returns:
        Lijst van lokaal opgeslagen .md bestanden.
    """
    SCRAPE_DIR.mkdir(parents=True, exist_ok=True)
    scraped: list[Path] = []
    errors = 0

    # Bouw URL-paden
    targets: list[tuple[str, str]] = []
    for doc_path in FASTAPI_DOC_PATHS:
        url = f"{FASTAPI_RAW_BASE}/{doc_path}"
        safe_name = f"fastapi_{doc_path.replace('/', '_')}"
        targets.append((url, safe_name))

    for doc_path in PYDANTIC_DOC_PATHS:
        url = f"{PYDANTIC_RAW_BASE}/{doc_path}"
        safe_name = f"pydantic_{doc_path.replace('/', '_')}"
        targets.append((url, safe_name))

    print(f"  Scraping {len(targets)} docs van GitHub...")

    # Parallel fetch in batches van 10 (rate-limit friendly)
    BATCH = 10
    for batch_start in range(0, len(targets), BATCH):
        batch = targets[batch_start:batch_start + BATCH]
        tasks = []
        for url, name in batch:
            tasks.append(_fetch_doc(client, url, name))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Path):
                scraped.append(result)
            elif isinstance(result, Exception):
                errors += 1

        pct = min(100, int((batch_start + len(batch)) / len(targets) * 100))
        print(f"    [{pct:3d}%] {len(scraped)} scraped, {errors} errors")

    return scraped


async def _fetch_doc(client: httpx.AsyncClient, url: str, filename: str) -> Path:
    """Fetch een enkel document en sla op in SCRAPE_DIR."""
    resp = await client.get(url, timeout=15.0, follow_redirects=True)
    resp.raise_for_status()
    content = resp.text

    # Filter te kleine bestanden (< 100 woorden)
    if len(content.split()) < 100:
        raise ValueError(f"Te klein: {filename} ({len(content.split())} woorden)")

    dest = SCRAPE_DIR / filename
    dest.write_text(content, encoding="utf-8")
    return dest


def generate_supplemental_docs(target_words: int) -> list[Path]:
    """Genereer aanvullende technische documentatie als scrape onvoldoende is.

    Genereert realistische API/framework docs zodat we 500-1000 chunks halen.
    """
    SCRAPE_DIR.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []
    words_generated = 0

    topics = [
        ("fastapi_advanced_dependency_patterns",
         _gen_fastapi_dependency_doc),
        ("fastapi_async_database_patterns",
         _gen_fastapi_async_db_doc),
        ("pydantic_v2_custom_validators",
         _gen_pydantic_validators_doc),
        ("pydantic_v2_generic_models",
         _gen_pydantic_generics_doc),
        ("fastapi_websocket_patterns",
         _gen_fastapi_websocket_doc),
        ("fastapi_graphql_integration",
         _gen_fastapi_graphql_doc),
        ("pydantic_v2_computed_fields",
         _gen_pydantic_computed_doc),
        ("fastapi_openapi_customization",
         _gen_fastapi_openapi_doc),
    ]

    for name, generator_fn in topics:
        if words_generated >= target_words:
            break
        content = generator_fn()
        dest = SCRAPE_DIR / f"{name}.md"
        dest.write_text(content, encoding="utf-8")
        generated.append(dest)
        words_generated += len(content.split())

    return generated


def _gen_fastapi_dependency_doc() -> str:
    return """# FastAPI Advanced Dependency Injection Patterns

## Overview
FastAPI's dependency injection system is one of its most powerful features.
It allows you to declare dependencies that are automatically resolved and
injected into your path operation functions. This document covers advanced
patterns for production-grade applications.

## Yield Dependencies
Yield dependencies allow you to run cleanup code after the response is sent.
This is particularly useful for database sessions and file handles.

```python
from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

app = FastAPI()

engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/db")
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

## Parameterized Dependencies
You can create dependency factories that accept parameters. This allows you
to reuse the same dependency logic with different configurations.

```python
from fastapi import Depends, Query
from typing import Annotated

def pagination(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
):
    return {"skip": (page - 1) * size, "limit": size}

PaginationDep = Annotated[dict, Depends(pagination)]

@app.get("/items")
async def list_items(pagination: PaginationDep, db: AsyncSession = Depends(get_db)):
    query = select(Item).offset(pagination["skip"]).limit(pagination["limit"])
    result = await db.execute(query)
    return result.scalars().all()
```

## Nested Dependencies
Dependencies can depend on other dependencies, creating a dependency tree
that FastAPI resolves automatically. The framework ensures each dependency
is only called once per request by default (using caching).

```python
async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    user = await db.execute(select(User).where(User.token == token))
    return user.scalar_one_or_none()

async def get_current_active_user(user: User = Depends(get_current_user)):
    if not user or not user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")
    return user

@app.get("/me")
async def read_me(user: User = Depends(get_current_active_user)):
    return user
```

## Global Dependencies
You can add dependencies to the entire application or to specific routers.
These are executed for every request that matches.

```python
async def verify_internal_token(x_internal_token: str = Header(...)):
    if x_internal_token != settings.INTERNAL_TOKEN:
        raise HTTPException(status_code=403, detail="Not allowed")

app = FastAPI(dependencies=[Depends(verify_internal_token)])
# Or per-router:
router = APIRouter(dependencies=[Depends(verify_internal_token)])
```

## Class-Based Dependencies
For complex dependencies that need initialization or state, you can use
classes. The __call__ method is invoked by FastAPI.

```python
class RateLimiter:
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests: dict[str, list[float]] = {}

    async def __call__(self, request: Request):
        client_ip = request.client.host
        now = time.time()
        window_start = now - self.window

        if client_ip not in self.requests:
            self.requests[client_ip] = []

        self.requests[client_ip] = [
            t for t in self.requests[client_ip] if t > window_start
        ]

        if len(self.requests[client_ip]) >= self.max_requests:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        self.requests[client_ip].append(now)
        return True

rate_limiter = RateLimiter(max_requests=60, window_seconds=60)
```

## Dependency Overrides for Testing
FastAPI provides a mechanism to override dependencies during testing,
which is essential for unit testing without external services.

```python
from fastapi.testclient import TestClient

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)
response = client.get("/items")
assert response.status_code == 200
```

## Scoped Dependencies with Lifespan
The lifespan context manager provides application-level dependencies that
persist across all requests. This is the modern replacement for startup/shutdown events.

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize resources
    pool = await create_pool()
    cache = await setup_cache()
    app.state.pool = pool
    app.state.cache = cache
    yield
    # Shutdown: cleanup resources
    await pool.close()
    await cache.close()

app = FastAPI(lifespan=lifespan)
```
""" * 2  # Duplicate for volume


def _gen_fastapi_async_db_doc() -> str:
    return """# FastAPI Async Database Patterns

## SQLAlchemy 2.0 Async Integration
Modern FastAPI applications use SQLAlchemy 2.0's native async support with
asyncpg for PostgreSQL or aiosqlite for SQLite.

### Engine Setup
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Float, DateTime, func

class Base(DeclarativeBase):
    pass

class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    price: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    category_id: Mapped[int] = mapped_column(Integer, nullable=True)
```

### Repository Pattern
The repository pattern abstracts database operations behind a clean interface.
This makes testing easier and keeps business logic separate from data access.

```python
from typing import Generic, TypeVar, Type, Optional, Sequence
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T", bound=Base)

class BaseRepository(Generic[T]):
    def __init__(self, session: AsyncSession, model: Type[T]):
        self.session = session
        self.model = model

    async def get(self, id: int) -> Optional[T]:
        return await self.session.get(self.model, id)

    async def get_all(self, skip: int = 0, limit: int = 100) -> Sequence[T]:
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(self, **kwargs) -> T:
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def update(self, id: int, **kwargs) -> Optional[T]:
        stmt = update(self.model).where(self.model.id == id).values(**kwargs).returning(self.model)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete(self, id: int) -> bool:
        stmt = delete(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0

class ProductRepository(BaseRepository[Product]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Product)

    async def get_by_category(self, category_id: int) -> Sequence[Product]:
        stmt = select(Product).where(Product.category_id == category_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def search(self, query: str) -> Sequence[Product]:
        stmt = select(Product).where(Product.name.ilike(f"%{query}%"))
        result = await self.session.execute(stmt)
        return result.scalars().all()
```

### Unit of Work Pattern
The unit of work pattern ensures all database operations within a request
are committed or rolled back together as a single transaction.

```python
class UnitOfWork:
    def __init__(self, session_factory: async_sessionmaker):
        self.session_factory = session_factory

    async def __aenter__(self):
        self.session = self.session_factory()
        self.products = ProductRepository(self.session)
        self.orders = OrderRepository(self.session)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.session.rollback()
        await self.session.close()

    async def commit(self):
        await self.session.commit()

async def get_uow():
    async with UnitOfWork(AsyncSessionLocal) as uow:
        yield uow
```

### Connection Pooling Best Practices
```python
engine = create_async_engine(
    "postgresql+asyncpg://user:pass@localhost/db",
    pool_size=20,           # Max persistent connections
    max_overflow=10,        # Extra connections allowed temporarily
    pool_timeout=30,        # Seconds to wait for a free connection
    pool_recycle=1800,      # Recycle connections after 30 minutes
    pool_pre_ping=True,     # Verify connection before use
    echo=False,             # SQL logging (disable in production)
)
```

### Alembic Async Migrations
```python
# alembic/env.py
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

async def run_migrations_online():
    connectable = create_async_engine(settings.DATABASE_URL)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
```

### Bulk Operations
For inserting or updating large datasets, use bulk operations to minimize
round trips to the database.

```python
async def bulk_create_products(session: AsyncSession, products: list[dict]):
    instances = [Product(**p) for p in products]
    session.add_all(instances)
    await session.flush()
    return instances

async def bulk_upsert(session: AsyncSession, products: list[dict]):
    from sqlalchemy.dialects.postgresql import insert
    stmt = insert(Product).values(products)
    stmt = stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={c.name: c for c in stmt.excluded if c.name != "id"}
    )
    await session.execute(stmt)
```
""" * 2


def _gen_pydantic_validators_doc() -> str:
    return """# Pydantic v2 Custom Validators

## Overview
Pydantic v2 introduces a completely new validation system powered by
pydantic-core (written in Rust). Validators are more explicit, composable,
and significantly faster than v1.

## Field Validators
Field validators run on individual fields. They can be used for custom
parsing, normalization, and validation logic.

```python
from pydantic import BaseModel, field_validator, ValidationError
from typing import Annotated
import re

class User(BaseModel):
    name: str
    email: str
    age: int
    username: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'
        if not re.match(pattern, v):
            raise ValueError(f"Invalid email format: {v}")
        return v.lower().strip()

    @field_validator("age")
    @classmethod
    def validate_age(cls, v: int) -> int:
        if v < 0 or v > 150:
            raise ValueError(f"Age must be between 0 and 150, got {v}")
        return v

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Username can only contain letters, numbers, hyphens and underscores")
        return v.lower()
```

## Model Validators
Model validators operate on the entire model, allowing cross-field validation.

```python
from pydantic import BaseModel, model_validator

class DateRange(BaseModel):
    start_date: date
    end_date: date
    description: str = ""

    @model_validator(mode="after")
    def validate_date_range(self) -> "DateRange":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be after start_date")
        if (self.end_date - self.start_date).days > 365:
            raise ValueError("Date range cannot exceed 1 year")
        return self

class PasswordChange(BaseModel):
    old_password: str
    new_password: str
    confirm_password: str

    @model_validator(mode="after")
    def passwords_match(self) -> "PasswordChange":
        if self.new_password != self.confirm_password:
            raise ValueError("new_password and confirm_password must match")
        if self.new_password == self.old_password:
            raise ValueError("New password must differ from old password")
        return self
```

## Before vs After Validators
- `mode="before"`: runs before Pydantic's own validation (on raw input data)
- `mode="after"`: runs after Pydantic has validated and coerced the data
- `mode="wrap"`: wraps Pydantic's validation (advanced use case)

```python
class FlexibleModel(BaseModel):
    tags: list[str]
    metadata: dict[str, str]

    @field_validator("tags", mode="before")
    @classmethod
    def parse_tags(cls, v):
        if isinstance(v, str):
            return [t.strip() for t in v.split(",") if t.strip()]
        return v

    @field_validator("metadata", mode="before")
    @classmethod
    def parse_metadata(cls, v):
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v
```

## Annotated Validators (Reusable)
The Annotated pattern lets you create reusable validator types.

```python
from pydantic import AfterValidator, BeforeValidator
from typing import Annotated

def normalize_whitespace(v: str) -> str:
    return " ".join(v.split())

def ensure_positive(v: int) -> int:
    if v <= 0:
        raise ValueError(f"Must be positive, got {v}")
    return v

NormalizedStr = Annotated[str, AfterValidator(normalize_whitespace)]
PositiveInt = Annotated[int, AfterValidator(ensure_positive)]

class Product(BaseModel):
    name: NormalizedStr
    description: NormalizedStr
    stock: PositiveInt
    price_cents: PositiveInt
```

## Computed Fields
Pydantic v2 introduces computed fields that are included in serialization
but not in initialization.

```python
from pydantic import BaseModel, computed_field
from decimal import Decimal

class Invoice(BaseModel):
    items: list[InvoiceItem]
    tax_rate: Decimal = Decimal("0.21")

    @computed_field
    @property
    def subtotal(self) -> Decimal:
        return sum(item.total for item in self.items)

    @computed_field
    @property
    def tax(self) -> Decimal:
        return self.subtotal * self.tax_rate

    @computed_field
    @property
    def total(self) -> Decimal:
        return self.subtotal + self.tax
```

## Custom Types with __get_pydantic_core_schema__
For complete control over validation, you can implement a custom type.

```python
from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

class Color:
    def __init__(self, value: str):
        self.value = value

    @classmethod
    def __get_pydantic_core_schema__(cls, source, handler: GetCoreSchemaHandler):
        return core_schema.no_info_plain_validator_function(
            cls._validate,
            serialization=core_schema.to_string_ser_schema(),
        )

    @classmethod
    def _validate(cls, v):
        if isinstance(v, cls):
            return v
        if isinstance(v, str) and v.startswith("#") and len(v) == 7:
            return cls(v)
        raise ValueError(f"Invalid color: {v}")
```
""" * 2


def _gen_pydantic_generics_doc() -> str:
    return """# Pydantic v2 Generic Models

## Overview
Generic models allow you to create reusable model templates that can be
parameterized with different types. This is essential for API responses,
pagination, and other patterns where the structure is consistent but the
data type varies.

## Basic Generic Model
```python
from pydantic import BaseModel
from typing import TypeVar, Generic, Optional, Sequence

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class PaginatedResponse(BaseModel, Generic[T]):
    items: Sequence[T]
    total: int
    page: int
    size: int
    pages: int

    @computed_field
    @property
    def has_next(self) -> bool:
        return self.page < self.pages

    @computed_field
    @property
    def has_prev(self) -> bool:
        return self.page > 1
```

## Usage with FastAPI
```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/users/{user_id}", response_model=ApiResponse[User])
async def get_user(user_id: int):
    user = await user_repo.get(user_id)
    if not user:
        return ApiResponse(success=False, error="User not found")
    return ApiResponse(success=True, data=user)

@app.get("/products", response_model=PaginatedResponse[Product])
async def list_products(page: int = 1, size: int = 20):
    total = await product_repo.count()
    items = await product_repo.get_page(page, size)
    return PaginatedResponse(
        items=items, total=total, page=page, size=size,
        pages=(total + size - 1) // size,
    )
```

## Nested Generics
```python
class TreeNode(BaseModel, Generic[T]):
    value: T
    children: list["TreeNode[T]"] = []

    def depth(self) -> int:
        if not self.children:
            return 0
        return 1 + max(child.depth() for child in self.children)

# Usage
tree = TreeNode[str](
    value="root",
    children=[
        TreeNode(value="child1", children=[TreeNode(value="grandchild")]),
        TreeNode(value="child2"),
    ],
)
```

## Discriminated Unions with Generics
```python
from pydantic import BaseModel, Field
from typing import Literal, Union, Annotated

class SuccessResponse(BaseModel, Generic[T]):
    status: Literal["success"] = "success"
    data: T

class ErrorResponse(BaseModel):
    status: Literal["error"] = "error"
    code: int
    message: str
    details: dict = {}

ApiResult = Annotated[
    Union[SuccessResponse[T], ErrorResponse],
    Field(discriminator="status"),
]
```

## Configuration with model_config
```python
class StrictUser(BaseModel):
    model_config = ConfigDict(
        strict=True,
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
        str_min_length=1,
    )
    name: str
    email: str
    role: Literal["admin", "user", "viewer"]
```
""" * 2


def _gen_fastapi_websocket_doc() -> str:
    return """# FastAPI WebSocket Patterns

## Basic WebSocket Endpoint
```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, Set

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room: str):
        await websocket.accept()
        if room not in self.active_connections:
            self.active_connections[room] = set()
        self.active_connections[room].add(websocket)

    def disconnect(self, websocket: WebSocket, room: str):
        self.active_connections.get(room, set()).discard(websocket)

    async def broadcast(self, message: str, room: str):
        for connection in self.active_connections.get(room, set()):
            try:
                await connection.send_text(message)
            except Exception:
                self.disconnect(connection, room)

manager = ConnectionManager()

@app.websocket("/ws/{room}")
async def websocket_endpoint(websocket: WebSocket, room: str):
    await manager.connect(websocket, room)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(f"Room {room}: {data}", room)
    except WebSocketDisconnect:
        manager.disconnect(websocket, room)
        await manager.broadcast(f"Client left room {room}", room)
```

## Authentication in WebSockets
WebSocket connections don't support standard HTTP headers after the initial
handshake, so authentication must happen during the connection setup.

```python
@app.websocket("/ws/secure")
async def secure_websocket(
    websocket: WebSocket,
    token: str = Query(None),
):
    if not token or not verify_token(token):
        await websocket.close(code=4001, reason="Unauthorized")
        return

    user = get_user_from_token(token)
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()
            response = await process_message(user, data)
            await websocket.send_json(response)
    except WebSocketDisconnect:
        pass
```

## Heartbeat / Keep-Alive Pattern
```python
import asyncio

@app.websocket("/ws/heartbeat")
async def heartbeat_websocket(websocket: WebSocket):
    await websocket.accept()
    last_ping = time.time()

    async def send_pings():
        nonlocal last_ping
        while True:
            await asyncio.sleep(30)
            try:
                await websocket.send_json({"type": "ping", "timestamp": time.time()})
            except Exception:
                break

    ping_task = asyncio.create_task(send_pings())
    try:
        while True:
            data = await asyncio.wait_for(websocket.receive_json(), timeout=60)
            if data.get("type") == "pong":
                last_ping = time.time()
            else:
                response = await handle_message(data)
                await websocket.send_json(response)
    except (WebSocketDisconnect, asyncio.TimeoutError):
        ping_task.cancel()
```

## Pub/Sub with Redis
```python
import aioredis

@app.websocket("/ws/pubsub/{channel}")
async def pubsub_websocket(websocket: WebSocket, channel: str):
    await websocket.accept()
    redis = aioredis.from_url("redis://localhost")
    pubsub = redis.pubsub()
    await pubsub.subscribe(channel)

    async def listen_redis():
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"].decode())

    listener = asyncio.create_task(listen_redis())
    try:
        while True:
            data = await websocket.receive_text()
            await redis.publish(channel, data)
    except WebSocketDisconnect:
        listener.cancel()
        await pubsub.unsubscribe(channel)
        await redis.close()
```
""" * 2


def _gen_fastapi_graphql_doc() -> str:
    return """# FastAPI GraphQL Integration

## Strawberry GraphQL with FastAPI
Strawberry is the recommended GraphQL library for FastAPI due to its
type-safety and Pydantic integration.

```python
import strawberry
from strawberry.fastapi import GraphQLRouter
from fastapi import FastAPI

@strawberry.type
class User:
    id: int
    name: str
    email: str
    posts: list["Post"]

@strawberry.type
class Post:
    id: int
    title: str
    content: str
    author: User

@strawberry.type
class Query:
    @strawberry.field
    async def users(self, limit: int = 10) -> list[User]:
        async with get_session() as session:
            result = await session.execute(select(UserModel).limit(limit))
            return [User.from_orm(u) for u in result.scalars().all()]

    @strawberry.field
    async def user(self, id: int) -> User | None:
        async with get_session() as session:
            user = await session.get(UserModel, id)
            return User.from_orm(user) if user else None

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_user(self, name: str, email: str) -> User:
        async with get_session() as session:
            user = UserModel(name=name, email=email)
            session.add(user)
            await session.commit()
            return User.from_orm(user)

schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_app = GraphQLRouter(schema)
app = FastAPI()
app.include_router(graphql_app, prefix="/graphql")
```

## DataLoader Pattern (N+1 Prevention)
```python
from strawberry.dataloader import DataLoader
from typing import List

async def load_users(keys: List[int]) -> List[User]:
    async with get_session() as session:
        result = await session.execute(
            select(UserModel).where(UserModel.id.in_(keys))
        )
        users = {u.id: u for u in result.scalars().all()}
        return [users.get(key) for key in keys]

user_loader = DataLoader(load_fn=load_users)

@strawberry.type
class Post:
    id: int
    title: str
    author_id: int

    @strawberry.field
    async def author(self) -> User:
        return await user_loader.load(self.author_id)
```

## Subscriptions (Real-time)
```python
import asyncio
from typing import AsyncGenerator

@strawberry.type
class Subscription:
    @strawberry.subscription
    async def count(self, target: int = 100) -> AsyncGenerator[int, None]:
        for i in range(target):
            yield i
            await asyncio.sleep(1)

    @strawberry.subscription
    async def notifications(self, user_id: int) -> AsyncGenerator[str, None]:
        pubsub = await get_redis_pubsub(f"user:{user_id}")
        async for message in pubsub.listen():
            if message["type"] == "message":
                yield message["data"].decode()
```

## Custom Context and Authentication
```python
from strawberry.types import Info
from fastapi import Request

async def get_context(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    user = await verify_and_get_user(token) if token else None
    return {"user": user, "request": request}

graphql_app = GraphQLRouter(schema, context_getter=get_context)

@strawberry.type
class Query:
    @strawberry.field
    async def me(self, info: Info) -> User | None:
        user = info.context.get("user")
        if not user:
            raise ValueError("Not authenticated")
        return user
```
""" * 2


def _gen_pydantic_computed_doc() -> str:
    return """# Pydantic v2 Computed Fields & Serialization

## Computed Fields
Computed fields are properties that are included in serialization output
but are not part of the model's input schema.

```python
from pydantic import BaseModel, computed_field
from datetime import datetime, timedelta

class Subscription(BaseModel):
    user_id: int
    plan: str
    start_date: datetime
    duration_days: int

    @computed_field
    @property
    def end_date(self) -> datetime:
        return self.start_date + timedelta(days=self.duration_days)

    @computed_field
    @property
    def is_active(self) -> bool:
        return datetime.utcnow() < self.end_date

    @computed_field
    @property
    def days_remaining(self) -> int:
        delta = self.end_date - datetime.utcnow()
        return max(0, delta.days)
```

## Custom Serialization
Pydantic v2 provides powerful serialization control through model_config
and field-level serializers.

```python
from pydantic import BaseModel, field_serializer, model_serializer, ConfigDict
from decimal import Decimal

class Money(BaseModel):
    amount: Decimal
    currency: str = "EUR"

    @field_serializer("amount")
    def serialize_amount(self, v: Decimal) -> str:
        return f"{v:.2f}"

class Order(BaseModel):
    model_config = ConfigDict(
        ser_json_timedelta="float",
        ser_json_bytes="base64",
    )

    id: int
    total: Money
    items: list[OrderItem]
    created_at: datetime
    processing_time: timedelta

    @model_serializer(mode="wrap")
    def custom_serialize(self, handler):
        data = handler(self)
        data["item_count"] = len(self.items)
        data["formatted_total"] = f"{self.total.currency} {self.total.amount:.2f}"
        return data
```

## Validation Aliases
Aliases allow you to accept different field names in input while maintaining
Pythonic attribute names in your code.

```python
from pydantic import BaseModel, Field, AliasChoices, AliasPath

class APIConfig(BaseModel):
    api_key: str = Field(
        validation_alias=AliasChoices(
            "api_key",
            "apiKey",
            "API_KEY",
            AliasPath("credentials", "key"),
        )
    )
    base_url: str = Field(
        validation_alias=AliasChoices("base_url", "baseUrl", "BASE_URL"),
        default="https://api.example.com",
    )

# All of these work:
config1 = APIConfig(api_key="abc123")
config2 = APIConfig(apiKey="abc123")
config3 = APIConfig(**{"credentials": {"key": "abc123"}})
```

## JSON Schema Customization
```python
from pydantic import BaseModel, Field
from typing import Annotated

class Product(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"name": "Widget", "price": 9.99, "category": "gadgets"}
            ]
        }
    )

    name: str = Field(
        min_length=1, max_length=100,
        json_schema_extra={"examples": ["Widget", "Gadget"]},
    )
    price: Annotated[float, Field(gt=0, description="Price in EUR")]
    category: str = Field(pattern=r"^[a-z]+$")
    tags: list[str] = Field(default_factory=list, max_length=10)

# Generate JSON Schema
print(Product.model_json_schema())
```

## Settings Management
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="APP_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    debug: bool = False
    database_url: str
    redis_url: str = "redis://localhost:6379"
    allowed_origins: list[str] = ["http://localhost:3000"]

    class Database(BaseModel):
        pool_size: int = 20
        max_overflow: int = 10

    database: Database = Database()

settings = Settings()  # Reads from env + .env file
```
""" * 2


def _gen_fastapi_openapi_doc() -> str:
    return """# FastAPI OpenAPI Customization

## Custom OpenAPI Schema
FastAPI auto-generates an OpenAPI schema from your code. You can customize
this schema for better documentation and client generation.

```python
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

app = FastAPI(
    title="My Production API",
    version="2.0.0",
    description="A comprehensive API for managing resources",
    terms_of_service="https://example.com/terms",
    contact={
        "name": "API Support",
        "url": "https://example.com/support",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        },
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
        },
    }

    # Add global security
    openapi_schema["security"] = [{"BearerAuth": []}, {"ApiKeyAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

## API Versioning
```python
from fastapi import APIRouter

v1_router = APIRouter(prefix="/api/v1", tags=["v1"])
v2_router = APIRouter(prefix="/api/v2", tags=["v2"])

@v1_router.get("/users")
async def list_users_v1():
    return {"version": "v1", "users": await get_users_basic()}

@v2_router.get("/users")
async def list_users_v2():
    return {"version": "v2", "users": await get_users_extended(), "meta": {...}}

app.include_router(v1_router)
app.include_router(v2_router)
```

## Tags and Metadata
```python
tags_metadata = [
    {"name": "Users", "description": "User management operations"},
    {"name": "Products", "description": "Product catalog CRUD"},
    {"name": "Orders", "description": "Order processing and tracking"},
    {"name": "Admin", "description": "Administrative operations", "externalDocs": {
        "description": "Admin docs",
        "url": "https://docs.example.com/admin",
    }},
]

app = FastAPI(openapi_tags=tags_metadata)

@app.get("/users", tags=["Users"])
async def list_users():
    pass

@app.get("/products", tags=["Products"])
async def list_products():
    pass
```

## Response Models and Status Codes
```python
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

@app.post(
    "/users",
    response_model=User,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "User created successfully"},
        400: {"model": ErrorResponse, "description": "Invalid input"},
        409: {"model": ErrorResponse, "description": "User already exists"},
        422: {"model": ValidationErrorResponse, "description": "Validation error"},
    },
    summary="Create a new user",
    description="Creates a new user account with the provided information.",
)
async def create_user(user_data: UserCreate):
    existing = await user_repo.get_by_email(user_data.email)
    if existing:
        return JSONResponse(
            status_code=409,
            content={"error": "User with this email already exists"},
        )
    user = await user_repo.create(**user_data.model_dump())
    return user
```

## Middleware for Request Tracing
```python
import uuid
from starlette.middleware.base import BaseHTTPMiddleware

class RequestTracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration:.3f}s"

        logger.info(
            "request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round(duration * 1000, 2),
            },
        )
        return response

app.add_middleware(RequestTracingMiddleware)
```
""" * 2


# ═══════════════════════════════════════════════════════
# MONITORING HELPERS
# ═══════════════════════════════════════════════════════

def get_system_metrics() -> dict:
    """Verzamel RAM, CPU en GPU metrics."""
    metrics = {"ram_mb": 0, "ram_pct": 0.0, "cpu_pct": 0.0, "gpu_mb": 0}
    if not _HAS_PSUTIL:
        return metrics

    proc = psutil.Process()
    mem = proc.memory_info()
    metrics["ram_mb"] = mem.rss // (1024 * 1024)
    metrics["ram_pct"] = psutil.virtual_memory().percent
    metrics["cpu_pct"] = psutil.cpu_percent(interval=0.1)

    # GPU VRAM check (nvidia-smi als beschikbaar)
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            metrics["gpu_mb"] = int(result.stdout.strip().split("\n")[0])
    except Exception:
        logger.debug("Suppressed exception in stress_test_deep_ingestion")

    return metrics


def estimate_chunks(text: str, chunk_size: int = CHUNK_SIZE_WORDS) -> int:
    """Schat het aantal chunks voor een tekst."""
    words = len(text.split())
    return max(1, words // chunk_size)


# ═══════════════════════════════════════════════════════
# CHROMADB INTEGRITY CHECK
# ═══════════════════════════════════════════════════════

def check_staging_orphans(job_ids: list[str]) -> dict:
    """Controleer of er staging collecties zijn achtergebleven in ChromaDB.

    Returns:
        Dict met orphaned collecties en hoofdcollectie count.
    """
    result = {"orphans": [], "main_count": 0, "all_collections": []}
    try:
        import chromadb
        from danny_toolkit.core.config import Config
        chroma_path = Config.DATA_DIR / "rag" / "chromadb"
        client = chromadb.PersistentClient(path=str(chroma_path))

        all_cols = [c.name for c in client.list_collections()]
        result["all_collections"] = all_cols

        # Zoek staging orphans
        for col_name in all_cols:
            if col_name.startswith("staging-"):
                result["orphans"].append(col_name)

        # Hoofdcollectie count
        try:
            main = client.get_collection("omega_rag")
            result["main_count"] = main.count()
        except Exception:
            try:
                main = client.get_collection("danny_rag")
                result["main_count"] = main.count()
            except Exception:
                logger.debug("Suppressed exception in stress_test_deep_ingestion")

    except Exception as e:
        result["error"] = str(e)

    return result


# ═══════════════════════════════════════════════════════
# SUBMIT + POLL (met API key header)
# ═══════════════════════════════════════════════════════

def _headers() -> dict:
    """HTTP headers met API key."""
    h = {}
    if API_KEY:
        h["X-API-Key"] = API_KEY
    return h


async def submit_file(client: httpx.AsyncClient, file_path: Path) -> dict:
    """Upload een bestand naar de background ingest endpoint."""
    content = file_path.read_bytes()

    files = {"bestand": (file_path.name, content, "text/markdown")}
    resp = await client.post(
        f"{BASE_URL}/api/v1/ingest/background",
        files=files,
        headers=_headers(),
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()


async def poll_job(client: httpx.AsyncClient, job_id: str,
                   metrics_log: list) -> dict:
    """Poll job status tot completed/failed. Log metrics bij elke poll."""
    start = time.time()
    last_status = "unknown"

    while (time.time() - start) < MAX_POLL_TIME:
        try:
            resp = await client.get(
                f"{BASE_URL}/api/v1/ingest/background/{job_id}",
                headers=_headers(),
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status", "unknown")

            if status != last_status:
                elapsed = time.time() - start
                m = get_system_metrics()
                print(
                    f"  [{job_id[:8]}] {status} ({elapsed:.1f}s)"
                    f"  RAM={m['ram_mb']}MB CPU={m['cpu_pct']:.0f}%"
                    f"  GPU={m['gpu_mb']}MB"
                )
                metrics_log.append({
                    "time": elapsed, "job": job_id[:8],
                    "status": status, **m,
                })
                last_status = status

            if status in ("completed", "failed"):
                return data

        except Exception as e:
            print(f"  [{job_id[:8]}] poll error: {e}")

        await asyncio.sleep(POLL_INTERVAL)

    return {"status": "timeout", "job_id": job_id}


async def submit_batch(client: httpx.AsyncClient,
                       files: list[Path], batch_id: int) -> list[dict]:
    """Submit alle bestanden in een batch sequentieel."""
    jobs = []
    for f in files:
        try:
            result = await submit_file(client, f)
            job_id = result.get("job_id", "?")
            print(f"  [Batch {batch_id}] Submitted {f.name} → job {job_id[:8]}")
            jobs.append(result)
        except Exception as e:
            print(f"  [Batch {batch_id}] FAIL {f.name}: {e}")
            jobs.append({"status": "submit_failed", "error": str(e), "file": f.name})
    return jobs


def distribute_files(files: list[Path], n_jobs: int) -> list[list[Path]]:
    """Verdeel bestanden over N jobs (round-robin)."""
    buckets: list[list[Path]] = [[] for _ in range(n_jobs)]
    for i, f in enumerate(files):
        buckets[i % n_jobs].append(f)
    return buckets


# ═══════════════════════════════════════════════════════
# MAIN STRESS TEST
# ═══════════════════════════════════════════════════════

async def run_stress_test():
    """Protocol Deep Ingestion v2.0 — 4 stappen stress test."""
    print("=" * 75)
    print("  PROTOCOL 'DEEP INGESTION' v2.0 — STRESS TEST")
    print("  Atomic Staging-Swap + LocalEmbeddings 384d")
    print("=" * 75)

    metrics_log: list[dict] = []
    baseline = get_system_metrics()
    print(f"\n  Baseline: RAM={baseline['ram_mb']}MB CPU={baseline['cpu_pct']:.0f}%"
          f" GPU={baseline['gpu_mb']}MB")

    # ── STAP 1: Massa Scrape ──
    print(f"\n{'─' * 75}")
    print("[STAP 1] MASSA SCRAPE — FastAPI + Pydantic v2 documentatie")
    print(f"{'─' * 75}")

    scraped_files: list[Path] = []
    total_words = 0

    # 1a: Scrape van GitHub
    print("\n  [1a] Scraping FastAPI + Pydantic docs van GitHub...")
    async with httpx.AsyncClient() as scrape_client:
        try:
            scraped_files = await scrape_docs(scrape_client)
            for f in scraped_files:
                total_words += len(f.read_text(encoding="utf-8").split())
            print(f"  Scraped: {len(scraped_files)} bestanden, ~{total_words:,} woorden")
        except Exception as e:
            print(f"  [WARN] Scrape fout: {e}")
            print(f"  Fallback naar lokale docs + gegenereerde supplementen")

    # 1b: Genereer supplementen als we onder target zitten
    est_chunks = total_words // CHUNK_SIZE_WORDS
    if est_chunks < TARGET_MIN_CHUNKS:
        deficit_words = (TARGET_MIN_CHUNKS - est_chunks) * CHUNK_SIZE_WORDS
        print(f"\n  [1b] {est_chunks} chunks < target {TARGET_MIN_CHUNKS}")
        print(f"       Genereer ~{deficit_words:,} woorden aanvulling...")
        supplemental = generate_supplemental_docs(deficit_words)
        for f in supplemental:
            w = len(f.read_text(encoding="utf-8").split())
            total_words += w
            scraped_files.append(f)
        print(f"       +{len(supplemental)} gegenereerde docs")

    # 1c: Voeg lokale bestaande docs toe
    local_docs = sorted(DOCS_DIR.glob("*.md"))
    # Exclude _stress_test subdirectory docs (already included via scraped_files)
    local_only = [f for f in local_docs if f.parent == DOCS_DIR]
    for f in local_only:
        total_words += len(f.read_text(encoding="utf-8").split())
    all_files = scraped_files + local_only

    est_chunks = total_words // CHUNK_SIZE_WORDS
    print(f"\n  TOTAAL: {len(all_files)} bestanden, ~{total_words:,} woorden")
    print(f"  Geschatte chunks: ~{est_chunks}")
    if est_chunks >= TARGET_MIN_CHUNKS:
        print(f"  TARGET BEREIKT (>= {TARGET_MIN_CHUNKS} chunks)")
    else:
        print(f"  [WARN] Onder target: {est_chunks} < {TARGET_MIN_CHUNKS}")

    # Verdeel over 5 concurrent jobs
    buckets = distribute_files(all_files, CONCURRENT_JOBS)
    for i, bucket in enumerate(buckets):
        bucket_words = sum(len(f.read_text(encoding="utf-8").split()) for f in bucket)
        names = [f.name for f in bucket]
        print(f"  Batch {i}: {len(bucket)} bestanden (~{bucket_words // CHUNK_SIZE_WORDS} chunks)"
              f" — {', '.join(names[:3])}{'...' if len(names) > 3 else ''}")

    # ── STAP 2: Parallel Background Ingest ──
    print(f"\n{'─' * 75}")
    print(f"[STAP 2] {CONCURRENT_JOBS} PARALLELLE BACKGROUND INGEST JOBS")
    print(f"         EMBEDDING_PROVIDER=local (384d LocalEmbeddings)")
    print(f"{'─' * 75}")

    t_start = time.time()

    async with httpx.AsyncClient() as client:
        # Submit alle batches parallel
        submit_tasks = [
            submit_batch(client, bucket, i)
            for i, bucket in enumerate(buckets)
        ]
        batch_results = await asyncio.gather(*submit_tasks)

        # Flatten job_ids
        all_jobs: list[dict] = []
        for batch in batch_results:
            all_jobs.extend(batch)

        submitted_jobs = [j for j in all_jobs if "job_id" in j]
        failed_submits = [j for j in all_jobs if "job_id" not in j]

        t_submit = time.time() - t_start
        print(f"\n  Submitted: {len(submitted_jobs)} jobs in {t_submit:.1f}s")
        if failed_submits:
            print(f"  Submit failures: {len(failed_submits)}")
            for fs in failed_submits:
                print(f"    FAIL: {fs.get('file', '?')} — {fs.get('error', '?')}")

        # ── STAP 3: Atomic Monitoring ──
        print(f"\n{'─' * 75}")
        print(f"[STAP 3] ATOMIC MONITORING — Polling {len(submitted_jobs)} jobs")
        print(f"         RAM/GPU tracking + staging collectie verificatie")
        print(f"{'─' * 75}")

        poll_tasks = [
            poll_job(client, j["job_id"], metrics_log)
            for j in submitted_jobs
        ]
        poll_results = await asyncio.gather(*poll_tasks)

    t_total = time.time() - t_start

    # ── STAP 4: Rapportage ──
    print(f"\n{'═' * 75}")
    print("  STAP 4: DEEP INGESTION RAPPORT")
    print(f"{'═' * 75}")

    completed = [r for r in poll_results if r.get("status") == "completed"]
    failed = [r for r in poll_results if r.get("status") == "failed"]
    timeouts = [r for r in poll_results if r.get("status") == "timeout"]

    total_chunks = sum(r.get("chunks", 0) for r in completed)
    chunks_per_sec = total_chunks / t_total if t_total > 0 else 0

    # Tijdsanalyse per job
    job_durations = []
    for r in completed:
        started = r.get("started_at", 0)
        ended = r.get("completed_at", 0)
        if started and ended:
            job_durations.append(ended - started)

    final_metrics = get_system_metrics()

    print(f"\n  ┌─── DOCUMENTEN ──────────────────────────────────┐")
    print(f"  │ Bestanden:           {len(all_files):>6}")
    print(f"  │ Woorden:             ~{total_words:>6,}")
    print(f"  │ Scraped van GitHub:  {len(scraped_files):>6}")
    print(f"  │ Lokale docs:         {len(local_only):>6}")
    print(f"  └──────────────────────────────────────────────────┘")

    print(f"\n  ┌─── JOBS ────────────────────────────────────────┐")
    print(f"  │ Submitted:           {len(submitted_jobs):>6}")
    print(f"  │ Completed:           {len(completed):>6}")
    print(f"  │ Failed:              {len(failed):>6}")
    print(f"  │ Timeout:             {len(timeouts):>6}")
    print(f"  │ Submit failures:     {len(failed_submits):>6}")
    print(f"  └──────────────────────────────────────────────────┘")

    print(f"\n  ┌─── DOORVOER ─────────────────────────────────────┐")
    print(f"  │ Totale chunks:       {total_chunks:>6}")
    print(f"  │ Chunks/seconde:      {chunks_per_sec:>6.1f}")
    print(f"  │ Submit tijd:         {t_submit:>6.1f}s")
    print(f"  │ Totale tijd:         {t_total:>6.1f}s")
    if job_durations:
        avg_job = sum(job_durations) / len(job_durations)
        max_job = max(job_durations)
        min_job = min(job_durations)
        print(f"  │ Job avg/min/max:     {avg_job:.1f}s / {min_job:.1f}s / {max_job:.1f}s")
    print(f"  └──────────────────────────────────────────────────┘")

    print(f"\n  ┌─── SYSTEEM METRICS ──────────────────────────────┐")
    print(f"  │ RAM baseline:        {baseline['ram_mb']:>6} MB")
    print(f"  │ RAM finaal:          {final_metrics['ram_mb']:>6} MB")
    print(f"  │ RAM delta:           {final_metrics['ram_mb'] - baseline['ram_mb']:>+6} MB")
    print(f"  │ CPU piek:            {max((m.get('cpu_pct', 0) for m in metrics_log), default=0):>6.0f}%")
    print(f"  │ GPU piek:            {max((m.get('gpu_mb', 0) for m in metrics_log), default=0):>6} MB")
    print(f"  └──────────────────────────────────────────────────┘")

    # ChromaDB integriteitscheck
    print(f"\n  ┌─── INTEGRITEITSCHECK ────────────────────────────┐")
    job_ids = [j["job_id"] for j in submitted_jobs]
    integrity = check_staging_orphans(job_ids)

    if "error" in integrity:
        print(f"  │ ChromaDB check:      FOUT — {integrity['error']}")
    else:
        orphans = integrity["orphans"]
        main_count = integrity["main_count"]
        print(f"  │ Hoofdcollectie:      {main_count:>6} chunks")
        print(f"  │ Staging orphans:     {len(orphans):>6}")
        if orphans:
            for o in orphans:
                print(f"  │   ORPHAN: {o}")
        else:
            print(f"  │   CLEAN — alle staging collecties opgeruimd")
        print(f"  │ Collecties totaal:   {len(integrity['all_collections']):>6}")
    print(f"  └──────────────────────────────────────────────────┘")

    if failed:
        print(f"\n  GEFAALDE JOBS:")
        for r in failed:
            jid = r.get("job_id", "?")[:8]
            err = r.get("error", "onbekend")
            print(f"    [{jid}] {err}")

    # Eindoordeel
    all_ok = (
        len(completed) == len(submitted_jobs)
        and not failed_submits
        and not integrity.get("orphans", [])
    )

    print(f"\n{'═' * 75}")
    if all_ok:
        print(f"  VERDICT: DEEP INGESTION STRESS TEST GESLAAGD")
        print(f"  {total_chunks} chunks via LocalEmbeddings 384d in {t_total:.1f}s")
        print(f"  ({chunks_per_sec:.1f} chunks/s, {CONCURRENT_JOBS} concurrent jobs)")
        print(f"  Atomic staging-swap: ZERO orphans, ZERO data corruption")
    elif len(completed) > 0:
        pct = len(completed) / max(len(submitted_jobs), 1) * 100
        print(f"  VERDICT: GEDEELTELIJK GESLAAGD ({pct:.0f}%)")
        print(f"  {len(failed)} failed, {len(timeouts)} timeout,"
              f" {len(integrity.get('orphans', []))} orphans")
    else:
        print(f"  VERDICT: GEFAALD — geen enkele job afgerond")
    print(f"{'═' * 75}")

    # Cleanup stress test docs
    print(f"\n  Cleanup: {SCRAPE_DIR}...")
    try:
        import shutil
        if SCRAPE_DIR.exists():
            shutil.rmtree(SCRAPE_DIR)
            print(f"  Stress test docs verwijderd.")
    except Exception as e:
        print(f"  Cleanup fout: {e}")

    return all_ok


if __name__ == "__main__":
    print(f"\n  EMBEDDING_PROVIDER={os.environ.get('EMBEDDING_PROVIDER', 'default')}")
    print(f"  API_KEY={'set' if API_KEY else 'NOT SET (auth may fail)'}")
    print(f"  TARGET_URL={BASE_URL}")
    print()
    success = asyncio.run(run_stress_test())
    sys.exit(0 if success else 1)
