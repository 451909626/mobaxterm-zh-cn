"""Exercise the compiled selector with our own harmless version-resource fixtures."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from mobaxterm_zh.launcher import build_launcher
from mobaxterm_zh.release import LAUNCHER_NAME


@unittest.skipUnless(os.name == "nt", "Windows launcher integration")
class LauncherSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        windows = Path(os.environ.get("WINDIR", r"C:\Windows"))
        cls.compiler = next((windows / "Microsoft.NET" / family / "v4.0.30319" / "csc.exe"
                             for family in ("Framework64", "Framework")
                             if (windows / "Microsoft.NET" / family / "v4.0.30319" / "csc.exe").is_file()), None)
        if cls.compiler is None:
            raise unittest.SkipTest(".NET Framework compiler unavailable")
        cls.temporary = tempfile.TemporaryDirectory(prefix="moba-launcher-test-")
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        cls.launcher = build_launcher(REPO, cls.root / "compiled")
        cls.fixtures = {}
        for version, product in [("26.4.0.1", "MobaXterm"), ("26.5.0.5542", "MobaXterm"),
                                 ("26.6.0.5560", "MobaXterm"), ("27.0.0.1", "MobaXterm"),
                                 ("27.0.0.2", "Other product")]:
            source = cls.root / (version + ".cs")
            source.write_text('using System.IO; using System.Reflection;\n'
                              '[assembly: AssemblyFileVersion("' + version + '")]\n'
                              '[assembly: AssemblyProduct("' + product + '")]\n'
                              'class Fixture { static void Main() { File.WriteAllText("fixture-ran.txt", "unexpected"); } }\n',
                              encoding="utf-8-sig")
            target = cls.root / ("MobaXterm_" + version + ".exe")
            subprocess.run([str(cls.compiler), "/nologo", "/target:winexe", "/out:" + str(target), str(source)],
                           check=True, capture_output=True, timeout=20)
            cls.fixtures[version] = target

    def setUp(self):
        self.directory = self.root / self._testMethodName
        self.directory.mkdir()
        self.program = self.directory / LAUNCHER_NAME
        shutil.copyfile(self.launcher, self.program)

    def supply(self, version):
        source = self.fixtures[version]
        shutil.copyfile(source, self.directory / source.name)
        return source.name

    def inspect(self, *args):
        result = self.directory / "inspection.json"
        process = subprocess.run([str(self.program), "--inspect", str(result), *args], cwd=self.directory,
                                 capture_output=True, timeout=10)
        report = json.loads(result.read_text(encoding="utf-8"))
        self.assertEqual(process.returncode, 0 if report["ok"] else 1)
        self.assertFalse((self.directory / "fixture-ran.txt").exists(), "Inspection launched the target")
        return report

    def test_auto_detection_accepts_minimum_current_and_future_metadata(self):
        for version in ("26.5.0.5542", "26.6.0.5560", "27.0.0.1"):
            with self.subTest(version=version):
                name = self.supply(version)
                report = self.inspect()
                self.assertTrue(report["ok"])
                self.assertEqual(report["detected_version"], version)
                self.assertEqual(report["selection"], "auto")
                (self.directory / name).unlink()

    def test_ambiguous_programs_require_an_explicit_choice(self):
        self.supply("26.5.0.5542")
        chosen = self.supply("26.6.0.5560")
        self.assertFalse(self.inspect()["ok"])
        selected = self.inspect("--exe", chosen)
        self.assertTrue(selected["ok"])
        self.assertEqual(selected["main_file"], chosen)

    def test_old_and_unrelated_programs_are_rejected(self):
        for version in ("26.4.0.1", "27.0.0.2"):
            name = self.supply(version)
            self.assertFalse(self.inspect("--exe", name)["ok"])
            self.assertFalse(self.inspect()["ok"])
            (self.directory / name).unlink()

    def test_target_cannot_escape_the_launcher_directory(self):
        self.supply("26.5.0.5542")
        self.assertFalse(self.inspect("--exe", "..\\MobaXterm_26.5.0.5542.exe")["ok"])

    def test_launcher_cannot_select_itself(self):
        self.supply("26.5.0.5542")
        self.assertFalse(self.inspect("--exe", self.program.name)["ok"])


if __name__ == "__main__":
    unittest.main()
