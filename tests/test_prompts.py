"""Execute prompt rendering and dialog wrappers without connecting or saving keys."""
from pathlib import Path
import json
import struct
import sys
import unittest

from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_PROT_READ, UC_PROT_EXEC
from unicorn.x86_const import (UC_X86_REG_EAX as EAX, UC_X86_REG_EBX as EBX,
                              UC_X86_REG_ECX as ECX, UC_X86_REG_EDX as EDX,
                              UC_X86_REG_ESI as ESI, UC_X86_REG_EDI as EDI,
                              UC_X86_REG_EBP as EBP, UC_X86_REG_ESP as ESP,
                              UC_X86_REG_EFLAGS as FLAGS)

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from mobaxterm_zh.prompts import (assemble, translate_bytes, variants, FORM_FIELDS, MAX_INPUT,
                                 NEW_STRING_RVA, CLEAR_STRING_RVA, GETTER_RVA, SETTER_RVA,
                                 LABEL_HELPER_RVA)


class Machine:
    def __init__(self, base, payload, rva=0x1100000, fail_alloc=False):
        self.base, self.rva, self.fail_alloc = base, rva, fail_alloc
        self.uc = Uc(UC_ARCH_X86, UC_MODE_32)
        self.uc.mem_map(base + rva, (len(payload) + 0xFFF) & ~0xFFF, UC_PROT_READ | UC_PROT_EXEC)
        self.uc.mem_write(base + rva, payload)
        for page in {target & ~0xFFF for target in (NEW_STRING_RVA, CLEAR_STRING_RVA, GETTER_RVA, SETTER_RVA, LABEL_HELPER_RVA)}:
            self.uc.mem_map(base + page, 0x1000)
        for target in (NEW_STRING_RVA, CLEAR_STRING_RVA, GETTER_RVA, SETTER_RVA, LABEL_HELPER_RVA):
            self.uc.mem_write(base + target, b"\xc3")
        self.uc.mem_map(0x3000000, 0x200000)
        self.uc.mem_map(0x4000000, 0x10000)
        self.uc.mem_map(base + 0x700000, 0x1000)
        self.finish, self.modal = base + 0x700000, base + 0x700100
        self.uc.mem_write(self.modal, b"\xc3")
        self.next, self.allocations, self.frees, self.native_calls = 0x3040008, set(), [], []
        self.states, self.modal_calls, self.set_calls = {}, [], []
        self.initial = {EAX: 0x3001000, EBX: 0x22334455, ECX: 0x33445566, EDX: 0x3002000,
                        ESI: 0x44556677, EDI: 0x55667788, EBP: 0x4008000, ESP: 0x4007000, FLAGS: 0x246}

    def put(self, pointer, value):
        if value is None:
            return 0
        self.uc.mem_write(pointer - 8, struct.pack("<iI", -1, len(value)) + value + b"\0")
        return pointer

    def allocate(self, value):
        pointer = self.next
        self.next += (len(value) + 19) & ~3
        self.uc.mem_write(pointer - 8, struct.pack("<iI", 1, len(value)) + value + b"\0")
        self.allocations.add(pointer)
        return pointer

    def read(self, pointer):
        if not pointer:
            return None
        n = struct.unpack("<I", self.uc.mem_read(pointer - 4, 4))[0]
        return bytes(self.uc.mem_read(pointer, n))

    def run(self, entry, args=None, on_modal=None, on_label=None):
        initial = self.initial | (args or {})
        for reg, value in initial.items():
            self.uc.reg_write(reg, value)
        self.uc.mem_write(initial[ESP], struct.pack("<I", self.finish))
        self.returned = False
        self.last_native = None

        def hook(uc, address, size, _):
            if address == self.finish:
                self.returned = True
                uc.emu_stop()
                return
            if address == self.base + NEW_STRING_RVA:
                n = uc.reg_read(EAX)
                value = 0 if self.fail_alloc else self.allocate(b"\0" * n)
                self.native_calls.append("allocate")
                uc.reg_write(EAX, value)
                uc.reg_write(ECX, 0x0A0B0C0D)
                uc.reg_write(EDX, 0x11224488)
                uc.reg_write(FLAGS, 0x202)
            elif address == self.base + CLEAR_STRING_RVA:
                at = uc.reg_read(EAX)
                pointer = struct.unpack("<I", uc.mem_read(at, 4))[0]
                if pointer in self.allocations:
                    self.allocations.remove(pointer)
                    self.frees.append(pointer)
                uc.mem_write(at, b"\0" * 4)
                uc.reg_write(EAX, 0xA1A2A3A4)
                uc.reg_write(ECX, 0xB1B2B3B4)
                uc.reg_write(EDX, 0xC1C2C3C4)
                uc.reg_write(FLAGS, 0x202)
            elif address == self.base + GETTER_RVA:
                control, out = uc.reg_read(EAX), uc.reg_read(EDX)
                if control not in self.states:
                    raise AssertionError("Read outside reviewed caption controls")
                value = self.states[control]
                pointer = 0 if value is None else self.allocate(value)
                uc.mem_write(out, struct.pack("<I", pointer))
                self.native_calls.append(("get_caption", control))
                uc.reg_write(EAX, 0x18181818)
                uc.reg_write(ECX, 0x28282828)
                uc.reg_write(EDX, 0x38383838)
                uc.reg_write(FLAGS, 0x202)
            elif address == self.base + SETTER_RVA:
                control = uc.reg_read(EAX)
                if control not in self.states:
                    raise AssertionError("Write outside reviewed caption controls")
                value = self.read(uc.reg_read(EDX))
                self.states[control] = value
                self.set_calls.append((control, value))
                uc.reg_write(EAX, 0x48484848)
                uc.reg_write(ECX, 0x58585858)
                uc.reg_write(EDX, 0x68686868)
                uc.reg_write(FLAGS, 0x202)
            elif address in (self.modal, self.base + LABEL_HELPER_RVA):
                callback = on_modal if address == self.modal else on_label
                if callback:
                    callback(self, initial)
                self.modal_calls.append(address)
                self.last_native = {EAX: getattr(self, "result", 3), EDX: 0x12345678, ECX: 0x23456789, FLAGS: 0x286}
                for reg, value in self.last_native.items():
                    uc.reg_write(reg, value)

        self.uc.hook_add(UC_HOOK_CODE, hook)
        self.uc.emu_start(self.base + self.rva + entry, self.finish + 1, count=2000000)
        if not self.returned:
            raise AssertionError("Prompt wrapper did not return")
        return initial


class PromptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        folder = REPO / "patches/26.6.0.5560"
        cls.catalog = json.loads((folder / "connection-prompts.json").read_text(encoding="utf-8"))
        cls.recipe = json.loads((folder / "prompt-sites.json").read_text(encoding="utf-8"))
        cls.payload, _, cls.entries, cls.renderers = assemble(0x1100000, cls.catalog, cls.recipe["sites"])

    def test_native_templates_preserve_variable_bytes_and_unknown_messages(self):
        cases = []
        for row in variants(self.catalog):
            captures = [("动态字段_" + str(i) + "_User@Host_SHA256:AbCd/+=").encode("gbk") + b"\x81\xff"
                        for i in range(len(row["source"]) - 1)]
            value = bytearray()
            for i, part in enumerate(row["source"]):
                value.extend(part)
                if i < len(captures):
                    value.extend(captures[i])
            cases.extend([(row["group"], bytes(value)), (row["group"], b"X" + bytes(value)),
                          (row["group"], bytes(value) + b"X")])
            if len(row["source"]) > 2:
                ambiguous = row["source"][0] + row["source"][1] + bytes(value)[len(row["source"][0]):]
                cases.append((row["group"], ambiguous))
        for group in self.renderers:
            cases.extend((group, x) for x in (None, b"", b"Unknown remote text", "已是中文".encode("gbk")))
        count = 0
        for base in (0x400000, 0x1400000):
            for group, value in cases:
                with self.subTest(base=base, group=group, size=None if value is None else len(value)):
                    machine = Machine(base, self.payload)
                    pointer = machine.put(0x3003008, value)
                    initial = machine.run(self.renderers[group], {EDX: pointer})
                    actual = machine.read(machine.uc.reg_read(EAX))
                    self.assertEqual(actual, translate_bytes(value, group, self.catalog))
                    for reg, old in initial.items():
                        if reg not in (EAX, ESP):
                            self.assertEqual(machine.uc.reg_read(reg), old)
                    self.assertEqual(machine.uc.reg_read(ESP), initial[ESP] + 4)
                    if pointer:
                        self.assertEqual(machine.read(pointer), value)
                    count += 1
            machine = Machine(base, self.payload)
            pointer = machine.put(0x3003008, b"x")
            machine.uc.mem_write(pointer - 4, struct.pack("<I", MAX_INPUT + 1))
            machine.run(self.renderers["body"], {EDX: pointer})
            self.assertEqual(machine.uc.reg_read(EAX), 0)
        print("Connection prompt render cases:", count)

    def test_modal_results_original_captions_and_message_keys_are_preserved(self):
        first = next(x for x in self.catalog["rules"] if x["id"] == "body_9dbc28")
        values = {"title": b"Connection to test.example:22", "body": first["source_parts"][0].replace("\r", "<br>").encode("ascii"),
                  "store": b"Do you want to update password for User@Host?", "button": b"Accept"}
        count = 0
        for base in (0x400000, 0x1400000):
            for kind, fields in FORM_FIELDS.items():
                for result in (0, 1, 2, 3, 4):
                    machine = Machine(base, self.payload)
                    machine.result = result
                    obj, vmt = 0x3001000, 0x3002000
                    machine.uc.mem_write(obj, struct.pack("<I", vmt))
                    machine.uc.mem_write(vmt + 0xEC, struct.pack("<I", machine.modal))
                    expected = {}
                    for i, (field, group) in enumerate(fields):
                        control = obj if not field else obj + 0x1000 + i * 0x100
                        if field:
                            machine.uc.mem_write(obj + field, struct.pack("<I", control))
                        text = values[group]
                        if group == "button":
                            text = (b"Accept", b"Cancel", b"More info...", b"OK")[i - 2]
                        machine.states[control] = text
                        expected[control] = (group, text)
                    original = dict(machine.states)
                    message_key = b"SuppressMessages|original-English-key|SSH_Hostkeys|StorePasswords=Ask"
                    machine.uc.mem_write(0x300E000, message_key)
                    sentinel = b"unread-password-edit-sentinel"
                    machine.uc.mem_write(0x300F000, sentinel)
                    def modal(m, initial):
                        self.assertEqual(m.uc.reg_read(EAX), obj)
                        self.assertEqual(m.uc.reg_read(EDX), vmt)
                        self.assertEqual(m.uc.reg_read(ECX), initial[ECX])
                        self.assertEqual(m.uc.reg_read(FLAGS), initial[FLAGS])
                        for control, (group, text) in expected.items():
                            translated = translate_bytes(text, group, self.catalog)
                            self.assertEqual(m.states[control], translated if translated is not None else text)
                        self.assertEqual(bytes(m.uc.mem_read(0x300E000, len(message_key))), message_key)
                    initial = machine.run(self.entries[kind], {EAX: obj}, on_modal=modal)
                    self.assertEqual(machine.modal_calls, [machine.modal])
                    self.assertEqual(machine.states, original)
                    self.assertFalse(machine.allocations)
                    self.assertEqual(bytes(machine.uc.mem_read(0x300F000, len(sentinel))), sentinel)
                    for reg, value in machine.last_native.items():
                        self.assertEqual(machine.uc.reg_read(reg), value)
                    for reg in (EBX, ESI, EDI, EBP):
                        self.assertEqual(machine.uc.reg_read(reg), initial[reg])
                    self.assertEqual(machine.uc.reg_read(ESP), initial[ESP] + 4)
                    count += 1
            for text in (b"Please enter your master password", b"Unknown server question", None):
                machine = Machine(base, self.payload)
                pointer = machine.put(0x3003008, text)
                def label(m, initial):
                    self.assertEqual(m.uc.reg_read(EAX), initial[EAX])
                    self.assertEqual(m.uc.reg_read(EDX), initial[EDX])
                    translated = translate_bytes(text, "body", self.catalog)
                    self.assertEqual(m.read(m.uc.reg_read(ECX)), translated if translated is not None else text)
                    self.assertEqual(m.uc.reg_read(FLAGS), initial[FLAGS])
                initial = machine.run(self.entries["input_label"], {ECX: pointer}, on_label=label)
                self.assertEqual(machine.modal_calls, [base + LABEL_HELPER_RVA])
                self.assertFalse(machine.allocations)
                if pointer:
                    self.assertEqual(machine.read(pointer), text)
                for reg, value in machine.last_native.items():
                    self.assertEqual(machine.uc.reg_read(reg), value)
                count += 1
        print("Connection prompt lifecycle cases:", count)

    def test_password_requirements_loss_warning_and_fingerprint_fields_remain_explicit(self):
        folder = REPO / "patches/26.6.0.5560"
        literals = json.loads((folder / "literals.json").read_text(encoding="utf-8"))
        errors = [x for x in literals["literals"] if x.get("purpose") == "native_master_password_error"]
        self.assertEqual(len(errors), 7)
        for row in errors:
            self.assertEqual(row["storage"], "pansichar")
            self.assertEqual(len(row["references"]), 1)
            self.assertEqual(row["english"].count("\r"), row["chinese"].count("\r"))
            for n in (12, 8, 7):
                if "at least " + str(n) + " characters" in row["english"]:
                    self.assertIn(str(n) + " 个字符", row["chinese"])
                    if n != 7:
                        self.assertTrue(all(x in row["chinese"] for x in ("小写字母", "大写字母", "数字", "符号", "至少三类")))
            if "LAST WARNING" in row["english"]:
                self.assertIn("忘记主密码", row["chinese"])
                self.assertIn("丢失所有已保存的密码", row["chinese"])
            if "resetmasterpassword.html" in row["english"]:
                self.assertIn("https://mobaxterm.mobatek.net/resetmasterpassword.html", row["chinese"])
                self.assertIn("丢失此前保存的所有密码", row["chinese"])
        forms = json.loads((folder / "forms.json").read_text(encoding="utf-8"))
        fingerprint = next(x for x in forms["forms"] if x["name"] == "TFORMHKFINGERPRINTDIALOG")
        self.assertTrue(all(x["property"] == "Caption" or x["property"] == "BoundLabel.Caption" for x in fingerprint["patches"]))
        sources = {x["id"]: x for x in self.catalog["rules"]}
        self.assertIn("首次连接", sources["body_9dbc28"]["target_parts"][0])
        self.assertIn("身份已变更", sources["body_9dbd34"]["target_parts"][0])
        self.assertIn("冒充", sources["body_9dbd34"]["target_parts"][0])
        # The specific credential wording must win over the general password prefix.
        for base in (0x400000, 0x1400000):
            for group in ("body", "store"):
                for action, chinese in (("save", "保存"), ("update", "更新")):
                    machine = Machine(base, self.payload)
                    text = ("Do you want to " + action + " password for credential User@Host?").encode("ascii")
                    pointer = machine.put(0x3003008, text)
                    machine.run(self.renderers[group], {EDX: pointer})
                    self.assertEqual(machine.read(machine.uc.reg_read(EAX)),
                                     ("是否" + chinese + "凭据 User@Host 的密码？").encode("gbk"))


if __name__ == "__main__":
    unittest.main()
