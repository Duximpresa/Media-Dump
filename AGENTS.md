# AGENTS.md

## 项目概览

MediaDump 是一款主要运行于 Windows 的 Python + Tkinter 桌面工具，面向摄影师的素材导入和文件整理工作。

当前功能包括：

- 从源文件夹向目标文件夹导入照片和视频。
- 根据 Windows 文件创建时间分类保存素材。
- 复制前生成导入预览。
- 智能处理目标目录中的同名文件。
- 复制完成后进行 SHA-256 校验。
- 显示复制进度、速度、日志，并支持取消。
- 分别记忆源文件夹和目标文件夹路径。
- Beta 版本提供批量查找替换和序列重命名功能。

项目仓库：

```text
https://github.com/Duximpresa/Media-Dump
```

作者：

```text
Duximpresa
```

## 当前状态

- GitHub 最新稳定版本：`v0.3.0`。
- 当前源码版本：`0.3.0`。
- 本地正式版程序：

```text
dist/MediaDump-v0.3.0-Windows-x64.exe
```

- 本地生成的手动测试素材位于：

```text
test_samples_20260531_024046/
```

除非用户明确要求，否则将 `test_samples_*` 视为一次性的本地测试素材，不要提交到 Git。

开始修改前必须检查：

```powershell
git status --short --branch
```

不要撤销、覆盖或丢弃当前未提交的修改。

## 运行环境和入口

- Python：3.12
- GUI：Tkinter
- 程序入口：

```text
media_date_copier.py
```

从源码运行：

```powershell
python media_date_copier.py
```

应用版本号只允许定义在：

```text
media_copier/__init__.py
```

需要显示版本号时，统一读取 `media_copier.__version__`，不要在界面或其他模块重复写死版本号。

## 代码结构

```text
media_date_copier.py        程序入口
media_copier/app.py         Tkinter 界面、菜单、分页和事件处理
media_copier/config.py      JSON 配置持久化
media_copier/constants.py   文件扩展名和日期模板常量
media_copier/scanner.py     源文件扫描
media_copier/templates.py   日期变量和目标路径生成
media_copier/planner.py     导入预览和重复文件处理计划
media_copier/copier.py      文件复制、进度、取消和校验
media_copier/hash_utils.py  SHA-256 文件校验
media_copier/file_types.py  文件扩展名筛选
media_copier/formatting.py  文件大小和速度格式化
media_copier/models.py      导入和复制数据结构
media_copier/renamer.py     批量重命名计划和执行
scripts/generate_icon.py    重新生成 PNG/ICO 应用图标
assets/icon/                SVG、PNG 和 ICO 图标资源
test_media_date_copier.py   单元测试和文件系统集成测试
```

不要把文件系统核心逻辑写进 `app.py`。复制、预览、校验和重命名行为应放在对应模块中，并添加测试。

## 导入复制流程

默认目标路径模板：

```text
{year}/{month}/{year}-{month}-{day}/{filename}
```

示例：

```text
2026/05/2026-05-26/IMG_0001.JPG
```

当前日期来源是 Windows 文件创建时间，通过 `os.path.getctime()` 获取。

用户必须先生成导入预览，之后才能执行复制。预览和复制必须共用同一个 `ImportPlan`，复制过程中不要再次独立计算目标路径。

同名文件处理规则：

- 目标文件同名且大小相同：跳过。
- 目标文件同名但大小不同：添加 `_1`、`_2` 等编号。
- 永远不要覆盖已经存在的文件。

复制规则：

- 先复制到临时 `.copying` 文件。
- 保留源文件元数据。
- 完成后将临时文件原子替换为最终文件。
- 对复制成功的文件执行 SHA-256 校验。
- 取消操作会在当前文件处理完成后停止。
- 已复制完成的文件不会回滚或删除。

配置文件位置：

```text
%APPDATA%/MediaDateCopier/config.json
```

源文件夹和目标文件夹必须使用不同的配置字段保存。

## 批量重命名流程

Beta 界面使用两个 `ttk.Notebook` 分页：

- `导入复制`
- `批量重命名`

所有重命名操作必须先预览，再允许执行。

### 查找替换

- 可以只处理文件、只处理文件夹，或者两者都处理。
- 可以只处理目标目录直属项目，也可以递归处理。
- 查找内容不能为空。
- 文件名中的每一处匹配文本都会被替换。
- 递归重命名文件夹时，必须按路径深度从深到浅执行，避免父目录先改名导致子路径失效。

### 序列重命名

- 只处理指定目录中的直属文件。
- 不处理子文件夹中的文件。
- 使用文件名自然排序，例如 `IMG_2` 排在 `IMG_10` 前面。
- 保留原文件扩展名。
- 支持设置前缀、起始编号和编号位数。

### 冲突处理

- 遇到目标名称已存在时跳过。
- 永远不要覆盖已有文件或文件夹。
- 预览中必须显示被跳过或发生冲突的项目。
- 任何重命名设置改变后，之前的预览必须失效。

## 界面约定

- 导入和重命名工作流必须通过分页清晰区分。
- 耗时的复制任务必须在后台线程中运行。
- Tkinter 控件更新必须通过主线程事件队列完成。
- 界面标签和提示信息使用清晰的中文。
- 保留现有的 `帮助 > 关于` 菜单。
- 关于弹窗中的版本号必须读取 `media_copier.__version__`。

PowerShell 可能因为控制台编码问题，把正常的 UTF-8 中文源码显示成乱码。不要仅根据 `Get-Content` 的显示判断文件已损坏。

需要确认文件实际内容时，可以使用：

```powershell
python -c "from pathlib import Path; print(Path('media_copier/app.py').read_text(encoding='utf-8'))"
```

## 测试

修改功能后运行完整测试：

```powershell
python -m unittest -v
```

运行语法和导入编译检查：

```powershell
$env:PYTHONPYCACHEPREFIX='.pycache-check'
python -m compileall -q media_date_copier.py media_copier test_media_date_copier.py scripts
```

当前 Beta 源码预期包含 18 个测试。

测试必须使用临时目录，并覆盖：

- 导入目标路径生成。
- 重复文件跳过和自动改名。
- 复制取消。
- SHA-256 校验成功和失败。
- 查找替换文件和文件夹。
- 递归和非递归重命名。
- 自然排序和编号补零。
- 重命名冲突时跳过且不覆盖。
- 递归文件夹从深到浅重命名。

## 手动测试素材

本地测试素材目录包含：

```text
import_source/    导入预览和复制测试的源文件
import_target/    用于测试跳过和自动改名的已有目标文件
rename_replace/   查找替换文件、文件夹、嵌套目录和冲突文件
rename_sequence/  自然排序文件和一个应被忽略的嵌套文件
```

手动测试前先阅读该目录中的：

```text
README_TESTING.txt
```

## 打包

PyInstaller 安装在用户 Python 环境中。因为 `pyinstaller` 命令可能没有加入 `PATH`，应通过模块方式调用。

Conda 的 Tk DLL 目录必须加入当前 PowerShell 的 `PATH`：

```powershell
$env:PATH='D:\ProgramData\miniconda3\envs\main\Library\bin;' + $env:PATH
python -m PyInstaller --clean --onefile --windowed --name MediaDump --icon assets\icon\mediadump-icon.ico --add-data "assets\icon\mediadump-icon.ico;assets\icon" --add-data "assets\icon\mediadump-icon-1024.png;assets\icon" media_date_copier.py
```

默认输出：

```text
dist/MediaDump.exe
```

正式版命名：

```powershell
Copy-Item dist\MediaDump.exe dist\MediaDump-v0.3.0-Windows-x64.exe
```

Windows 打包日志中出现以下 Unix 可选模块缺失属于正常现象：

```text
grp
pwd
posix
resource
fcntl
```

如果出现 `tcl86t.dll` 或 `tk86t.dll` 缺失，则说明打包前没有正确加入 Conda 的 `Library\bin` 路径。

## Git 和发布

除非用户明确要求，否则不要自动提交或发布。

提交前运行：

```powershell
python -m unittest -v
git status --short
```

稳定版本附件命名：

```text
MediaDump-vX.Y.Z-Windows-x64.exe
```

Beta 版本附件命名：

```text
MediaDump-vX.Y.Z-beta.N-Windows-x64.exe
```

GitHub CLI 路径：

```text
C:\Program Files\GitHub CLI\gh.exe
```

检查登录状态：

```powershell
& 'C:\Program Files\GitHub CLI\gh.exe' auth status
```

创建 Release 前，必须先提交并推送源码，然后创建并推送对应 Tag。发布 Beta 版本时，应在 GitHub Releases 中标记为预发布版本。

## 安全规则

- 永远不要覆盖源素材。
- 永远不要覆盖已经存在的重命名目标。
- 导入完成后不要删除源素材。
- 相关设置发生变化时，必须让已有预览失效。
- 保留已有用户配置字段，修改默认值时要谨慎迁移。
- 除非明确要求，否则不要提交以下内容：

```text
build/
dist/
.tools/
*.spec
__pycache__/
test_samples_*/
```
