# 摄影素材按日期复制工具

这是一个 Python + Tkinter 的 Windows 桌面小工具，用来把内存卡或任意源文件夹里的照片、视频复制到电脑，并按 Windows 文件创建时间分类保存。

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
- 复制时显示进度、当前文件、当前速度、平均速度和日志
- 目标文件已存在时跳过
- 支持复制过程中取消，已复制的文件会保留

## 代码结构

```text
media_date_copier.py       程序入口
media_copier/app.py        Tkinter 界面
media_copier/copier.py     复制引擎、速度统计、取消控制
media_copier/scanner.py    文件扫描
media_copier/templates.py  日期路径模板
media_copier/config.py     配置读写
media_copier/file_types.py 文件类型选择
```

配置文件保存在：

```text
%APPDATA%/MediaDateCopier/config.json
```

## 后续打包为 EXE

安装 PyInstaller 后可以执行：

```powershell
pyinstaller --onefile --windowed media_date_copier.py
```
