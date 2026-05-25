import queue
import threading
from pathlib import Path
from tkinter import (
    BooleanVar,
    Button,
    Checkbutton,
    Entry,
    Frame,
    Label,
    LabelFrame,
    StringVar,
    Tk,
    filedialog,
    messagebox,
)
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from .config import load_config, save_config
from .constants import (
    CUSTOM_TEMPLATE_LABEL,
    DATE_TEMPLATES,
    DEFAULT_TEMPLATE,
    PHOTO_EXTENSIONS,
    VIDEO_EXTENSIONS,
)
from .copier import copy_files
from .file_types import selected_extensions
from .formatting import format_bytes, format_speed
from .models import CopyStats
from .templates import validate_template


class MediaDateCopierApp:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title("摄影素材按日期复制工具")
        self.root.geometry("940x690")
        self.root.minsize(780, 580)

        self.config = load_config()
        self.events: queue.Queue = queue.Queue()
        self.cancel_event = threading.Event()
        self.worker: threading.Thread | None = None

        self.source_var = StringVar(value=self.config.get("source_dir", ""))
        self.target_var = StringVar(value=self.config.get("target_dir", ""))
        self.custom_ext_var = StringVar(
            value=self.config.get(
                "custom_extensions",
                ",".join(PHOTO_EXTENSIONS + VIDEO_EXTENSIONS),
            )
        )
        saved_template = self.config.get("date_template", DEFAULT_TEMPLATE)
        self.template_choice_var = StringVar(value=self._choice_for_template(saved_template))
        self.custom_template_var = StringVar(value=saved_template)
        self.current_file_var = StringVar(value="等待开始")
        self.status_var = StringVar(value="请选择源文件夹和目标文件夹")
        self.stats_var = StringVar(value="成功 0 / 跳过 0 / 失败 0")
        self.speed_var = StringVar(value="速度 0 B/s / 已处理 0 B")

        selected_modes = set(self.config.get("selected_modes", ["photos", "videos"]))
        self.photos_var = BooleanVar(value="photos" in selected_modes)
        self.videos_var = BooleanVar(value="videos" in selected_modes)
        self.all_files_var = BooleanVar(value="all" in selected_modes)
        self.custom_files_var = BooleanVar(value="custom" in selected_modes)

        self._build_ui()
        self._toggle_custom_template()
        self._poll_events()

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(4, weight=1)

        paths_frame = LabelFrame(self.root, text="路径")
        paths_frame.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 8))
        paths_frame.columnconfigure(1, weight=1)

        Label(paths_frame, text="源文件夹").grid(row=0, column=0, sticky="w", padx=10, pady=8)
        Entry(paths_frame, textvariable=self.source_var).grid(
            row=0, column=1, sticky="ew", padx=8, pady=8
        )
        Button(paths_frame, text="选择源", command=self.choose_source).grid(
            row=0, column=2, padx=10, pady=8
        )

        Label(paths_frame, text="目标文件夹").grid(row=1, column=0, sticky="w", padx=10, pady=8)
        Entry(paths_frame, textvariable=self.target_var).grid(
            row=1, column=1, sticky="ew", padx=8, pady=8
        )
        Button(paths_frame, text="选择目标", command=self.choose_target).grid(
            row=1, column=2, padx=10, pady=8
        )

        types_frame = LabelFrame(self.root, text="复制文件类型")
        types_frame.grid(row=1, column=0, sticky="ew", padx=14, pady=8)
        types_frame.columnconfigure(4, weight=1)

        Checkbutton(types_frame, text="照片", variable=self.photos_var, command=self._on_mode_changed).grid(
            row=0, column=0, padx=10, pady=8, sticky="w"
        )
        Checkbutton(types_frame, text="视频", variable=self.videos_var, command=self._on_mode_changed).grid(
            row=0, column=1, padx=10, pady=8, sticky="w"
        )
        Checkbutton(
            types_frame,
            text="全部文件",
            variable=self.all_files_var,
            command=self._on_mode_changed,
        ).grid(row=0, column=2, padx=10, pady=8, sticky="w")
        Checkbutton(
            types_frame,
            text="自定义扩展名",
            variable=self.custom_files_var,
            command=self._on_mode_changed,
        ).grid(row=0, column=3, padx=10, pady=8, sticky="w")
        Entry(types_frame, textvariable=self.custom_ext_var).grid(
            row=0, column=4, sticky="ew", padx=(4, 10), pady=8
        )

        template_frame = LabelFrame(self.root, text="保存路径格式")
        template_frame.grid(row=2, column=0, sticky="ew", padx=14, pady=8)
        template_frame.columnconfigure(1, weight=1)

        Label(template_frame, text="格式").grid(row=0, column=0, sticky="w", padx=10, pady=8)
        template_combo = ttk.Combobox(
            template_frame,
            textvariable=self.template_choice_var,
            values=list(DATE_TEMPLATES.keys()),
            state="readonly",
        )
        template_combo.grid(row=0, column=1, sticky="ew", padx=8, pady=8)
        template_combo.bind("<<ComboboxSelected>>", self._on_template_changed)

        Label(template_frame, text="模板").grid(row=1, column=0, sticky="w", padx=10, pady=8)
        self.template_entry = Entry(template_frame, textvariable=self.custom_template_var)
        self.template_entry.grid(row=1, column=1, sticky="ew", padx=8, pady=8)

        controls_frame = Frame(self.root)
        controls_frame.grid(row=3, column=0, sticky="ew", padx=14, pady=8)
        controls_frame.columnconfigure(2, weight=1)

        self.start_button = Button(controls_frame, text="开始复制", command=self.start_copy)
        self.start_button.grid(row=0, column=0, padx=(0, 8), pady=4)
        self.cancel_button = Button(
            controls_frame,
            text="取消",
            command=self.cancel_copy,
            state="disabled",
        )
        self.cancel_button.grid(row=0, column=1, padx=8, pady=4)
        Label(controls_frame, textvariable=self.status_var, anchor="w").grid(
            row=0, column=2, sticky="ew", padx=8
        )

        progress_frame = LabelFrame(self.root, text="复制进度")
        progress_frame.grid(row=4, column=0, sticky="nsew", padx=14, pady=(8, 14))
        progress_frame.columnconfigure(0, weight=1)
        progress_frame.rowconfigure(5, weight=1)

        self.progress = ttk.Progressbar(progress_frame, maximum=100, value=0)
        self.progress.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        Label(progress_frame, textvariable=self.current_file_var, anchor="w").grid(
            row=1, column=0, sticky="ew", padx=10, pady=4
        )
        Label(progress_frame, textvariable=self.stats_var, anchor="w").grid(
            row=2, column=0, sticky="ew", padx=10, pady=4
        )
        Label(progress_frame, textvariable=self.speed_var, anchor="w").grid(
            row=3, column=0, sticky="ew", padx=10, pady=4
        )
        self.log_text = ScrolledText(progress_frame, height=14, wrap="word")
        self.log_text.grid(row=5, column=0, sticky="nsew", padx=10, pady=(6, 10))
        self.log_text.configure(state="disabled")

    def choose_source(self) -> None:
        selected = filedialog.askdirectory(
            title="选择源文件夹",
            initialdir=self.source_var.get().strip() or None,
        )
        if selected:
            self.source_var.set(selected)
            self._save_current_config()

    def choose_target(self) -> None:
        selected = filedialog.askdirectory(
            title="选择目标文件夹",
            initialdir=self.target_var.get().strip() or None,
        )
        if selected:
            self.target_var.set(selected)
            self._save_current_config()

    def start_copy(self) -> None:
        source_text = self.source_var.get().strip()
        target_text = self.target_var.get().strip()
        source_dir = Path(source_text)
        target_dir = Path(target_text)
        template = self.custom_template_var.get().strip()

        if not source_text or not source_dir.is_dir():
            messagebox.showerror("无法开始", "请选择有效的源文件夹。")
            return
        if not target_text:
            messagebox.showerror("无法开始", "请选择有效的目标文件夹。")
            return
        if not template:
            messagebox.showerror("无法开始", "保存路径模板不能为空。")
            return

        try:
            validate_template(template)
        except ValueError as exc:
            messagebox.showerror("模板错误", str(exc))
            return

        extensions = self._selected_extensions()
        if extensions == set():
            messagebox.showerror("无法开始", "请选择至少一种文件类型，或填写自定义扩展名。")
            return

        self._save_current_config()
        self.cancel_event.clear()
        self._clear_log()
        self.progress.configure(maximum=100, value=0)
        self.current_file_var.set("正在扫描文件...")
        self.status_var.set("正在运行")
        self.stats_var.set("成功 0 / 跳过 0 / 失败 0")
        self.speed_var.set("速度 0 B/s / 已处理 0 B")
        self.start_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")

        self.worker = threading.Thread(
            target=copy_files,
            args=(source_dir, target_dir, extensions, template, self.cancel_event, self.events),
            daemon=True,
        )
        self.worker.start()

    def cancel_copy(self) -> None:
        self.cancel_event.set()
        self.status_var.set("正在取消，当前文件完成后停止...")
        self.cancel_button.configure(state="disabled")
        self._append_log("已请求取消：当前文件完成后停止。")

    def _selected_extensions(self) -> set[str] | None:
        return selected_extensions(
            include_photos=self.photos_var.get(),
            include_videos=self.videos_var.get(),
            include_all=self.all_files_var.get(),
            include_custom=self.custom_files_var.get(),
            custom_extensions=self.custom_ext_var.get(),
        )

    def _on_mode_changed(self) -> None:
        if self.all_files_var.get():
            self.photos_var.set(False)
            self.videos_var.set(False)
            self.custom_files_var.set(False)
        self._save_current_config()

    def _on_template_changed(self, _event=None) -> None:
        choice = self.template_choice_var.get()
        template = DATE_TEMPLATES.get(choice, DEFAULT_TEMPLATE)
        if template:
            self.custom_template_var.set(template)
        self._toggle_custom_template()
        self._save_current_config()

    def _toggle_custom_template(self) -> None:
        state = "normal" if self.template_choice_var.get() == CUSTOM_TEMPLATE_LABEL else "readonly"
        self.template_entry.configure(state=state)

    def _choice_for_template(self, template: str) -> str:
        for label, value in DATE_TEMPLATES.items():
            if value == template and label != CUSTOM_TEMPLATE_LABEL:
                return label
        return CUSTOM_TEMPLATE_LABEL

    def _save_current_config(self) -> None:
        selected_modes = []
        if self.photos_var.get():
            selected_modes.append("photos")
        if self.videos_var.get():
            selected_modes.append("videos")
        if self.all_files_var.get():
            selected_modes.append("all")
        if self.custom_files_var.get():
            selected_modes.append("custom")

        save_config(
            {
                "source_dir": self.source_var.get().strip(),
                "target_dir": self.target_var.get().strip(),
                "selected_modes": selected_modes,
                "custom_extensions": self.custom_ext_var.get().strip(),
                "date_template": self.custom_template_var.get().strip() or DEFAULT_TEMPLATE,
                "duplicate_policy": "skip",
            }
        )

    def _poll_events(self) -> None:
        while True:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            self._handle_event(event)
        self.root.after(100, self._poll_events)

    def _handle_event(self, event: tuple) -> None:
        event_type = event[0]
        if event_type == "total":
            _, total_files, total_bytes = event
            self.progress.configure(maximum=max(total_bytes, 1), value=0)
            self.status_var.set(f"找到 {total_files} 个文件，共 {format_bytes(total_bytes)}")
            if total_files == 0:
                self.current_file_var.set("没有匹配的文件")
        elif event_type == "current":
            _, file_name, stats = event
            self.current_file_var.set(f"正在处理：{file_name}")
            self._update_progress(stats)
        elif event_type == "progress":
            self._update_progress(event[1])
        elif event_type == "log":
            self._append_log(event[1])
        elif event_type == "fatal":
            self._finish_with_message("复制失败", event[1])
        elif event_type == "done":
            self._finish_copy(event[1])

    def _update_progress(self, stats: CopyStats) -> None:
        self.progress.configure(value=min(stats.processed_bytes, max(stats.total_bytes, 1)))
        self.stats_var.set(
            f"成功 {stats.copied} / 跳过 {stats.skipped} / 失败 {stats.failed} / "
            f"文件 {stats.processed_files}/{stats.total_files}"
        )
        self.speed_var.set(
            f"当前速度 {format_speed(stats.current_speed_bps)} / "
            f"平均 {format_speed(stats.average_speed_bps)} / "
            f"已处理 {format_bytes(stats.processed_bytes)}"
        )

    def _finish_copy(self, stats: CopyStats) -> None:
        self.start_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")
        self._update_progress(stats)

        if stats.cancelled:
            title = "已取消"
            status = "已取消"
        else:
            title = "复制完成"
            status = "完成"

        self.status_var.set(status)
        self.current_file_var.set(status)
        summary = (
            f"总数：{stats.total_files}\n"
            f"总大小：{format_bytes(stats.total_bytes)}\n"
            f"已处理：{stats.processed_files}\n"
            f"已复制：{stats.copied}\n"
            f"已跳过：{stats.skipped}\n"
            f"失败：{stats.failed}\n"
            f"未处理：{stats.remaining_files}\n"
            f"平均速度：{format_speed(stats.average_speed_bps)}"
        )
        self._append_log(summary.replace("\n", "；"))
        messagebox.showinfo(title, summary)

    def _finish_with_message(self, title: str, message: str) -> None:
        self.start_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")
        self.status_var.set(title)
        self.current_file_var.set(message)
        self._append_log(message)
        messagebox.showerror(title, message)

    def _append_log(self, message: str) -> None:
        from datetime import datetime

        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")


def main() -> None:
    root = Tk()
    MediaDateCopierApp(root)
    root.mainloop()
