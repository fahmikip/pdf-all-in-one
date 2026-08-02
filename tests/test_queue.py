from pathlib import Path

from core.jobs.queue import JobQueue, JobStatus


def test_job_queue_lifecycle(tmp_path: Path) -> None:
    queue = JobQueue(); first = queue.add(tmp_path / "one.pdf", "Compress PDF", tmp_path / "one_out.pdf"); second = queue.add(tmp_path / "two.pdf", "Compress PDF", tmp_path / "two_out.pdf")
    assert queue.next_waiting() == first
    queue.update(first.id, status=JobStatus.PROCESSING, progress=50)
    assert queue.next_waiting() == second
    queue.update(first.id, status=JobStatus.COMPLETED, progress=100); assert queue.cancel(second.id)
    assert queue.get(second.id).status == JobStatus.CANCELLED
    queue.clear_finished(); assert queue.snapshot() == []


def test_completed_job_cannot_be_cancelled(tmp_path: Path) -> None:
    queue = JobQueue(); job = queue.add(tmp_path / "one.pdf", "Compress PDF", tmp_path / "out.pdf")
    queue.update(job.id, status=JobStatus.COMPLETED)
    assert not queue.cancel(job.id)
