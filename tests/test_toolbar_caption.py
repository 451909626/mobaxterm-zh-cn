"""Execute caption and layout adapters under x86 emulation at two load bases."""
from pathlib import Path
import struct
import sys
import unittest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from mobaxterm_zh.toolbar import (LABELS, SETTER_RVA, GETTER_RVA, ASSIGN_RVA, assemble)


def emulate():
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP, UC_X86_REG_ESP, UC_X86_REG_EFLAGS
    cases = list(LABELS) + ["Unknown custom button", "Session-extra", "session", "Games ", "", None]
    checked = 0
    for base in (0x400000, 0x1400000):
        rva, setter = 0x900000, SETTER_RVA
        payload, _, getter_entry = assemble(rva, setter)
        for text in cases:
            uc = Uc(UC_ARCH_X86, UC_MODE_32)
            uc.mem_map(base + rva, 0x2000)
            uc.mem_write(base + rva, payload)
            uc.mem_map(base + (setter & ~0xFFF), 0x2000)
            uc.mem_map(0x3000000, 0x10000)
            uc.mem_map(0x4000000, 0x10000)
            pointer = 0 if text is None else 0x3001008
            if text is not None:
                raw = text.encode("ascii")
                uc.mem_write(pointer - 8, struct.pack("<iI", -1, len(raw)) + raw + b"\0")
            initial = {UC_X86_REG_EAX: 0x12345678, UC_X86_REG_EBX: 0x22334455,
                       UC_X86_REG_ECX: 0x33445566, UC_X86_REG_ESI: 0x44556677,
                       UC_X86_REG_EDI: 0x55667788, UC_X86_REG_EBP: 0x4008000,
                       UC_X86_REG_ESP: 0x4007000, UC_X86_REG_EFLAGS: 0x246}
            for register, value in initial.items(): uc.reg_write(register, value)
            uc.reg_write(UC_X86_REG_EDX, pointer)
            reached = []
            def stop_at_setter(instance, address, size, user):
                if address == base + setter:
                    reached.append(True)
                    instance.emu_stop()
            uc.hook_add(UC_HOOK_CODE, stop_at_setter)
            uc.emu_start(base + rva, base + setter + 1, count=10000)
            if not reached: raise AssertionError("The original setter was not reached")
            for register, value in initial.items():
                if uc.reg_read(register) != value: raise AssertionError("Register/stack/flags changed")
            actual = uc.reg_read(UC_X86_REG_EDX)
            if text in LABELS:
                raw = LABELS[text].encode("gbk")
                if bytes(uc.mem_read(actual, len(raw) + 1)) != raw + b"\0": raise AssertionError("Wrong display caption")
                if bytes(uc.mem_read(actual - 8, 8)) != struct.pack("<iI", -1, len(raw)): raise AssertionError("Invalid AnsiString header")
            elif actual != pointer:
                raise AssertionError("An unknown/empty caption was changed")
            if text is not None and bytes(uc.mem_read(pointer, len(text) + 1)) != text.encode() + b"\0":
                raise AssertionError("The original identifier was modified")
            checked += 1
        for text in cases:
            uc = Uc(UC_ARCH_X86, UC_MODE_32)
            uc.mem_map(base + rva, 0x2000)
            uc.mem_write(base + rva, payload)
            for target in (GETTER_RVA, ASSIGN_RVA):
                uc.mem_map(base + (target & ~0xFFF), 0x1000)
            uc.mem_map(0x3000000, 0x10000)
            uc.mem_map(0x4000000, 0x10000)
            pointer = 0 if text is None else 0x3001008
            if text is not None:
                raw = text.encode("ascii")
                uc.mem_write(pointer - 8, struct.pack("<iI", -1, len(raw)) + raw + b"\0")
            control, destination = 0x3003000, 0x3006000
            uc.mem_write(control + 0x154, struct.pack("<I", pointer))
            initial = {UC_X86_REG_EBX: 0x22334455, UC_X86_REG_ECX: 0x33445566,
                       UC_X86_REG_ESI: 0x44556677, UC_X86_REG_EDI: 0x55667788,
                       UC_X86_REG_EBP: 0x4008000, UC_X86_REG_ESP: 0x4007000,
                       UC_X86_REG_EFLAGS: 0x246}
            for register, value in initial.items(): uc.reg_write(register, value)
            uc.reg_write(UC_X86_REG_EAX, control)
            uc.reg_write(UC_X86_REG_EDX, destination)
            reached = []
            def stop_at_getter(instance, address, size, user):
                if address in (base + GETTER_RVA, base + ASSIGN_RVA):
                    reached.append(address)
                    instance.emu_stop()
            uc.hook_add(UC_HOOK_CODE, stop_at_getter)
            uc.emu_start(base + rva + getter_entry, base + ASSIGN_RVA + 1, count=10000)
            if not reached: raise AssertionError("The original string operation was not reached")
            for register, value in initial.items():
                if uc.reg_read(register) != value: raise AssertionError("Getter register/stack/flags changed")
            if text in LABELS:
                if reached != [base + ASSIGN_RVA] or uc.reg_read(UC_X86_REG_EAX) != destination or uc.reg_read(UC_X86_REG_EDX) != pointer:
                    raise AssertionError("The layout did not receive the original English identifier")
            elif reached != [base + GETTER_RVA] or uc.reg_read(UC_X86_REG_EAX) != control or uc.reg_read(UC_X86_REG_EDX) != destination:
                raise AssertionError("The custom caption getter was not preserved")
            if bytes(uc.mem_read(control + 0x154, 4)) != struct.pack("<I", pointer):
                raise AssertionError("The control identifier field was changed")
            checked += 1
    return checked


class ToolbarCaptionTests(unittest.TestCase):
    def test_display_and_layout_keep_registers_stack_flags_and_english_keys(self):
        self.assertEqual(emulate(), 80)


if __name__ == "__main__":
    unittest.main()
