"""Session option labels and scoped dialog captions for native consumers.

Resource item order and saved indexes remain unchanged. Native getters run
first; only exact translated labels at reviewed sites become their original
connection values. Unknown values and dynamic names retain native behavior.
"""
import struct

import pefile

from .toolbar import align


def pairs(source, target):
    if len(source) != len(target):
        raise ValueError("Session option counts must match")
    return tuple(zip(source, target))


S = "FormSessionEdit."
R = "FormAdvancedRdpSettings."
T = "FormAdvancedTermSettings."
PROXY = pairs(
    ["No proxy", "User site proxy", "Site proxy", "Open proxy", "Userpath proxy", "Transparent proxy",
     "Socks4 proxy", "Socks4 proxy with authentication", "Socks5 proxy", "Socks5 proxy with authentication",
     "Web proxy", "Web proxy with basic authentication", "Web proxy with digest authentication",
     "Web proxy with NTLM authentication"],
    ["不使用代理", "USER SITE 代理", "SITE 代理", "OPEN 代理", "USERPATH 代理", "透明代理",
     "SOCKS4 代理", "SOCKS4 代理（身份验证）", "SOCKS5 代理", "SOCKS5 代理（身份验证）",
     "Web 代理", "Web 代理（基本身份验证）", "Web 代理（摘要身份验证）", "Web 代理（NTLM 身份验证）"])
SSH_DESKTOPS = ["Interactive shell", "LXDE desktop", "Gnome desktop", "KDE desktop", "Fvwm2 desktop",
                "DWM desktop", "i3 desktop", "TWM desktop", "Awesome desktop", "Xmonad desktop",
                "IceWM desktop", "WMaker desktop", "Blackbox desktop", "Fluxbox desktop", "Openbox desktop",
                "Xfce4 desktop", "Enlightenment desktop", "CDE desktop", "MATE desktop", "I3 desktop",
                "WMII desktop", "FLWM desktop", "Spectrwm desktop"]
WSL_DESKTOPS = ["Interactive shell", "XFCE4 desktop", "MATE desktop", "LXDE desktop", "Fluxbox desktop",
                "IceWM desktop", "Openbox desktop", "Fvwm2 desktop", "i3 desktop", "TWM desktop",
                "Awesome desktop", "Xmonad desktop", "WMaker desktop", "Blackbox desktop",
                "Enlightenment desktop", "WMII desktop", "FLWM desktop", "Spectrwm desktop",
                "KDE desktop", "Gnome desktop"]


def desktop_pairs(items):
    return pairs(items, ["交互式 Shell" if x == "Interactive shell" else x[:-8] + " 桌面" for x in items])


LABELS = {
    ("TFORMSESSIONEDIT", S + "PC1.TabSSH.sComboBox12"): desktop_pairs(SSH_DESKTOPS),
    ("TFORMSESSIONEDIT", S + "PC1.TabSSH.sComboBox35"): pairs(
        ["None", "SFTP protocol", "SCP (enhanced speed)", "SCP (normal speed)"],
        ["无", "SFTP 协议", "SCP（高速）", "SCP（普通速度）"]),
    ("TFORMSESSIONEDIT", S + "PC1.TabTelnet.sPanel5.sComboBox40"): pairs(
        ["Active mode", "Passive mode"], ["主动模式", "被动模式"]),
    ("TFORMSESSIONEDIT", S + "PC1.TabXDMCP.sComboBox8"): pairs(
        ["Automatic", "GDI", "DirectDraw", "DirectDraw fullscreen", "DirectDraw fullscreen @ 8 bpp",
         "DirectDraw fullscreen @ 16 bpp", "DirectDraw fullscreen @ 24 bpp", "DirectDraw fullscreen @ 32 bpp",
         "DirectDraw4", "DirectDraw4 fullscreen", "DirectDraw4 fullscreen @ 8 bpp",
         "DirectDraw4 fullscreen @ 16 bpp", "DirectDraw4 fullscreen @ 24 bpp", "DirectDraw4 fullscreen @ 32 bpp"],
        ["自动", "GDI", "DirectDraw", "DirectDraw 全屏", "DirectDraw 全屏（8 位色）",
         "DirectDraw 全屏（16 位色）", "DirectDraw 全屏（24 位色）", "DirectDraw 全屏（32 位色）",
         "DirectDraw4", "DirectDraw4 全屏", "DirectDraw4 全屏（8 位色）", "DirectDraw4 全屏（16 位色）",
         "DirectDraw4 全屏（24 位色）", "DirectDraw4 全屏（32 位色）"]),
    ("TFORMSESSIONEDIT", S + "PC1.TabXDMCP.sComboBox9"): (("Automatic", "自动"),),
    ("TFORMSESSIONEDIT", S + "PC1.TabXDMCP.sComboBox22"): pairs(
        ["disabled", "enabled", "disable primary"], ["禁用", "启用", "禁用主选择区共享"]),
    ("TFORMSESSIONEDIT", S + "PC1.TabRDP.sComboBox7"): pairs(
        ["Fit to terminal", "Fit to screen"], ["适应终端窗口", "适应屏幕"]),
    ("TFORMSESSIONEDIT", S + "PC1.TabRDP.CmbZoom"): pairs(["no", "auto"], ["不缩放", "自动"]),
    ("TFORMSESSIONEDIT", S + "PC1.TabRDP.sComboBox31"): pairs(
        ["No audio", "Redirect audio", "Play on remote server"],
        ["禁用音频", "重定向到本机", "在远程服务器播放"]),
    ("TFORMSESSIONEDIT", S + "PC1.TabRDP.sComboBox39"): pairs(
        ["0 (none)", "1 (force)", "2 (prompt)"], ["0（无）", "1（强制）", "2（询问）"]),
    ("TFORMSESSIONEDIT", S + "PC1.TabFTP.sComboBox19"): PROXY,
    ("TFORMSESSIONEDIT", S + "PC1.sTabSheet1.sComboBox21"): PROXY[:1] + PROXY[6:],
    ("TFORMSESSIONEDIT", S + "PC1.TabSerial.sComboBox15"): pairs(
        ["None", "Odd", "Even", "Mark", "Space"],
        ["无校验", "奇校验", "偶校验", "传号校验（1）", "空号校验（0）"]),
    ("TFORMSESSIONEDIT", S + "PC1.TabSerial.sComboBox16"): (("None", "无"),),
    ("TFORMSESSIONEDIT", S + "PC1.TabSerial.sComboBox17"): pairs(
        ["Microcom    (automatically set COM port parameters)", "Minicom    (allows manual COM port setting)",
         "PuTTY    (allows manual COM port setting)"],
        ["Microcom（自动设置 COM 端口参数）", "Minicom（可手动设置 COM 端口）", "PuTTY（可手动设置 COM 端口）"]),
    ("TFORMSESSIONEDIT", S + "PC1.TabBrowser.sComboBox33"): (("No emulation", "不模拟"),),
    ("TFORMSESSIONEDIT", S + "PC1.TabBrowser.ComboWhichBrowser"): pairs(
        ["Internet Explorer", "Google Chrome (experimental)", "Mozilla Firefox (experimental)", "Microsoft Edge (WebView2)"],
        ["Internet Explorer", "Google Chrome（实验性）", "Mozilla Firefox（实验性）", "Microsoft Edge (WebView2)"]),
    ("TFORMSESSIONEDIT", S + "PC1.TabBrowser.sPanel3.sGroupBox2.sComboBox38"): pairs(
        ["System proxy settings", "No proxy (direct connection)", "Autodetect proxy", "Specify a proxy server", "Specify a proxy script"],
        ["使用系统代理设置", "不使用代理（直接连接）", "自动检测代理", "指定代理服务器", "指定代理脚本"]),
    ("TFORMSESSIONEDIT", S + "PC1.TabMosh.sComboBox24"): (("auto", "自动"),),
    ("TFORMSESSIONEDIT", S + "PC1.TabMosh.sComboBox25"): pairs(
        ["adaptive", "always", "never"], ["自适应", "始终", "从不"]),
    ("TFORMSESSIONEDIT", S + "PC1.sTabSheet18.sComboBox36"): desktop_pairs(WSL_DESKTOPS),
    ("TFORMSESSIONEDIT", S + "PC1.TabTerminal.sPanel9.sComboBox2"): pairs(
        ["Block", "Underline", "Line", "Blinking block", "Blinking underline", "Blinking line"],
        ["块状", "下划线", "竖线", "闪烁块状", "闪烁下划线", "闪烁竖线"]),
    ("TFORMSESSIONEDIT", S + "PC1.TabTerminal.sComboBox32"): pairs(
        ["None", "Standard keywords (OK/warning/error/...)", "Unix shell script", "Cisco (network configuration)", "Perl syntax", "SQL syntax"],
        ["无", "标准关键字（OK / 警告 / 错误等）", "Unix Shell 脚本", "Cisco（网络配置）", "Perl 语法", "SQL 语法"]),
    ("TFORMSESSIONEDIT", S + "PC1.TabTerminal.sComboBox34"): pairs(["Auto", "no delay"], ["自动", "无延迟"]),
    ("TFORMSESSIONEDIT", S + "PC1.TabTerminal.sComboBox4"): (("Use", "使用字体编码"),),
    ("TFORMSESSIONEDIT", S + "PC1.TabNetwork.sGroupBox1.sComboBox20"): pairs(
        ["None", "Socks4", "Socks5", "Http", "Telnet", "Local", "SSH forwarding", "SSH command"],
        ["无", "Socks4", "Socks5", "Http", "Telnet", "本地", "SSH 转发", "SSH 命令"]),
    ("TFORMSESSIONEDIT", S + "PC1.TabSession.sComboBox10"): pairs(
        ["Normal tab", "Detached tab", "Maximized detached tab", "Fullscreen"],
        ["普通标签页", "独立窗口", "最大化独立窗口", "全屏"]),
    ("TFORMSESSIONEDIT", S + "PC0.sTabSheet17.sComboBox23"): pairs(
        ["Autodetection", "Localhost connection", "Native connector", "Wsl command"],
        ["自动检测", "连接本地主机", "原生连接器", "Wsl 命令"]),
    ("TFORMADVANCEDRDPSETTINGS", R + "sGroupBox1.sComboBox37"): (("auto", "自动"),),
    ("TFORMADVANCEDRDPSETTINGS", R + "sGroupBox2.sComboBox1"): pairs(
        ["Use Windows account", "Ask for credentials"], ["使用 Windows 账户", "询问登录凭据"]),
    ("TFORMADVANCEDRDPSETTINGS", R + "sGroupBox4.sComboBox21"): pairs(
        ["Never", "Detect", "Always"], ["从不", "自动检测", "始终"]),
    ("TFORMADVANCEDRDPSETTINGS", R + "sGroupBox4.sComboBox2"): pairs(
        ["Same as end server", "Prompt during connection", "Specify login/password", "Use smartcard"],
        ["与目标服务器相同", "连接时询问", "指定用户名和密码", "使用智能卡"]),
    ("TFORMADVANCEDTERMSETTINGS", T + "sGroupBox2.sComboBox11"): pairs(
        ["None", "Default sound", "Visual", "PC speakers"], ["无", "默认提示音", "视觉提示", "电脑扬声器"]),
    ("TFORMADVANCEDTERMSETTINGS", T + "sGroupBox4.sComboBox5"): (("Any other key", "其他任意键"),),
    ("TFORMSSHPROTOSETTINGS", "FormSSHProtoSettings.sComboBox1"): pairs(
        ["auto", "SSHv2", "SSHv1 (insecure)"], ["自动", "SSHv2", "SSHv1（不安全）"]),
}

SECONDARY_LABELS = {
    ("TFORMPORTFORWARDING", "FormPortForwarding.PanPrincipal.sScrollBox1.sPanel2.sComboBox1"): pairs(
        ["No proxy", "SOCKS4 proxy", "SOCKS5 proxy", "WEB proxy"],
        ["不使用代理", "SOCKS4 代理", "SOCKS5 代理", "Web 代理"]),
    ("TFORMCOLORSSELECTOR", "FormColorsSelector.sGroupBox3.ComboCursor"): LABELS[("TFORMSESSIONEDIT", S + "PC1.TabTerminal.sPanel9.sComboBox2")],
    ("TFORMCOLORSSELECTOR", "FormColorsSelector.sComboBox8"): pairs(
        ["Current global color theme", "Dark background / Light text", "Light background / Dark text", "Solarized dark", "Solarized light", "Soft pastel", "Bright", "Monokai", "AfterGlow", "Monochrome", "Custom color theme"],
        ["当前全局配色", "深色背景／浅色文字", "浅色背景／深色文字", "Solarized 深色", "Solarized 浅色", "柔和粉彩", "明亮", "Monokai", "AfterGlow", "单色", "自定义配色"]),
    ("TFORMCSVIMPORT", "FormCSVImport.sComboBox1"): pairs(['comma ","', 'semicolon ";"'], ['逗号 ","', '分号 ";"']),
    ("TFORMEDITMACROLINE", "FormEditMacroLine.sPanel2.sComboBox2"): pairs(["Key down", "Key up"], ["按下按键", "松开按键"]),
    ("TFORMEDITMACROLINE", "FormEditMacroLine.sPanel2.sComboBox1"): pairs(
        ["Left button down", "Left button up", "Right button down", "Right button up", "Middle button down", "Middle button up"],
        ["按下左键", "松开左键", "按下右键", "松开右键", "按下中键", "松开中键"]),
    ("TFORMEDITMACROLINE", "FormEditMacroLine.sPanel2.sComboBox3"): pairs(["window under cursor", "focused window"], ["鼠标所在窗口", "当前焦点窗口"]),
    ("TFORMIMPORTEXPORT", "FormImportExport.PC1.GB2.sComboBox1"): pairs(
        ["Use a password to encrypt the entire file", "Encrypt only passwords and credentials"],
        ["使用密码加密整个文件", "仅加密密码和登录凭据"]),
    ("TFORMIMPORTEXPORT", "FormImportExport.PC1.GB2.sComboBox3"): pairs(
        ["Enter a password to protect this file", "Use my current Master Password"],
        ["输入用于保护此文件的密码", "使用当前主密码"]),
    ("TFORMSHAREDSESSIONS", "FormSharedSessions.sPageControl1.TabEditSharedSession.sGroupBox1.sComboBox1"): (("shared folder", "共享文件夹"),),
    ("TFORMSHAREDSESSIONS", "FormSharedSessions.sComboBox2"): pairs(
        ["Do not automatically refresh shared sessions", "Change icon when shared sessions have been updated", "Refresh shared sessions automatically"],
        ["不自动刷新共享会话", "共享会话更新时更改图标", "自动刷新共享会话"]),
}
_persistent = pairs(["<Default>", "<Temp directory>", "<Same as application>", "<Custom>"],
                    ["<默认>", "<临时目录>", "<程序所在目录>", "<自定义>"])
for _name in ("ComboPersistentRoot", "ComboPersistentHome", "ComboPersistentIni"):
    SECONDARY_LABELS[("TFORMPARAMS", "FormParams.PC36.OngletProGeneral." + _name)] = _persistent if _name != "ComboPersistentIni" else (_persistent[0], _persistent[3])
_encoding_descriptions = {
    "West Europe": "西欧", "East Europe": "东欧", "South Europe": "南欧", "North Europe": "北欧", "Cyrillic": "西里尔文",
    "Arabic": "阿拉伯文", "Greek": "希腊文", "Hebrew": "希伯来文", "Turkish": "土耳其文", "Nordic": "北欧", "Thai": "泰文",
    "Baltic": "波罗的海", "Celtic": "凯尔特文", "Euro": "欧元", "Balkan": "巴尔干", "Unicode": "统一码",
    "Russian": "俄文", "Ukrainian": "乌克兰文", "Chinese": "中文", "Japanese": "日文", "Korean": "韩文",
    "OEM Codepage": "OEM 代码页", "Western": "西欧", "Central European": "中欧", "Vietnamese": "越南文", "Mazovia": "马佐维亚",
}
_encodings = ["ISO-8859-1 (West Europe)", "ISO-8859-2 (East Europe)", "ISO-8859-3 (South Europe)", "ISO-8859-4 (North Europe)", "ISO-8859-5 (Cyrillic)",
              "ISO-8859-6 (Arabic)", "ISO-8859-7 (Greek)", "ISO-8859-8 (Hebrew)", "ISO-8859-9 (Turkish)", "ISO-8859-10 (Nordic)",
              "ISO-8859-11 (Thai)", "ISO-8859-13 (Baltic)", "ISO-8859-14 (Celtic)", "ISO-8859-15 (Euro)", "ISO-8859-16 (Balkan)",
              "UTF-8 (Unicode)", "KOI8-R (Russian)", "KOI8-U (Ukrainian)", "GBK (Chinese)", "Big5 (Chinese)", "SJIS (Japanese)", "eucKR (Korean)",
              "CP850 (OEM Codepage)", "Win1252 (Western)", "Win1251 (Cyrillic)", "Win1250 (Central European)", "Win1253 (Greek)", "Win1254 (Turkish)",
              "Win1255 (Hebrew)", "Win1256 (Arabic)", "Win1257 (Baltic)", "Win1258 (Vietnamese)", "CP437", "CP620 (Mazovia)", "CP819", "CP852", "CP878", "HP-ROMAN8", "VSCII", "DEC-MCS", "Use font encoding"]
_translated_encodings = []
for _text in _encodings:
    _target = _text
    for _source, _translation in _encoding_descriptions.items():
        _target = _target.replace("(" + _source + ")", "(" + _translation + ")")
    if _text == "Use font encoding": _target = "使用字体编码"
    _translated_encodings.append(_target)
SECONDARY_LABELS[("TFORMFONTSELECTOR", "FormFontSelector.sGroupBox1.sComboBox4")] = pairs(_encodings, _translated_encodings)
LABELS.update(SECONDARY_LABELS)

# These labels also feed connection commands or legacy textual lookups.
VALUE_NAMES = {"sComboBox4", "sComboBox12", "sComboBox8", "sComboBox9", "sComboBox7", "CmbZoom", "sComboBox19",
               "sComboBox21", "sComboBox15", "ComboWhichBrowser", "sComboBox24", "sComboBox25", "sComboBox36"}
VALUE_LABELS = {component: values for (form, component), values in LABELS.items()
                if form == "TFORMSESSIONEDIT" and component.rsplit(".", 1)[-1] in VALUE_NAMES}
for _key in [("TFORMCOLORSSELECTOR", "FormColorsSelector.sComboBox8"),
             ("TFORMIMPORTEXPORT", "FormImportExport.PC1.GB2.sComboBox1"),
             ("TFORMPORTFORWARDING", "FormPortForwarding.PanPrincipal.sScrollBox1.sPanel2.sComboBox1")]:
    VALUE_LABELS[_key[1]] = LABELS[_key]
for _name in ("ComboPersistentRoot", "ComboPersistentHome", "ComboPersistentIni"):
    _component = "FormParams.PC36.OngletProGeneral." + _name
    VALUE_LABELS[_component] = LABELS[("TFORMPARAMS", _component)]
ITEM_LIMITS = {"FormColorsSelector.sComboBox8": 11}
GETTER_RVA = 0x893FC
FIND_RVA = 0x6B1F5C
ASSIGN_RVA = 0x5170
SETTER_RVA = 0x8942C
CAPTION_LABELS = {
    "FormSessionEdit.sBitBtn7": (("Save", "保存"), ("OK", "确定")),
    "FormSessionEdit.sBitBtn8": (("Close", "关闭"), ("Cancel", "取消")),
    # AlphaSkins refreshes these captions from its English language globals.
    "PathDialogForm.sBitBtn1": (("OK", "确定"),),
    "PathDialogForm.sBitBtn2": (("Cancel", "取消"),),
    "PathDialogForm.sBitBtn3": (("Create", "新建"),),
    "sColorDialogForm.sBitBtn1": (("OK", "确定"),),
    "sColorDialogForm.sBitBtn2": (("Cancel", "取消"),),
}
SETTEXT_LABELS = {S + "PC1.TabTerminal.sComboBox4": (("Use", "使用字体编码"),)}


def permitted(form, value, target):
    return (value["property"] in ("Text", "Items.Strings[]")
            and (value["value"], target) in LABELS.get((form, value["component"]), ())
            and value["value"] != target)


def assemble(rva, sites):
    code, labels, fixups, string_fixups, entries = bytearray(), {}, [], [], {}

    def emit(value): code.extend(value)
    def label(name): labels[name] = len(code)
    def branch(op, name):
        emit(op)
        fixups.append((len(code), name))
        emit(b"\0" * 4)
    def relative(op, destination): emit(op + struct.pack("<i", destination - rva - len(code) - 5))
    def string_address(raw, anchor):
        emit(b"\x8d\x93")
        string_fixups.append((len(code), raw, anchor))
        emit(b"\0" * 4)
    def capture_return():
        emit(bytes.fromhex("8944240489542408894c240c9c5889442430"))
    def return_native():
        emit(bytes.fromhex("8b4424048944242c8b442408894424248b44240c8944242883c410619dc3"))
    def compare_string(raw, next_label, case_insensitive=False):
        emit(b"\x81\x7f\xfc" + struct.pack("<I", len(raw)))
        branch(b"\x0f\x85", next_label)
        if len(raw) < 4:
            for offset, byte in enumerate(raw):
                emit(bytes.fromhex("0fb607") if not offset else b"\x0f\xb6\x47" + bytes([offset]))
                if case_insensitive and (65 <= byte <= 90 or 97 <= byte <= 122): emit(b"\x0c\x20")
                emit(b"\x3c" + bytes([ord(chr(byte).lower()) if case_insensitive else byte]))
                branch(b"\x0f\x85", next_label)
        else:
            offsets = list(range(0, len(raw) - 3, 4))
            if len(raw) % 4: offsets.append(len(raw) - 4)
            for offset in dict.fromkeys(offsets):
                emit(b"\x8b\x07" if not offset else b"\x8b\x47" + bytes([offset]))
                block = raw[offset:offset + 4]
                if case_insensitive:
                    mask = bytes(32 if 65 <= x <= 90 or 97 <= x <= 122 else 0 for x in block)
                    if any(mask): emit(b"\x0d" + mask)
                    block = block.lower()
                emit(b"\x3d" + block)
                branch(b"\x0f\x85", next_label)

    for site in sites:
        key = (site["control"], site["kind"], site.get("vmt_register", ""))
        if key in entries: continue
        entries[key] = len(code)
        prefix = "entry_" + str(len(entries))
        if site["kind"] in ("caption", "settext"):
            emit(bytes.fromhex("9c608bfae8000000005b"))
            anchor = len(code) - 1
            emit(bytes.fromhex("85ff"))
            branch(b"\x0f\x84", prefix + "_caption_done")
            values = (CAPTION_LABELS if site["kind"] == "caption" else SETTEXT_LABELS)[site["control"]]
            for number, (english, chinese) in enumerate(values):
                following = prefix + "_caption_next_" + str(number)
                compare_string(english.encode("ascii"), following)
                string_address(chinese.encode("gbk"), anchor)
                emit(bytes.fromhex("89542414"))
                branch(b"\xe9", prefix + "_caption_done")
                label(following)
            label(prefix + "_caption_done")
            emit(bytes.fromhex("619d"))
            relative(b"\xe9", SETTER_RVA)
            continue
        values = [(a, b) for a, b in VALUE_LABELS[site["control"]] if a != b]
        if site["kind"] == "item":
            emit(bytes.fromhex(site["before_hex"])[:2])
        elif site["kind"] == "indexof":
            emit(bytes.fromhex("8b08"))
        emit(bytes.fromhex("9c6083ec10"))
        if site["kind"] == "text":
            emit(bytes.fromhex("891424"))  # save the native output pointer
            relative(b"\xe8", GETTER_RVA)
        elif site["kind"] == "item":
            emit(bytes.fromhex("890c24"))
            emit(bytes.fromhex(site["before_hex"])[2:])
        elif site["kind"] == "findtext":
            relative(b"\xe8", FIND_RVA)
        else:
            emit(bytes.fromhex("ff5154"))  # native lookup first, for custom/unchanged items
        capture_return()
        emit(bytes.fromhex("e8000000005b"))
        anchor = len(code) - 1
        if site["kind"] in ("indexof", "findtext"):
            emit(bytes.fromhex("837c240400"))
            branch(b"\x0f\x8d", prefix + "_native")
            emit(bytes.fromhex("8b7c2424"))  # original query AnsiString
        else:
            if site["control"] in ITEM_LIMITS:
                emit(bytes.fromhex("817c2424") + struct.pack("<I", ITEM_LIMITS[site["control"]]))
                branch(b"\x0f\x83", prefix + "_native")
            emit(bytes.fromhex("8b3c248b3f"))  # native getter result AnsiString
        emit(bytes.fromhex("85ff"))
        branch(b"\x0f\x84", prefix + "_native")
        for number, (english, chinese) in enumerate(values):
            following = prefix + "_next_" + str(number)
            raw = english.encode("ascii") if site["kind"] in ("indexof", "findtext") else chinese.encode("gbk")
            compare_string(raw, following, site["kind"] in ("indexof", "findtext"))
            if site["kind"] in ("indexof", "findtext"):
                string_address(chinese.encode("gbk"), anchor)
                emit(bytes.fromhex("8b44242c"))
                if site["kind"] == "findtext":
                    emit(bytes.fromhex("8b4c2428"))
                    relative(b"\xe8", FIND_RVA)
                else:
                    emit(bytes.fromhex("8b08ff5154"))
                capture_return()
                branch(b"\xe9", prefix + "_native")
            else:
                string_address(english.encode("ascii"), anchor)
                emit(bytes.fromhex("8b04248944242c895424248b44240c8944242883c410619d"))
                relative(b"\xe9", ASSIGN_RVA)
            label(following)
        label(prefix + "_native")
        return_native()
    code_size = len(code)
    stored = {}
    for at, raw, anchor in string_fixups:
        if raw not in stored:
            while len(code) % 4: emit(b"\0")
            emit(struct.pack("<iI", -1, len(raw)))
            stored[raw] = len(code)
            emit(raw + b"\0")
        struct.pack_into("<i", code, at, stored[raw] - anchor)
    for at, name in fixups:
        struct.pack_into("<i", code, at, labels[name] - at - 4)
    return bytes(code), code_size, entries


def patch(data, spec):
    pe = pefile.PE(data=data)
    if spec["upstream_version"] != "26.6.0.5560" or pe.FILE_HEADER.Machine != 0x14C or pe.OPTIONAL_HEADER.Magic != 0x10B:
        raise ValueError("No reviewed session option adapter for this executable")
    sites = spec["sites"]
    seen = set()
    for site in sites:
        supported = CAPTION_LABELS if site["kind"] == "caption" else SETTEXT_LABELS if site["kind"] == "settext" else VALUE_LABELS
        if site["rva"] in seen or site["control"] not in supported or site["kind"] not in ("text", "item", "indexof", "findtext", "caption", "settext"):
            raise ValueError("Unreviewed or duplicate session value site")
        seen.add(site["rva"])
        at = pe.get_offset_from_rva(site["rva"])
        expected, before = bytes.fromhex(site["before_hex"]), bytes.fromhex(site["context_before_hex"])
        if len(expected) != 5 or data[at:at + 5] != expected or data[at - len(before):at] != before:
            raise ValueError("Session value call or argument provenance differs")
        if site["kind"] in ("caption", "settext"):
            if expected != b"\xe8" + struct.pack("<i", SETTER_RVA - site["rva"] - 5):
                raise ValueError("Unexpected native session caption setter")
        elif site["kind"] == "findtext":
            if expected != b"\xe8" + struct.pack("<i", FIND_RVA - site["rva"] - 5):
                raise ValueError("Unexpected native session option lookup")
        elif site["kind"] == "text":
            if expected != b"\xe8" + struct.pack("<i", GETTER_RVA - site["rva"] - 5):
                raise ValueError("Unexpected native session text getter")
        elif site["kind"] == "indexof":
            if expected != bytes.fromhex("8b08ff5154"):
                raise ValueError("Unexpected native session item lookup")
        elif {"8b18ff530c": "ebx", "8b30ff560c": "esi", "8b38ff570c": "edi"}.get(expected.hex()) != site["vmt_register"]:
            raise ValueError("Unexpected native session item getter")
    header_at = pe.sections[-1].get_file_offset() + 40
    if header_at + 40 > min(s.PointerToRawData for s in pe.sections if s.SizeOfRawData):
        raise ValueError("No room for the reviewed session adapter section")
    rva = align(max(s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData)
                    for s in pe.sections), pe.OPTIONAL_HEADER.SectionAlignment)
    payload, size, entries = assemble(rva, sites)
    raw_at = align(len(data), pe.OPTIONAL_HEADER.FileAlignment)
    raw_size = align(len(payload), pe.OPTIONAL_HEADER.FileAlignment)
    out = bytearray(data.ljust(raw_at, b"\0"))
    out.extend(payload.ljust(raw_size, b"\0"))
    out[header_at:header_at + 40] = struct.pack(
        "<8sIIIIIIHHI", b".zhss\0\0\0", len(payload), rva, raw_size, raw_at, 0, 0, 0, 0, 0x60000020)
    struct.pack_into("<H", out, pe.FILE_HEADER.get_field_absolute_offset("NumberOfSections"), pe.FILE_HEADER.NumberOfSections + 1)
    struct.pack_into("<I", out, pe.OPTIONAL_HEADER.get_field_absolute_offset("SizeOfImage"), align(rva + len(payload), pe.OPTIONAL_HEADER.SectionAlignment))
    struct.pack_into("<I", out, pe.OPTIONAL_HEADER.get_field_absolute_offset("SizeOfCode"), pe.OPTIONAL_HEADER.SizeOfCode + raw_size)
    changes = {}
    for site in sites:
        key = (site["control"], site["kind"], site.get("vmt_register", ""))
        replacement = b"\xe8" + struct.pack("<i", rva + entries[key] - site["rva"] - 5)
        at = pe.get_offset_from_rva(site["rva"])
        out[at:at + 5] = replacement
        changes[site["rva"]] = replacement
    result = pefile.PE(data=out)
    struct.pack_into("<I", out, result.OPTIONAL_HEADER.get_field_absolute_offset("CheckSum"), result.generate_checksum())
    result = pefile.PE(data=out)
    if not result.verify_checksum(): raise ValueError("Invalid session adapter checksum")
    for old, new in zip(pe.sections, result.sections):
        expected = bytearray(old.get_data())
        if old.Name.rstrip(b"\0") == b"CODE":
            for call, value in changes.items(): expected[call - old.VirtualAddress:call - old.VirtualAddress + 5] = value
        if old.VirtualAddress != new.VirtualAddress or bytes(expected) != new.get_data():
            raise ValueError("Unexpected changes outside reviewed session calls")
    return bytes(out), {"call_rvas": list(changes), "stub_rva": rva, "stub_bytes": len(payload),
                       "executable_bytes": size, "canonical_controls": len(VALUE_LABELS),
                       "caption_labels": sum(len(x) for x in CAPTION_LABELS.values()),
                       "option_set_labels": sum(len(x) for x in SETTEXT_LABELS.values()),
                       "changed_existing_code_bytes": 5 * len(sites), "native_getters_first": True,
                       "section_flags": "execute/read; no write permission"}
