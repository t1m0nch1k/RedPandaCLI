import logging
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Literal

logger = logging.getLogger(__name__)

@dataclass
class Timer:
    id: str
    label: str
    type: Literal["timer", "stopwatch", "alarm"]
    duration_sec: int | None      
    target_time: str | None       
    started_at: float | None
    paused_elapsed: float = 0.0
    state: Literal["idle", "running", "paused", "finished"] = "idle"

    @property
    def remaining(self) -> float:
        if self.type == "stopwatch":
            return 0.0
            
        if self.state == "idle":
            return float(self.duration_sec or 0)
            
        if self.state == "paused":
            return float(self.duration_sec or 0) - self.paused_elapsed
            
        if self.state == "running" and self.started_at is not None:
            elapsed = time.time() - self.started_at + self.paused_elapsed
            rem = float(self.duration_sec or 0) - elapsed
            return max(0.0, rem)
            
        return 0.0

    @property
    def elapsed(self) -> float:
        if self.state == "idle":
            return 0.0
            
        if self.state == "paused":
            return self.paused_elapsed
            
        if self.state == "running" and self.started_at is not None:
            return time.time() - self.started_at + self.paused_elapsed
            
        return self.paused_elapsed

class TimerEngine:
    def __init__(self):
        self.timers: dict[str, Timer] = {}

    def create_timer(self, label: str, duration_sec: int) -> str:
        tid = str(uuid.uuid4())
        self.timers[tid] = Timer(
            id=tid, label=label, type="timer", duration_sec=duration_sec,
            target_time=None, started_at=time.time(), state="running"
        )
        return tid

    def create_stopwatch(self, label: str) -> str:
        tid = str(uuid.uuid4())
        self.timers[tid] = Timer(
            id=tid, label=label, type="stopwatch", duration_sec=None,
            target_time=None, started_at=time.time(), state="running"
        )
        return tid

    def create_alarm(self, label: str, target_time: str) -> str:
        # target_time ISO 8601
        try:
            tt = datetime.fromisoformat(target_time.replace("Z", "+00:00"))
            delta = (tt - datetime.now(tt.tzinfo)).total_seconds()
            duration_sec = int(max(0, delta))
        except Exception:
            duration_sec = 0
            
        tid = str(uuid.uuid4())
        self.timers[tid] = Timer(
            id=tid, label=label, type="alarm", duration_sec=duration_sec,
            target_time=target_time, started_at=time.time(), state="running"
        )
        return tid

    def pause(self, tid: str) -> bool:
        if tid in self.timers and self.timers[tid].state == "running":
            t = self.timers[tid]
            t.paused_elapsed += time.time() - (t.started_at or time.time())
            t.started_at = None
            t.state = "paused"
            return True
        return False

    def resume(self, tid: str) -> bool:
        if tid in self.timers and self.timers[tid].state == "paused":
            t = self.timers[tid]
            t.started_at = time.time()
            t.state = "running"
            return True
        return False

    def stop(self, tid: str) -> bool:
        if tid in self.timers:
            self.pause(tid) # Updates elapsed
            self.timers[tid].state = "finished"
            return True
        return False

    def delete(self, tid: str) -> bool:
        if tid in self.timers:
            del self.timers[tid]
            return True
        return False

    def get_all(self) -> list[dict]:
        # Also auto-update state if expired
        self.check_expired()
        res = []
        for t in self.timers.values():
            d = asdict(t)
            d["remaining_sec"] = t.remaining
            d["elapsed_sec"] = t.elapsed
            res.append(d)
        return res

    def check_expired(self) -> list[Timer]:
        expired = []
        for t in self.timers.values():
            if t.state == "running" and t.type in ["timer", "alarm"]:
                if t.remaining <= 0:
                    t.state = "finished"
                    expired.append(t)
        return expired
