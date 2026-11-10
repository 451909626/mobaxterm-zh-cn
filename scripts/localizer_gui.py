"""Frozen desktop entry point; diagnostic modes also work without a console."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile

REPO = Path(__file__).resolve().parents[1]
if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(REPO / "src"))
from mobaxterm_zh.desktop import apply_package, inspect_package, release_info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--self-test", action="store_true")
    modes.add_argument("--inspect", action="store_true")
    modes.add_argument("--apply", action="store_true")
    parser.add_argument("--source-zip", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    payload = args.payload or Path(getattr(sys, "_MEIPASS", REPO)) / "payload"
    if not (args.self_test or args.inspect or args.apply):
        from mobaxterm_zh.desktop_gui import run_gui
        run_gui(payload, args.source_zip, args.output)
        return 0
    if args.report is None:
        raise SystemExit("Diagnostic modes require --report")
    try:
        info = release_info(payload)
        if args.self_test:
            import pefile
            import tkinter
            root = tkinter.Tk()
            root.withdraw()
            root.update_idletasks()
            root.destroy()
            with tempfile.TemporaryDirectory(prefix="moba-zh-selftest-") as temporary:
                catalog = Path(temporary) / "catalog.json"
                subprocess.run([str(payload / "launcher" / "启动汉化版.exe"), "--catalog", str(catalog)],
                               check=True, timeout=15)
                actual = json.loads(catalog.read_text(encoding="utf-8-sig"))
                expected = json.loads((payload / "translations" / "terminal-menu.json").read_text(encoding="utf-8"))
                if actual != expected:
                    raise ValueError("Compiled menu catalog mismatch")
            result = {"ok": True, "upstream_version": info["upstream_version"], "tool_version": info["tool_version"],
                      "menu_labels": len(actual), "tk": tkinter.TkVersion, "pefile": pefile.__version__,
                      "frozen": bool(getattr(sys, "frozen", False)), "runtime_compiler_required": False}
        elif args.inspect:
            result = {"ok": True, "inspection": inspect_package(payload, args.source_zip)}
        else:
            result = {"ok": True, "build": apply_package(payload, args.source_zip, args.output)}
    except Exception as exc:
        result = {"ok": False, "error": str(exc)}
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
