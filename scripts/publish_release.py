"""Publish the audited tool, localized portable ZIP and checksums to an official tag."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from datetime import datetime, timezone

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from mobaxterm_zh.release import asset_name, portable_asset_name, audit_archive, audit_portable_archive, parse_tag, official_version
from mobaxterm_zh.patcher import load_spec
from mobaxterm_zh.upstream import manifests


def release_command(tag, repository, assets):
    short = parse_tag(tag)
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Expected owner/repository")
    assets = Path(assets).resolve()
    report = json.loads((assets / "release-build-report.json").read_text(encoding="utf-8"))
    upstream = report["upstream_version"]
    version, _, _ = load_spec(REPO, upstream)
    if (report["tag"] != tag or official_version(upstream) != short or not report["self_test"]["ok"]
            or not report["portable_self_test"]["ok"]):
        raise ValueError("Release build report mismatch")
    archive = assets / (asset_name(upstream) + ".zip")
    portable = assets / (portable_asset_name(upstream) + ".zip")
    checksum = assets / "SHA256SUMS.txt"
    tool_audit = audit_archive(archive)
    portable_audit = audit_portable_archive(portable, version, report["launcher_sha256"])
    expected = tool_audit["sha256"] + "  " + archive.name + "\n" + portable_audit["sha256"] + "  " + portable.name + "\n"
    if checksum.read_text(encoding="ascii") != expected:
        raise ValueError("Release checksum mismatch")
    wanted = {("tool", archive.name): tool_audit["sha256"], ("portable", portable.name): portable_audit["sha256"]}
    recorded = {(item["kind"], item["filename"]): item["sha256"] for item in report["assets"]}
    if recorded != wanted or len(report["assets"]) != 2:
        raise ValueError("Release asset report mismatch")
    with zipfile.ZipFile(archive) as z:
        info = json.loads(z.read(next(n for n in z.namelist() if n.endswith("/release-manifest.json"))))
        if info["upstream_version"] != upstream or info["launcher_sha256"] != report["launcher_sha256"]:
            raise ValueError("Tool and portable launcher do not match")
    latest = upstream == manifests(REPO)[-1]["upstream_version"]
    command = ["gh", "release", "create", tag, str(archive), str(portable), str(checksum), "--repo", repository,
               "--verify-tag", "--title", short,
               "--notes-file", str(assets / "release-notes.md"), "--latest=" + str(latest).lower()]
    if version.get("visual_validation", {}).get("status") != "passed":
        command.append("--prerelease")
    return command


def update_release(command, tag, repository, assets):
    """Preserve the previous assets before explicitly replacing a mutable release."""
    query = subprocess.run(["gh", "api", "repos/" + repository + "/releases/tags/" + tag],
                           capture_output=True, text=True, encoding="utf-8")
    if query.returncode:
        if "HTTP 404" in query.stderr:
            subprocess.run(command, check=True)
            return
        raise RuntimeError("Cannot inspect the existing release")
    release = json.loads(query.stdout)
    if release.get("immutable"):
        raise RuntimeError("The existing release is immutable; assets were not changed")
    files = command[4:7]
    expected = {Path(path).name for path in files}
    existing = {asset["name"]: asset for asset in release["assets"]}
    if set(existing) != expected:
        raise ValueError("Existing release assets differ; refusing to replace unrelated files")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = Path(assets).resolve().parent / "previous-release-assets" / tag / stamp
    backup.mkdir(parents=True, exist_ok=False)
    subprocess.run(["gh", "release", "download", tag, "--repo", repository, "--dir", str(backup)], check=True)
    for name, asset in existing.items():
        digest = "sha256:" + hashlib.sha256((backup / name).read_bytes()).hexdigest()
        if asset.get("digest") != digest:
            raise ValueError("Previous release backup failed verification")
    (backup / "release-metadata.json").write_text(json.dumps(release, ensure_ascii=False, indent=2), encoding="utf-8")
    current = subprocess.run(["gh", "api", "repos/" + repository + "/releases/tags/" + tag],
                             capture_output=True, text=True, encoding="utf-8", check=True)
    current_assets = json.loads(current.stdout)["assets"]
    if {(a["id"], a.get("digest")) for a in current_assets} != {(a["id"], a.get("digest")) for a in release["assets"]}:
        raise RuntimeError("Release assets changed during backup; existing files were not replaced")
    subprocess.run(["gh", "release", "upload", tag, *files, "--repo", repository, "--clobber"], check=True)
    title = command[command.index("--title") + 1]
    notes = command[command.index("--notes-file") + 1]
    latest = next(value for value in command if value.startswith("--latest="))
    subprocess.run(["gh", "release", "edit", tag, "--repo", repository, "--title", title,
                    "--notes-file", notes, "--prerelease=" + str("--prerelease" in command).lower(), latest], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--assets", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--replace-assets", action="store_true", help="Explicitly replace assets of an existing mutable release")
    args = parser.parse_args()
    command = release_command(args.tag, args.repo, args.assets)
    if args.dry_run:
        print(json.dumps(command, ensure_ascii=False, indent=2))
    elif args.replace_assets:
        update_release(command, args.tag, args.repo, args.assets)
    else:
        subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
