from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import local

from shuiyuan_cache.core.models import MediaRecord
from shuiyuan_cache.core.progress import ProgressCallback
from shuiyuan_cache.fetch.session import ShuiyuanSession
from shuiyuan_cache.store.paths import CachePaths


@dataclass(slots=True)
class _ImageDownloadResult:
    task_key: tuple[str, str, str]
    local_path: str
    status: str
    content_length: int | None = None
    error: str | None = None


class MediaStore:
    def __init__(self, paths: CachePaths, session: ShuiyuanSession):
        self.paths = paths
        self.session = session
        self._worker_local = local()

    def download_images(
        self,
        media_records: list[MediaRecord],
        progress_callback: ProgressCallback | None = None,
        progress_every: int = 25,
    ) -> tuple[list[MediaRecord], int, int, list[str]]:
        grouped_records: dict[tuple[str, str, str], list[MediaRecord]] = defaultdict(
            list
        )
        ordered_task_keys: list[tuple[str, str, str]] = []
        updated_records: list[MediaRecord] = []

        for media in media_records:
            if not self._is_downloadable_image(media):
                continue
            normalized_ext = self._normalize_ext(media.file_ext)
            local_path = self.paths.ensure_parent(
                self.paths.image_path(media.media_key, normalized_ext)
            )
            media.local_path = str(local_path)
            task_key = (media.media_key, normalized_ext, media.resolved_url)
            if task_key not in grouped_records:
                ordered_task_keys.append(task_key)
            grouped_records[task_key].append(media)

        results = self._run_download_tasks(
            ordered_task_keys,
            progress_callback=progress_callback,
            progress_every=progress_every,
        )
        result_map = {result.task_key: result for result in results}

        downloaded = sum(1 for result in results if result.status == "downloaded")
        skipped = sum(1 for result in results if result.status == "skipped")
        errors = [result.error for result in results if result.error]

        for media in media_records:
            if self._is_downloadable_image(media):
                task_key = (
                    media.media_key,
                    self._normalize_ext(media.file_ext),
                    media.resolved_url,
                )
                result = result_map[task_key]
                media.local_path = result.local_path
                media.download_status = result.status
                media.content_length = result.content_length
            updated_records.append(media)

        return updated_records, downloaded, skipped, errors

    def _run_download_tasks(
        self,
        ordered_task_keys: list[tuple[str, str, str]],
        progress_callback: ProgressCallback | None = None,
        progress_every: int = 25,
    ) -> list[_ImageDownloadResult]:
        if not ordered_task_keys:
            return []

        max_workers = min(
            max(self.paths.config.image_download_workers, 1),
            len(ordered_task_keys),
        )
        results: list[_ImageDownloadResult] = []
        downloaded = 0
        skipped = 0
        failed = 0

        if max_workers == 1:
            iterator = (
                self._download_image_task(task_key) for task_key in ordered_task_keys
            )
            for processed, result in enumerate(iterator, start=1):
                results.append(result)
                if result.status == "downloaded":
                    downloaded += 1
                elif result.status == "skipped":
                    skipped += 1
                else:
                    failed += 1
                self._report_progress(
                    progress_callback,
                    processed,
                    len(ordered_task_keys),
                    downloaded,
                    skipped,
                    failed,
                    progress_every,
                )
            return results

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for processed, result in enumerate(
                executor.map(self._download_image_task, ordered_task_keys),
                start=1,
            ):
                results.append(result)
                if result.status == "downloaded":
                    downloaded += 1
                elif result.status == "skipped":
                    skipped += 1
                else:
                    failed += 1
                self._report_progress(
                    progress_callback,
                    processed,
                    len(ordered_task_keys),
                    downloaded,
                    skipped,
                    failed,
                    progress_every,
                )

        return results

    def _download_image_task(
        self,
        task_key: tuple[str, str, str],
    ) -> _ImageDownloadResult:
        media_key, normalized_ext, resolved_url = task_key
        local_path = self.paths.ensure_parent(
            self.paths.image_path(media_key, normalized_ext)
        )
        if local_path.exists() and local_path.stat().st_size > 0:
            return _ImageDownloadResult(
                task_key=task_key,
                local_path=str(local_path),
                status="skipped",
                content_length=local_path.stat().st_size,
            )

        session = self._get_worker_session()
        try:
            response = session.get_binary(session.absolute_url(resolved_url))
            with open(local_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
            return _ImageDownloadResult(
                task_key=task_key,
                local_path=str(local_path),
                status="downloaded",
                content_length=local_path.stat().st_size,
            )
        except Exception as exc:
            return _ImageDownloadResult(
                task_key=task_key,
                local_path=str(local_path),
                status="failed",
                error=f"image download failed for media_key {media_key}: {exc}",
            )

    def _get_worker_session(self) -> ShuiyuanSession:
        worker_session = getattr(self._worker_local, "session", None)
        if worker_session is None:
            worker_session = ShuiyuanSession(self.paths.config)
            self._worker_local.session = worker_session
        return worker_session

    @staticmethod
    def _normalize_ext(file_ext: str | None) -> str:
        if not file_ext:
            return ".bin"
        return file_ext if file_ext.startswith(".") else f".{file_ext}"

    @staticmethod
    def _is_downloadable_image(media: MediaRecord) -> bool:
        return bool(
            media.media_type == "image"
            and media.resolved_url
            and media.media_key
            and media.file_ext
        )

    @staticmethod
    def _report_progress(
        progress_callback: ProgressCallback | None,
        processed: int,
        eligible_total: int,
        downloaded: int,
        skipped: int,
        failed: int,
        progress_every: int,
    ) -> None:
        if not progress_callback or eligible_total <= 0:
            return
        if processed % max(progress_every, 1) != 0 and processed != eligible_total:
            return
        progress_callback(
            "images "
            f"{processed}/{eligible_total} "
            f"(downloaded={downloaded}, skipped={skipped}, failed={failed})"
        )
