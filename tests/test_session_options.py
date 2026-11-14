"""Run session value adapters with native getters, old data and dynamic values."""
from pathlib import Path
import json
import struct
import sys
import unittest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from mobaxterm_zh.session_options import (ASSIGN_RVA, GETTER_RVA, SETTER_RVA, FIND_RVA, LABELS, VALUE_LABELS, CAPTION_LABELS, SETTEXT_LABELS, ITEM_LIMITS, assemble)
from mobaxterm_zh.patcher import load_spec, permitted


class SessionOptionTests(unittest.TestCase):
    def test_catalog_is_scoped_and_keeps_functional_properties_protected(self):
        version, forms, _ = load_spec(REPO, "26.6.0.5560")
        self.assertEqual(version["session_combo_controls"] + version["secondary_combo_controls"], len(LABELS))
        self.assertEqual(version["session_combo_item_labels"] + version["secondary_combo_item_labels"], sum(a != b for values in LABELS.values() for a, b in values))
        by_form = {form["name"]: form for form in forms["forms"]}
        for (form, component), values in LABELS.items():
            expected = [b for a, b in values if a != b]
            actual = [item["target"] for item in sorted(by_form[form]["patches"], key=lambda x: x["index"])
                      if item["component"] == component and item["property"] == "Items.Strings[]"]
            self.assertEqual(actual, expected, component)
            source, target = next((a, b) for a, b in values if a != b)
            value = {"component": component, "property": "Text", "value": source, "type": 6}
            self.assertTrue(permitted(form, value, target))
            for prop in ("ItemIndex", "OnChange", "HelpKeyword", "Command"):
                value["property"] = prop
                self.assertFalse(permitted(form, value, target))
        for component, source in [("FormSessionEdit.PC1.TabTerminal.sComboBox4", "UTF-8"),
                                  ("FormSessionEdit.PC1.TabTerminal.sComboBox11", "xterm"),
                                  ("FormSessionEdit.PC1.TabXDMCP.sComboBox9", "us")]:
            value = {"component": component, "property": "Items.Strings[]", "value": source, "type": 6}
            self.assertFalse(permitted("TFORMSESSIONEDIT", value, "中文"))
        self.assertNotIn("FormSessionEdit.ComboMacros", VALUE_LABELS)
        self.assertNotIn("FormSessionEdit.PC0.sTabSheet17.WslDistros", VALUE_LABELS)

    def test_native_values_custom_values_and_legacy_lookups_at_two_bases(self):
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
        from unicorn.x86_const import (UC_X86_REG_EAX as EAX, UC_X86_REG_EBX as EBX,
                                      UC_X86_REG_ECX as ECX, UC_X86_REG_EDX as EDX,
                                      UC_X86_REG_ESI as ESI, UC_X86_REG_EDI as EDI,
                                      UC_X86_REG_EBP as EBP, UC_X86_REG_ESP as ESP,
                                      UC_X86_REG_EFLAGS as FLAGS)
        spec = json.loads((REPO / "patches/26.6.0.5560/session-values.json").read_text(encoding="utf-8"))
        count = 0
        for base in (0x400000, 0x1400000):
            rva = 0x900000
            payload, _, entries = assemble(rva, spec["sites"])
            for key, entry in entries.items():
                component, kind, vmt_register = key
                if kind in ("caption", "settext"): continue
                lookup = kind in ("indexof", "findtext")
                values = VALUE_LABELS[component]
                changed = [(a, b) for a, b in values if a != b]
                if lookup:
                    cases = [(a, False) for a, b in changed] + [(a.upper(), False) for a, b in changed]
                    cases += [(b, False) for a, b in changed] + [(a, True) for a, b in changed]
                    cases += [(x, False) for x in (None, "", "CustomDesktop", "用户自定义会话", changed[0][0] + " extra")]
                else:
                    cases = [(x, False) for a, b in changed for x in (a, b)]
                    cases += [(x, False) for x in (None, "", "1920x1080", "用户自定义值", changed[0][1] + " extra")]
                    if kind == "item": cases += [("native-index-error", False)]
                cases = [(value, old_items, 7) for value, old_items in cases]
                if kind == "item" and component in ITEM_LIMITS:
                    cases += [(chinese, False, 30) for english, chinese in changed]
                for value, old_items, native_index in cases:
                    uc = Uc(UC_ARCH_X86, UC_MODE_32)
                    uc.mem_map(base + rva, (len(payload) + 0xfff) & ~0xfff)
                    uc.mem_write(base + rva, payload)
                    native, finish = base + 0x100000, base + 0x100300
                    uc.mem_map(native, 0x1000)
                    uc.mem_write(native, b"\xc3")
                    uc.mem_write(native + 0x100, b"\xc3")
                    for target in (ASSIGN_RVA, GETTER_RVA, FIND_RVA):
                        uc.mem_map(base + (target & ~0xfff), 0x1000)
                        uc.mem_write(base + target, b"\xc3")
                    uc.mem_map(0x3000000, 0x10000)
                    uc.mem_map(0x4000000, 0x10000)
                    obj, vmt, out = 0x3001000, 0x3002000, 0x3003000
                    uc.mem_write(obj, struct.pack("<I", vmt))
                    uc.mem_write(vmt + 0xc, struct.pack("<I", native))
                    uc.mem_write(vmt + 0x54, struct.pack("<I", native + 0x100))

                    def put(pointer, text):
                        if text is None: return 0
                        raw = text.encode("gbk")
                        uc.mem_write(pointer - 8, struct.pack("<iI", 1, len(raw)) + raw + b"\0")
                        return pointer

                    def string(pointer):
                        if not pointer: return None
                        size = struct.unpack("<I", uc.mem_read(pointer - 4, 4))[0]
                        return bytes(uc.mem_read(pointer, size)).decode("gbk")

                    query = put(0x3004008, value) if lookup else native_index
                    caption = put(0x3005008, value) if not lookup else None
                    initial = {EAX: obj, EBX: 0x22334455, ECX: out if kind == "item" else 0x33445566,
                               EDX: query if kind in ("item", "indexof", "findtext") else out,
                               ESI: 0x44556677, EDI: 0x55667788, EBP: 0x4008000,
                               ESP: 0x4007000, FLAGS: 0x246}
                    uc.mem_write(initial[ESP], struct.pack("<I", finish))
                    for reg, number in initial.items(): uc.reg_write(reg, number)
                    nonvolatile = {reg: initial[reg] for reg in (EBX, ESI, EDI, EBP)}
                    if kind == "item": nonvolatile[{"ebx": EBX, "esi": ESI, "edi": EDI}[vmt_register]] = vmt
                    native_calls, assignments, returned = [], [], []
                    last_native = {}
                    rows = [a if old_items else b for a, b in values] + ["用户自定义会话"]

                    def hook(instance, address, size, user):
                        if address == finish:
                            returned.append(True)
                            instance.emu_stop()
                            return
                        if address == base + ASSIGN_RVA:
                            self.assertEqual(instance.reg_read(EAX), out)
                            translated_back = string(instance.reg_read(EDX))
                            assignments.append(translated_back)
                            self.assertEqual(bytes(instance.mem_read(instance.reg_read(EDX) - 8, 4)), b"\xff" * 4)
                            instance.mem_write(out, struct.pack("<I", instance.reg_read(EDX)))
                            return
                        if address not in (native, native + 0x100, base + GETTER_RVA, base + FIND_RVA): return
                        self.assertEqual(instance.reg_read(EAX), obj)
                        if kind == "item":
                            self.assertEqual(address, native)
                            self.assertEqual(instance.reg_read(EDX), native_index)
                            self.assertEqual(instance.reg_read(ECX), out)
                        elif kind == "text":
                            self.assertEqual(address, base + GETTER_RVA)
                            self.assertEqual(instance.reg_read(EDX), out)
                        elif kind == "indexof":
                            self.assertEqual(address, native + 0x100)
                            self.assertEqual(instance.reg_read(ECX), vmt)
                        else:
                            self.assertEqual(address, base + FIND_RVA)
                            self.assertEqual(instance.reg_read(ECX), initial[ECX])
                        native_calls.append(address)
                        if value == "native-index-error":
                            instance.emu_stop()
                            return
                        if lookup:
                            text = string(instance.reg_read(EDX))
                            result = next((i for i, x in enumerate(rows)
                                           if text is not None and x.lower() == text.lower()), -1) & 0xffffffff
                        else:
                            instance.mem_write(out, struct.pack("<I", caption or 0))
                            result = 0x11223344
                        last_native.update({EAX: result, EDX: 0x12345600 + len(native_calls),
                                            ECX: 0x23456700 + len(native_calls), FLAGS: 0x202})
                        for reg, number in last_native.items(): instance.reg_write(reg, number)

                    uc.hook_add(UC_HOOK_CODE, hook)
                    uc.emu_start(base + rva + entry, finish + 1, count=30000)
                    self.assertTrue(native_calls, (key, value))
                    if value == "native-index-error":
                        self.assertFalse(assignments)
                        self.assertFalse(returned)
                        continue
                    self.assertTrue(returned, (key, value))
                    self.assertEqual(uc.reg_read(ESP), initial[ESP] + 4)
                    for reg, number in nonvolatile.items(): self.assertEqual(uc.reg_read(reg), number)
                    self.assertEqual(uc.reg_read(FLAGS), last_native[FLAGS])
                    if lookup:
                        expected = next((i for i, x in enumerate(rows)
                                         if value is not None and x.lower() == value.lower()), -1)
                        if expected < 0 and value is not None:
                            target = next((b for a, b in changed if a.lower() == value.lower()), None)
                            if target is not None: expected = next(i for i, x in enumerate(rows) if x.lower() == target.lower())
                        self.assertEqual(uc.reg_read(EAX), expected & 0xffffffff, (key, value))
                        self.assertLessEqual(len(native_calls), 2)
                        if value is not None: self.assertEqual(string(query), value)
                        self.assertFalse(assignments)
                    else:
                        expected = next((a for a, b in changed if b == value), value)
                        if component in ITEM_LIMITS and native_index >= ITEM_LIMITS[component]: expected = value
                        self.assertEqual(string(struct.unpack("<I", uc.mem_read(out, 4))[0]), expected, (key, value))
                        self.assertEqual(len(native_calls), 1)
                        self.assertEqual(assignments, [expected] if expected != value else [])
                        if caption: self.assertEqual(string(caption), value)
                    if not assignments:
                        for reg in (EAX, EDX, ECX): self.assertEqual(uc.reg_read(reg), last_native[reg])
                    count += 1
        self.assertGreater(count, 600)
        print("Session adapter native-behavior cases:", count)

    def test_runtime_session_buttons_keep_native_setter_and_source_strings(self):
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
        from unicorn.x86_const import (UC_X86_REG_EAX as EAX, UC_X86_REG_EBX as EBX,
                                      UC_X86_REG_ECX as ECX, UC_X86_REG_EDX as EDX,
                                      UC_X86_REG_ESI as ESI, UC_X86_REG_EDI as EDI,
                                      UC_X86_REG_EBP as EBP, UC_X86_REG_ESP as ESP,
                                      UC_X86_REG_EFLAGS as FLAGS)
        spec = json.loads((REPO / "patches/26.6.0.5560/session-values.json").read_text(encoding="utf-8"))
        captions = [s for s in spec["sites"] if s["kind"] == "caption"]
        self.assertEqual(len(captions), 9)
        self.assertEqual({s["source_label"] for s in captions}, {"OK", "Cancel", "Save", "Close", "Create"})
        for base in (0x400000, 0x1400000):
            rva = 0x900000
            payload, _, entries = assemble(rva, spec["sites"])
            for control, values in (CAPTION_LABELS | SETTEXT_LABELS).items():
                kind = "caption" if control in CAPTION_LABELS else "settext"
                cases = [x for pair in values for x in pair] + ["Other button", "OK extra", "Cancel ", "", None]
                for text in cases:
                    uc = Uc(UC_ARCH_X86, UC_MODE_32)
                    uc.mem_map(base + rva, (len(payload) + 0xfff) & ~0xfff)
                    uc.mem_write(base + rva, payload)
                    uc.mem_map(base + (SETTER_RVA & ~0xfff), 0x1000)
                    uc.mem_map(0x3000000, 0x10000)
                    uc.mem_map(0x4000000, 0x10000)
                    pointer = 0
                    if text is not None:
                        pointer = 0x3001008
                        raw = text.encode("gbk")
                        uc.mem_write(pointer - 8, struct.pack("<iI", -1, len(raw)) + raw + b"\0")
                    initial = {EAX: 0x3004000, EBX: 0x22334455, ECX: 0x33445566,
                               ESI: 0x44556677, EDI: 0x55667788, EBP: 0x4008000,
                               ESP: 0x4007000, FLAGS: 0x246}
                    for reg, number in initial.items(): uc.reg_write(reg, number)
                    uc.reg_write(EDX, pointer)
                    reached = []
                    def hook(instance, address, size, user):
                        if address == base + SETTER_RVA:
                            reached.append(True)
                            instance.emu_stop()
                    uc.hook_add(UC_HOOK_CODE, hook)
                    uc.emu_start(base + rva + entries[(control, kind, "")], base + SETTER_RVA + 1, count=30000)
                    self.assertEqual(reached, [True])
                    for reg, number in initial.items(): self.assertEqual(uc.reg_read(reg), number)
                    actual = uc.reg_read(EDX)
                    translated = dict(values).get(text)
                    if translated:
                        raw = translated.encode("gbk")
                        self.assertEqual(bytes(uc.mem_read(actual - 8, 8)), struct.pack("<iI", -1, len(raw)))
                        self.assertEqual(bytes(uc.mem_read(actual, len(raw) + 1)), raw + b"\0")
                    else:
                        self.assertEqual(actual, pointer)
                    if pointer:
                        self.assertEqual(bytes(uc.mem_read(pointer, len(text.encode("gbk")) + 1)), text.encode("gbk") + b"\0")


if __name__ == "__main__":
    unittest.main()
