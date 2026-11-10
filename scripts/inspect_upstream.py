"""Inspect the supplied upstream version and compatibility without writing any files."""
from pathlib import Path
import argparse
import json
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from mobaxterm_zh.upstream import inspect_upstream


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--source-zip", type=Path)
    source.add_argument("--source-dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(inspect_upstream(REPO, args.source_zip, args.source_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
