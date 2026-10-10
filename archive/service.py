import json
import os
import time
import uuid
from pathlib import Path

from app.processing.validator import Validator


class ArchiveService:
    def __init__(self, store, archive_dir, objects_by_id, wal_path):
        self.store = store
        self.archive_dir = Path(archive_dir)
        self.objects_by_id = objects_by_id
        self.wal_path = Path(wal_path)

        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self.wal_path.parent.mkdir(parents=True, exist_ok=True)
        self.wal_path.touch(exist_ok=True)

    def _write_wal(self, record):
        with open(self.wal_path, "a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
            file.flush()
            os.fsync(file.fileno())

    def run_once(self, cutoff):
        rows = self.store.fetch_before(cutoff)

        if not rows:
            return {
                "selected": 0,
                "archived": 0,
                "rejected": 0,
                "deleted": 0,
            }

        archived_rows = []
        rejected = 0

        for row in rows:
            try:
                object_id = int(row["object_id"])
                obj = self.objects_by_id.get(object_id)
                value = json.loads(row["value_json"])

                if obj is None or not Validator.validate(value, obj)[0]:
                    rejected += 1
                    continue

                archived_rows.append({
                    "id": row["id"],
                    "object_id": object_id,
                    "source_id": row["source_id"],
                    "value": value,
                    "timestamp": row["timestamp"],
                    "changed": bool(row["changed"]),
                })
            except (ValueError, TypeError, KeyError, json.JSONDecodeError):
                rejected += 1

        operation_id = uuid.uuid4().hex
        archive_file = self.archive_dir / (
            f"archive_{int(time.time())}_{operation_id[:8]}.jsonl"
        )

        self._write_wal({
            "kind": "BEGIN",
            "operation_id": operation_id,
            "archive_file": str(archive_file),
            "selected": len(rows),
        })

        with open(archive_file, "w", encoding="utf-8") as file:
            for row in archived_rows:
                file.write(json.dumps(row, ensure_ascii=False) + "\n")
            file.flush()
            os.fsync(file.fileno())

        deleted = self.store.delete_ids([row["id"] for row in rows])

        self._write_wal({
            "kind": "COMMIT",
            "operation_id": operation_id,
            "archived": len(archived_rows),
            "rejected": rejected,
            "deleted": deleted,
        })

        return {
            "selected": len(rows),
            "archived": len(archived_rows),
            "rejected": rejected,
            "deleted": deleted,
        }