import queue
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from media_copier.constants import DEFAULT_TEMPLATE
from media_copier.copier import copy_files
from media_copier.file_types import normalize_extensions
from media_copier.models import ACTION_COPY_RENAMED, ACTION_SKIP_DUPLICATE
from media_copier.planner import build_import_plan
from media_copier.renamer import (
    RENAME_ACTION_RENAME,
    RENAME_ACTION_SKIP,
    build_replace_plan,
    build_sequence_plan,
    execute_rename_plan,
    rename_with_retry,
)
from media_copier.templates import (
    build_target_path,
)


class MediaDateCopierTests(unittest.TestCase):
    def test_normalize_extensions_accepts_commas_semicolons_and_missing_dots(self):
        self.assertEqual(
            normalize_extensions("jpg, .MP4;mov"),
            {".jpg", ".mp4", ".mov"},
        )

    def test_default_template_builds_expected_path(self):
        source = Path("IMG_0001.JPG")
        target = Path("D:/Photos")
        fake_time = 1782432000
        with mock.patch("media_copier.templates.os.path.getctime", return_value=fake_time):
            result = build_target_path(source, target, DEFAULT_TEMPLATE)
        self.assertEqual(result, target / "2026" / "06" / "2026-06-26" / "IMG_0001.JPG")

    def test_copy_files_skips_existing_destination(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_dir = root / "source"
            target_dir = root / "target"
            source_dir.mkdir()
            existing = source_dir / "IMG_0001.JPG"
            existing.write_text("new", encoding="utf-8")

            destination = build_target_path(existing, target_dir, DEFAULT_TEMPLATE)
            destination.parent.mkdir(parents=True)
            destination.write_text("old", encoding="utf-8")

            events = queue.Queue()
            stats = copy_files(
                source_dir,
                target_dir,
                {".jpg"},
                DEFAULT_TEMPLATE,
                threading.Event(),
                events,
            )

            self.assertEqual(stats.total_files, 1)
            self.assertEqual(stats.copied, 0)
            self.assertEqual(stats.skipped, 1)
            self.assertEqual(destination.read_text(encoding="utf-8"), "old")
            self.assertEqual(stats.verify_success, 0)

    def test_import_plan_renames_existing_destination_with_different_size(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_dir = root / "source"
            target_dir = root / "target"
            source_dir.mkdir()
            source = source_dir / "IMG_0001.JPG"
            source.write_text("new content", encoding="utf-8")

            destination = build_target_path(source, target_dir, DEFAULT_TEMPLATE)
            destination.parent.mkdir(parents=True)
            destination.write_text("old", encoding="utf-8")

            plan = build_import_plan(source_dir, target_dir, {".jpg"}, DEFAULT_TEMPLATE)

            self.assertEqual(plan.summary.total_files, 1)
            self.assertEqual(plan.summary.copy_count, 1)
            self.assertEqual(plan.summary.renamed_count, 1)
            self.assertEqual(plan.items[0].action, ACTION_COPY_RENAMED)
            self.assertEqual(plan.items[0].destination.name, "IMG_0001_1.JPG")

    def test_import_plan_skips_existing_destination_with_same_size(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_dir = root / "source"
            target_dir = root / "target"
            source_dir.mkdir()
            source = source_dir / "IMG_0001.JPG"
            source.write_text("abc", encoding="utf-8")

            destination = build_target_path(source, target_dir, DEFAULT_TEMPLATE)
            destination.parent.mkdir(parents=True)
            destination.write_text("xyz", encoding="utf-8")

            plan = build_import_plan(source_dir, target_dir, {".jpg"}, DEFAULT_TEMPLATE)

            self.assertEqual(plan.summary.skip_count, 1)
            self.assertEqual(plan.items[0].action, ACTION_SKIP_DUPLICATE)

    def test_import_plan_renames_repeated_planned_destinations(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_dir = root / "source"
            target_dir = root / "target"
            nested = source_dir / "nested"
            nested.mkdir(parents=True)
            (source_dir / "IMG_0001.JPG").write_text("a", encoding="utf-8")
            (nested / "IMG_0001.JPG").write_text("bb", encoding="utf-8")

            plan = build_import_plan(source_dir, target_dir, {".jpg"}, DEFAULT_TEMPLATE)
            destinations = sorted(item.destination.name for item in plan.items)

            self.assertEqual(plan.summary.total_files, 2)
            self.assertEqual(plan.summary.renamed_count, 1)
            self.assertEqual(destinations, ["IMG_0001.JPG", "IMG_0001_1.JPG"])

    def test_copy_files_can_be_cancelled_before_start(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_dir = root / "source"
            target_dir = root / "target"
            source_dir.mkdir()
            for index in range(3):
                (source_dir / f"IMG_{index}.JPG").write_text("x", encoding="utf-8")

            cancel_event = threading.Event()
            cancel_event.set()
            stats = copy_files(
                source_dir,
                target_dir,
                {".jpg"},
                DEFAULT_TEMPLATE,
                cancel_event,
                queue.Queue(),
            )

            self.assertTrue(stats.cancelled)
            self.assertEqual(stats.processed_files, 0)
            self.assertEqual(stats.remaining_files, 3)
            self.assertFalse(target_dir.exists())

    def test_copy_files_tracks_bytes_and_average_speed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_dir = root / "source"
            target_dir = root / "target"
            source_dir.mkdir()
            (source_dir / "CLIP_0001.MP4").write_bytes(b"x" * 2048)

            stats = copy_files(
                source_dir,
                target_dir,
                {".mp4"},
                DEFAULT_TEMPLATE,
                threading.Event(),
                queue.Queue(),
            )

            self.assertEqual(stats.total_files, 1)
            self.assertEqual(stats.total_bytes, 2048)
            self.assertEqual(stats.processed_bytes, 2048)
            self.assertEqual(stats.copied, 1)
            self.assertEqual(stats.verify_success, 1)
            self.assertEqual(stats.verify_failed, 0)
            self.assertGreater(stats.average_speed_bps, 0)

    def test_copy_files_counts_hash_verification_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_dir = root / "source"
            target_dir = root / "target"
            source_dir.mkdir()
            (source_dir / "IMG_0002.JPG").write_bytes(b"image")

            with mock.patch("media_copier.copier.files_match_sha256", return_value=False):
                stats = copy_files(
                    source_dir,
                    target_dir,
                    {".jpg"},
                    DEFAULT_TEMPLATE,
                    threading.Event(),
                    queue.Queue(),
                )

            self.assertEqual(stats.copied, 0)
            self.assertEqual(stats.failed, 1)
            self.assertEqual(stats.verify_success, 0)
            self.assertEqual(stats.verify_failed, 1)

    def test_replace_plan_files_only_non_recursive(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "old_file.jpg").write_text("x", encoding="utf-8")
            (root / "old_folder").mkdir()

            plan = build_replace_plan(root, "old", "new", True, False, False)

            self.assertEqual(plan.summary.rename_count, 1)
            self.assertEqual(plan.summary.file_count, 1)
            self.assertEqual(plan.items[0].destination.name, "new_file.jpg")

    def test_replace_plan_folders_only_recursive(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            nested = root / "keep"
            nested.mkdir()
            (nested / "old_dir").mkdir()
            (nested / "old_file.jpg").write_text("x", encoding="utf-8")

            plan = build_replace_plan(root, "old", "new", False, True, True)

            self.assertEqual(plan.summary.rename_count, 1)
            self.assertEqual(plan.summary.folder_count, 1)
            self.assertEqual(plan.items[0].destination.name, "new_dir")

    def test_replace_plan_rejects_empty_find_text(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError):
                build_replace_plan(Path(temp_dir), "", "new", True, False, False)

    def test_sequence_plan_direct_files_only_with_padding(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "IMG_10.jpg").write_text("x", encoding="utf-8")
            (root / "IMG_2.jpg").write_text("x", encoding="utf-8")
            nested = root / "nested"
            nested.mkdir()
            (nested / "IMG_1.jpg").write_text("x", encoding="utf-8")

            plan = build_sequence_plan(root, "Shoot_", 1, 3)
            destinations = [item.destination.name for item in plan.items]

            self.assertEqual(destinations, ["Shoot_001.jpg", "Shoot_002.jpg"])
            self.assertEqual(plan.summary.file_count, 2)

    def test_rename_plan_skips_conflicts_without_overwriting(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "old.jpg"
            conflict = root / "new.jpg"
            source.write_text("source", encoding="utf-8")
            conflict.write_text("conflict", encoding="utf-8")

            plan = build_replace_plan(root, "old", "new", True, False, False)
            result = execute_rename_plan(plan)

            self.assertEqual(plan.items[0].action, RENAME_ACTION_SKIP)
            self.assertEqual(result.renamed, 0)
            self.assertEqual(result.skipped, 1)
            self.assertEqual(conflict.read_text(encoding="utf-8"), "conflict")
            self.assertTrue(source.exists())

    def test_execute_rename_plan_renames_deep_paths_first(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            folder = root / "old_dir"
            folder.mkdir()
            child = folder / "old_file.txt"
            child.write_text("x", encoding="utf-8")

            plan = build_replace_plan(root, "old", "new", True, True, True)
            result = execute_rename_plan(plan)

            self.assertEqual(result.renamed, 2)
            self.assertTrue((root / "new_dir" / "new_file.txt").exists())

    def test_execute_rename_plan_processes_files_before_folders(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            folder = root / "old_dir"
            folder.mkdir()
            child = folder / "old_file.txt"
            child.write_text("x", encoding="utf-8")
            plan = build_replace_plan(root, "old", "new", True, True, True)

            real_rename = Path.rename
            calls = []

            def record_rename(source, destination):
                calls.append(source)
                return real_rename(source, destination)

            with mock.patch(
                "media_copier.renamer.rename_with_retry",
                side_effect=record_rename,
            ):
                result = execute_rename_plan(plan)

            self.assertEqual(result.renamed, 2)
            self.assertEqual(calls, [child, folder])

    def test_rename_with_retry_recovers_from_temporary_permission_error(self):
        source = Path("old_folder")
        destination = Path("new_folder")
        denied = PermissionError(13, "Access is denied")
        denied.winerror = 5

        with (
            mock.patch.object(Path, "rename", side_effect=[denied, None]) as rename,
            mock.patch("media_copier.renamer.time.sleep") as sleep,
        ):
            rename_with_retry(source, destination)

        self.assertEqual(rename.call_count, 2)
        sleep.assert_called_once_with(0.2)

    def test_execute_rename_plan_reports_permanent_access_denied(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "old_folder"
            source.mkdir()
            plan = build_replace_plan(root, "old", "new", False, True, False)
            denied = PermissionError(13, "Access is denied")
            denied.winerror = 5

            with mock.patch(
                "media_copier.renamer.rename_with_retry",
                side_effect=denied,
            ):
                result = execute_rename_plan(plan)

            self.assertEqual(result.failed, 1)
            self.assertEqual(result.renamed, 0)
            self.assertTrue(source.exists())
            self.assertIn("Windows 错误 5", result.messages[0])
            self.assertIn(str(plan.items[0].destination), result.messages[0])


if __name__ == "__main__":
    unittest.main()
