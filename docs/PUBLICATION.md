# 本地仓库与上传准备

准备推送到 Git 的内容：工具源码、翻译补丁数据、菜单对照、测试、构建与发布说明、工作流及只含菜单的复查图。预编译工具和汉化便携包通过同一个官方版本 Release 的附件发布。

不纳入 Git 的内容：厂商 EXE、插件、完整软件 ZIP、用户 INI、会话导出、日志、快捷方式、完整上游资源、提取的厂商图标、个人目录和调试记录。

## 发布前

1. 项目自身代码已选择 MIT，根目录提供 `LICENSE`，上游软件和依赖适用各自条款。
2. Release 同时提供预编译工具和干净的汉化便携包；两类 ZIP 与摘要文件经核对后上传，二进制文件不加入 Git。
3. 使用计划公开的 Git 提交姓名和邮箱。Git 作者邮箱会进入提交历史，可按个人偏好使用 GitHub 提供的 noreply 邮箱。
4. 审阅暂存区，并运行测试与发布检查。

```powershell
git status --short
git diff --cached --stat
python -m unittest discover -s tests -v
python scripts/check_publication.py --index
```

## 创建首个提交及远程关联

本地仓库的默认分支为 `main`。维护者确定公开提交身份与仓库地址后，可执行：

```powershell
git config user.name "YOUR_GITHUB_NAME"
git config user.email "YOUR_PUBLIC_OR_NOREPLY_EMAIL"
git add .
git commit -m "Initial localization sources"
git remote add origin https://github.com/YOUR_ACCOUNT/mobaxterm-zh-cn.git
git push -u origin main
```

提交身份使用维护者指定的信息。当前项目仓库为 https://github.com/451909626/mobaxterm-zh-cn ，源代码与二进制附件分别通过 Git 和 Release 发布。

若在 GitHub 创建仓库时选择了 VisualStudio `.gitignore` 和 MIT，远程会已有初始提交。关联前先取得并合并远程初始内容，保留 README、MIT 许可和本项目额外排除规则；不要强制推送覆盖远程历史。创建空仓库时可以直接推送本地首个提交。

本地 `.gitignore` 采用 GitHub 的 VisualStudio 模板，并追加官方输入、完整成品、用户配置、Python 缓存和打包产物的排除规则。按版本发布步骤见 [RELEASES.md](RELEASES.md)。
