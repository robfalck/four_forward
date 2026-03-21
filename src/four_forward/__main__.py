"""Entry point: python -m four_forward  or  four_forward (via project.scripts)."""

import asyncio

from .game import Game


def main() -> None:
    asyncio.run(Game().run())


if __name__ == "__main__":
    main()
