import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def store_evaluation_result(
    result: dict[str, Any],
    output_directory: str | Path,
) -> Path:
    """Persist one immutable timestamped evaluation result and update latest."""
    directory = Path(output_directory)
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    result = {
        **result,
        "run_id": timestamp,
        "created_at": datetime.now(UTC).isoformat(),
    }
    output_path = directory / f"evaluation-{timestamp}.json"
    serialized = json.dumps(result, indent=2)
    output_path.write_text(serialized, encoding="utf-8")
    (directory / "latest.json").write_text(serialized, encoding="utf-8")
    return output_path
