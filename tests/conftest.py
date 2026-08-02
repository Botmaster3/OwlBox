import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from owlbox.config import Config
from owlbox.db import init_db


@pytest.fixture
def config(tmp_path):
    cfg = Config()
    cfg.simulate = True
    cfg.paths.database = str(tmp_path / "owlbox.db")
    cfg.paths.media_dir = str(tmp_path / "media")
    init_db(cfg.database_path)
    cfg.media_dir.mkdir(parents=True, exist_ok=True)
    return cfg
