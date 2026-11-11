"""Names and archive audits shared by local and GitHub release builds."""
from pathlib import Path, PurePosixPath
import hashlib
import re
import zipfile

TOOL_VERSION = "2.6.2"
TAG = re.compile(r"v(\d+\.\d+)\Z")


def parse_tag(value):
    match = TAG.fullmatch(value)
    if not match:
        raise ValueError("Expected the official version tag, for example v26.6")
    return match.group(1)


def official_version(upstream_version):
    if not isinstance(upstream_version, str) or not re.fullmatch(r"\d+\.\d+(?:\.\d+\.\d+)?", upstream_version):
        raise ValueError("Invalid release version")
    return ".".join(upstream_version.split(".")[:2])


def upstream_for_tag(repo, tag):
    from .upstream import manifests
    version = parse_tag(tag)
    found = [v["upstream_version"] for v in manifests(repo) if official_version(v["upstream_version"]) == version]
    if len(found) != 1:
        raise ValueError("Official version must match exactly one reviewed build: " + version)
    return found[0]


def asset_name(upstream_version):
    return "MobaXterm_Chinese_Tool_v" + official_version(upstream_version) + "_win-x64"


def portable_asset_name(upstream_version):
    return "MobaXterm_Portable_v" + official_version(upstream_version) + "_zh-CN"


def audit_archive(path):
    """Release ZIP contains our tool and notices, never the upstream application."""
    with zipfile.ZipFile(path) as archive:
        rows = archive.infolist()
        names = [r.filename for r in rows]
        if len(set(names)) != len(names) or archive.testzip() is not None:
            raise ValueError("Invalid or duplicate release ZIP entries")
        executables = []
        for row in rows:
            name = row.filename
            item = PurePosixPath(name)
            if item.is_absolute() or ".." in item.parts or "\\" in name:
                raise ValueError("Unsafe release archive path")
            lower = name.lower()
            if item.suffix.lower() in {".plugin", ".ini", ".dll", ".mxtsessions", ".log", ".bak"}:
                raise ValueError("Upstream/private artifact in release: " + name)
            if lower.endswith(".exe"):
                executables.append(name)
                if item.name != "MobaXterm汉化工具.exe":
                    raise ValueError("Unexpected executable in release: " + name)
        if len(executables) != 1:
            raise ValueError("Release must contain exactly one graphical localization tool")
        if not any(PurePosixPath(n).name == "LICENSE" for n in names):
            raise ValueError("Release license is missing")
    return {"files": len(names), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


PORTABLE_NOTICES = {"汉化说明.txt", "汉化工具-MIT-LICENSE.txt", "上游许可说明.txt", "组件许可说明.txt"}


def audit_portable_archive(path, version, launcher_sha256):
    """Match the official flat layout, reviewed executable and original plugins."""
    required = {version["upstream_main_name"]: version["localized_exe_sha256"],
                "CygUtils.plugin": version["files"]["CygUtils.plugin"],
                "CygUtils64.plugin": version["files"]["CygUtils64.plugin"],
                "MobaXterm.exe": launcher_sha256}
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(set(names)) != len(names) or archive.testzip() is not None:
            raise ValueError("Invalid or duplicate portable ZIP entries")
        if set(names) != set(required) | PORTABLE_NOTICES:
            raise ValueError("Portable ZIP must contain only the official root files, launcher and notices")
        for name, expected in required.items():
            if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                raise ValueError("Portable file SHA-256 mismatch: " + name)
        for name in PORTABLE_NOTICES:
            text = archive.read(name).decode("utf-8-sig")
            if not text.strip():
                raise ValueError("Empty portable notice: " + name)
    return {"files": len(names), "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}
