"""A small Chinese desktop interface; the source archive stays read-only."""
from pathlib import Path
import ctypes
import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, font, messagebox, ttk

from .desktop import UserError, apply_package, release_info
from .release import LAUNCHER_NAME


def suggest_output(parent, version):
    base = Path(parent) / ("MobaXterm_" + ".".join(version.split(".")[:2]) + "_中文")
    result, number = base, 2
    while result.exists():
        result = base.with_name(base.name + "_" + str(number))
        number += 1
    return result


def run_gui(payload, initial_zip=None, initial_output=None):
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass
    root = tk.Tk()
    root.title("MobaXterm 简体中文汉化工具")
    scale = max(1.0, root.winfo_fpixels("1i") / 96)
    root.geometry(str(int(760 * scale)) + "x" + str(int(490 * scale)))
    root.minsize(int(680 * scale), int(460 * scale))
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
        font.nametofont(name).configure(family="Microsoft YaHei UI", size=10)
    style = ttk.Style(root)
    if "vista" in style.theme_names():
        style.theme_use("vista")
    try:
        info = release_info(payload)
    except Exception:
        messagebox.showerror("无法打开汉化工具", "工具文件不完整，请重新下载对应版本的发布包。", parent=root)
        root.destroy()
        return
    version = info["upstream_version"]
    root.title("MobaXterm " + ".".join(version.split(".")[:2]) + " 汉化工具")
    outer = ttk.Frame(root, padding=24)
    outer.pack(fill="both", expand=True)
    outer.columnconfigure(0, weight=1)
    outer.rowconfigure(7, weight=1)
    ttk.Label(outer, text="MobaXterm 简体中文汉化", font=("Microsoft YaHei UI", 17, "bold")).grid(
        row=0, column=0, columnspan=2, sticky="w")
    ttk.Label(outer, text="发行版本：" + ".".join(version.split(".")[:2]) + "    ·    适用：" + version + " Home 便携版").grid(
        row=1, column=0, columnspan=2, sticky="w", pady=(6, 18))
    ttk.Label(outer, text="1. 选择从官网下载的便携版 ZIP 文件").grid(row=2, column=0, columnspan=2, sticky="w")
    source = tk.StringVar(value=str(initial_zip or ""))
    source_entry = ttk.Entry(outer, textvariable=source)
    source_entry.grid(row=3, column=0, sticky="ew", pady=(6, 16), padx=(0, 10))
    target = tk.StringVar(value=str(initial_output or ""))

    def choose_source():
        chosen = filedialog.askopenfilename(parent=root, title="选择官方 Home 便携版 ZIP", filetypes=[("ZIP 压缩包", "*.zip")])
        if chosen:
            source.set(chosen)
            if not target.get():
                target.set(str(suggest_output(Path(chosen).parent, version)))

    source_button = ttk.Button(outer, text="选择原包…", command=choose_source)
    source_button.grid(row=3, column=1, sticky="ew", pady=(6, 16))
    ttk.Label(outer, text="2. 指定新的汉化目录（原版和已有文件均会保留）").grid(row=4, column=0, columnspan=2, sticky="w")
    target_entry = ttk.Entry(outer, textvariable=target)
    target_entry.grid(row=5, column=0, sticky="ew", pady=(6, 14), padx=(0, 10))

    def choose_target():
        parent = filedialog.askdirectory(parent=root, title="选择保存位置；工具将在其中新建汉化目录")
        if parent:
            target.set(str(suggest_output(parent, version)))

    target_button = ttk.Button(outer, text="选择位置…", command=choose_target)
    target_button.grid(row=5, column=1, sticky="ew", pady=(6, 14))
    ttk.Label(outer, text=f"生成后双击新目录中的“{LAUNCHER_NAME}”。已有会话需要另行迁移。",
              wraplength=int(650 * scale)).grid(row=6, column=0, columnspan=2, sticky="w")
    status = tk.StringVar(value="请选择官方原包和保存位置。")
    ttk.Label(outer, textvariable=status, wraplength=int(650 * scale), foreground="#225785").grid(
        row=7, column=0, columnspan=2, sticky="nw", pady=(18, 8))
    progress = ttk.Progressbar(outer, mode="indeterminate")
    progress.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(0, 14))
    actions = ttk.Frame(outer)
    actions.grid(row=9, column=0, columnspan=2, sticky="e")
    messages = queue.Queue()
    busy, completed = False, None
    open_button = ttk.Button(actions, text="打开汉化目录", state="disabled", command=lambda: os.startfile(str(completed)))
    open_button.pack(side="left", padx=(0, 10))

    def worker(selected_zip, destination):
        try:
            report = apply_package(payload, selected_zip, destination, lambda text: messages.put(("status", text)))
            messages.put(("done", (destination, report)))
        except UserError as exc:
            messages.put(("error", str(exc)))
        except PermissionError:
            messages.put(("error", "无法写入所选位置。请选择您有权限使用的新文件夹。"))
        except Exception:
            messages.put(("error", "汉化未完成，原包已保留。请核对版本并重新选择新的输出目录。"))

    def start():
        nonlocal busy
        if not source.get().strip() or not target.get().strip():
            messagebox.showinfo("请选择文件", "请先选择官方便携包，并指定新的汉化目录。", parent=root)
            return
        busy = True
        for control in controls:
            control.configure(state="disabled")
        open_button.configure(state="disabled")
        status.set("正在准备汉化……")
        progress.start(12)
        threading.Thread(target=worker, args=(Path(source.get()), Path(target.get())), daemon=True).start()

    start_button = ttk.Button(actions, text="开始汉化", command=start)
    start_button.pack(side="left")
    controls = (source_entry, source_button, target_entry, target_button, start_button)

    def poll():
        nonlocal busy, completed
        while not messages.empty():
            kind, value = messages.get_nowait()
            if kind == "status":
                status.set(value)
                continue
            busy = False
            progress.stop()
            for control in controls:
                control.configure(state="normal")
            if kind == "done":
                completed, _ = value
                status.set(f"汉化完成。请点击“打开汉化目录”，再双击“{LAUNCHER_NAME}”。")
                open_button.configure(state="normal")
            else:
                status.set("未生成汉化目录，原版文件已保留。")
                messagebox.showerror("汉化未完成", value, parent=root)
        root.after(100, poll)

    def close():
        if busy:
            messagebox.showinfo("正在汉化", "正在生成文件，请稍候完成后再关闭。", parent=root)
        else:
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", close)
    root.after(100, poll)
    root.mainloop()
