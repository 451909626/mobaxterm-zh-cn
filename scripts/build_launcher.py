"""Build only the independent terminal-menu launcher."""
from pathlib import Path
import argparse
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from mobaxterm_zh.launcher import build_launcher


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=REPO / "dist" / "menu-launcher")
    parser.add_argument("--target-exe", help="Optional fixed EXE basename; otherwise auto-detect MobaXterm 26.5+")
    args = parser.parse_args()
    path = build_launcher(REPO, args.output, args.target_exe)
    print("Built independent launcher: " + str(path))


if __name__ == "__main__":
    main()
