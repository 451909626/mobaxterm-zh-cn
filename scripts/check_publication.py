"""Check the Git index for private data and upstream binary artifacts."""
from pathlib import Path
import argparse
import re
import subprocess
import sys

REPO = Path(__file__).resolve().parents[1]
DENIED = {".exe", ".dll", ".plugin", ".ini", ".lnk", ".mxtsessions", ".log", ".bak", ".zip", ".7z", ".bin", ".pdb"}
PATTERNS = [
    ("private-key block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("GitHub credential", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b")),
    ("literal Windows user path", re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+[^<%\\/\s]+")),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", action="store_true", help="Check staged blobs; the default checks tracked working files")
    args = parser.parse_args()
    names = subprocess.check_output(["git", "ls-files", "-z"], cwd=REPO).decode("utf-8").split("\0")
    errors = []
    for name in filter(None, names):
        path = Path(name)
        if path.suffix.lower() in DENIED or any(part in {".local", "dist", "build", "original", "vendor"} for part in path.parts):
            errors.append(name + ": private/generated/upstream artifact")
            continue
        data = (subprocess.check_output(["git", "show", ":" + name], cwd=REPO) if args.index else (REPO / path).read_bytes())
        if path.suffix.lower() == ".png":
            continue
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            errors.append(name + ": unexpected binary file")
            continue
        for label, pattern in PATTERNS:
            if pattern.search(text):
                errors.append(name + ": " + label)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        raise SystemExit(1)
    print("Publication audit passed for " + str(sum(bool(n) for n in names)) + " tracked files.")


if __name__ == "__main__":
    main()
