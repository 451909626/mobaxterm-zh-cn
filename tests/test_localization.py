from pathlib import Path
import json
import re
import struct
import sys
import unittest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from mobaxterm_zh.dfm import Reader, encode_text
from mobaxterm_zh.patcher import load_spec, permitted
from mobaxterm_zh.upstream import inspect_upstream, registry
from mobaxterm_zh.profiles import migrate


class ManifestTests(unittest.TestCase):
    def test_reviewed_scope_and_fixed_size_literals(self):
        for version, count in [("26.5.0.5542", 1608), ("26.6.0.5560", 1613)]:
            with self.subTest(version=version):
                self.check_manifest(version, count)

    def check_manifest(self, name, count):
        version, forms, literals = load_spec(REPO, name)
        self.assertEqual(version["upstream_version"], name)
        self.assertEqual(len(forms["forms"]), 45)
        changes = [item for form in forms["forms"] for item in form["patches"]]
        self.assertEqual(sum(isinstance(item["target"], str) for item in changes), count)
        self.assertEqual(sum(type(item["target"]) is int for item in changes), 1)
        self.assertEqual(len(literals["literals"]), 21)
        self.assertEqual(version["literal_display_locations"], len(literals["literals"]))
        self.assertEqual(version["total_display_locations"], count + len(literals["literals"]) + 36)
        spans = []
        for item in literals["literals"]:
            before, after = bytes.fromhex(item["before_hex"]), bytes.fromhex(item["after_hex"])
            self.assertEqual(len(before), len(after))
            size = struct.unpack_from("<I", after, 0)[0]
            self.assertEqual(after[4:4 + size].decode("gbk"), item["chinese"])
            self.assertFalse(any(after[4 + size:]))
            start = item["offset"]
            self.assertTrue(all(start >= b or a >= start + len(before) for a, b in spans))
            spans.append((start, start + len(before)))

    def test_close_confirmation_keeps_line_breaks_and_dynamic_session_suffix(self):
        body = "One or more sessions are currently running.\rDo you want to close the following tab(s) anyway?\r\rTerminal "
        expected = {"Terminal ": "终端 ", body: "仍有会话正在运行。\r仍要关闭以下标签页吗？\r\r终端 "}
        for name in ("26.5.0.5542", "26.6.0.5560"):
            with self.subTest(version=name):
                _, _, spec = load_spec(REPO, name)
                entries = [item for item in spec["literals"] if item.get("purpose") == "session_close_confirmation"]
                self.assertEqual(len(entries), 2)
                self.assertEqual({item["english"]: item["chinese"] for item in entries}, expected)
                for item in entries:
                    raw = bytes.fromhex(item["after_hex"])
                    size = struct.unpack_from("<I", raw)[0]
                    prefix = raw[4:4 + size].decode("gbk")
                    self.assertEqual(prefix.count("\r"), item["english"].count("\r"))
                    self.assertTrue(prefix.endswith("终端 "))
                    suffix = "2:  Production SSH 中文名称"
                    self.assertEqual((raw[4:4 + size] + suffix.encode("gbk")).decode("gbk"), expected[item["english"]] + suffix)
                self.assertNotIn("AlwaysWarnOnClose", {item["english"] for item in spec["literals"]})

    def test_close_confirmation_yes_has_a_scoped_runtime_caption_patch(self):
        for name in ("26.5.0.5542", "26.6.0.5560"):
            with self.subTest(version=name):
                _, forms, spec = load_spec(REPO, name)
                entries = [item for item in spec["literals"] if item.get("purpose") == "session_close_confirmation_button"]
                self.assertEqual(len(entries), 1)
                item = entries[0]
                self.assertEqual((item["english"], item["chinese"]), ("Yes", "是"))
                self.assertEqual(len(item["references"]), 1)
                self.assertEqual(bytes.fromhex(item["before_hex"]), struct.pack("<I", 3) + b"Yes\0")
                self.assertEqual([p for p in spec["literals"] if p["english"] == "Yes"], entries)
                form = next(f for f in forms["forms"] if f["name"] == "TFORMTERMCONFIRMCLOSE")
                captions = {p["component"].rsplit(".", 1)[-1]: p["target"] for p in form["patches"] if p["property"] == "Caption"}
                self.assertEqual(captions["sBitBtn1"], "是")
                self.assertEqual(captions["sSpeedButton2"], "否")
                # The click handler uses OK as its alternate-mode marker.
                self.assertFalse({"AlwaysWarnOnClose", "OK"} & {p["english"] for p in spec["literals"]})

    def test_protected_functional_properties(self):
        value = {"component": "Form.Component", "property": "OnClick", "type": 7, "value": "Handler"}
        self.assertFalse(permitted("TFORMXTERM", value, "新处理"))
        for prop in ["Text", "FileName", "URL", "Command", "HelpKeyword"]:
            value.update(property=prop, type=6)
            self.assertFalse(permitted("TFORMXTERM", value, "中文"))
        value.update(property="Hint", value="powershell.exe")
        self.assertFalse(permitted("TFORMXTERM", value, "命令"))
        value.update(component="FormColorsSelector.Group.Col1", property="Hint", value="1")
        self.assertFalse(permitted("TFORMCOLORSSELECTOR", value, "一"))

    def test_bad_source_is_rejected_before_loading(self):
        directory = REPO / ".local" / "tests"
        directory.mkdir(parents=True, exist_ok=True)
        source = directory / "wrong-input.zip"
        source.write_bytes(b"not an upstream archive")
        with self.assertRaisesRegex(ValueError, "not a valid official ZIP"):
            inspect_upstream(REPO, source_zip=source)

    def test_launcher_catalog_and_shortcuts(self):
        catalog = json.loads((REPO / "translations" / "terminal-menu.json").read_text(encoding="utf-8"))
        source = (REPO / "launcher" / "MenuLauncher.cs").read_text(encoding="utf-8")
        self.assertIn('const string MinimumVersion = "' + registry(REPO)["minimum_version"] + '";', source)
        pattern = r'new Label\((\d+|uint\.MaxValue),("(?:\\.|[^"\\])*"),("(?:\\.|[^"\\])*")\)'
        actual = [{"id": 4294967295 if ident == "uint.MaxValue" else int(ident),
                   "english": json.loads(english), "chinese": json.loads(chinese)}
                  for ident, english, chinese in re.findall(pattern, source)]
        self.assertEqual(actual, catalog)
        self.assertEqual(len(catalog), 36)
        for item in catalog:
            self.assertEqual(item["english"].split("\t")[1:], item["chinese"].split("\t")[1:])
        for forbidden_api in ["SendInput", "keybd_event", "PostMessage", "WriteProcessMemory", "OpenClipboard", "SetClipboardData"]:
            self.assertNotIn(forbidden_api, source)


class DfmTests(unittest.TestCase):
    def test_unicode_patch_preserves_opaque_bytes_and_structure(self):
        short = lambda value: bytes([len(value)]) + value.encode("ascii")
        raw = (b"TPF0" + short("TTest") + short("Root")
               + short("Caption") + b"\x06\x05Hello"
               + short("Glyph.Data") + b"\x0a" + struct.pack("<I", 6) + b"opaque"
               + b"\0\0")
        old = Reader(raw).read()
        item = old.values[0]
        new = raw[:item["start"]] + encode_text("中文\U0001f600") + raw[item["end"]:]
        parsed = Reader(new).read()
        self.assertEqual(parsed.components, old.components)
        self.assertEqual(parsed.values[0]["value"], "中文\U0001f600")
        self.assertEqual(parsed.values[1]["value"], {"binary_bytes": 6})
        self.assertIn(b"opaque", new)


class ProfileTests(unittest.TestCase):
    def test_only_history_root_references_are_changed(self):
        original = (b"[Bookmarks]\r\n1=User sessions\\Custom\r\n"
                    b"[Recently started]\r\n1=User sessions\\Session A\r\n"
                    b"2=Shared sessions\\Session B\r\nLabel=User sessions\\not-a-reference\r\n"
                    b"[LastInstanceSessions]\r\n1=User sessions\\Session A\r\n"
                    b"[Other]\r\nOpaque=unchanged-value\r\n")
        expected = original.replace(b"1=User sessions\\Session A", "1=用户会话\\Session A".encode("gbk"))
        migrated, changes = migrate(original)
        self.assertEqual(migrated, expected)
        self.assertEqual(len(changes), 2)
        self.assertEqual(migrate(migrated), (migrated, []))


if __name__ == "__main__":
    unittest.main()
