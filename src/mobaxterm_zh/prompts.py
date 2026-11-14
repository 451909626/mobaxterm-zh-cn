"""Render reviewed connection prompts without changing native message identities.

Modal captions are translated after native layout/key generation, then restored
after the original modal call. Templates copy variable bytes without decoding.
Unknown or ambiguous messages retain native text and native results.
"""
import struct

import pefile

from .toolbar import align

GETTER_RVA = 0x893FC
SETTER_RVA = 0x8942C
NEW_STRING_RVA = 0x519C
CLEAR_STRING_RVA = 0x50D8
LABEL_HELPER_RVA = 0x64D1A8
MAX_INPUT = 1024 * 1024
GROUPS = ("title", "body", "store", "button")
FORM_FIELDS = {
    "message": ((0, "title"), (0x2FC, "body"), (0x2F8, "button"),
                (0x300, "button"), (0x308, "button"), (0x30C, "button")),
    "store": ((0x304, "store"),),
}


def variants(spec):
    result, seen = [], set()
    for row in spec["rules"]:
        source, target = row["source_parts"], row["target_parts"]
        if row["group"] not in GROUPS or not 1 <= len(source) <= 16 or len(source) != len(target) or not source[0]:
            raise ValueError("Unreviewed connection prompt template")
        if any(not value for value in source[1:-1]):
            raise ValueError("Empty interior connection prompt delimiter")
        for mode in ("plain", "html"):
            a = [x.replace("\r", "<br>") if mode == "html" else x for x in source]
            b = [x.replace("\r", "<br>") if mode == "html" else x for x in target]
            key = (row["group"], tuple(a))
            if key in seen:
                continue
            seen.add(key)
            result.append(dict(id=row["id"], group=row["group"],
                               source=[x.encode("ascii") for x in a], target=[x.encode("gbk") for x in b]))
    return result


def translate_bytes(value, group, spec):
    """Reference semantics used to exercise the generated native renderer."""
    if value is None or not value or len(value) > MAX_INPUT:
        return None
    for row in variants(spec):
        if row["group"] != group:
            continue
        parts = row["source"]
        if len(parts) == 1:
            if value == parts[0]:
                return row["target"][0]
            continue
        if len(value) < sum(map(len, parts)) or not value.startswith(parts[0]) or not value.endswith(parts[-1]):
            continue
        position, end, captures = len(parts[0]), len(value) - len(parts[-1]), []
        valid = True
        for part in parts[1:-1]:
            at = value.find(part, position, end)
            if at < 0 or value.find(part, at + 1, end) >= 0:
                valid = False
                break
            captures.append(value[position:at])
            position = at + len(part)
        if not valid or position > end:
            continue
        captures.append(value[position:end])
        result = bytearray()
        for i, part in enumerate(row["target"]):
            result.extend(part)
            if i < len(captures):
                result.extend(captures[i])
        return bytes(result)
    return None


class Assembler:
    def __init__(self, rva):
        self.rva, self.code = rva, bytearray()
        self.labels, self.branches, self.strings = {}, [], []

    def emit(self, raw):
        self.code.extend(bytes.fromhex(raw) if isinstance(raw, str) else raw)

    def mark(self, name):
        self.labels[name] = len(self.code)

    def jump(self, op, name):
        self.emit(op)
        self.branches.append((len(self.code), name))
        self.emit(b"\0" * 4)

    def native(self, op, rva):
        self.emit(op + struct.pack("<i", rva - self.rva - len(self.code) - 5))

    def pic(self):
        self.emit("e8000000005b")
        return len(self.code) - 1

    def address(self, register, raw, anchor):
        self.emit({"eax": "8d83", "edx": "8d93", "esi": "8db3", "edi": "8dbb"}[register])
        self.strings.append((len(self.code), raw, anchor))
        self.emit(b"\0" * 4)

    def load(self, register, offset):
        self.emit({"eax": "8b8424", "ecx": "8b8c24", "edx": "8b9424", "esi": "8bb424", "edi": "8bbc24"}[register])
        self.emit(struct.pack("<I", offset))

    def save(self, register, offset):
        self.emit({"eax": "898424", "ecx": "898c24", "edx": "899424", "edi": "89bc24"}[register])
        self.emit(struct.pack("<I", offset))

    def constant(self, offset, value):
        self.emit("c78424")
        self.emit(struct.pack("<II", offset, value))

    def lea(self, register, offset):
        self.emit({"eax": "8d8424", "edx": "8d9424"}[register])
        self.emit(struct.pack("<I", offset))

    def finish(self):
        code_size, stored = len(self.code), {}
        for at, raw, anchor in self.strings:
            if raw not in stored:
                while len(self.code) % 4:
                    self.emit("00")
                self.emit(struct.pack("<iI", -1, len(raw)))
                stored[raw] = len(self.code)
                self.emit(raw + b"\0")
            struct.pack_into("<i", self.code, at, stored[raw] - anchor)
        for at, name in self.branches:
            struct.pack_into("<i", self.code, at, self.labels[name] - at - 4)
        return bytes(self.code), code_size


def assemble(rva, catalog, sites):
    a, renderers, entries = Assembler(rva), {}, {}
    local = 192
    for group in GROUPS:
        renderers[group] = len(a.code)
        a.emit("9c6081ec" + struct.pack("<I", local).hex())
        anchor = a.pic()
        a.emit("fc")
        a.load("edx", local + 20)
        a.save("edx", 4)
        a.emit("85d2")
        a.jump("0f84", group + "_miss")
        a.emit("8b42fc")
        a.save("eax", 8)
        a.emit("85c0")
        a.jump("0f84", group + "_miss")
        a.emit(b"\x3d" + struct.pack("<I", MAX_INPUT))
        a.jump("0f87", group + "_miss")
        for number, row in enumerate(x for x in variants(catalog) if x["group"] == group):
            prefix = group + "_" + str(number)
            next_rule = prefix + "_next"
            parts, targets = row["source"], row["target"]
            a.load("eax", 8)
            a.emit(b"\x3d" + struct.pack("<I", sum(map(len, parts))))
            a.jump("0f85" if len(parts) == 1 else "0f82", next_rule)
            a.load("esi", 4)
            a.address("edi", parts[0], anchor)
            a.emit(b"\xb9" + struct.pack("<I", len(parts[0])) + b"\xf3\xa6")
            a.jump("0f85", next_rule)
            if len(parts) == 1:
                a.address("eax", targets[0], anchor)
                a.jump("e9", group + "_return")
                a.mark(next_rule)
                continue
            if parts[-1]:
                a.load("esi", 4)
                a.load("eax", 8)
                a.emit(b"\x2d" + struct.pack("<I", len(parts[-1])) + b"\x01\xc6")
                a.address("edi", parts[-1], anchor)
                a.emit(b"\xb9" + struct.pack("<I", len(parts[-1])) + b"\xf3\xa6")
                a.jump("0f85", next_rule)
            a.constant(12, len(parts[0]))
            for index, part in enumerate(parts[1:-1]):
                loop, scan_next, found = (prefix + "_scan_" + str(index), prefix + "_advance_" + str(index), prefix + "_found_" + str(index))
                a.load("eax", 8)
                a.emit(b"\x2d" + struct.pack("<I", len(parts[-1]) + len(part)))
                a.save("eax", 28)
                a.load("eax", 12)
                a.save("eax", 24)
                a.constant(20, 0)
                a.mark(loop)
                a.load("eax", 24)
                a.emit("3b8424" + struct.pack("<I", 28).hex())
                a.jump("0f87", found)
                a.load("esi", 4)
                a.emit("01c6")
                a.address("edi", part, anchor)
                a.emit(b"\xb9" + struct.pack("<I", len(part)) + b"\xf3\xa6")
                a.jump("0f85", scan_next)
                a.emit("ff8424" + struct.pack("<I", 20).hex())
                a.emit("83bc24" + struct.pack("<I", 20).hex() + "01")
                a.jump("0f87", next_rule)
                a.load("eax", 24)
                a.save("eax", 16)
                a.mark(scan_next)
                a.emit("ff8424" + struct.pack("<I", 24).hex())
                a.jump("e9", loop)
                a.mark(found)
                a.emit("83bc24" + struct.pack("<I", 20).hex() + "01")
                a.jump("0f85", next_rule)
                a.load("eax", 12)
                a.save("eax", 32 + index * 8)
                a.load("edx", 16)
                a.emit("29c2")
                a.save("edx", 36 + index * 8)
                a.load("eax", 16)
                a.emit(b"\x05" + struct.pack("<I", len(part)))
                a.save("eax", 12)
            last = len(parts) - 2
            a.load("eax", 12)
            a.save("eax", 32 + last * 8)
            a.load("edx", 8)
            a.emit(b"\x81\xea" + struct.pack("<I", len(parts[-1])) + b"\x29\xc2")
            a.jump("0f82", next_rule)
            a.save("edx", 36 + last * 8)
            a.emit(b"\xb8" + struct.pack("<I", sum(map(len, targets))))
            for index in range(len(parts) - 1):
                a.emit("038424" + struct.pack("<I", 36 + index * 8).hex())
            a.native(b"\xe8", NEW_STRING_RVA)
            a.emit("85c0")
            a.jump("0f84", group + "_miss")
            a.save("eax", 0)
            a.emit("8bf8")
            for index, part in enumerate(targets):
                if part:
                    a.address("esi", part, anchor)
                    a.emit(b"\xb9" + struct.pack("<I", len(part)) + b"\xf3\xa4")
                if index < len(parts) - 1:
                    a.load("esi", 4)
                    a.emit("03b424" + struct.pack("<I", 32 + index * 8).hex())
                    a.load("ecx", 36 + index * 8)
                    a.emit("f3a4")
            a.emit("c60700")
            a.load("eax", 0)
            a.jump("e9", group + "_return")
            a.mark(next_rule)
        a.mark(group + "_miss")
        a.emit("33c0")
        a.mark(group + "_return")
        a.save("eax", local + 28)
        a.emit("81c4" + struct.pack("<I", local).hex() + "619dc3")

    def capture_return(size):
        a.save("eax", size + 28)
        a.save("edx", size + 20)
        a.save("ecx", size + 24)
        a.emit("9c58")
        a.save("eax", size + 32)

    def restore_flags(size):
        a.emit("ffb424" + struct.pack("<I", size + 32).hex() + "9d")

    for site in sites:
        kind = site["kind"]
        if kind in entries:
            continue
        entries[kind] = len(a.code)
        size = 80
        if kind == "input_label":
            a.emit("9c6083ec50")
            a.constant(0, 0)
            a.load("edx", size + 24)
            a.native(b"\xe8", rva + renderers["body"])
            a.save("eax", 0)
            a.emit("85c0")
            a.jump("0f84", "input_unchanged")
            a.load("ecx", 0)
            a.load("eax", size + 28)
            a.load("edx", size + 20)
            restore_flags(size)
            a.native(b"\xe8", LABEL_HELPER_RVA)
            capture_return(size)
            a.lea("eax", 0)
            a.native(b"\xe8", CLEAR_STRING_RVA)
            a.emit("83c450619dc3")
            a.mark("input_unchanged")
            a.emit("83c450619d")
            a.native(b"\xe9", LABEL_HELPER_RVA)
            continue
        if kind not in FORM_FIELDS:
            raise ValueError("Unknown prompt form")
        fields = FORM_FIELDS[kind]
        a.emit("8b109c6083ec50")  # original VMT load, then save the native call state
        a.load("eax", size + 28)
        a.save("eax", 0)
        a.emit("8b82ec000000")
        a.save("eax", 4)
        for index, (field, group) in enumerate(fields):
            slot = 16 + index * 8
            a.constant(slot, 0)
            a.constant(slot + 4, 0)
            a.load("eax", 0)
            if field:
                a.emit(b"\x8b\x80" + struct.pack("<I", field))
            a.lea("edx", slot)
            a.native(b"\xe8", GETTER_RVA)
            a.load("edx", slot)
            a.native(b"\xe8", rva + renderers[group])
            a.save("eax", slot + 4)
            a.emit("85c0")
            a.jump("0f84", kind + "_field_" + str(index))
            a.load("edx", slot + 4)
            a.load("eax", 0)
            if field:
                a.emit(b"\x8b\x80" + struct.pack("<I", field))
            a.native(b"\xe8", SETTER_RVA)
            a.mark(kind + "_field_" + str(index))
        a.load("eax", size + 28)
        a.load("edx", size + 20)
        a.load("ecx", size + 24)
        restore_flags(size)
        a.emit("ff542404")
        capture_return(size)
        for index, (field, group) in enumerate(fields):
            slot = 16 + index * 8
            a.load("eax", slot + 4)
            a.emit("85c0")
            a.jump("0f84", kind + "_restore_" + str(index))
            a.load("edx", slot)
            a.load("eax", 0)
            if field:
                a.emit(b"\x8b\x80" + struct.pack("<I", field))
            a.native(b"\xe8", SETTER_RVA)
            a.mark(kind + "_restore_" + str(index))
            for clear in (slot, slot + 4):
                a.lea("eax", clear)
                a.native(b"\xe8", CLEAR_STRING_RVA)
        a.emit("83c450619dc3")
    payload, code_size = a.finish()
    return payload, code_size, entries, renderers


def patch(data, catalog, recipe):
    pe = pefile.PE(data=data)
    if catalog["upstream_version"] != "26.6.0.5560" or recipe["upstream_version"] != catalog["upstream_version"] or pe.FILE_HEADER.Machine != 0x14C:
        raise ValueError("No reviewed connection prompt adapter for this executable")
    sites, seen = recipe["sites"], set()
    for site in sites:
        at = pe.get_offset_from_rva(site["rva"])
        before, context = bytes.fromhex(site["before_hex"]), bytes.fromhex(site["context_before_hex"])
        if site["rva"] in seen or data[at:at + len(before)] != before or data[at - len(context):at] != context:
            raise ValueError("Connection prompt call or argument provenance differs")
        seen.add(site["rva"])
        expected = (b"\xe8" + struct.pack("<i", LABEL_HELPER_RVA - site["rva"] - 5)
                    if site["kind"] == "input_label" else bytes.fromhex("8b10ff92ec000000"))
        if before != expected or site["kind"] not in (*FORM_FIELDS, "input_label"):
            raise ValueError("Unreviewed connection prompt entry")
    header = pe.sections[-1].get_file_offset() + 40
    if header + 40 > min(s.PointerToRawData for s in pe.sections if s.SizeOfRawData):
        raise ValueError("No room for the reviewed prompt adapter")
    rva = align(max(s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData) for s in pe.sections), pe.OPTIONAL_HEADER.SectionAlignment)
    payload, code_size, entries, _ = assemble(rva, catalog, sites)
    raw_at = align(len(data), pe.OPTIONAL_HEADER.FileAlignment)
    raw_size = align(len(payload), pe.OPTIONAL_HEADER.FileAlignment)
    out = bytearray(data.ljust(raw_at, b"\0"))
    out.extend(payload.ljust(raw_size, b"\0"))
    out[header:header + 40] = struct.pack("<8sIIIIIIHHI", b".zhpr\0\0\0", len(payload), rva, raw_size, raw_at, 0, 0, 0, 0, 0x60000020)
    struct.pack_into("<H", out, pe.FILE_HEADER.get_field_absolute_offset("NumberOfSections"), len(pe.sections) + 1)
    struct.pack_into("<I", out, pe.OPTIONAL_HEADER.get_field_absolute_offset("SizeOfImage"), align(rva + len(payload), pe.OPTIONAL_HEADER.SectionAlignment))
    struct.pack_into("<I", out, pe.OPTIONAL_HEADER.get_field_absolute_offset("SizeOfCode"), pe.OPTIONAL_HEADER.SizeOfCode + raw_size)
    changes = {}
    for site in sites:
        at = pe.get_offset_from_rva(site["rva"])
        before = bytes.fromhex(site["before_hex"])
        value = b"\xe8" + struct.pack("<i", rva + entries[site["kind"]] - site["rva"] - 5) + b"\x90" * (len(before) - 5)
        out[at:at + len(before)] = value
        changes[site["rva"]] = value
    result = pefile.PE(data=out)
    struct.pack_into("<I", out, result.OPTIONAL_HEADER.get_field_absolute_offset("CheckSum"), result.generate_checksum())
    result = pefile.PE(data=out)
    if not result.verify_checksum():
        raise ValueError("Invalid prompt adapter checksum")
    for old, new in zip(pe.sections, result.sections):
        expected = bytearray(old.get_data())
        if old.Name.rstrip(b"\0") == b"CODE":
            for call, value in changes.items():
                expected[call - old.VirtualAddress:call - old.VirtualAddress + len(value)] = value
        if old.VirtualAddress != new.VirtualAddress or bytes(expected) != new.get_data():
            raise ValueError("Unexpected changes outside reviewed prompt calls")
    return bytes(out), dict(call_spans={str(k): len(v) for k, v in changes.items()}, stub_rva=rva,
                           stub_bytes=len(payload), executable_bytes=code_size, display_rules=len(catalog["rules"]),
                           compiled_variants=len(variants(catalog)), changed_existing_code_bytes=sum(map(len, changes.values())),
                           native_modal_result_preserved=True, native_message_keys_preserved=True,
                           variable_bytes_copied_without_decoding=True, section_flags="execute/read; no write permission")
