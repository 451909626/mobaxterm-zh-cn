# 跟随官方版本的双包 Release

每个官方版本发布一个 Release：标签为 `v26.5`、`v26.6`，标题为“ MobaXterm 26.6 简体中文汉化”等。公开版本号不再使用独立的工具版本号。

## 三个附件

以 v26.6 为例：

| 附件 | 内容 |
|---|---|
| `MobaXterm_Chinese_Tool_v26.6_win-x64.zip` | 预编译图形化汉化工具、运行环境、补丁和依赖许可 |
| `MobaXterm_Portable_v26.6_zh-CN.zip` | 按官方便携包根目录结构整理的汉化客户端、启动器和说明 |
| `SHA256SUMS.txt` | 两个 ZIP 的摘要 |

便携 ZIP 根目录保留 `MobaXterm_Personal_26.6.exe`、`CygUtils.plugin`、`CygUtils64.plugin`，另附 `启动汉化版.exe` 和四份说明/许可文本。主程序必须匹配已复核的汉化摘要，两个插件必须匹配对应官方原文件，启动器必须与工具内置版本一致。

便携包不包含 INI、会话、凭据、日志、调试产物或原版备份；配置由首次运行创建。工具 ZIP 中不包含 MobaXterm 本体。二进制附件不提交到 Git。

## 构建

```powershell
python -m pip install -r requirements-build.txt
python -m unittest discover -s tests -v
python scripts/build_release.py --tag v26.6 --source-zip "D:\Downloads\MobaXterm_Portable_v26.6.zip" --output dist/v26.6
```

省略 `--source-zip` 时，从精确版本清单中的官方 HTTPS 地址下载原包，并验证原包、主 EXE 和两个插件的摘要。已有缓存只在摘要正确时复用，不覆盖错误输入。

构建过程先编译启动器并封装工具，运行封装自检，再调用封装 EXE 的诊断模式生成干净客户端。只将允许的四个程序/组件文件和四份说明放入便携 ZIP。工具、便携 ZIP 和共同校验文件均在发布前检查。

## 自动发布

源码推送到 main 且 CI 通过后，分别推送官方版本标签：

```powershell
git tag v26.5
git push origin v26.5
git tag v26.6
git push origin v26.6
```

`.github/workflows/release.yml` 自动取得原包、测试、构建两类 ZIP 并通过仓库 `GITHUB_TOKEN` 发布附件。不需要创建新的个人令牌。工作流不修改原包备份，不向 Git 提交软件二进制。

完整版本号仍记录在各补丁清单及构建报告中：v26.5 对应 26.5.0.5542，v26.6 对应 26.6.0.5560。同一公开版本必须唯一对应一个已适配构建；未知或歧义版本停止处理。

26.5 完整实屏回归待补，当前标记为预发布；已适配版本中的最新构建可标记 Latest。已公开的 Release 和标签不会被发布脚本自动覆盖。

## 本地上传与校验

```powershell
python scripts/publish_release.py --tag v26.6 --repo 451909626/mobaxterm-zh-cn --assets dist/v26.6 --dry-run
```

`--dry-run` 只列出待执行的发布命令。实际上传前要求远程标签已经存在，并再次核对两个 ZIP、工具内置清单、便携文件摘要和 `SHA256SUMS.txt`。只上传这三个附件，不上传日志或构建报告。

## 许可范围

Git 仓库和工具中的自编代码采用 MIT。便携包为非官方修改版，厂商本体和组件继续适用上游许可；维护者选择的发布结构不表示取得了官方额外授权。见 [UPSTREAM_LICENSE.md](UPSTREAM_LICENSE.md)。
