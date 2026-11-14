"""Auto-select reviewed UI patches for authorized local use; no automatic publishing."""
from pathlib import Path
import argparse
import hashlib
import json
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from mobaxterm_zh.patcher import build_local_ui
from mobaxterm_zh.launcher import build_launcher
from mobaxterm_zh.release import LAUNCHER_NAME, toolbar_notice


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--source-zip", type=Path)
    source.add_argument("--source-dir", type=Path)
    parser.add_argument("--output", type=Path, default=REPO / "dist" / "R2.13")
    args = parser.parse_args()
    report = build_local_ui(REPO, args.output, args.source_zip, args.source_dir)
    launcher = build_launcher(REPO, args.output, report["main_file"])
    report["launcher_sha256"] = hashlib.sha256(launcher.read_bytes()).hexdigest()
    report["upstream_binaries_in_git"] = False
    report["distribution"] = "Local build only. Upstream redistribution rights are separate."
    (args.output / "build-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output / "使用说明.txt").write_text(
        f"请使用“{LAUNCHER_NAME}”运行，以自动提供终端右键菜单中文。\n"
        + toolbar_notice(report) + "\n"
        "本目录由使用者自备的官方 " + report["upstream_version"] + " 便携包在本机生成。\n"
        "此构建不会改写原始输入文件，配置为默认空白配置。\n"
        "保留旧版历史记录时，请使用仓库提供的独立配置迁移工具。\n"
        "上游修改与分发许可请见 https://mobaxterm.mobatek.net/license.html 。\n",
        encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
