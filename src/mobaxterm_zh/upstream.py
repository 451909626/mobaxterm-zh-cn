"""Detect official inputs and select a reviewed, version-specific patch set."""
from pathlib import Path
import hashlib
import io
import json
import zipfile


def version_tuple(value):
    parts = value.split(".")
    if not 2 <= len(parts) <= 4 or not all(p.isascii() and p.isdigit() for p in parts):
        raise ValueError("Invalid numeric version: " + value)
    return tuple(map(int, parts)) + (0,) * (4 - len(parts))


def registry(repo):
    data = json.loads((Path(repo) / "patches" / "index.json").read_text(encoding="utf-8"))
    if data["schema"] != 1 or not data["versions"] or len(set(data["versions"])) != len(data["versions"]):
        raise ValueError("Invalid patch registry")
    minimum = version_tuple(data["minimum_version"])
    if any(version_tuple(v) < minimum for v in data["versions"]):
        raise ValueError("Registered version is below the minimum")
    return data


def manifests(repo):
    result = []
    for name in registry(repo)["versions"]:
        value = json.loads((Path(repo) / "patches" / name / "version.json").read_text(encoding="utf-8"))
        if value["upstream_version"] != name:
            raise ValueError("Patch registry/version mismatch")
        result.append(value)
    return sorted(result, key=lambda v: version_tuple(v["upstream_version"]))


def read_metadata(data):
    import pefile
    try:
        pe = pefile.PE(data=data, fast_load=False)
        fixed = pe.VS_FIXEDFILEINFO[0]
        parts = (fixed.FileVersionMS >> 16, fixed.FileVersionMS & 65535,
                 fixed.FileVersionLS >> 16, fixed.FileVersionLS & 65535)
        strings = {}
        for group in pe.FileInfo:
            for entry in group:
                for table in getattr(entry, "StringTable", []):
                    strings.update({k.decode("utf-8"): v.decode("utf-8") for k, v in table.entries.items()})
        if strings.get("ProductName", "").strip().lower() != "mobaxterm":
            raise ValueError("The executable is not identified as MobaXterm")
        return {"version": ".".join(map(str, parts)), "product": strings["ProductName"]}
    except (pefile.PEFormatError, AttributeError, IndexError, UnicodeError) as exc:
        raise ValueError("Cannot read the MobaXterm executable version") from exc


def read_source(source_zip=None, source_dir=None):
    if bool(source_zip) == bool(source_dir):
        raise ValueError("Provide either an official ZIP or an extracted source directory")
    files, archive_hash = {}, None

    def wanted(name):
        lower = name.lower()
        return ((lower.startswith("mobaxterm") and lower.endswith(".exe"))
                or lower in {"cygutils.plugin", "cygutils64.plugin"})

    if source_zip:
        raw = Path(source_zip).read_bytes()
        archive_hash = hashlib.sha256(raw).hexdigest()
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                for item in archive.infolist():
                    name = item.filename.replace("\\", "/").rsplit("/", 1)[-1]
                    if item.is_dir() or not wanted(name):
                        continue
                    if name.lower() in {n.lower() for n in files}:
                        raise ValueError("Duplicate input filename: " + name)
                    files[name] = archive.read(item)
        except zipfile.BadZipFile as exc:
            raise ValueError("Input is not a valid official ZIP") from exc
    else:
        for path in sorted(Path(source_dir).iterdir()):
            if path.is_file() and wanted(path.name):
                if path.name.lower() in {n.lower() for n in files}:
                    raise ValueError("Duplicate input filename: " + path.name)
                files[path.name] = path.read_bytes()
    mains = [name for name in files if name.lower().endswith(".exe")]
    if len(mains) != 1:
        raise ValueError("Input must contain exactly one MobaXterm executable; found " + str(len(mains)))
    return files, archive_hash


def assess_source(repo, files, archive_hash=None):
    mains = [name for name in files if name.lower().endswith(".exe")]
    if len(mains) != 1:
        raise ValueError("Input must contain exactly one MobaXterm executable; found " + str(len(mains)))
    main = mains[0]
    metadata = read_metadata(files[main])
    index, available = registry(repo), manifests(repo)
    found = next((v for v in available if v["upstream_version"] == metadata["version"]), None)
    eligible = version_tuple(metadata["version"]) >= version_tuple(index["minimum_version"])
    errors = []
    if not eligible:
        errors.append("Versions below " + index["minimum_version"] + " are unsupported")
    elif found is None:
        errors.append("Full UI patches have not been reviewed for " + metadata["version"])
    else:
        if archive_hash is not None and archive_hash != found["archive_sha256"]:
            errors.append("Official ZIP SHA-256 mismatch")
        if main != found["upstream_main_name"]:
            errors.append("Original executable filename mismatch")
        for name, expected in found["files"].items():
            if name not in files or hashlib.sha256(files[name]).hexdigest() != expected:
                errors.append("Original file SHA-256 mismatch or missing: " + name)
    report = {
        "detected_version": metadata["version"], "main_file": main,
        "main_sha256": hashlib.sha256(files[main]).hexdigest(),
        "minimum_version": index["minimum_version"],
        "registered_full_ui_versions": [v["upstream_version"] for v in available],
        "full_ui_supported": not errors,
        "menu_version_eligible": eligible,
        "menu_note": "Only matching menu IDs and original English labels are translated; future menus require verification.",
        "reasons": errors,
    }
    return report, found


def inspect_upstream(repo, source_zip=None, source_dir=None):
    files, archive_hash = read_source(source_zip, source_dir)
    return assess_source(repo, files, archive_hash)[0]


def select_upstream(repo, source_zip=None, source_dir=None):
    files, archive_hash = read_source(source_zip, source_dir)
    report, version = assess_source(repo, files, archive_hash)
    if not report["full_ui_supported"]:
        raise ValueError("; ".join(report["reasons"]) + ". No files were modified.")
    return version, files
