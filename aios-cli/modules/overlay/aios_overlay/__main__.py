"""Точка входа: python -m aios_overlay [--settings DIR] [--host H] [--port P]

Запускает оверлей-демон: глобальные хоткеи + compact overlay в стиле
Perplexity Computer. Подключается к ядру AIOS по WebSocket.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _parse_args() -> tuple[Path | None, str | None, int | None]:
    parser = argparse.ArgumentParser(description="AIOS Overlay — глобальные хоткеи и оверлей")
    parser.add_argument("--settings", help="Каталог с settings/ (иначе repo settings/)", default=None)
    parser.add_argument("--host", help="WebSocket host ядра (override settings)", default=None)
    parser.add_argument("--port", type=int, help="WebSocket port ядра", default=None)
    args, _ = parser.parse_known_args()
    settings_dir = Path(args.settings) if args.settings else None
    return settings_dir, args.host, args.port


def main() -> int:
    _setup_logging()
    log = logging.getLogger("aios.overlay")
    settings_dir, host, port = _parse_args()

    from .config import load_config

    config = load_config(settings_dir)
    if host:
        config.ipc.host = host
    if port:
        config.ipc.port = port

    try:
        from .app import OverlayApp
    except ImportError as exc:
        log.error("PySide6 не установлен: pip install -e \"modules/overlay\" (%s)", exc)
        return 2

    try:
        app = OverlayApp(config=config)
        return app.run()
    except KeyboardInterrupt:
        log.info("AIOS Overlay остановлен (Ctrl-C)")
        return 0
    except Exception:  # noqa: BLE001
        log.exception("Фатальная ошибка оверлей-демона")
        return 1


if __name__ == "__main__":
    sys.exit(main())
