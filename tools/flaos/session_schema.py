from dataclasses import dataclass, asdict
import json
from typing import Optional

@dataclass
class SessionMetadata:
    session_id: str
    task_id: str
    mode: str
    status: str
    created_at: str
    stdout_log: str
    stderr_log: str
    metadata_path: str
    pid: Optional[int]
    expected_duration_seconds: int
    command: str

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> 'SessionMetadata':
        return cls(
            session_id=data.get("session_id", ""),
            task_id=data.get("task_id", ""),
            mode=data.get("mode", ""),
            status=data.get("status", ""),
            created_at=data.get("created_at", ""),
            stdout_log=data.get("stdout_log", ""),
            stderr_log=data.get("stderr_log", ""),
            metadata_path=data.get("metadata_path", ""),
            pid=data.get("pid"),
            expected_duration_seconds=data.get("expected_duration_seconds", 0),
            command=data.get("command", "")
        )

    @classmethod
    def load(cls, filepath: str) -> 'SessionMetadata':
        with open(filepath, 'r', encoding='utf-8') as f:
            return cls.from_dict(json.load(f))

    def save(self) -> None:
        with open(self.metadata_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2)
