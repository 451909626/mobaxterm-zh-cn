# 构建说明

普通用户可下载 Releases 中的汉化便携包解压运行，也可使用图形化工具自行生成副本。以下是开发者构建与配置迁移说明；双包发布方式见 [RELEASES.md](RELEASES.md)。

## 独立终端菜单启动器

此工具在运行时替换菜单标题，不改写磁盘上的 MobaXterm 或 MoTTY 文件。使用者需要自己取得运行目标。

```powershell
python scripts/build_launcher.py --output dist/menu-launcher
```

将生成的 `启动汉化版.exe` 放到目标程序旁边，再从启动器进入。默认自动查找同目录中产品信息为 MobaXterm、版本为 26.5 或更新的 EXE；不按具体版本文件名猜测。它只处理选定文件所属的 MobaXterm 主窗口及其 CMoTTY 子窗口。关闭匹配的软件后，启动器自行退出。

同目录有多个合格 EXE 时停止并提示选择，可以启动时指定：

```powershell
.\启动汉化版.exe --exe MobaXterm_Personal_26.5.exe
```

也可在构建时用 `--target-exe MobaXterm_Personal_26.5.exe` 固定目标文件名。两种方式都校验产品信息与最低版本。仅检查启动器将选择哪个文件而不启动软件：

```powershell
.\启动汉化版.exe --inspect selection.json
```

构建时会导出已编译程序的菜单目录，与 `translations/terminal-menu.json` 比较。输出中的 `.generated` 保存生成源码与检查数据，供本地复核；不纳入 Git。

## 完整界面本地重建

这种方式修改官方 EXE 的副本，原始输入保留。项目代码许可不代替 Mobatek 的许可；公开便携包由独立发布入口筛选文件并检查，避免附带用户数据。

从[官网](https://mobaxterm.mobatek.net/download-home-edition.html)取得 26.5 或 26.6 Home 便携原包。工具根据 EXE 的版本信息自动选择清单，同时核对全部输入摘要。已登记的原包：

| 上游版本 | 官方 ZIP 的 SHA-256 |
|---|---|
| 26.5.0.5542 | `a26e7e4e2f7bd47a13fbc6d93d08a2d946f21c3e0d135b9e4f55149842c09ef6` |
| 26.6.0.5560 | `03c827c3467518de45542acba8caae63d951aede4b479962bf065b4df0d8a845` |

主程序和两个插件的逐文件摘要、官方原包地址及预期输出记录在 [26.5 清单](../patches/26.5.0.5542/version.json)与 [26.6 清单](../patches/26.6.0.5560/version.json)。先做只读检查：

```powershell
python scripts/inspect_upstream.py --source-zip "D:\Downloads\MobaXterm_Portable_v26.5.zip"
```

`full_ui_supported` 表示该输入是否通过已登记完整界面版本及摘要检查；`menu_version_eligible` 只表示达到菜单启动器的最低版本，不代表真实菜单已经完成回归。

安装依赖后，使用一个新的空输出目录：

```powershell
python -m pip install -r requirements.txt
python scripts/build_local_ui.py --source-zip "D:\Downloads\MobaXterm_Portable_v26.5.zip" --output dist/26.5
```

26.6 使用相同命令并更换原包和空输出路径，无需选择版本参数。也可用 `--source-dir` 指定已经解压、包含三个官方文件的目录。目录中只能有一个 MobaXterm EXE。原始输入只读，输出目录非空时会停止，不会覆盖现有程序或配置。未知新版、低于 26.5 的版本或摘要不符的输入在生成输出前被拒绝；不提供跳过校验的强制选项。

输出主程序名对应输入版本，从同目录的 `启动汉化版.exe` 运行。主程序结果必须与该版本清单一致：

| 输出主程序 | SHA-256 |
|---|---|
| MobaXterm_Personal_26.5.exe | `2efdc21f410c26bccd7456a3b954f1012726fae962743ecd7df1cf66c719924b` |
| MobaXterm_Personal_26.6.exe | `b11639f46d06e231c3663874da4f6e85a92a2a60570470f8de23dcd58de154ee` |

26.6 主程序与此前实屏检查的 R2.4/R2.5 主程序字节一致；26.5 实屏验证进度见[验证记录](VALIDATION.md)。启动器不嵌入厂商图标，其文件名选择逻辑已扩展，因此它与早期本地启动器的二进制摘要不同；编译后的 36 项菜单数据会独立核对。

完整构建会移除已失效的厂商签名数据并重新计算 PE 校验和，不会伪装原厂签名。官方原始输入保留原样。

## 复制旧配置并适配历史引用

关闭相关软件后，将旧配置复制到新的配置路径：

```powershell
python scripts/migrate_profile.py --source "D:\OldPortable\MobaXterm.ini" --output "D:\NewPortable\MobaXterm.ini"
```

输出文件必须不存在。工具只修改 `[Recently started]` 和 `[LastInstanceSessions]` 中数字项的默认 `User sessions\` 根目录引用，保留其他所有原始字节；不重命名用户会话、不解密或导出凭据。迁移幂等，源文件不改写。

## 本地构建数据

`dist/`、`.local/`、可执行文件、插件、INI、日志和完整软件压缩包均由 Git 忽略。本页的界面构建入口不下载软件或发布 Release；独立发布入口会下载并校验官方原包、构建双包并发布。均不自动打开主程序建立会话。
