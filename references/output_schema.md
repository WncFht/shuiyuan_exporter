# Output Schema

All bundled scripts print JSON with `ensure_ascii=False` and `indent=2`.

## `inspect_topic.py`

Returns:

- `topic_id`
- `title`
- `topic_posts_count`
- `db_post_count`
- `json_page_count`
- `raw_page_count`
- `media_image_count`
- `image_file_count`
- `last_posted_at`
- `last_sync_status`
- `last_sync_mode`
- `last_sync_finished_at`
- `cache_path`
- `issues`
- `usable_for_analysis`
- `usable_for_export`
- `has_issues`

## `ensure_cached.py`

Returns:

- `topic_id`
- `cache_hit_before`
- `cache_ready_after`
- `sync_executed`
- `effective_mode`
- `sync_result`
- `inspect_before`
- `inspect_after`

## `query_topic.py`

Returns:

- `topic_id`
- `title`
- `total_hits`
- `ensure_cache`
- `posts[]`

Each item in `posts[]` includes:

- `post_id`
- `post_number`
- `username`
- `display_name`
- `created_at`
- `updated_at`
- `plain_text`
- `image_paths`
- `image_count`
- `score`
- `reply_to_post_number`
- `is_op`
- `like_count`
- `has_images`
- `has_attachments`
- `has_audio`
- `has_video`
- `quote_targets[]`

Each `quote_targets[]` item includes:

- `topic_id`
- `post_number`
- `url`

## `summarize_topic.py`

Returns:

- `topic_id`
- `title`
- `time_range`
- `post_count_in_scope`
- `top_authors`
- `top_keywords`
- `key_posts`
- `image_post_numbers`
- `summary`
- `ensure_cache`

## `export_topic.py`

Returns:

- `topic_id`
- `filename`
- `topic_dir`
- `save_dir`
- `raw_seconds`
- `image_seconds`
- `attachment_seconds`
- `video_seconds`
- `audio_seconds`
- `total_seconds`
- `ensure_cache`
