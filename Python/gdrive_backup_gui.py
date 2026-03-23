#!/usr/bin/env python3
from __future__ import annotations

import fnmatch
import os
import queue
import shutil
import threading
import traceback
from pathlib import Path
from typing import Callable

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

EXCLUDED_DIR_NAMES = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    "bin",
    "obj",
    "build",
    "dist",
    "out",
    "target",
    "coverage",
    "_result",
    "tmp",
    "temp",
    "cache",
    ".cache",
    "logs",
    "log",
    ".idea",
    ".vscode",
}

EXCLUDED_FILE_PATTERNS = [
    "*.log",
    "*.tmp",
    "*.cache",
    ".env",
    ".env.*",
    "Thumbs.db",
    ".DS_Store",
]


def is_excluded(rel_path: Path, is_dir: bool) -> bool:
    parts = rel_path.parts
    if any(part in EXCLUDED_DIR_NAMES for part in parts):
        return True

    if is_dir:
        return rel_path.name in EXCLUDED_DIR_NAMES

    name = rel_path.name
    return any(fnmatch.fnmatch(name, pattern) for pattern in EXCLUDED_FILE_PATTERNS)


def needs_copy(src: Path, dst: Path) -> bool:
    if not dst.exists():
        return True

    src_stat = src.stat()
    dst_stat = dst.stat()
    if src_stat.st_size != dst_stat.st_size:
        return True

    return abs(src_stat.st_mtime - dst_stat.st_mtime) > 1.0


def ensure_dir(path: Path, dry_run: bool) -> None:
    if path.exists() or dry_run:
        return
    path.mkdir(parents=True, exist_ok=True)


def run_backup(
    source: Path,
    dest: Path,
    dry_run: bool = False,
    delete: bool = False,
    verbose: bool = False,
    log_func: Callable[[str], None] | None = None,
) -> dict[str, int]:
    source = source.resolve()
    dest = dest.resolve()

    if not source.exists() or not source.is_dir():
        raise ValueError(f"source directory not found: {source}")
    if source == dest:
        raise ValueError("source and destination are the same directory.")

    copied = 0
    deleted = 0
    skipped = 0
    expected_paths: set[str] = set()
    managed_top_level_dirs: set[str] = set()
    managed_top_level_files: set[str] = set()

    ensure_dir(dest, dry_run)

    for entry in source.iterdir():
        rel_entry = Path(entry.name)
        if is_excluded(rel_entry, is_dir=entry.is_dir()):
            continue
        if entry.is_dir():
            managed_top_level_dirs.add(entry.name)
        elif entry.is_file():
            managed_top_level_files.add(entry.name)

    for root, dirs, files in os.walk(source):
        root_path = Path(root)
        rel_root = root_path.relative_to(source)

        kept_dirs: list[str] = []
        for dname in dirs:
            rel_dir = rel_root / dname if rel_root != Path(".") else Path(dname)
            if is_excluded(rel_dir, is_dir=True):
                continue
            kept_dirs.append(dname)
            expected_paths.add(rel_dir.as_posix())
            ensure_dir(dest / rel_dir, dry_run)
        dirs[:] = kept_dirs

        for fname in files:
            rel_file = rel_root / fname if rel_root != Path(".") else Path(fname)
            if is_excluded(rel_file, is_dir=False):
                skipped += 1
                continue

            src_file = source / rel_file
            dst_file = dest / rel_file
            expected_paths.add(rel_file.as_posix())
            ensure_dir(dst_file.parent, dry_run)

            if needs_copy(src_file, dst_file):
                copied += 1
                if verbose:
                    msg = f"[COPY] {rel_file}"
                    if log_func:
                        log_func(msg)
                    else:
                        print(msg)
                if not dry_run:
                    shutil.copy2(src_file, dst_file)

    if delete and dest.exists():
        for top_dir in managed_top_level_dirs:
            dest_top = dest / top_dir
            if not dest_top.exists():
                continue
            if not dest_top.is_dir():
                deleted += 1
                if verbose:
                    msg = f"[DEL ] {top_dir}"
                    if log_func:
                        log_func(msg)
                    else:
                        print(msg)
                if not dry_run:
                    dest_top.unlink(missing_ok=True)
                continue

            for root, dirs, files in os.walk(dest_top, topdown=False):
                rel_root = Path(root).relative_to(dest)

                for fname in files:
                    rel_file = rel_root / fname
                    if is_excluded(rel_file, is_dir=False):
                        continue
                    if rel_file.as_posix() not in expected_paths:
                        deleted += 1
                        if verbose:
                            msg = f"[DEL ] {rel_file}"
                            if log_func:
                                log_func(msg)
                            else:
                                print(msg)
                        if not dry_run:
                            (dest / rel_file).unlink(missing_ok=True)

                for dname in dirs:
                    rel_dir = rel_root / dname
                    if is_excluded(rel_dir, is_dir=True):
                        continue
                    dir_path = dest / rel_dir
                    if rel_dir.as_posix() not in expected_paths and dir_path.exists():
                        try:
                            if not any(dir_path.iterdir()):
                                deleted += 1
                                if verbose:
                                    msg = f"[DEL ] {rel_dir}/"
                                    if log_func:
                                        log_func(msg)
                                    else:
                                        print(msg)
                                if not dry_run:
                                    dir_path.rmdir()
                        except OSError:
                            pass

            top_rel = Path(top_dir)
            if top_rel.as_posix() not in expected_paths and dest_top.exists():
                try:
                    if not any(dest_top.iterdir()):
                        deleted += 1
                        if verbose:
                            msg = f"[DEL ] {top_rel}/"
                            if log_func:
                                log_func(msg)
                            else:
                                print(msg)
                        if not dry_run:
                            dest_top.rmdir()
                except OSError:
                    pass

        for top_file in managed_top_level_files:
            rel_file = Path(top_file)
            if rel_file.as_posix() in expected_paths:
                continue
            dest_file = dest / rel_file
            if dest_file.exists() and dest_file.is_file():
                deleted += 1
                if verbose:
                    msg = f"[DEL ] {rel_file}"
                    if log_func:
                        log_func(msg)
                    else:
                        print(msg)
                if not dry_run:
                    dest_file.unlink(missing_ok=True)

    return {"copied": copied, "skipped": skipped, "deleted": deleted}


class BackupGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Google Drive Backup")
        self.root.geometry("760x520")

        self.source_var = tk.StringVar(
            value=r"C:\Users\ron06\OneDrive\Documents\Program\GitHub"
        )
        self.dest_var = tk.StringVar(value=r"G:\マイドライブ\Program\Github")
        self.dry_run_var = tk.BooleanVar(value=False)
        self.delete_var = tk.BooleanVar(value=True)
        self.verbose_var = tk.BooleanVar(value=False)

        self.is_running = False
        self.msg_queue: queue.Queue[str] = queue.Queue()

        self._build_ui()
        self._poll_messages()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Source").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.source_var).grid(
            row=1, column=0, sticky="ew", padx=(0, 8)
        )
        ttk.Button(frame, text="参照", command=self._pick_source).grid(row=1, column=1)

        ttk.Label(frame, text="Destination").grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(frame, textvariable=self.dest_var).grid(
            row=3, column=0, sticky="ew", padx=(0, 8)
        )
        ttk.Button(frame, text="参照", command=self._pick_dest).grid(row=3, column=1)

        options = ttk.Frame(frame)
        options.grid(row=4, column=0, columnspan=2, sticky="w", pady=(10, 4))
        ttk.Checkbutton(options, text="Dry Run", variable=self.dry_run_var).pack(
            side=tk.LEFT, padx=(0, 12)
        )
        ttk.Checkbutton(options, text="Mirror Delete (--delete)", variable=self.delete_var).pack(
            side=tk.LEFT, padx=(0, 12)
        )
        ttk.Checkbutton(options, text="Verbose", variable=self.verbose_var).pack(side=tk.LEFT)

        self.run_btn = ttk.Button(frame, text="バックアップ実行", command=self._start_backup)
        self.run_btn.grid(row=5, column=0, sticky="w", pady=(8, 8))

        ttk.Label(frame, text="Log").grid(row=6, column=0, sticky="w")
        self.log_text = tk.Text(frame, height=18, wrap=tk.WORD)
        self.log_text.grid(row=7, column=0, columnspan=2, sticky="nsew")
        self.log_text.configure(state=tk.DISABLED)

        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(7, weight=1)

    def _pick_source(self) -> None:
        path = filedialog.askdirectory(initialdir=self.source_var.get() or None)
        if path:
            self.source_var.set(path)

    def _pick_dest(self) -> None:
        path = filedialog.askdirectory(initialdir=self.dest_var.get() or None)
        if path:
            self.dest_var.set(path)

    def _append_log(self, msg: str) -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _poll_messages(self) -> None:
        try:
            while True:
                msg = self.msg_queue.get_nowait()
                self._append_log(msg)
        except queue.Empty:
            pass
        self.root.after(120, self._poll_messages)

    def _start_backup(self) -> None:
        if self.is_running:
            return

        source = Path(self.source_var.get().strip())
        dest = Path(self.dest_var.get().strip())
        dry_run = self.dry_run_var.get()
        delete = self.delete_var.get()
        verbose = self.verbose_var.get()

        if not str(source):
            messagebox.showerror("Error", "Source が空です。")
            return
        if not str(dest):
            messagebox.showerror("Error", "Destination が空です。")
            return

        self.is_running = True
        self.run_btn.configure(state=tk.DISABLED)
        self.msg_queue.put("=== Backup start ===")
        self.msg_queue.put(f"Source: {source}")
        self.msg_queue.put(f"Dest  : {dest}")
        self.msg_queue.put(f"Options: dry_run={dry_run}, delete={delete}, verbose={verbose}")

        t = threading.Thread(
            target=self._run_backup_worker,
            args=(source, dest, dry_run, delete, verbose),
            daemon=True,
        )
        t.start()

    def _run_backup_worker(
        self, source: Path, dest: Path, dry_run: bool, delete: bool, verbose: bool
    ) -> None:
        try:
            stats = run_backup(
                source=source,
                dest=dest,
                dry_run=dry_run,
                delete=delete,
                verbose=verbose,
                log_func=lambda msg: self.msg_queue.put(msg),
            )
            self.msg_queue.put("Backup finished")
            self.msg_queue.put(f"  Copied: {stats['copied']}")
            self.msg_queue.put(f"  Skipped (excluded): {stats['skipped']}")
            self.msg_queue.put(
                f"  Deleted (mirror mode): {stats['deleted'] if delete else 0}"
            )
            if dry_run:
                self.msg_queue.put("  Mode: DRY RUN")
        except Exception as e:
            self.msg_queue.put(f"[ERROR] {e}")
            self.msg_queue.put(traceback.format_exc())
        finally:
            self.root.after(0, self._finish_run)

    def _finish_run(self) -> None:
        self.is_running = False
        self.run_btn.configure(state=tk.NORMAL)
        self.msg_queue.put("=== End ===")


def main() -> None:
    root = tk.Tk()
    app = BackupGUI(root)
    _ = app
    root.mainloop()


if __name__ == "__main__":
    main()
