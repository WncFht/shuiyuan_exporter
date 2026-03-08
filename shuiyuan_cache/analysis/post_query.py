import sqlite3
from collections import defaultdict
from collections.abc import Iterable

from shuiyuan_cache.core.config import CacheConfig
from shuiyuan_cache.core.models import QueryPostItem, QueryResult
from shuiyuan_cache.fetch.topic_fetcher import TopicFetcher
from shuiyuan_cache.store.sqlite_store import SQLiteStore


class TopicQueryService:
    def __init__(self, config: CacheConfig):
        self.config = config
        self.sqlite_store = SQLiteStore(config.db_path)

    def close(self) -> None:
        self.sqlite_store.close()

    def query_topic_posts(
        self,
        topic_id: str | int,
        keyword: str | None = None,
        author: str | None = None,
        only_op: bool = False,
        date_from: str | None = None,
        date_to: str | None = None,
        has_images: bool | None = None,
        limit: int | None = 50,
        offset: int = 0,
        order: str = "asc",
        include_images: bool = True,
    ) -> QueryResult:
        resolved_topic_id = TopicFetcher.resolve_topic_id(topic_id)
        op_username = self._get_op_username(resolved_topic_id) if only_op else None
        if only_op and not op_username:
            return QueryResult(topic_id=resolved_topic_id, total_hits=0, items=[])

        rows, total_hits = self._fetch_rows(
            topic_id=resolved_topic_id,
            keyword=keyword,
            author=author,
            op_username=op_username,
            date_from=date_from,
            date_to=date_to,
            has_images=has_images,
            limit=limit,
            offset=offset,
            order=order,
        )

        image_map = (
            self._load_image_paths(
                resolved_topic_id, [row["post_number"] for row in rows]
            )
            if include_images
            else {}
        )
        items = [
            QueryPostItem(
                post_id=row["post_id"],
                post_number=row["post_number"],
                username=row["username"],
                created_at=row["created_at"],
                plain_text=row["plain_text"],
                image_paths=image_map.get(row["post_number"], []),
                image_count=row["image_count"] or 0,
                score=row["score"]
                if "score" in row.keys() and row["score"] is not None
                else None,
            )
            for row in rows
        ]
        return QueryResult(
            topic_id=resolved_topic_id, total_hits=total_hits, items=items
        )

    def _fetch_rows(
        self,
        topic_id: int,
        keyword: str | None,
        author: str | None,
        op_username: str | None,
        date_from: str | None,
        date_to: str | None,
        has_images: bool | None,
        limit: int | None,
        offset: int,
        order: str,
    ) -> tuple[list[sqlite3.Row], int]:
        order_sql = "ASC" if order.lower() != "desc" else "DESC"
        if keyword:
            try:
                rows, total = self._fts_query(
                    topic_id,
                    keyword,
                    author,
                    op_username,
                    date_from,
                    date_to,
                    has_images,
                    limit,
                    offset,
                    order_sql,
                )
                if rows:
                    return rows, total
            except sqlite3.OperationalError:
                pass
            return self._like_query(
                topic_id,
                keyword,
                author,
                op_username,
                date_from,
                date_to,
                has_images,
                limit,
                offset,
                order_sql,
            )
        return self._plain_query(
            topic_id,
            author,
            op_username,
            date_from,
            date_to,
            has_images,
            limit,
            offset,
            order_sql,
        )

    def _base_filters(
        self,
        topic_id: int,
        author: str | None,
        op_username: str | None,
        date_from: str | None,
        date_to: str | None,
        has_images: bool | None,
    ) -> tuple[list[str], list]:
        clauses = ["p.topic_id = ?"]
        params: list = [topic_id]
        if author:
            clauses.append("p.username = ?")
            params.append(author)
        if op_username:
            clauses.append("p.username = ?")
            params.append(op_username)
        if date_from:
            clauses.append("p.created_at >= ?")
            params.append(self._normalize_date_lower(date_from))
        if date_to:
            clauses.append("p.created_at <= ?")
            params.append(self._normalize_date_upper(date_to))
        if has_images is True:
            clauses.append("p.has_images = 1")
        elif has_images is False:
            clauses.append("p.has_images = 0")
        return clauses, params

    def _plain_query(
        self,
        topic_id: int,
        author: str | None,
        op_username: str | None,
        date_from: str | None,
        date_to: str | None,
        has_images: bool | None,
        limit: int | None,
        offset: int,
        order_sql: str,
    ) -> tuple[list[sqlite3.Row], int]:
        clauses, params = self._base_filters(
            topic_id, author, op_username, date_from, date_to, has_images
        )
        where_sql = " AND ".join(clauses)
        total = self.sqlite_store.conn.execute(
            f"SELECT COUNT(*) FROM posts p WHERE {where_sql}", params
        ).fetchone()[0]
        sql = f"SELECT p.*, NULL as score FROM posts p WHERE {where_sql} ORDER BY p.post_number {order_sql}"
        query_params = list(params)
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            query_params.extend([limit, offset])
        rows = self.sqlite_store.conn.execute(sql, query_params).fetchall()
        return rows, total

    def _like_query(
        self,
        topic_id: int,
        keyword: str,
        author: str | None,
        op_username: str | None,
        date_from: str | None,
        date_to: str | None,
        has_images: bool | None,
        limit: int | None,
        offset: int,
        order_sql: str,
    ) -> tuple[list[sqlite3.Row], int]:
        clauses, params = self._base_filters(
            topic_id, author, op_username, date_from, date_to, has_images
        )
        clauses.append(
            '(COALESCE(p.plain_text, "") LIKE ? OR COALESCE(p.raw_markdown, "") LIKE ? OR COALESCE(p.username, "") LIKE ?)'
        )
        like_term = f"%{keyword}%"
        params.extend([like_term, like_term, like_term])
        where_sql = " AND ".join(clauses)
        total = self.sqlite_store.conn.execute(
            f"SELECT COUNT(*) FROM posts p WHERE {where_sql}", params
        ).fetchone()[0]
        sql = f"SELECT p.*, NULL as score FROM posts p WHERE {where_sql} ORDER BY p.post_number {order_sql}"
        query_params = list(params)
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            query_params.extend([limit, offset])
        rows = self.sqlite_store.conn.execute(sql, query_params).fetchall()
        return rows, total

    def _fts_query(
        self,
        topic_id: int,
        keyword: str,
        author: str | None,
        op_username: str | None,
        date_from: str | None,
        date_to: str | None,
        has_images: bool | None,
        limit: int | None,
        offset: int,
        order_sql: str,
    ) -> tuple[list[sqlite3.Row], int]:
        clauses, params = self._base_filters(
            topic_id, author, op_username, date_from, date_to, has_images
        )
        where_sql = " AND ".join(clauses)
        total_sql = f"""
            SELECT COUNT(*)
            FROM posts_fts
            JOIN posts p ON p.post_id = posts_fts.post_id
            WHERE {where_sql} AND posts_fts MATCH ?
        """
        total_params = list(params) + [keyword]
        total = self.sqlite_store.conn.execute(total_sql, total_params).fetchone()[0]
        sql = f"""
            SELECT p.*, bm25(posts_fts) as score
            FROM posts_fts
            JOIN posts p ON p.post_id = posts_fts.post_id
            WHERE {where_sql} AND posts_fts MATCH ?
            ORDER BY p.post_number {order_sql}
        """
        query_params = list(params) + [keyword]
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            query_params.extend([limit, offset])
        rows = self.sqlite_store.conn.execute(sql, query_params).fetchall()
        return rows, total

    def _load_image_paths(
        self, topic_id: int, post_numbers: Iterable[int], limit_per_post: int = 3
    ) -> dict[int, list[str]]:
        post_numbers = [
            post_number for post_number in post_numbers if post_number is not None
        ]
        if not post_numbers:
            return {}
        placeholders = ",".join(["?"] * len(post_numbers))
        sql = f"""
            SELECT DISTINCT post_number, local_path
            FROM media
            WHERE topic_id = ?
              AND media_type = 'image'
              AND post_number IN ({placeholders})
              AND local_path IS NOT NULL
            ORDER BY post_number ASC, local_path ASC
        """
        rows = self.sqlite_store.conn.execute(sql, [topic_id, *post_numbers]).fetchall()
        mapping: dict[int, list[str]] = defaultdict(list)
        for row in rows:
            if len(mapping[row["post_number"]]) < limit_per_post:
                mapping[row["post_number"]].append(row["local_path"])
        return dict(mapping)

    def _get_op_username(self, topic_id: int) -> str | None:
        row = self.sqlite_store.conn.execute(
            "SELECT username FROM posts WHERE topic_id = ? AND post_number = 1 LIMIT 1",
            (topic_id,),
        ).fetchone()
        return row["username"] if row else None

    @staticmethod
    def _normalize_date_lower(value: str) -> str:
        return value if "T" in value else f"{value}T00:00:00Z"

    @staticmethod
    def _normalize_date_upper(value: str) -> str:
        return value if "T" in value else f"{value}T23:59:59Z"
