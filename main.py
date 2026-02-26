#! /usr/bin/env python3

import argparse
import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Mapping


def iter_files(base: Path, recursive: bool) -> Iterator[Path]:
    if recursive:
        for root, _dirs, files in os.walk(base):
            for name in files:
                yield Path(root) / name
    else:
        with os.scandir(base) as entries:
            for entry in entries:
                if entry.is_file():
                    yield Path(entry.path)


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def format_mtime(ts: float) -> str:
    dt = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone()
    return dt.isoformat(timespec="seconds")


def file_info(path: Path) -> tuple[int, str, str]:
    stat = path.stat()
    size = stat.st_size
    mtime = format_mtime(stat.st_mtime)
    checksum = sha256_file(path)
    return size, mtime, checksum


def safe_file_info(path: Path) -> tuple[int, str, str]:
    try:
        return file_info(path)
    except (OSError, PermissionError) as exc:
        return -1, "ERROR", f"{exc.__class__.__name__}: {exc}"


def collect_rows(
    base: Path, paths: Iterable[Path], absolute: bool
) -> list[tuple[str, int, str, str]]:
    rows: list[tuple[str, int, str, str]] = []
    for path in paths:
        display_path = str(path if absolute else path.relative_to(base))
        size, mtime, checksum = safe_file_info(path)
        rows.append((display_path, size, mtime, checksum))
    return rows


def print_rows(rows: list[tuple[str, int, str, str]]) -> None:
    for path, size, mtime, checksum in rows:
        print(f"{path}\t{size}\t{mtime}\t{checksum}")


def build_index(base: Path, recursive: bool = True) -> dict[str, Path]:
    index: dict[str, Path] = {}
    for path in iter_files(base, recursive):
        rel = str(path.relative_to(base))
        index[rel] = path
    return index


def diff_rows(
    left_base: Path,
    right_base: Path,
    left: Mapping[str, Path],
    right: Mapping[str, Path],
    verbose: bool,
) -> list[tuple[str, str, str, str, str, str, str, str]]:
    rows: list[tuple[str, str, str, str, str, str, str, str]] = []
    keys = sorted(set(left.keys()) | set(right.keys()))
    for rel in keys:
        left_path = left.get(rel)
        right_path = right.get(rel)
        if left_path is None:
            status = "ADDED"
            left_info = ("-", "-", "-")
            right_info = safe_file_info(right_path) if right_path else ("-", "-", "-")
        elif right_path is None:
            status = "REMOVED"
            left_info = safe_file_info(left_path)
            right_info = ("-", "-", "-")
        else:
            left_info = safe_file_info(left_path)
            right_info = safe_file_info(right_path)
            status = "UNCHANGED" if left_info == right_info else "CHANGED"

        if status == "UNCHANGED" and not verbose:
            continue

        rows.append(
            (
                status,
                rel,
                str(left_info[0]),
                left_info[1],
                left_info[2],
                str(right_info[0]),
                right_info[1],
                right_info[2],
            )
        )
    return rows


def print_diff_rows(rows: list[tuple[str, str, str, str, str, str, str, str]]) -> None:
    for status, rel, lsize, lmtime, lsum, rsize, rmtime, rsum in rows:
        print(f"{status}\t{rel}\t{lsize}\t{lmtime}\t{lsum}\t{rsize}\t{rmtime}\t{rsum}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List file size, modification time, and SHA-256 checksum."
    )
    parser.add_argument(
        "--diff",
        nargs=2,
        metavar=("LEFT", "RIGHT"),
        help="Compare two paths recursively and report differences",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Include unchanged files in --diff output",
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Directory to scan (default: current working directory)",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Recurse into subdirectories",
    )
    parser.add_argument(
        "-A",
        "--absolute",
        action="store_true",
        help="Use absolute paths instead of paths relative to the base directory",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.diff:
        left_base = Path(args.diff[0]).expanduser().resolve()
        right_base = Path(args.diff[1]).expanduser().resolve()
        for base in (left_base, right_base):
            if not base.exists():
                raise SystemExit(f"Directory not found: {base}")
            if not base.is_dir():
                raise SystemExit(f"Not a directory: {base}")

        left_index = build_index(left_base, recursive=True)
        right_index = build_index(right_base, recursive=True)
        rows = diff_rows(left_base, right_base, left_index, right_index, args.verbose)
        print_diff_rows(rows)
        return

    base = Path(args.directory).expanduser().resolve()
    if not base.exists():
        raise SystemExit(f"Directory not found: {base}")
    if not base.is_dir():
        raise SystemExit(f"Not a directory: {base}")

    rows = collect_rows(base, iter_files(base, args.recursive), args.absolute)
    print_rows(rows)


if __name__ == "__main__":
    main()
