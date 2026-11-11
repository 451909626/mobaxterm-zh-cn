"""Settings localization must preserve native option order and on-disk values."""
from pathlib import Path
import struct
import sys
import unittest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from mobaxterm_zh.patcher import load_spec, permitted
from mobaxterm_zh.settings import (ASSIGN_RVA, CANONICAL, COMBO_LABELS, DISPLAY,
                                  MISC, X11, assemble)


class SettingsTests(unittest.TestCase):
    def test_only_reviewed_display_pairs_are_allowed(self):
        version, forms, _ = load_spec(REPO, "26.6.0.5560")
        self.assertEqual(version["settings_combo_controls"], len(COMBO_LABELS))
        form = next(x for x in forms["forms"] if x["name"] == "TFORMPARAMS")
        actual = [x for x in form["patches"] if x["component"] in COMBO_LABELS
                  and x["property"] in ("Text", "Items.Strings[]")]
        for component, pairs in COMBO_LABELS.items():
            expected = [target for source, target in pairs if source != target]
            items = [x["target"] for x in sorted(actual, key=lambda x: x["index"])
                     if x["component"] == component and x["property"] == "Items.Strings[]"]
            self.assertEqual(items, expected, component)
        value = {"component": DISPLAY + "sRadioGroup2", "property": "Text",
                 "type": 6, "value": "Buttons with captions"}
        self.assertTrue(permitted("TFORMPARAMS", value, "带文字的按钮"))
        for prop, source, target in [("ItemIndex", 2, 0), ("Text", "Buttons with captions", "任意替换"),
                                     ("OnChange", "Handler", "替换"), ("HelpKeyword", "Session", "会话")]:
            value.update(property=prop, value=source)
            self.assertFalse(permitted("TFORMPARAMS", value, target))
        value.update(component=X11 + "sComboBox5", property="Items.Strings[]", value="us")
        self.assertFalse(permitted("TFORMPARAMS", value, "美国"))
        self.assertNotIn(DISPLAY + "ComboSkins", COMBO_LABELS)
        self.assertEqual(dict(COMBO_LABELS[X11 + "ComboAccessControl"]),
                         {"on-demand": "按需询问", "full": "允许所有远程访问", "disabled": "禁用远程访问"})
        self.assertEqual(CANONICAL["home"], tuple(x[0] for x in COMBO_LABELS[MISC + "sGroupBox1.sComboEdit1"]))
        self.assertEqual(CANONICAL["new_tab"], tuple(x[0] for x in COMBO_LABELS[MISC + "sGroupBox1.sComboEdit2"]))
        self.assertEqual(CANONICAL["dpi"], tuple(x[0] for x in COMBO_LABELS[X11 + "sComboBox4"]))

    def test_canonical_load_save_and_custom_fallback_at_two_bases(self):
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
        from unicorn.x86_const import (UC_X86_REG_EAX as EAX, UC_X86_REG_EBX as EBX,
                                      UC_X86_REG_ECX as ECX, UC_X86_REG_EDX as EDX,
                                      UC_X86_REG_ESI as ESI, UC_X86_REG_EDI as EDI,
                                      UC_X86_REG_EBP as EBP, UC_X86_REG_ESP as ESP,
                                      UC_X86_REG_EFLAGS as FLAGS)
        count = 0
        for base in (0x400000, 0x1400000):
            rva = 0x900000
            payload, _, entries = assemble(rva)
            for name, canonical in CANONICAL.items():
                component = {"home": MISC + "sGroupBox1.sComboEdit1",
                             "new_tab": MISC + "sGroupBox1.sComboEdit2",
                             "dpi": X11 + "sComboBox4"}[name]
                localized = [x[1] for x in COMBO_LABELS[component]] + ["用户自定义会话"]
                load_cases = list(canonical) + [x.upper() for x in canonical] + list(localized)
                load_cases += [None, "", "<Home> extra", "auto-extra", "CustomSession", "主页"]
                save_cases = list(range(len(localized))) + [-1, 99]
                for mode, cases in (("load", load_cases), ("save", save_cases)):
                    for value in cases:
                        uc = Uc(UC_ARCH_X86, UC_MODE_32)
                        uc.mem_map(base + rva, 0x3000)
                        uc.mem_write(base + rva, payload)
                        native, finish = base + 0x100000, base + 0x100200
                        uc.mem_map(native, 0x1000)
                        uc.mem_write(native, b"\xc3")
                        uc.mem_write(native + 0x100, b"\xc3")
                        uc.mem_map(base + (ASSIGN_RVA & ~0xfff), 0x1000)
                        uc.mem_write(base + ASSIGN_RVA, b"\xc3")
                        uc.mem_map(0x3000000, 0x10000)
                        uc.mem_map(0x4000000, 0x10000)
                        items, vmt, out = 0x3001000, 0x3002000, 0x3003000
                        uc.mem_write(items, struct.pack("<I", vmt))
                        uc.mem_write(vmt + 0x54, struct.pack("<I", native))
                        uc.mem_write(vmt + 0xc, struct.pack("<I", native + 0x100))
                        def string_at(pointer, text):
                            raw = text.encode("gbk")
                            uc.mem_write(pointer - 8, struct.pack("<iI", -1, len(raw)) + raw + b"\0")
                            return pointer
                        pointer = (0 if value is None else string_at(0x3004008, value)) if mode == "load" else value & 0xffffffff
                        initial = {EAX: items, EBX: 0x22334455, ECX: out, EDX: pointer,
                                   ESI: 0x44556677, EDI: 0x55667788, EBP: 0x4008000,
                                   ESP: 0x4007000, FLAGS: 0x246}
                        uc.mem_write(initial[ESP], struct.pack("<I", finish))
                        for reg, number in initial.items(): uc.reg_write(reg, number)
                        reached = []
                        saved = []
                        def hook(instance, address, size, user):
                            if address == finish:
                                reached.append("returned")
                                instance.emu_stop()
                                return
                            if address not in (native, native + 0x100, base + ASSIGN_RVA): return
                            self.assertEqual(instance.reg_read(ESP), initial[ESP])
                            for reg in (EBX, EDI, EBP, FLAGS):
                                self.assertEqual(instance.reg_read(reg), initial[reg])
                            if mode == "load":
                                self.assertEqual(address, native)
                                self.assertEqual(instance.reg_read(EAX), items)
                                self.assertEqual(instance.reg_read(EDX), pointer)
                                self.assertEqual(instance.reg_read(ECX), vmt)
                                found = next((i for i, label in enumerate(localized)
                                              if isinstance(value, str) and label.lower() == value.lower()), -1)
                                instance.reg_write(EAX, found & 0xffffffff)
                                reached.append("native_index")
                            elif address == native + 0x100:
                                self.assertEqual(instance.reg_read(EAX), items)
                                self.assertEqual(instance.reg_read(EDX), pointer)
                                self.assertEqual(instance.reg_read(ECX), out)
                                self.assertEqual(instance.reg_read(ESI), vmt)
                                reached.append("native_item")
                            else:
                                self.assertEqual(instance.reg_read(EAX), out)
                                self.assertEqual(instance.reg_read(ECX), out)
                                self.assertEqual(instance.reg_read(ESI), vmt)
                                text_pointer = instance.reg_read(EDX)
                                length = struct.unpack("<I", instance.mem_read(text_pointer - 4, 4))[0]
                                saved.append(bytes(instance.mem_read(text_pointer, length)).decode("ascii"))
                                self.assertEqual(bytes(instance.mem_read(text_pointer - 8, 4)), b"\xff" * 4)
                                reached.append("canonical_item")
                        uc.hook_add(UC_HOOK_CODE, hook)
                        uc.emu_start(base + rva + entries[name + "_" + mode], finish + 1, count=10000)
                        self.assertEqual(reached[-1:], ["returned"], (base, name, mode, value))
                        self.assertEqual(uc.reg_read(ESP), initial[ESP] + 4)
                        for reg in (EBX, EDI, EBP, FLAGS): self.assertEqual(uc.reg_read(reg), initial[reg])
                        if mode == "load":
                            known = next((i for i, text in enumerate(canonical)
                                          if isinstance(value, str) and text.lower() == value.lower()), None)
                            if known is not None:
                                self.assertEqual(reached, ["returned"])
                                self.assertEqual(uc.reg_read(EAX), known)
                            else:
                                self.assertIn("native_index", reached)
                            self.assertEqual(uc.reg_read(EDX), initial[EDX])
                            self.assertEqual(uc.reg_read(ESI), initial[ESI])
                            self.assertEqual(uc.reg_read(ECX), vmt)
                            if value is not None:
                                self.assertEqual(bytes(uc.mem_read(pointer, len(value.encode("gbk")))), value.encode("gbk"))
                        elif 0 <= value < len(canonical):
                            self.assertEqual(saved, [canonical[value]])
                            self.assertEqual(reached, ["canonical_item", "returned"])
                        else:
                            self.assertEqual(reached, ["native_item", "returned"])
                        count += 1
        self.assertGreaterEqual(count, 100)


if __name__ == "__main__":
    unittest.main()
