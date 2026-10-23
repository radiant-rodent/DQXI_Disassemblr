"""Launch helper for ``python -m viewer``."""

from __future__ import annotations


def main() -> int:
    from .app import App

    app = App()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
