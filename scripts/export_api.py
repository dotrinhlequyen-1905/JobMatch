"""Export the live FastAPI contract without starting the server or loading ML models."""

import argparse
from pathlib import Path

import yaml

from app.main import app

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "docs/api-spec.yaml"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the saved contract differs from the API",
    )
    args = parser.parse_args()
    contract = app.openapi()
    if args.check:
        if (
            not TARGET.exists()
            or yaml.safe_load(TARGET.read_text(encoding="utf-8")) != contract
        ):
            raise SystemExit("API changed: run python scripts/export_api.py")
        print("API contract matches docs/api-spec.yaml")
    else:
        TARGET.write_text(
            yaml.safe_dump(contract, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        print(f"Exported {len(contract['paths'])} paths to docs/api-spec.yaml")


if __name__ == "__main__":
    main()
