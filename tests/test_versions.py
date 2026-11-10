"""Version selection tests use synthetic input bytes, never vendor binaries."""
from pathlib import Path
from unittest.mock import patch
import hashlib
import json
import sys
import tempfile
import unittest
import zipfile

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from mobaxterm_zh.upstream import inspect_upstream, read_source, select_upstream, version_tuple


class VersionSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="moba-version-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo, self.source = self.root / "repo", self.root / "source"
        self.source.mkdir()
        self.specs = {}
        for version in ("26.5.0.5542", "26.6.0.5560"):
            short = ".".join(version.split(".")[:2])
            main = "MobaXterm_Personal_" + short + ".exe"
            files = {main: version.encode(), "CygUtils.plugin": b"synthetic-plugin-32",
                     "CygUtils64.plugin": b"synthetic-plugin-64"}
            self.specs[version] = (main, files)
            folder = self.repo / "patches" / version
            folder.mkdir(parents=True)
            spec = {"upstream_version": version, "upstream_main_name": main, "archive_sha256": "0" * 64,
                    "files": {n: hashlib.sha256(b).hexdigest() for n, b in files.items()}}
            (folder / "version.json").write_text(json.dumps(spec), encoding="utf-8")
        (self.repo / "patches" / "index.json").write_text(json.dumps({"schema": 1, "minimum_version": "26.5",
                                                                   "versions": list(self.specs)}), encoding="utf-8")

    def supply(self, version):
        for name, data in self.specs[version][1].items():
            (self.source / name).write_bytes(data)

    def metadata(self, version):
        return patch("mobaxterm_zh.upstream.read_metadata", return_value={"version": version, "product": "MobaXterm"})

    def test_both_reviewed_versions_select_their_own_files(self):
        for version in self.specs:
            with self.subTest(version=version), self.metadata(version):
                main, files = self.specs[version]
                directory = self.root / version
                directory.mkdir()
                for name, data in files.items():
                    (directory / name).write_bytes(data)
                selected, loaded = select_upstream(self.repo, source_dir=directory)
                self.assertEqual(selected["upstream_version"], version)
                self.assertEqual(loaded[main], files[main])

    def test_future_version_is_inspected_but_never_patched(self):
        self.supply("26.6.0.5560")
        with self.metadata("27.0.0.1"):
            report = inspect_upstream(self.repo, source_dir=self.source)
            self.assertTrue(report["menu_version_eligible"])
            self.assertFalse(report["full_ui_supported"])
            with self.assertRaisesRegex(ValueError, "not been reviewed"):
                select_upstream(self.repo, source_dir=self.source)

    def test_older_versions_are_ineligible(self):
        self.supply("26.5.0.5542")
        with self.metadata("26.4.0.1"):
            report = inspect_upstream(self.repo, source_dir=self.source)
            self.assertFalse(report["menu_version_eligible"])
            with self.assertRaisesRegex(ValueError, "below 26.5"):
                select_upstream(self.repo, source_dir=self.source)
        self.assertLess(version_tuple("26.9"), version_tuple("26.10"))

    def test_same_version_with_changed_exe_or_plugin_is_rejected(self):
        version = "26.5.0.5542"
        self.supply(version)
        with self.metadata(version):
            for name, original in self.specs[version][1].items():
                with self.subTest(file=name):
                    (self.source / name).write_bytes(original + b"tampered")
                    with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                        select_upstream(self.repo, source_dir=self.source)
                    (self.source / name).write_bytes(original)

    def test_repackaged_archive_is_rejected_even_with_identical_files(self):
        version = "26.5.0.5542"
        archive = self.root / "repackaged.zip"
        with zipfile.ZipFile(archive, "w") as z:
            for name, data in self.specs[version][1].items():
                z.writestr(name, data)
        with self.metadata(version), self.assertRaisesRegex(ValueError, "Official ZIP SHA-256 mismatch"):
            select_upstream(self.repo, source_zip=archive)

    def test_duplicate_archive_names_and_multiple_exes_are_rejected(self):
        archive = self.root / "ambiguous.zip"
        with zipfile.ZipFile(archive, "w") as z:
            z.writestr("a/MobaXterm.exe", b"a")
            z.writestr("b/MobaXterm.exe", b"b")
        with self.assertRaisesRegex(ValueError, "Duplicate input"):
            read_source(source_zip=archive)
        self.supply("26.5.0.5542")
        (self.source / "MobaXterm_extra.exe").write_bytes(b"extra")
        with self.assertRaisesRegex(ValueError, "exactly one"):
            read_source(source_dir=self.source)


if __name__ == "__main__":
    unittest.main()
