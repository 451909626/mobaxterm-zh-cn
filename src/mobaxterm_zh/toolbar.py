"""Reviewed 26.6 toolbar caption display and stable layout lookup adapters.

Only three guarded calls are redirected. English identifiers stay unchanged;
unknown controls retain the native getter and setter. No runtime process access.
"""
import struct
import pefile


LABELS = {
    "Session": "新建会话", "Servers": "服务", "Tools": "工具", "Games": "游戏",
    "Sessions": "会话", "View": "查看", "Split": "分屏", "MultiExec": "多端执行",
    "Tunneling": "隧道", "Packages": "软件包", "Settings": "设置", "Help": "帮助",
    "X server": "X服务器", "Exit": "退出",
}


CALL_RVA = 0x565EE9


SETTER_RVA = 0x8942C


EXPECTED_CALL = bytes.fromhex("e83e35b2ff")


GETTER_RVA = 0x893FC


ASSIGN_RVA = 0x5170


LAYOUT_GETTER_CALLS = {0x58258A: bytes.fromhex("e86d6eb0ff"),
                       0x5826CA: bytes.fromhex("e82d6db0ff")}


def align(n, unit):
    return (n + unit - 1) // unit * unit


def assemble(rva, setter_rva):
    code = bytearray()
    labels, fixups, strings = {}, [], []
    def emit(data): code.extend(data)
    def label(name): labels[name] = len(code)
    def branch(opcode, target):
        emit(opcode)
        fixups.append((len(code), target))
        emit(b"\0" * 4)
    # Preserve the complete call interface. EAX is the control and EDX its
    # display caption; no control field, help key, or configuration is written.
    emit(bytes.fromhex("9c515356578bf88bf2e8000000005b"))
    anchor = 14  # return address of call/pop, relative to the stub start
    emit(bytes.fromhex("85f6"))
    branch(b"\x0f\x84", "fallback")
    for index, (english, chinese) in enumerate(LABELS.items()):
        raw = english.encode("ascii")
        following = "next_" + str(index)
        emit(b"\x83\x7e\xfc" + bytes([len(raw)]))
        branch(b"\x0f\x85", following)
        offsets = list(range(0, len(raw) - 3, 4))
        if len(raw) % 4: offsets.append(len(raw) - 4)
        for offset in dict.fromkeys(offsets):
            emit((b"\x81\x3e" if offset == 0 else b"\x81\x7e" + bytes([offset])) + raw[offset:offset + 4])
            branch(b"\x0f\x85", following)
        emit(b"\x8d\x93")  # lea edx,[ebx + static_ansi_caption - anchor]
        strings.append((len(code), chinese.encode("gbk")))
        emit(b"\0" * 4)
        branch(b"\xe9", "done")
        label(following)
    label("fallback")
    emit(b"\x8b\xd6")
    label("done")
    emit(bytes.fromhex("8bc75f5e5b599d"))
    emit(b"\xe9" + struct.pack("<i", setter_rva - (rva + len(code) + 5)))
    getter_entry = len(code)
    # Layout resolution used Caption as an identifier. Read the unchanged
    # HelpKeyword for these fourteen built-ins instead; custom controls keep
    # the original caption getter. This does not change stored configuration.
    emit(bytes.fromhex("9c515356578bf88bf28b985401000085db"))
    branch(b"\x0f\x84", "getter_fallback")
    for index, english in enumerate(LABELS):
        raw = english.encode("ascii")
        following = "getter_next_" + str(index)
        emit(b"\x83\x7b\xfc" + bytes([len(raw)]))
        branch(b"\x0f\x85", following)
        offsets = list(range(0, len(raw) - 3, 4))
        if len(raw) % 4: offsets.append(len(raw) - 4)
        for offset in dict.fromkeys(offsets):
            emit((b"\x81\x3b" if offset == 0 else b"\x81\x7b" + bytes([offset])) + raw[offset:offset + 4])
            branch(b"\x0f\x85", following)
        branch(b"\xe9", "getter_key")
        label(following)
    label("getter_fallback")
    emit(bytes.fromhex("8bc78bd65f5e5b599d"))
    emit(b"\xe9" + struct.pack("<i", GETTER_RVA - (rva + len(code) + 5)))
    label("getter_key")
    emit(bytes.fromhex("8bc68bd35f5e5b599d"))
    emit(b"\xe9" + struct.pack("<i", ASSIGN_RVA - (rva + len(code) + 5)))
    executable_size = len(code)
    for at, raw in strings:
        while len(code) % 4: emit(b"\0")
        emit(struct.pack("<iI", -1, len(raw)))  # immutable Delphi AnsiString
        string_at = len(code)
        emit(raw + b"\0")
        struct.pack_into("<i", code, at, string_at - anchor)
    for at, destination in fixups:
        struct.pack_into("<i", code, at, labels[destination] - (at + 4))
    return bytes(code), executable_size, getter_entry


def patch(data):
    pe = pefile.PE(data=data)
    if pe.FILE_HEADER.Machine != 0x14C or pe.OPTIONAL_HEADER.Magic != 0x10B:
        raise ValueError("Only the reviewed 32-bit PE is accepted")
    at = pe.get_offset_from_rva(CALL_RVA)
    if data[at:at + 5] != EXPECTED_CALL:
        raise ValueError("The toolbar caption call does not match")
    # Guard the argument provenance: the source is the HelpKeyword field,
    # passed only to the caption setter in the toolbar-style refresh loop.
    if data[at - 0x15:at] != bytes.fromhex("8b8054010000508bd68b8328050000e8186ab2ff5a"):
        raise ValueError("The toolbar caption argument sequence does not match")
    last_header = pe.sections[-1].get_file_offset() + 40
    if last_header + 40 > min(s.PointerToRawData for s in pe.sections if s.SizeOfRawData):
        raise ValueError("No space for a separate, read-only code section")
    rva = align(max(s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData) for s in pe.sections), pe.OPTIONAL_HEADER.SectionAlignment)
    payload, code_size, getter_entry = assemble(rva, SETTER_RVA)
    raw_at = align(len(data), pe.OPTIONAL_HEADER.FileAlignment)
    raw_size = align(len(payload), pe.OPTIONAL_HEADER.FileAlignment)
    out = bytearray(data.ljust(raw_at, b"\0"))
    out.extend(payload.ljust(raw_size, b"\0"))
    header = struct.pack("<8sIIIIIIHHI", b".zhui\0\0\0", len(payload), rva, raw_size, raw_at, 0, 0, 0, 0, 0x60000020)
    out[last_header:last_header + 40] = header
    struct.pack_into("<H", out, pe.FILE_HEADER.get_field_absolute_offset("NumberOfSections"), pe.FILE_HEADER.NumberOfSections + 1)
    struct.pack_into("<I", out, pe.OPTIONAL_HEADER.get_field_absolute_offset("SizeOfImage"), align(rva + len(payload), pe.OPTIONAL_HEADER.SectionAlignment))
    struct.pack_into("<I", out, pe.OPTIONAL_HEADER.get_field_absolute_offset("SizeOfCode"), pe.OPTIONAL_HEADER.SizeOfCode + raw_size)
    out[at:at + 5] = b"\xe8" + struct.pack("<i", rva - (CALL_RVA + 5))
    reviewed_changes = {CALL_RVA: out[at:at + 5]}
    for call_rva, expected in LAYOUT_GETTER_CALLS.items():
        where = pe.get_offset_from_rva(call_rva)
        if data[where:where + 5] != expected:
            raise ValueError("The reviewed layout caption getter does not match")
        if data[where - 3:where] not in (bytes.fromhex("8d55e4"), bytes.fromhex("8d55dc")):
            raise ValueError("Unexpected layout output-string argument")
        replacement = b"\xe8" + struct.pack("<i", rva + getter_entry - (call_rva + 5))
        out[where:where + 5] = replacement
        reviewed_changes[call_rva] = replacement
    result = pefile.PE(data=out)
    struct.pack_into("<I", out, result.OPTIONAL_HEADER.get_field_absolute_offset("CheckSum"), result.generate_checksum())
    result = pefile.PE(data=out)
    if not result.verify_checksum(): raise ValueError("Invalid PE checksum")
    for before, after in zip(pe.sections, result.sections):
        expected = bytearray(before.get_data())
        if before.Name.rstrip(b"\0") == b"CODE":
            for call_rva, replacement in reviewed_changes.items():
                offset = call_rva - before.VirtualAddress
                expected[offset:offset + 5] = replacement
        if before.VirtualAddress != after.VirtualAddress or bytes(expected) != after.get_data():
            raise ValueError("Unexpected changes outside the caption call")
    return bytes(out), {"call_rva": CALL_RVA, "setter_rva": SETTER_RVA, "stub_rva": rva,
                        "stub_bytes": len(payload), "executable_bytes": code_size,
                        "translated_labels": len(LABELS), "changed_existing_code_bytes": 15,
                        "layout_getter_calls": list(LAYOUT_GETTER_CALLS),
                        "section_flags": "execute/read; no write permission"}
