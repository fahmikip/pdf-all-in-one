"""Thread-safe batch job state model."""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
from threading import RLock
from uuid import uuid4


class JobStatus(StrEnum):
    WAITING = "Waiting"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"


@dataclass(frozen=True, slots=True)
class BatchJob:
    id: str
    source: Path
    task: str
    output: Path
    status: JobStatus = JobStatus.WAITING
    progress: int = 0
    error: str = ""


class JobQueue:
    def __init__(self) -> None: self._jobs: list[BatchJob] = []; self._lock = RLock()
    def add(self, source: str | Path, task: str, output: str | Path) -> BatchJob:
        job = BatchJob(str(uuid4()), Path(source).resolve(), task, Path(output).resolve())
        with self._lock: self._jobs.append(job)
        return job
    def snapshot(self) -> list[BatchJob]:
        with self._lock: return list(self._jobs)
    def get(self, job_id: str) -> BatchJob | None:
        return next((job for job in self.snapshot() if job.id == job_id), None)
    def update(self, job_id: str, **changes) -> BatchJob:
        with self._lock:
            for index, job in enumerate(self._jobs):
                if job.id == job_id:
                    updated = replace(job, **changes); self._jobs[index] = updated; return updated
        raise KeyError(job_id)
    def next_waiting(self) -> BatchJob | None:
        return next((job for job in self.snapshot() if job.status == JobStatus.WAITING), None)
    def cancel(self, job_id: str) -> bool:
        job = self.get(job_id)
        if not job or job.status not in {JobStatus.WAITING, JobStatus.PROCESSING}: return False
        self.update(job_id, status=JobStatus.CANCELLED); return True
    def clear_finished(self) -> None:
        with self._lock: self._jobs = [job for job in self._jobs if job.status in {JobStatus.WAITING, JobStatus.PROCESSING}]
