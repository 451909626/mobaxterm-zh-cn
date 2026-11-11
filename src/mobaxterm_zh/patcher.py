"""Version-aware local UI reconstruction; upstream binaries are not distributed."""
from pathlib import Path
from ctypes import wintypes
import ctypes
import hashlib
import json
import os
import re
import struct
import tempfile

from .dfm import Reader, encode_text
from .upstream import manifests, select_upstream


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load_spec(repo, upstream_version=None):
    reviewed = manifests(repo)
    if upstream_version is None:
        upstream_version = reviewed[-1]["upstream_version"]
    if upstream_version not in {v["upstream_version"] for v in reviewed}:
        raise ValueError("No reviewed patches for " + upstream_version)
    directory = Path(repo) / "patches" / upstream_version
    return tuple(json.loads((directory / name).read_text(encoding="utf-8"))
                 for name in ("version.json", "forms.json", "literals.json"))


def resources(pe):
    return {(str(t.name) if t.name else t.id, str(n.name) if n.name else n.id, l.id):
            pe.get_data(l.data.struct.OffsetToData, l.data.struct.Size)
            for t in pe.DIRECTORY_ENTRY_RESOURCE.entries
            for n in t.directory.entries for l in n.directory.entries}


PROMPT_FIELDS = {
    ("TFORMXTERM", "FormXterm.PanIce1.sPanel12.EdSearch"),
    ("TFRAMEHOME", "FrameHome.sPanel1.PanelHome.Panel1.EdSearch"),
}
DISPLAY_LISTS = {
    ("TFORMADVANCEDTERMSETTINGS", "FormAdvancedTermSettings.sGroupBox2.ChkListFeatures", "Items.Strings[]"),
    ("TFORMPASTESETTINGS", "FormPasteSettings.ChkList", "Items.Strings[]"),
    ("TFORMMASTERPASSWORD", "FormMasterPassword.sRadioGroup1", "Items.Strings[]"),
    ("TFORMSYNTAX", "FormSyntax.sTabControl1", "Tabs.Strings[]"),
}
LIST_HEIGHT = ("TFORMADVANCEDTERMSETTINGS", "FormAdvancedTermSettings.sGroupBox2.ChkListFeatures", "Height")
COMMAND_HINTS = {"ctris", "TCPCapture --showdata yes", "MobaTaskList", "dwm", "fvwm", "twm",
                 "MobaHwInfo", "MobaSwInfo", "cmd.exe", "powershell.exe", "vim", "ascii",
                 "mathomatic", "nedit", "soliterm", "termwalk", "sudoku", "nimesweeper",
                 "ninvaders", "greed", "typespeed", "net", "mines", "solo", "guess", "map",
                 "untangle", "MobApt"}


def permitted(form, value, target):
    component, prop = value["component"], value["property"]
    if type(target) is int:
        return (form, component, prop) == LIST_HEIGHT and value["value"] == 70 and target == 67
    if not isinstance(target, str) or value["type"] not in (6, 12, 18, 20):
        return False
    if prop == "Hint" and value["value"] in COMMAND_HINTS:
        return False
    if (form == "TFORMCOLORSSELECTOR" and prop == "Hint"
            and re.fullmatch(r"Col\d+", component.rsplit(".", 1)[-1])):
        return False
    if form == "TFORMPARAMS" and prop in ("Text", "Items.Strings[]"):
        from .settings import permitted as permitted_setting
        return permitted_setting(form, value, target)
    if prop == "Text":
        return (form, component) in PROMPT_FIELDS
    if prop == "HelpKeyword":
        # Toolbar customization persists and resolves these values as keys.
        # They are also used to restore captions, but are not display-only.
        return False
    return (prop in {"Caption", "Hint", "TextHint", "Title"} or prop.endswith(".Caption")
            or prop.endswith(".Hint") or (form, component, prop) in DISPLAY_LISTS)


def patch_form(raw, form):
    if digest(raw) != form["source_sha256"]:
        raise ValueError("Unexpected original form: " + form["name"])
    reader = Reader(raw).read()
    edits = []
    seen = set()
    for item in form["patches"]:
        index = item["index"]
        if index in seen:
            raise ValueError("Duplicate form patch")
        seen.add(index)
        value = reader.values[index]
        if ((value["component"], value["property"], value["type"])
                != (item["component"], item["property"], item["source_type"])):
            raise ValueError("Form location mismatch")
        original = raw[value["start"]:value["end"]]
        if digest(original) != item["source_value_sha256"]:
            raise ValueError("Original property hash mismatch")
        if not permitted(form["name"], value, item["target"]):
            raise ValueError("Protected property is not a display label")
        if isinstance(item["target"], str):
            encoded = encode_text(item["target"])
        else:
            width = {2: 1, 3: 2, 4: 4}[value["type"]]
            encoded = bytes([value["type"]]) + item["target"].to_bytes(width, "little", signed=True)
        edits.append((value["start"], value["end"], encoded))
    patched = raw
    for start, end, encoded in sorted(edits, reverse=True):
        patched = patched[:start] + encoded + patched[end:]
    check = Reader(patched).read()
    if check.components != reader.components or len(check.values) != len(reader.values):
        raise ValueError("Form structure changed")
    if digest(patched) != form["target_sha256"]:
        raise ValueError("Translated form hash mismatch")
    return patched


def patch_literals(data, pe, spec):
    result = bytearray(data)
    spans = []
    for item in spec["literals"]:
        start = item["offset"]
        before, after = bytes.fromhex(item["before_hex"]), bytes.fromhex(item["after_hex"])
        if len(before) != len(after) or data[start:start + len(before)] != before:
            raise ValueError("Runtime label location mismatch")
        section = pe.get_section_by_offset(start)
        if section.Name.rstrip(b"\0") != b"CODE":
            raise ValueError("Runtime text is outside the reviewed section")
        storage = item.get("storage", "ansistring")
        if storage not in ("ansistring", "pansichar"):
            raise ValueError("Unknown runtime label storage")
        pointer_offset = 0 if storage == "pansichar" else 4
        pointer = struct.pack("<I", pe.OPTIONAL_HEADER.ImageBase + pe.get_rva_from_offset(start + pointer_offset))
        actual = [match.start() for match in re.finditer(re.escape(pointer), data)]
        if actual != item["references"]:
            raise ValueError("Runtime label references changed")
        if any(start < b and a < start + len(before) for a, b in spans):
            raise ValueError("Overlapping literal patches")
        spans.append((start, start + len(before)))
        result[start:start + len(before)] = after
    return bytes(result)


def update_resources(destination, patches):
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.BeginUpdateResourceW.argtypes = [wintypes.LPCWSTR, wintypes.BOOL]
    kernel.BeginUpdateResourceW.restype = wintypes.HANDLE
    kernel.UpdateResourceW.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                     wintypes.WORD, ctypes.c_void_p, wintypes.DWORD]
    kernel.UpdateResourceW.restype = wintypes.BOOL
    kernel.EndUpdateResourceW.argtypes = [wintypes.HANDLE, wintypes.BOOL]
    kernel.EndUpdateResourceW.restype = wintypes.BOOL
    handle = kernel.BeginUpdateResourceW(str(destination), False)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        for form, language, data in patches:
            name = ctypes.create_unicode_buffer(form)
            blob = ctypes.create_string_buffer(data)
            if not kernel.UpdateResourceW(handle, ctypes.c_void_p(10), ctypes.cast(name, ctypes.c_void_p),
                                          language, blob, len(data)):
                raise ctypes.WinError(ctypes.get_last_error())
    except BaseException:
        kernel.EndUpdateResourceW(handle, True)
        raise
    if not kernel.EndUpdateResourceW(handle, False):
        raise ctypes.WinError(ctypes.get_last_error())


def build_local_ui(repo, output, source_zip=None, source_dir=None):
    """Build to a new local directory; never modify the supplied original files."""
    if os.name != "nt":
        raise RuntimeError("PE resource updates require Windows")
    import pefile
    version, files = select_upstream(repo, source_zip, source_dir)
    _, forms, literals = load_spec(repo, version["upstream_version"])
    original = files[version["upstream_main_name"]]
    p0 = pefile.PE(data=original)
    before = resources(p0)
    patches = [(f["name"], f["language"], patch_form(before[(10, f["name"], f["language"])], f))
               for f in forms["forms"]]
    expected_code = patch_literals(original, p0, literals)
    data = bytearray(expected_code)
    security = p0.OPTIONAL_HEADER.DATA_DIRECTORY[4]
    if security.VirtualAddress:
        if security.VirtualAddress + security.Size != len(data):
            raise ValueError("Unexpected certificate/overlay layout")
        data = data[:security.VirtualAddress]
        data[security.get_file_offset():security.get_file_offset() + 8] = b"\0" * 8
    output = Path(output).resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("Output must be empty; existing programs/configuration are preserved")
    # Update in a local temporary directory: cloud-synced folders may reject PE
    # resource commits. Publish only the fully verified result to the output.
    with tempfile.TemporaryDirectory(prefix="moba-zh-") as temporary:
        candidate = Path(temporary) / version["main_output_name"]
        candidate.write_bytes(data)
        update_resources(candidate, patches)
        data = bytearray(candidate.read_bytes())
    toolbar_report = None
    if version.get("toolbar_caption_labels", 0):
        if version["upstream_version"] != "26.6.0.5560":
            raise ValueError("No reviewed toolbar display adapter for this version")
        from .toolbar import patch as patch_toolbar
        data, toolbar_report = patch_toolbar(bytes(data))
        data = bytearray(data)
        if toolbar_report["translated_labels"] != version["toolbar_caption_labels"]:
            raise ValueError("Toolbar label count differs from the reviewed version")
        # The existing-code allowance is limited to the three guarded calls.
        expected_code = bytearray(expected_code)
        hook_pe = pefile.PE(data=bytes(data))
        call_rvas = [toolbar_report["call_rva"], *toolbar_report["layout_getter_calls"]]
        for rva in call_rvas:
            old_offset = p0.get_offset_from_rva(rva)
            new_offset = hook_pe.get_offset_from_rva(rva)
            expected_code[old_offset:old_offset + 5] = data[new_offset:new_offset + 5]
    settings_report = None
    if version.get("settings_combo_controls", 0):
        if version["upstream_version"] != "26.6.0.5560":
            raise ValueError("No reviewed settings value adapter for this version")
        from .settings import COMBO_LABELS, patch as patch_settings
        if len(COMBO_LABELS) != version["settings_combo_controls"]:
            raise ValueError("Settings control count differs from the reviewed version")
        data, settings_report = patch_settings(bytes(data))
        data = bytearray(data)
        expected_code = bytearray(expected_code)
        hook_pe = pefile.PE(data=bytes(data))
        for rva in settings_report["call_rvas"]:
            old_offset = p0.get_offset_from_rva(rva)
            new_offset = hook_pe.get_offset_from_rva(rva)
            expected_code[old_offset:old_offset + 5] = data[new_offset:new_offset + 5]
    p1 = pefile.PE(data=bytes(data))
    struct.pack_into("<I", data, p1.OPTIONAL_HEADER.get_field_absolute_offset("CheckSum"), p1.generate_checksum())
    p1 = pefile.PE(data=bytes(data))
    if not p1.verify_checksum():
        raise ValueError("PE checksum verification failed")
    after = resources(p1)
    changed = {(10, name, lang) for name, lang, _ in patches}
    if before.keys() != after.keys() or {k for k in before if before[k] != after[k]} != changed:
        raise ValueError("Unexpected resource change")
    added_sections = ([b".zhui"] if toolbar_report else []) + ([b".zhset"] if settings_report else [])
    if len(p1.sections) != len(p0.sections) + len(added_sections):
        raise ValueError("Unexpected number of PE sections")
    for section, name in zip(p1.sections[len(p0.sections):], added_sections):
        if section.Name.rstrip(b"\0") != name or section.Characteristics != 0x60000020:
            raise ValueError("Unexpected display adapter section or permissions")
    for old, new in zip(p0.sections, p1.sections):
        if old.Name != new.Name or old.VirtualAddress != new.VirtualAddress:
            raise ValueError("Unexpected section layout")
        if old.Name.rstrip(b"\0") != b".rsrc":
            start = old.PointerToRawData
            if new.get_data() != expected_code[start:start + old.SizeOfRawData]:
                raise ValueError("Unexpected non-resource bytes changed")
    if digest(data) != version["localized_exe_sha256"]:
        raise ValueError("Local reconstruction differs from the reviewed " + version["upstream_version"] + " result")
    output.mkdir(parents=True, exist_ok=True)
    destination = output / version["main_output_name"]
    destination.write_bytes(data)
    for name in ("CygUtils.plugin", "CygUtils64.plugin"):
        (output / name).write_bytes(files[name])
    (output / "MobaXterm.ini").write_bytes(b"[Misc]\r\n")
    return {"release": version["localization_release"], "upstream_version": version["upstream_version"],
            "source_sha256": digest(original), "localized_exe_sha256": digest(data),
            "resource_forms": len(patches), "resource_strings": version["resource_display_locations"],
            "runtime_literals": len(literals["literals"]), "main_file": destination.name,
            "toolbar_caption_labels": version.get("toolbar_caption_labels", 0),
            "toolbar_display_adapter": toolbar_report,
            "settings_combo_controls": version.get("settings_combo_controls", 0),
            "settings_value_adapter": settings_report}
