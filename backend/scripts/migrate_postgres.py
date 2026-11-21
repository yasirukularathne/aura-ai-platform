import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from app.database import ensure_postgres_schema  # noqa: E402


def main() -> None:
    ensure_postgres_schema()


if __name__ == "__main__":
    main()
