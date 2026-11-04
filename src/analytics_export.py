from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
import json
from typing import Mapping
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd


def build_analytics_export(tables: Mapping[str, pd.DataFrame]) -> bytes:
    """Bundle analytical tables and a manifest into a downloadable ZIP archive."""
    buffer = BytesIO()
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "files": [],
    }

    with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as archive:
        for table_name, frame in tables.items():
            safe_name = "".join(
                character if character.isalnum() or character in {"_", "-"} else "_"
                for character in table_name.strip()
            ).strip("_")
            if not safe_name:
                raise ValueError("Export table names must contain at least one letter or number.")
            filename = f"{safe_name}.csv"
            csv_data = frame.to_csv(index=False).encode("utf-8-sig")
            archive.writestr(filename, csv_data)
            manifest["files"].append(
                {"filename": filename, "rows": int(len(frame)), "columns": list(frame.columns)}
            )

        archive.writestr(
            "README.txt",
            (
                "StockWise AI analytics export\n"
                "Each CSV contains data from the current application database and selected analytics filters.\n"
                "Inventory recommendations are estimates based on recorded daily sales averages and user-entered stock settings.\n"
                "See manifest.json for included files, row counts, and columns.\n"
            ),
        )
        archive.writestr("manifest.json", json.dumps(manifest, indent=2))

    return buffer.getvalue()
