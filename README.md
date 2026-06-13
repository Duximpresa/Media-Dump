# 摄影素材按日期复制工具

MediaDump 是一个 Python + Tkinter 的 Windows 桌面小工具，用来把内存卡或任意源文件夹里的照片、视频复制到电脑，并按 Windows 文件创建时间分类保存。

## 运行

```powershell
python media_date_copier.py
```

## 默认保存格式

```text
{year}/{month}/{year}-{month}-{day}/{filename}
```

示例：

```text
2026/05/2026-05-26/IMG_0001.JPG
```

## 功能

- 选择源文件夹和目标文件夹
- 分别记忆源文件夹和目标文件夹路径
- 选择照片、视频、全部文件或自定义扩展名
- 导入前预览文件数量、总大小、跳过数量、自动改名数量和日期文件夹数量
- 目标文件已存在且大小相同时自动跳过
- 目标文件已存在但大小不同时自动改名，避免覆盖
- 复制时显示进度、当前文件、当前速度、平均速度和日志
- 复制完成后使用 SHA-256 校验源文件和目标文件
- 支持复制过程中取消，已复制的文件会保留
- 批量重命名分页：
  - 查找替换指定目录下的文件和文件夹名称
  - 可选择是否包含子文件夹和里面的文件
  - 对指定文件夹直属文件进行序列重命名
  - 重命名前必须预览，遇到冲突默认跳过且不覆盖

## 代码结构

```text
media_date_copier.py       程序入口
media_copier/app.py        Tkinter 界面
media_copier/planner.py    导入预览和重复处理计划
media_copier/copier.py     复制引擎、速度统计、取消控制、校验
media_copier/hash_utils.py SHA-256 文件校验
media_copier/scanner.py    文件扫描
media_copier/templates.py  日期路径模板
media_copier/config.py     配置读写
media_copier/file_types.py 文件类型选择
media_copier/renamer.py    批量重命名计划和执行
```

配置文件保存在：

```text
%APPDATA%/MediaDateCopier/config.json
```

## 打包为 EXE

Conda 环境下建议先把 Tk DLL 路径加入当前 PowerShell：

```powershell
$env:PATH='D:\ProgramData\miniconda3\envs\main\Library\bin;' + $env:PATH
python -m PyInstaller --clean --onefile --windowed --name MediaDump --icon assets\icon\mediadump-icon.ico --add-data "assets\icon\mediadump-icon.ico;assets\icon" --add-data "assets\icon\mediadump-icon-1024.png;assets\icon" media_date_copier.py
```
