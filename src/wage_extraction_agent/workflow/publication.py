"""Final response projection and atomic JSON publication."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from wage_extraction_agent.models.domain import ExtractionResponse


def publish_response(response: ExtractionResponse, output_dir: Path) -> Path:
    """Write a validated response without exposing an interrupted partial file."""

    output_dir.mkdir(parents=True, exist_ok=True)
    safe_request_id = "".join(
        character if character.isalnum() or character in {"-", "_"} else "_"
        for character in response.request_id
    )
    final_path = output_dir / f"{safe_request_id}.json"
    payload = response.model_dump_json(by_alias=True, indent=2)

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=output_dir,
            prefix=f".{safe_request_id}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(payload)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
            temporary_path = Path(handle.name)
        os.replace(temporary_path, final_path)
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise
    return final_path
