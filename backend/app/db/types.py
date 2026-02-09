from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.compiler import compiles
from sqlalchemy.types import TEXT, TypeDecorator, UserDefinedType


class _Vector(UserDefinedType):
    cache_ok = True

    def __init__(self, dim: int):
        self.dim = dim

    def get_col_spec(self, **_kw: Any) -> str:
        return f"vector({self.dim})"


@compiles(_Vector, "postgresql")
def _compile_vector_pg(element: _Vector, _compiler: Any, **_kw: Any) -> str:
    return element.get_col_spec()


@compiles(_Vector)
def _compile_vector_fallback(_element: _Vector, _compiler: Any, **_kw: Any) -> str:
    # SQLite/dev environments don't support the pgvector type. We keep the column
    # present for portability, but compile it to TEXT.
    return "TEXT"


class VectorString(TypeDecorator):
    """Vector type that binds Python lists as pgvector literals.

    On Postgres this compiles to `vector(dim)`. On other dialects it compiles to TEXT.
    """

    cache_ok = True
    impl = TEXT

    def __init__(self, dim: int):
        self.dim = dim
        super().__init__()

    def load_dialect_impl(self, dialect):  # type: ignore[override]
        if dialect.name == "postgresql":
            return dialect.type_descriptor(_Vector(self.dim))
        return dialect.type_descriptor(TEXT())

    def process_bind_param(self, value: object, dialect) -> str | None:  # type: ignore[override]
        if value is None:
            return None

        if isinstance(value, str):
            return value

        if isinstance(value, (list, tuple)):
            # Use JSON list literal; pgvector accepts `[1,2,3]` input.
            return json.dumps([float(x) for x in value])

        # Last resort: coerce anything else to a string.
        return str(value)
