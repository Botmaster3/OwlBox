from __future__ import annotations

import argparse
import logging
import signal
import sys

from .config import load_config
from .db import init_db
from .engine import Engine
from .web import create_app

logger = logging.getLogger("owlbox.main")


def main() -> None:
    parser = argparse.ArgumentParser(description="OwlBox core service")
    parser.add_argument("--config", help="Path to config.yaml", default=None)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    config = load_config(args.config)
    init_db(config.database_path)
    config.media_dir.mkdir(parents=True, exist_ok=True)

    engine = Engine(config)
    engine.start()

    def handle_signal(signum, _frame):
        logger.info("received signal %s, shutting down", signum)
        engine.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    app = create_app(engine, config)
    try:
        app.run(host=config.web.host, port=config.web.port, threaded=True, use_reloader=False)
    finally:
        engine.stop()


if __name__ == "__main__":
    main()
