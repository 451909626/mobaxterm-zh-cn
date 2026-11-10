"""Copy a legacy profile while adapting only built-in history-root references."""
from pathlib import Path
import argparse
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from mobaxterm_zh.profiles import migrate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("The output profile already exists; it will not be overwritten")
    data, changes = migrate(args.source.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents replacing a file created concurrently.
    with args.output.open("xb") as stream:
        stream.write(data)
    print("Created a separate profile; migrated history references: " + str(len(changes)))


if __name__ == "__main__":
    main()
