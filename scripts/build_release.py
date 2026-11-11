"""Build a graphical tool and a localized portable ZIP for one official version."""
from pathlib import Path
import argparse
import hashlib
import importlib.metadata
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from mobaxterm_zh.launcher import build_launcher
from mobaxterm_zh.patcher import load_spec
from mobaxterm_zh.release import (TOOL_VERSION, PORTABLE_NOTICES, asset_name, portable_asset_name,
                                 audit_archive, audit_portable_archive, official_version, upstream_for_tag)
from mobaxterm_zh.download import download_upstream
from mobaxterm_zh.upstream import select_upstream


def dependency_notices(folder):
    folder.mkdir()
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if not python_license.is_file():
        raise FileNotFoundError("Python license not found")
    shutil.copyfile(python_license, folder / "Python-LICENSE.txt")
    for package in ("pefile", "pyinstaller", "pyinstaller-hooks-contrib", "altgraph", "packaging", "pywin32-ctypes"):
        distribution = importlib.metadata.distribution(package)
        for item in distribution.files or []:
            if (".dist-info/" in str(item).replace("\\", "/")
                    and any(word in item.name.upper() for word in ("LICENSE", "COPYING", "NOTICE"))):
                source = Path(distribution.locate_file(item))
                shutil.copyfile(source, folder / (package + "-" + item.name))
    for source in (REPO / "legal").glob("*.txt"):
        shutil.copyfile(source, folder / source.name)


def build_release(upstream_version, tool_version, output, source_zip=None):
    if os.name != "nt" or struct.calcsize("P") != 8:
        raise RuntimeError("Release builds require 64-bit Python on Windows")
    name = asset_name(upstream_version)
    short = official_version(upstream_version)
    version, _, _ = load_spec(REPO, upstream_version)
    source_zip = Path(source_zip).resolve() if source_zip else download_upstream(REPO, upstream_version, REPO / ".local" / "upstream")
    actual, _ = select_upstream(REPO, source_zip=source_zip)
    if actual["upstream_version"] != upstream_version:
        raise ValueError("The official ZIP does not match this release version")
    output = Path(output).resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("Choose an empty output directory; existing assets are preserved")
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="moba-zh-release-") as temporary:
        work = Path(temporary)
        payload = work / "payload"
        (payload / "patches" / upstream_version).mkdir(parents=True)
        index = {"schema": 1, "minimum_version": "26.5", "versions": [upstream_version]}
        (payload / "patches" / "index.json").write_text(json.dumps(index), encoding="utf-8")
        for filename in ("version.json", "forms.json", "literals.json"):
            shutil.copyfile(REPO / "patches" / upstream_version / filename, payload / "patches" / upstream_version / filename)
        (payload / "translations").mkdir()
        shutil.copyfile(REPO / "translations" / "terminal-menu.json", payload / "translations" / "terminal-menu.json")
        launcher = build_launcher(REPO, work / "compiled-launcher", version["main_output_name"])
        (payload / "launcher").mkdir()
        shutil.copyfile(launcher, payload / "launcher" / launcher.name)
        info = {"schema": 1, "tool_version": tool_version, "localization_release": version["localization_release"],
                "upstream_version": upstream_version, "official_version": short,
                "main_file": version["main_output_name"], "launcher_sha256": hashlib.sha256(launcher.read_bytes()).hexdigest(),
                "contains_upstream_binaries": False}
        (payload / "release.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        package = work / name
        package.mkdir()
        dependency_notices(package / "licenses")
        for document in ("LICENSE", "NOTICE.md", "THIRD_PARTY_NOTICES.md"):
            shutil.copyfile(REPO / document, package / document)
        command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile", "--windowed", "--noupx",
                   "--name", "MobaXterm汉化工具", "--paths", str(REPO / "src"),
                   "--add-data", str(payload) + os.pathsep + "payload",
                   "--distpath", str(package), "--workpath", str(work / "build"),
                   "--specpath", str(work), str(REPO / "scripts" / "localizer_gui.py")]
        process = subprocess.run(command, cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace")
        (output / "build.log").write_text(process.stdout + process.stderr, encoding="utf-8")
        process.check_returncode()
        program = package / "MobaXterm汉化工具.exe"
        smoke = work / "self-test.json"
        subprocess.run([str(program), "--self-test", "--report", str(smoke)], cwd=package, check=True, timeout=60)
        smoke_result = json.loads(smoke.read_text(encoding="utf-8"))
        if not smoke_result["ok"] or not smoke_result["frozen"]:
            raise ValueError("Packaged self-test failed")
        info["tool_sha256"] = hashlib.sha256(program.read_bytes()).hexdigest()
        info["self_test"] = smoke_result
        (package / "release-manifest.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        instructions = ("MobaXterm " + short + " 简体中文汉化工具\n\n"
                        "适用官方版本：" + upstream_version + " Home 便携版\n"
                        "运行环境：Windows 10/11 64 位；无需安装 Python 或编译环境。\n\n"
                        "1. 从官网下载对应版本的 Home 便携版 ZIP，保留原包，无需解压。\n"
                        "2. 双击本发布包中的“MobaXterm汉化工具.exe”。\n"
                        "3. 选择官方 ZIP，指定一个新的输出文件夹，点击“开始汉化”。\n"
                        "4. 完成后打开输出目录，双击“MobaXterm.exe”。以后均从此入口使用。\n\n"
                        "工具只生成独立副本；官方原包与已有配置保留原样。输出采用新配置，旧会话需单独迁移。\n"
                        "本发布包包含自编工具与翻译数据，不包含 MobaXterm 本体、CygUtils 插件或完整汉化成品。\n"
                        "MobaXterm 官方下载：https://mobaxterm.mobatek.net/download-home-edition.html\n"
                        "本项目工具采用 MIT；上游软件及依赖适用各自许可。\n")
        (package / "使用说明.txt").write_text(instructions, encoding="utf-8-sig")
        archive = output / (name + ".zip")
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for path in sorted(package.rglob("*")):
                if path.is_file():
                    z.write(path, path.relative_to(work).as_posix())
        audit = audit_archive(archive)
        portable = work / "portable"
        applied = work / "portable-test.json"
        subprocess.run([str(program), "--apply", "--source-zip", str(source_zip), "--output", str(portable),
                        "--report", str(applied)], check=True, timeout=90)
        portable_test = json.loads(applied.read_text(encoding="utf-8"))
        if not portable_test["ok"] or portable_test["build"]["localized_exe_sha256"] != version["localized_exe_sha256"]:
            raise ValueError("Frozen tool reconstruction failed")
        notices = {
            "汉化说明.txt": ("MobaXterm " + short + " 非官方简体中文便携版\n\n"
                          "汉化修订：" + version["localization_release"] + "；工具构建：" + tool_version + "。\n"
                          "解压到独立目录后双击“MobaXterm.exe”。无需运行汉化工具或安装 Python。\n"
                          "前三个程序文件沿用官方便携包的名称和根目录结构；主程序已汉化，两个 CygUtils 组件保留原版。\n"
                          "终端右键菜单中文由附带启动器提供；直接打开主 EXE 不会自动启用该菜单功能。\n"
                          "此包不携带用户配置、会话、凭据或日志。首次运行会在本目录创建配置，旧会话需自行迁移。\n"
                          "本包是修改后的非官方副本，原厂数字签名已失效并移除，不代表 Mobatek 官方发行。\n"
                          "MobaXterm 本体及组件适用各自上游许可，MIT 仅覆盖自编工具与有权授权的贡献。\n"),
            "汉化工具-MIT-LICENSE.txt": (REPO / "LICENSE").read_text(encoding="utf-8"),
            "上游许可说明.txt": ("MobaXterm 的名称、程序和商标属于相应权利人。本包为非官方汉化副本。\n"
                              "原始软件许可：https://mobaxterm.mobatek.net/license.html\n"
                              "官网：https://mobaxterm.mobatek.net/\n"
                              "官方许可对修改及修改版分发设有限制；本项目 MIT 许可证不替代上游许可，也不表示获得官方额外授权。\n"),
            "组件许可说明.txt": ("CygUtils.plugin 与 CygUtils64.plugin 为对应官方便携包的原文件，未做修改。\n"
                              "MobaXterm 内置与外部组件分别适用其上游许可：\nhttps://mobaxterm.mobatek.net/license.html\n"
                              "组件源码及许可：https://download.mobatek.net/sources/\n"
                              "中文启动器为独立编写的 .NET Framework 程序，适用附带 MIT 许可；操作系统运行组件不随包附带。\n"),
        }
        portable_archive = output / (portable_asset_name(upstream_version) + ".zip")
        with zipfile.ZipFile(portable_archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for filename in (version["upstream_main_name"], "CygUtils.plugin", "CygUtils64.plugin", "MobaXterm.exe"):
                z.write(portable / filename, filename)
            for filename in sorted(PORTABLE_NOTICES):
                z.writestr(filename, notices[filename].encode("utf-8-sig"))
        portable_audit = audit_portable_archive(portable_archive, version, info["launcher_sha256"])
        sums = audit["sha256"] + "  " + archive.name + "\n" + portable_audit["sha256"] + "  " + portable_archive.name + "\n"
        (output / "SHA256SUMS.txt").write_text(sums, encoding="ascii")
        pending = "\n" + short + " 已通过构建及静态校验，完整实屏回归仍待补做。\n" if version.get("visual_validation", {}).get("status") != "passed" else ""
        notes = ("# MobaXterm " + short + " 简体中文汉化\n\n"
                 "对应官方 Home 便携版 **" + upstream_version + "**。发行版本跟随官方版本。\n\n"
                 "汉化修订 **" + version["localization_release"] + "**，工具构建 **" + tool_version + "**。补齐关闭运行中会话确认框的正文及“终端”前缀，保留会话名称。\n\n"
                 "| 附件 | 用途 |\n|---|---|\n"
                 "| `" + portable_archive.name + "` | 已汉化便携包，解压后双击 `MobaXterm.exe` |\n"
                 "| `" + archive.name + "` | 预编译图形化工具，可自行选择官方原包生成汉化副本 |\n"
                 "| `SHA256SUMS.txt` | 两个 ZIP 的 SHA-256 |\n\n"
                 "便携包保留官方三个文件的名称和根目录结构，附带中文启动器与说明。两个 CygUtils 组件未修改，不携带用户配置、会话或日志。\n\n"
                 "工具和便携包无需安装 Python 或编译环境。此为非官方修改版，MobaXterm 及组件仍适用各自上游许可；MIT 仅覆盖自编工具和有权授权的贡献。\n\n"
                 "[官方原包下载](" + version["official_archive_url"] + ") · "
                 "[官网下载页](" + version["official_download_page"] + ")\n" + pending)
        (output / "release-notes.md").write_text(notes, encoding="utf-8")
        report = {"tag": "v" + short, "official_version": short, "upstream_version": upstream_version,
                  "launcher_sha256": info["launcher_sha256"], "tool_build_version": tool_version,
                  "assets": [{"kind": "tool", "filename": archive.name, **audit},
                             {"kind": "portable", "filename": portable_archive.name, **portable_audit}],
                  "self_test": smoke_result, "portable_self_test": portable_test}
        (output / "release-build-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream-version")
    parser.add_argument("--tool-version", default=TOOL_VERSION)
    parser.add_argument("--tag")
    parser.add_argument("--source-zip", type=Path, help="Official original ZIP; downloaded and checked if omitted")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    upstream_version = upstream_for_tag(REPO, args.tag) if args.tag else args.upstream_version
    print(json.dumps(build_release(upstream_version, args.tool_version, args.output, args.source_zip), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
