import json
from io import BytesIO
from zipfile import ZipFile

import pandas as pd

from src.analytics_export import build_analytics_export


def test_analytics_export_contains_tables_and_manifest():
    payload = build_analytics_export(
        {"daily_sales": pd.DataFrame({"sku": ["A1"], "units": [3]})}
    )

    with ZipFile(BytesIO(payload)) as archive:
        assert {"daily_sales.csv", "README.txt", "manifest.json"} <= set(archive.namelist())
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["files"][0]["rows"] == 1
        assert b"A1" in archive.read("daily_sales.csv")
