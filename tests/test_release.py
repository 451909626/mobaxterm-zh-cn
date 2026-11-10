from pathlib import Path
from unittest.mock import patch
import hashlib
import json
import os
import sys
import tempfile
import unittest
import zipfile

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from mobaxterm_zh.desktop import UserError, apply_package, inspect_package, release_info
from mobaxterm_zh.release import (PORTABLE_NOTICES, asset_name, portable_asset_name, audit_archive,
                                 audit_portable_archive, parse_tag, upstream_for_tag)
from mobaxterm_zh.download import download_upstream


class ReleaseArchiveTests(unittest.TestCase):
    def test_tags_follow_official_versions_and_reject_shell_characters(self):
        self.assertEqual(parse_tag("v26.6"), "26.6")
        for tag in ("v2.6.0", "moba-26.6-zh-v2.6.0", "v26.6;command"):
            with self.assertRaises(ValueError):
                parse_tag(tag)
        self.assertEqual(asset_name("26.5.0.5542"), "MobaXterm_Chinese_Tool_v26.5_win-x64")
        self.assertEqual(portable_asset_name("26.6.0.5560"), "MobaXterm_Portable_v26.6_zh-CN")
        self.assertEqual(upstream_for_tag(REPO, "v26.6"), "26.6.0.5560")
        with self.assertRaises(ValueError):
            upstream_for_tag(REPO, "v99.0")

    def test_archive_requires_our_tool_and_excludes_upstream_artifacts(self):
        with tempfile.TemporaryDirectory(prefix="moba-archive-test-") as temporary:
            root = Path(temporary)
            def write(name, extra=None):
                archive = root / name
                with zipfile.ZipFile(archive, "w") as z:
                    z.writestr("tool/MobaXterm汉化工具.exe", b"synthetic-test-tool")
                    z.writestr("tool/LICENSE", "synthetic license")
                    if extra:
                        z.writestr(extra, b"forbidden-test-data")
                return archive
            self.assertEqual(audit_archive(write("good.zip"))["files"], 2)
            for name in ("tool/CygUtils.plugin", "tool/MobaXterm_Personal_26.6.exe", "tool/MobaXterm.ini", "../outside.txt"):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    audit_archive(write("bad.zip", name))

    def test_portable_archive_requires_reviewed_bytes_and_excludes_user_files(self):
        main = "MobaXterm_Personal_26.6.exe"
        core = {main: b"synthetic-localized", "CygUtils.plugin": b"original32",
                "CygUtils64.plugin": b"original64", "启动汉化版.exe": b"our-launcher"}
        sha = lambda b: hashlib.sha256(b).hexdigest()
        spec = {"upstream_main_name": main, "localized_exe_sha256": sha(core[main]),
                "files": {n: sha(core[n]) for n in ("CygUtils.plugin", "CygUtils64.plugin")}}
        with tempfile.TemporaryDirectory(prefix="moba-portable-audit-") as temporary:
            archive = Path(temporary) / "portable.zip"
            def write(entries):
                with zipfile.ZipFile(archive, "w") as z:
                    for name, value in entries.items():
                        z.writestr(name, value)
                    for name in PORTABLE_NOTICES:
                        z.writestr(name, "notice".encode("utf-8"))
            write(core)
            self.assertEqual(audit_portable_archive(archive, spec, sha(core["启动汉化版.exe"]))["files"], 8)
            for extra in ("MobaXterm.ini", "session.mxtsessions", "debug.log", "folder/extra.txt"):
                write({**core, extra: b"private"})
                with self.assertRaises(ValueError):
                    audit_portable_archive(archive, spec, sha(core["启动汉化版.exe"]))
            for name in core:
                write({**core, name: b"changed"})
                with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                    audit_portable_archive(archive, spec, sha(core["启动汉化版.exe"]))

    def test_cached_download_is_verified_and_never_overwritten(self):
        original = b"synthetic-official-archive"
        spec = {"official_archive_url": "https://download.mobatek.net/pinned/MobaXterm_Portable_v26.6.zip",
                "archive_sha256": hashlib.sha256(original).hexdigest()}
        with tempfile.TemporaryDirectory(prefix="moba-download-test-") as temporary:
            cache = Path(temporary)
            archive = cache / "MobaXterm_Portable_v26.6.zip"
            archive.write_bytes(original)
            with patch("mobaxterm_zh.download.load_spec", return_value=(spec, {}, {})), patch("mobaxterm_zh.download.subprocess.run") as run:
                self.assertTrue(download_upstream(REPO, "26.6.0.5560", cache).samefile(archive))
                run.assert_not_called()
                archive.write_bytes(b"changed")
                with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                    download_upstream(REPO, "26.6.0.5560", cache)
                self.assertEqual(archive.read_bytes(), b"changed")


class DesktopPackageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="moba-desktop-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.payload = self.root / "payload"
        folder = self.payload / "patches" / "26.6.0.5560"
        folder.mkdir(parents=True)
        (self.payload / "launcher").mkdir()
        self.launcher = b"synthetic-launcher"
        (self.payload / "launcher" / "启动汉化版.exe").write_bytes(self.launcher)
        info = {"tool_version": "2.6.0", "upstream_version": "26.6.0.5560", "main_file": "MobaXterm_Personal_26.6_zh.exe",
                "launcher_sha256": hashlib.sha256(self.launcher).hexdigest()}
        (self.payload / "release.json").write_text(json.dumps(info), encoding="utf-8")
        index = {"schema": 1, "minimum_version": "26.5", "versions": ["26.6.0.5560"]}
        (self.payload / "patches" / "index.json").write_text(json.dumps(index), encoding="utf-8")
        (folder / "version.json").write_text(json.dumps({"upstream_version": "26.6.0.5560", "main_output_name": info["main_file"]}), encoding="utf-8")
        (folder / "forms.json").write_text('{"forms": []}', encoding="utf-8")
        (folder / "literals.json").write_text('{"literals": []}', encoding="utf-8")
        self.source = self.root / "official.zip"
        self.source.write_bytes(b"synthetic-original")
        self.output = self.root / "new-output"

    def test_modified_embedded_launcher_is_rejected(self):
        (self.payload / "launcher" / "启动汉化版.exe").write_bytes(b"changed")
        with self.assertRaises(UserError):
            release_info(self.payload)

    def test_wrong_version_and_unverified_archive_are_rejected(self):
        for report in ({"detected_version": "26.5.0.5542", "full_ui_supported": True},
                       {"detected_version": "26.6.0.5560", "full_ui_supported": False}):
            with patch("mobaxterm_zh.desktop.inspect_upstream", return_value=report), self.assertRaises(UserError):
                inspect_package(self.payload, self.source)
        self.assertEqual(self.source.read_bytes(), b"synthetic-original")

    @unittest.skipUnless(os.name == "nt", "Windows atomic directory publishing")
    def test_existing_output_is_preserved_before_any_build(self):
        self.output.mkdir()
        sentinel = self.output / "MobaXterm.ini"
        sentinel.write_bytes(b"existing-user-config")
        with patch("mobaxterm_zh.desktop.build_local_ui") as build, self.assertRaises(UserError):
            apply_package(self.payload, self.source, self.output)
        build.assert_not_called()
        self.assertEqual(sentinel.read_bytes(), b"existing-user-config")

    @unittest.skipUnless(os.name == "nt", "Windows atomic directory publishing")
    def test_failed_build_does_not_publish_a_partial_output(self):
        def fail(repo, stage, **kwargs):
            stage.mkdir()
            (stage / "partial.exe").write_bytes(b"partial")
            raise RuntimeError("synthetic failure")
        with patch("mobaxterm_zh.desktop.inspect_package"), patch("mobaxterm_zh.desktop.build_local_ui", side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, "synthetic failure"):
                apply_package(self.payload, self.source, self.output)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.source.read_bytes(), b"synthetic-original")

    @unittest.skipUnless(os.name == "nt", "Windows atomic directory publishing")
    def test_output_created_during_build_is_never_overwritten(self):
        def simulate(repo, stage, **kwargs):
            stage.mkdir()
            self.output.mkdir()
            (self.output / "keep.txt").write_text("user-created", encoding="utf-8")
            return {"upstream_version": "26.6.0.5560"}
        with patch("mobaxterm_zh.desktop.inspect_package"), patch("mobaxterm_zh.desktop.build_local_ui", side_effect=simulate):
            with self.assertRaises(UserError):
                apply_package(self.payload, self.source, self.output)
        self.assertEqual(list(p.name for p in self.output.iterdir()), ["keep.txt"])
        self.assertEqual((self.output / "keep.txt").read_text(encoding="utf-8"), "user-created")


if __name__ == "__main__":
    unittest.main()
