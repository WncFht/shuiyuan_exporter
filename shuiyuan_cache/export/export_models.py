from dataclasses import dataclass


@dataclass(slots=True)
class TopicExportResult:
    topic_id: str
    filename: str
    topic_dir: str
    raw_seconds: float
    image_seconds: float
    attachment_seconds: float
    video_seconds: float
    audio_seconds: float
    total_seconds: float
