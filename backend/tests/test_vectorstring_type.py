import json

from sqlalchemy import Column, MetaData, Table
from sqlalchemy.dialects import sqlite
from sqlalchemy.schema import CreateTable

from app.db.types import VectorString


def test_vectorstring_binds_list_as_json_string():
    vt = VectorString(3)
    raw = vt.process_bind_param([1, 2, 3], dialect=None)
    assert isinstance(raw, str)
    assert json.loads(raw) == [1.0, 2.0, 3.0]


def test_vectorstring_compiles_to_text_on_sqlite():
    t = Table("t", MetaData(), Column("v", VectorString(3)))
    ddl = str(CreateTable(t).compile(dialect=sqlite.dialect()))
    # SQLite fallback is plain TEXT for portability.
    assert "TEXT" in ddl.upper()
