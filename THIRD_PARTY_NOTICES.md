# 依赖与上游权利

| 项目 | 用途 | 许可/来源 |
|---|---|---|
| MobaXterm Home Edition 26.5、26.6 | 官方原包为构建输入，Release 便携包内为修改后的非官方副本 | [Mobatek 官方许可](https://mobaxterm.mobatek.net/license.html)；不适用本项目 MIT |
| CygUtils / CygUtils64 | 官方便携包中的插件，Release 便携包保留原始字节 | 保留其各自上游条款；Git 源码仓库不纳入这些二进制文件 |
| pefile 2024.8.26 | 本地读取和验证 PE 结构 | MIT；通过 pip 安装，[上游项目](https://github.com/erocarrera/pefile) |
| .NET Framework / Windows API | 编译与运行独立菜单启动器 | 使用操作系统环境提供的组件，本仓库不打包这些组件 |
| Python | 预编译图形化工具内的运行环境 | PSF 及 Python 分发中的许可，随发布包附上 `licenses/Python-LICENSE.txt` |
| Tcl / Tk | 预编译工具的图形界面 | 各自许可文本位于 `legal/`，并随发布包附上 |
| PyInstaller / hooks-contrib | 构建独立 EXE | GPL 附打包例外及部分 Apache-2.0；[上游说明](https://pyinstaller.org/en/stable/license.html)，构建版本固定在 `requirements-build.txt` |

`src/mobaxterm_zh/dfm.py` 是本项目编写的二进制窗体解析工具，不是从上游提取的窗体资源或厂商源代码。

公开版本的工具和启动器使用默认图标，不提取或附带 Mobatek 图标。菜单截图来自本地检查，只显示菜单标签，不含终端输出、主机地址或凭据。Release ZIP 中的 `licenses/` 另附打包环境中相关依赖的许可文本。
