"""Apply a packaged patch set without a developer toolchain on the user's PC."""
from pathlib import Path
import hashlib
import json
import os
import tempfile

from .patcher import build_local_ui, load_spec
from .upstream import inspect_upstream


class UserError(ValueError):
    """A concise error suitable for the desktop UI."""


def release_info(payload):
    payload = Path(payload)
    info = json.loads((payload / "release.json").read_text(encoding="utf-8"))
    version, _, _ = load_spec(payload, info["upstream_version"])
    launcher = payload / "launcher" / "MobaXterm.exe"
    if hashlib.sha256(launcher.read_bytes()).hexdigest() != info["launcher_sha256"]:
        raise UserError("汉化工具文件不完整，请重新下载并解压对应版本的发布包。")
    if version["main_output_name"] != info["main_file"]:
        raise UserError("汉化工具的版本数据不一致，请重新下载。")
    return info


def inspect_package(payload, source_zip):
    info = release_info(payload)
    source_zip = Path(source_zip)
    if not source_zip.is_file():
        raise UserError("请先选择从官网下载的 Home 便携版 ZIP 文件。")
    try:
        report = inspect_upstream(payload, source_zip=source_zip)
    except (ValueError, OSError) as exc:
        raise UserError("无法读取官方便携包。请确认选择的是完整的 Home 便携版 ZIP 文件。") from exc
    if report["detected_version"] != info["upstream_version"]:
        raise UserError("本工具适用于 " + info["upstream_version"] + "，选择的程序是 "
                        + report["detected_version"] + "。请下载与官方原包对应的汉化工具。")
    if not report["full_ui_supported"]:
        raise UserError("原包校验未通过。请重新从官网下载此版本的 Home 便携版 ZIP，保留原始文件内容。")
    return report


def apply_package(payload, source_zip, output, progress=None):
    """Create a new folder atomically; never overwrite an original or an old build."""
    if os.name != "nt":
        raise UserError("此汉化工具需要在 Windows 上运行。")
    progress = progress or (lambda message: None)
    payload, output = Path(payload).resolve(), Path(output).resolve()
    info = release_info(payload)
    if output.exists():
        raise UserError("输出文件夹已存在，请选择新的文件夹名称。原有文件已保留。")
    progress("正在校验官方便携包……")
    inspect_package(payload, source_zip)
    output.parent.mkdir(parents=True, exist_ok=True)
    # The staging folder and final folder share a parent/volume. Windows rename
    # refuses an existing destination, including one created during the build.
    with tempfile.TemporaryDirectory(prefix=".moba-zh-build-", dir=output.parent) as temporary:
        stage = Path(temporary).resolve() / "result"
        progress("正在生成中文界面……")
        report = build_local_ui(payload, stage, source_zip=source_zip)
        progress("正在安装菜单启动器并核对结果……")
        launcher = (payload / "launcher" / "MobaXterm.exe").read_bytes()
        (stage / "MobaXterm.exe").write_bytes(launcher)
        report.update(tool_version=info["tool_version"], launcher_sha256=info["launcher_sha256"],
                      input_preserved=True, output_profile="fresh", distribution="Local user build only")
        (stage / "build-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (stage / "使用说明.txt").write_text(
            "请双击“MobaXterm.exe”使用，主界面与终端右键菜单将显示中文。\n"
            "此目录根据您提供的官方 " + info["upstream_version"] + " 便携包在本机生成，原包保留原样。\n"
            "两个 CygUtils 组件为对应版本的官方原文件。配置为新配置，旧会话需单独迁移。\n",
            encoding="utf-8")
        if (stage.parent != Path(temporary).resolve() or stage.parent.parent != output.parent
                or output.exists()):
            raise UserError("输出位置发生变化，已停止操作；请重新选择新的文件夹名称。")
        stage.rename(output)
    progress("汉化完成。请从新目录中的“MobaXterm.exe”进入。")
    return report
