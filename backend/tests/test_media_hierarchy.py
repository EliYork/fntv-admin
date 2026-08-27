from __future__ import annotations

import sqlite3
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.schema_check import TableInfo
from app.models import Base, MediaProfile
from app.services import fntv_schema_adapter as adapter


def _schema() -> adapter.FntvSchemaInfo:
    columns = ["guid", "title", "type", "parent_guid", "season_number", "episode_number", "runtime"]
    items = adapter.FntvFieldMap(
        "item",
        {
            "guid": "guid",
            "title": "title",
            "original_title": "title",
            "media_type": "type",
            "parent_guid": "parent_guid",
            "season_number": "season_number",
            "episode_number": "episode_number",
            "runtime": "runtime",
            "release_date": None,
        },
    )
    empty = adapter.FntvFieldMap(None, {})
    return adapter.FntvSchemaInfo({"item": TableInfo("item", columns)}, empty, items, empty, {"has_items": True})


def _create_media_database(path: Path) -> None:
    with sqlite3.connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE item (
                guid TEXT PRIMARY KEY,
                title TEXT,
                type TEXT,
                parent_guid TEXT,
                season_number INTEGER,
                episode_number INTEGER,
                runtime INTEGER
            );
            INSERT INTO item VALUES ('movie-1', 'Arrival', 'Movie', NULL, NULL, NULL, 6960);
            INSERT INTO item VALUES ('series-1', 'Breaking Bad', 'Series', NULL, NULL, NULL, NULL);
            INSERT INTO item VALUES ('season-2', 'Season 2', 'Season', 'series-1', 2, NULL, NULL);
            INSERT INTO item VALUES ('season-1', 'Season 1', 'Season', 'series-1', 1, NULL, NULL);
            INSERT INTO item VALUES ('episode-2', 'Cat in the Bag', 'Episode', 'season-1', 1, 2, 2880);
            INSERT INTO item VALUES ('episode-1', 'Pilot', 'Episode', 'season-1', 1, 1, 3480);
            INSERT INTO item VALUES ('series-direct', 'Direct Episodes', 'Series', NULL, NULL, NULL, NULL);
            INSERT INTO item VALUES ('direct-2', 'Second', 'Episode', 'series-direct', NULL, 2, 1200);
            INSERT INTO item VALUES ('direct-1', 'First', 'Episode', 'series-direct', NULL, 1, 1200);
            INSERT INTO item VALUES ('video-1', 'Standalone Clip', 'Video', NULL, NULL, NULL, 60);
            INSERT INTO item VALUES ('directory-1', 'Internal Folder', 'Directory', NULL, NULL, NULL, NULL);
            """
        )


def _patch_database(monkeypatch, path: Path) -> None:
    schema = _schema()
    monkeypatch.setattr(adapter, "detect_schema", lambda: schema)

    def connect() -> sqlite3.Connection:
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only = ON")
        return conn

    monkeypatch.setattr(adapter, "open_fntv_connection", connect)


def test_library_scope_filters_searches_and_paginates_top_level(tmp_path: Path, monkeypatch) -> None:
    database = tmp_path / "fntv.db"
    _create_media_database(database)
    _patch_database(monkeypatch, database)

    first = adapter.media_page(1, 2, scope="library")
    second = adapter.media_page(2, 2, scope="library")
    assert first["total"] == 4
    assert first["pages"] == 2
    assert {item["media_type"] for item in first["items"] + second["items"]} == {"Movie", "Series", "Video"}

    movies = adapter.media_page(1, 20, media_type="Movie", scope="library")
    assert [item["guid"] for item in movies["items"]] == ["movie-1"]
    series = adapter.media_page(1, 20, media_type="Series", scope="library")
    assert {item["guid"] for item in series["items"]} == {"series-1", "series-direct"}
    assert [item["guid"] for item in adapter.media_page(1, 20, keyword="Breaking", scope="library")["items"]] == ["series-1"]
    assert adapter.media_page(1, 20, keyword="Pilot", scope="library")["items"] == []


def test_children_are_immediate_sorted_and_support_direct_episodes(tmp_path: Path, monkeypatch) -> None:
    database = tmp_path / "fntv.db"
    _create_media_database(database)
    _patch_database(monkeypatch, database)
    assert [item["guid"] for item in adapter.media_children("series-1")] == ["season-1", "season-2"]
    assert [item["guid"] for item in adapter.media_children("season-1")] == ["episode-1", "episode-2"]
    assert [item["guid"] for item in adapter.media_children("series-direct")] == ["direct-1", "direct-2"]


def test_library_scope_preserves_existing_hidden_profile_behavior(tmp_path: Path, monkeypatch) -> None:
    database = tmp_path / "fntv.db"
    admin = tmp_path / "admin.db"
    _create_media_database(database)
    _patch_database(monkeypatch, database)
    engine = create_engine(f"sqlite:///{admin.as_posix()}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(MediaProfile(fntv_item_guid="series-1", hidden=1, created_at=1, updated_at=1))
        db.commit()
        visible = adapter.media_page(1, 20, db=db, scope="library")
        all_items = adapter.media_page(1, 20, db=db, scope="library", show_hidden=True)
    assert "series-1" not in {item["guid"] for item in visible["items"]}
    assert "series-1" in {item["guid"] for item in all_items["items"]}
