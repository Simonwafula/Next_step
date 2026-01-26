import os
import sys
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(autouse=True, scope="session")
def _default_skill_extractor_mode():
    os.environ.setdefault("SKILL_EXTRACTOR_MODE", "skillner")
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_THREADING_LAYER", "GNU")

    # Prevent torch import aborts in spaCy/thinc during tests.
    stub_dir = Path(tempfile.mkdtemp(prefix="pytest_torch_stub_"))
    torch_stub = stub_dir / "torch.py"
    torch_stub.write_text("raise ImportError('torch disabled in tests')\n")
    sys.path.insert(0, str(stub_dir))
    sys.modules.pop("torch", None)


@pytest.fixture()
def db_path():
    default_path = Path(__file__).resolve().parent / "jobs.sqlite3"
    return os.getenv("JOBS_DB_PATH", str(default_path))
