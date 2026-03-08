from pathlib import Path

from shuiyuan_cache.core.models import MediaRecord
from shuiyuan_cache.fetch.session import ShuiyuanSession
from shuiyuan_cache.store.paths import CachePaths


class MediaStore:
    def __init__(self, paths: CachePaths, session: ShuiyuanSession):
        self.paths = paths
        self.session = session

    def download_images(self, media_records: list[MediaRecord]) -> tuple[list[MediaRecord], int, int, list[str]]:
        downloaded = 0
        skipped = 0
        errors: list[str] = []
        updated_records: list[MediaRecord] = []
        for media in media_records:
            if media.media_type != "image" or not media.resolved_url or not media.media_key or not media.file_ext:
                updated_records.append(media)
                continue
            local_path = self.paths.ensure_parent(self.paths.image_path(media.media_key, media.file_ext))
            media.local_path = str(local_path)
            if local_path.exists() and local_path.stat().st_size > 0:
                media.download_status = "skipped"
                skipped += 1
                updated_records.append(media)
                continue
            try:
                response = self.session.get_binary(media.resolved_url)
                with open(local_path, "wb") as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            file.write(chunk)
                media.download_status = "downloaded"
                media.content_length = local_path.stat().st_size
                downloaded += 1
            except Exception as exc:
                media.download_status = "failed"
                errors.append(f"image download failed for post #{media.post_number}: {exc}")
            updated_records.append(media)
        return updated_records, downloaded, skipped, errors
