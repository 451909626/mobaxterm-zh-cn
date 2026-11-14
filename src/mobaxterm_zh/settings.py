"""Reviewed settings labels and canonical-value adapters for 26.6.0.5560.

Most controls persist ItemIndex. Three lists persist their item strings: their
six guarded load/save sites keep the upstream English values in configuration.
Custom entries always retain the native IndexOf/Get behavior.
"""
import struct

import pefile

from .toolbar import align


def _pairs(source, target):
    if len(source) != len(target):
        raise ValueError("A translated list must preserve every item position")
    return tuple(zip(source, target))


GENERAL = "FormParams.PC36.OngletProGeneral."
TERMINAL = "FormParams.PC36.OngletTerminal."
X11 = "FormParams.PC36.OngletX11.sGroupBox9."
SSH = "FormParams.PC36.OngletSSH.sGroupBox3."
DISPLAY = "FormParams.PC36.OngletDisplay."
MISC = "FormParams.PC36.sTabSheet2."
CUSTOM = "FormParams.PC36.OngletCustom."

COMBO_LABELS = {
    # Directory templates use the separately guarded R2.11 option adapters.
    # They are not part of the Home Edition's available settings surface.
    GENERAL + "ComboDefaultUserProfile": _pairs(
        ["<Automatic>", "<Application Data>", "<My Documents>", "<Local Application Data>"],
        ["<自动>", "<应用程序数据>", "<我的文档>", "<本地应用程序数据>"]),
    TERMINAL + "sGroupBox6.ComboPromptType": _pairs(
        ["Standard", "No separation line", "Modern"], ["标准", "不显示分隔线", "现代"]),
    TERMINAL + "sGroupBox7.sComboBox32": _pairs(
        ["None", "Standard keywords (OK/warning/error/...)", "Unix shell script",
         "Cisco (network configuration)", "Perl syntax", "SQL syntax"],
        ["无", "标准关键字（OK / 警告 / 错误等）", "Unix Shell 脚本",
         "Cisco（网络配置）", "Perl 语法", "SQL 语法"]),
    TERMINAL + "sGroupBox8.sComboBox10": _pairs(
        ["Printable output", "All session output", "Printable output with timestamps"],
        ["可打印输出", "全部会话输出", "带时间戳的可打印输出"]),
    X11 + "ComboAccessControl": _pairs(
        ["on-demand", "full", "disabled"], ["按需询问", "允许所有远程访问", "禁用远程访问"]),
    X11 + "sComboBox6": _pairs(
        ['"Multiwindow mode":  Transparent X11 server integrated in Windows desktop',
         '"Windowed mode":  X11 server constrained to a single container window',
         '"Windowed mode with DWM":  X11 server and DWM desktop in a container window',
         '"Windowed mode with Twm desktop":  X11 server and Twm desktop in a container window',
         '"Internal WM": Transparent X11 server integrated in Windows desktop (experimental)',
         '"ExtWM": Transparent X11 server with Xwinwm window frames (experimental)',
         '"Rootless": Transparent X11 server with Twm window borders (experimental)'],
        ["多窗口模式：X11 窗口融入 Windows 桌面", "窗口模式：X11 显示在单个容器窗口中",
         "DWM 窗口模式：X11 与 DWM 桌面显示在容器窗口中",
         "Twm 窗口模式：X11 与 Twm 桌面显示在容器窗口中",
         "内部窗口管理器：X11 窗口融入 Windows 桌面（实验性）",
         "ExtWM：使用 Xwinwm 窗框的透明 X11 模式（实验性）",
         "无根窗口模式：使用 Twm 窗框的透明 X11 模式（实验性）"]),
    X11 + "sComboBox12": _pairs(["Software", "Hardware", "None"], ["软件", "硬件", "无"]),
    X11 + "sComboBox7": _pairs(
        ["disabled", "enabled", "disable primary"], ["禁用", "启用", "禁用主选择区共享"]),
    # Keyboard layout identifiers and numeric DPI values are protocol data.
    X11 + "sComboBox5": (("Automatic", "自动"),),
    X11 + "sComboBox4": (("stretched", "拉伸"), ("auto", "自动")),
    SSH + "sComboBox13": _pairs(
        ["<Native Windows>", "<MIT Kerberos>", "<Custom library>"],
        ["<Windows 原生>", "<MIT Kerberos>", "<自定义库>"]),
    SSH + "sComboBox1": _pairs(["<legacy>", "<new>"], ["<旧版>", "<新版>"]),
    DISPLAY + "sRadioGroup3": _pairs(["left", "right"], ["左侧", "右侧"]),
    DISPLAY + "sRadioGroup2": _pairs(
        ["Small buttons", "Standard buttons", "Buttons with captions"],
        ["小图标按钮", "标准图标按钮", "带文字的按钮"]),
    DISPLAY + "sRadioGroup1": _pairs(
        ["Show menu bar", "Show buttons bar", "Show both"],
        ["显示菜单栏", "显示按钮栏", "同时显示"]),
    DISPLAY + "ComboIconsTheme": _pairs(["Flat design", "Crystal"], ["扁平", "水晶"]),
    DISPLAY + "ComboCustomDpi": _pairs(
        ["Autodetect", "Small", "Normal", "Big", "Huge", "HighDPI 4K", "HighDPI big"],
        ["自动检测", "小", "标准", "大", "特大", "高 DPI（4K）", "高 DPI（大）"]),
    MISC + "sGroupBox1.sComboEdit2": _pairs(["<Home>", "<Terminal>"], ["<主页>", "<终端>"]),
    MISC + "sGroupBox1.sComboEdit1": _pairs(
        ["<Home>", "<Home (pinned)>", "<Terminal>"], ["<主页>", "<主页（固定）>", "<终端>"]),
    MISC + "sGroupBox1.CmbNewTabPosition": _pairs(
        ["never", "when duplicating tab", "always"], ["从不", "仅复制标签页时", "始终"]),
    MISC + "sGroupBox5.ComboPopupConsolePosition": _pairs(
        ["left", "top", "right", "bottom", "floating"], ["左侧", "顶部", "右侧", "底部", "浮动"]),
    CUSTOM + "GB1.CmbForceMasterPassword": _pairs(
        ["none", "standard (8 characters min)", "strong (12 characters min)"],
        ["不要求", "标准（至少 8 个字符）", "强（至少 12 个字符）"]),
    CUSTOM + "GB2.ComboX11RemoteAccess": _pairs(
        ["let user choose X11 security settings", "prompt on remote access request",
         "prompt on remote access + local access control", "disable remote access",
         "disable remote access + local access control", "disable X11 server"],
        ["允许用户选择 X11 安全设置", "远程访问时询问", "远程访问时询问并控制本地访问",
         "禁用远程访问", "禁用远程访问并控制本地访问", "禁用 X11 服务器"]),
    CUSTOM + "GB2.sComboBox2": _pairs(
        ["Enable all macros", "Disable graphical macros", "Disable all macros"],
        ["启用全部宏", "禁用图形宏", "禁用全部宏"]),
    CUSTOM + "GB2.CmbCyg": _pairs(
        ["Enable CygUtils 32 & 64 bit", "Disable CygUtils 32 & 64 bit",
         "Disable obsolete CygUtils32", "Disable all local terminals"],
        ["启用 32 位和 64 位 CygUtils", "禁用 32 位和 64 位 CygUtils",
         "禁用旧版 32 位 CygUtils", "禁用全部本地终端"]),
}


def permitted(form, value, target):
    return (form == "TFORMPARAMS"
            and value["property"] in ("Text", "Items.Strings[]")
            and (value["value"], target) in COMBO_LABELS.get(value["component"], ())
            and value["value"] != target)


# Each original instruction sequence is five bytes. The leading MOV restores
# the same VMT register before either a native tail call or a canonical result.
SITES = (
    ("home", "load", 0x503A90, "8b08ff5154", "95c4feffff8b45fc8b98500400008b833c020000"),
    ("new_tab", "load", 0x503AD3, "8b08ff5154", "95c0feffff8b45fc8b98540400008b833c020000"),
    ("dpi", "load", 0x503DA4, "8b08ff5154", "38ff178b95bcfeffff8b45fc8b98300500008bc6"),
    ("dpi", "save", 0x506FE3, "8b30ff560c", "ff92cc0000008bd08d8d44ffffff8b863c020000"),
    ("home", "save", 0x50723C, "8b30ff560c", "ff92cc0000008bd08d8d10ffffff8b863c020000"),
    ("new_tab", "save", 0x507278, "8b30ff560c", "ff92cc0000008bd08d8d0cffffff8b863c020000"),
)
CANONICAL = {"home": ("<Home>", "<Home (pinned)>", "<Terminal>"),
             "new_tab": ("<Home>", "<Terminal>"), "dpi": ("stretched", "auto")}
ASSIGN_RVA = 0x5170


def assemble(rva):
    code, entries, fixups, strings = bytearray(), {}, [], []
    labels = {}

    def emit(data): code.extend(data)
    def label(name): labels[name] = len(code)
    def branch(opcode, target):
        emit(opcode)
        fixups.append((len(code), target))
        emit(b"\0" * 4)

    for name, mode, *_ in SITES:
        key = name + "_" + mode
        entries[key] = len(code)
        emit(bytes.fromhex("8b08" if mode == "load" else "8b30"))
        emit(bytes.fromhex("9c60"))  # preserve registers and flags
        if mode == "load":
            emit(bytes.fromhex("8bfa85ff"))  # EDI = input AnsiString
            branch(b"\x0f\x84", key + "_fallback")
        else:
            emit(bytes.fromhex("e8000000005b"))
            anchor = len(code) - 1
        for index, text in enumerate(CANONICAL[name]):
            following = key + "_next_" + str(index)
            raw = text.encode("ascii")
            if mode == "load":
                emit(b"\x83\x7f\xfc" + bytes([len(raw)]))
                branch(b"\x0f\x85", following)
                for offset, byte in enumerate(raw):
                    emit(bytes.fromhex("0fb607") if offset == 0 else b"\x0f\xb6\x47" + bytes([offset]))
                    emit(b"\x0c\x20\x3c" + bytes([byte | 0x20]))  # ASCII case insensitive
                    branch(b"\x0f\x85", following)
                emit(b"\xc7\x44\x24\x1c" + struct.pack("<I", index))
                emit(bytes.fromhex("619dc3"))
            else:
                emit(b"\x83\xfa" + bytes([index]))
                branch(b"\x0f\x85", following)
                emit(b"\x8d\x93")
                strings.append((len(code), raw, anchor))
                emit(b"\0" * 4)
                # LStrAsg takes EAX=out pointer, EDX=immutable canonical string.
                emit(bytes.fromhex("8b4424188944241c89542414619d"))
                emit(b"\xe9" + struct.pack("<i", ASSIGN_RVA - (rva + len(code) + 5)))
            label(following)
        label(key + "_fallback")
        emit(bytes.fromhex("619d"))
        emit(bytes.fromhex("ff6154" if mode == "load" else "ff660c"))
    executable_size = len(code)
    for at, raw, anchor in strings:
        while len(code) % 4: emit(b"\0")
        emit(struct.pack("<iI", -1, len(raw)))
        string_at = len(code)
        emit(raw + b"\0")
        struct.pack_into("<i", code, at, string_at - anchor)
    for at, target in fixups:
        struct.pack_into("<i", code, at, labels[target] - at - 4)
    return bytes(code), executable_size, entries


def patch(data):
    pe = pefile.PE(data=data)
    if pe.FILE_HEADER.Machine != 0x14C or pe.OPTIONAL_HEADER.Magic != 0x10B:
        raise ValueError("Only the reviewed 32-bit PE is accepted")
    for name, mode, call_rva, expected, prefix in SITES:
        at = pe.get_offset_from_rva(call_rva)
        before = bytes.fromhex(prefix)
        if data[at:at + 5] != bytes.fromhex(expected) or data[at - len(before):at] != before:
            raise ValueError("Unexpected settings value operation: " + name + " " + mode)
    header_at = pe.sections[-1].get_file_offset() + 40
    if header_at + 40 > min(s.PointerToRawData for s in pe.sections if s.SizeOfRawData):
        raise ValueError("No space for a separate settings code section")
    rva = align(max(s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData)
                    for s in pe.sections), pe.OPTIONAL_HEADER.SectionAlignment)
    payload, code_size, entries = assemble(rva)
    raw_at = align(len(data), pe.OPTIONAL_HEADER.FileAlignment)
    raw_size = align(len(payload), pe.OPTIONAL_HEADER.FileAlignment)
    out = bytearray(data.ljust(raw_at, b"\0"))
    out.extend(payload.ljust(raw_size, b"\0"))
    out[header_at:header_at + 40] = struct.pack(
        "<8sIIIIIIHHI", b".zhset\0\0", len(payload), rva, raw_size, raw_at, 0, 0, 0, 0, 0x60000020)
    struct.pack_into("<H", out, pe.FILE_HEADER.get_field_absolute_offset("NumberOfSections"),
                     pe.FILE_HEADER.NumberOfSections + 1)
    struct.pack_into("<I", out, pe.OPTIONAL_HEADER.get_field_absolute_offset("SizeOfImage"),
                     align(rva + len(payload), pe.OPTIONAL_HEADER.SectionAlignment))
    struct.pack_into("<I", out, pe.OPTIONAL_HEADER.get_field_absolute_offset("SizeOfCode"),
                     pe.OPTIONAL_HEADER.SizeOfCode + raw_size)
    changes = {}
    for name, mode, call_rva, *_ in SITES:
        at = pe.get_offset_from_rva(call_rva)
        replacement = b"\xe8" + struct.pack("<i", rva + entries[name + "_" + mode] - call_rva - 5)
        out[at:at + 5] = replacement
        changes[call_rva] = replacement
    result = pefile.PE(data=out)
    struct.pack_into("<I", out, result.OPTIONAL_HEADER.get_field_absolute_offset("CheckSum"),
                     result.generate_checksum())
    result = pefile.PE(data=out)
    if not result.verify_checksum():
        raise ValueError("Invalid settings PE checksum")
    for old, new in zip(pe.sections, result.sections):
        expected = bytearray(old.get_data())
        if old.Name.rstrip(b"\0") == b"CODE":
            for call_rva, replacement in changes.items():
                at = call_rva - old.VirtualAddress
                expected[at:at + 5] = replacement
        if old.VirtualAddress != new.VirtualAddress or bytes(expected) != new.get_data():
            raise ValueError("Unexpected change outside the six settings operations")
    return bytes(out), {"call_rvas": list(changes), "stub_rva": rva,
                        "stub_bytes": len(payload), "executable_bytes": code_size,
                        "canonical_settings": len(CANONICAL), "changed_existing_code_bytes": 30,
                        "section_flags": "execute/read; no write permission"}
