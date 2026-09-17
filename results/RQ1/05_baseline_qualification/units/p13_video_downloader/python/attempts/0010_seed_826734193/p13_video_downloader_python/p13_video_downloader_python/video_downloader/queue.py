"""Download queue management for synchronous job processing."""

from typing import Optional, List, Dict
from .transfer import TransferAdapter, TransferResult
from .request import DownloadRequest
from .progress import Progress, CancellationToken
from .errors import CancelledError


class _Job:
    """Internal representation of a download job."""

    def __init__(self, job_id: int, req: DownloadRequest, adapter: TransferAdapter):
        """Initialize a job.

        Args:
            job_id: The unique identifier for this job.
            req: The download request.
            adapter: The transfer adapter to use for this job.
        """
        self.id = job_id
        self.req = req
        self.adapter = adapter
        self.state = "pending"  # pending, running, completed, failed, cancelled
        self.progress = Progress(adapter.total_bytes(req))
        self.cancel_token = CancellationToken()
        self.result: Optional[TransferResult] = None
        self.final_name: Optional[str] = None


class DownloadQueue:
    """Synchronous download queue managing job lifecycle and pre-start cancellation."""

    def __init__(self, adapter: TransferAdapter) -> None:
        """Initialize the download queue.

        Args:
            adapter: The transfer adapter to use for downloads.
        """
        self._adapter = adapter
        self._jobs: List[_Job] = []
        self._next_id = 1

    def enqueue(self, req: DownloadRequest) -> int:
        """Enqueue a download request.

        Args:
            req: The download request to enqueue.

        Returns:
            The unique job ID assigned to the new job.
        """
        job_id = self._next_id
        self._next_id += 1
        job = _Job(job_id, req, self._adapter)
        self._jobs.append(job)
        return job_id

    def cancel(self, job_id: int) -> bool:
        """Cancel a pending job.

        Args:
            job_id: The ID of the job to cancel.

        Returns:
            True if the job was successfully cancelled, False if the job was not found
            or was already in a terminal state.
        """
        for job in self._jobs:
            if job.id == job_id:
                if job.state in ("pending", "running"):
                    job.state = "cancelled"
                    job.cancel_token.cancel()
                    # Reset progress for cancelled jobs
                    job.progress = Progress(job.progress.total)
                    return True
                else:
                    # Job is already terminal (completed, failed, cancelled)
                    return False
        # Job not found
        return False

    def process_next(self) -> None:
        """Process the next pending job.

        Skips jobs that are already cancelled.
        """
        for job in self._jobs:
            if job.state == "pending":
                # Mark as running
                job.state = "running"
                try:
                    result = self._adapter.transfer(
                        job.req, job.progress, job.cancel_token
                    )
                    job.result = result
                    job.final_name = result.final_name
                    job.state = "completed"
                except CancelledError:
                    job.state = "cancelled"
                except Exception:
                    job.state = "failed"
                return

    def process_all(self) -> None:
        """Process all pending jobs until none remain."""
        while True:
            self.process_next()
            # Check if any pending jobs remain
            if not any(job.state == "pending" for job in self._jobs):
                break

    def get_status(self, job_id: int) -> Dict[str, object]:
        """Get the status of a specific job.

        Args:
            job_id: The ID of the job to query.

        Returns:
            A dictionary containing the job's status with keys:
            - state: One of "pending", "running", "completed", "failed", "cancelled"
            - transferred: Number of bytes transferred
            - total: Total number of bytes to transfer, or None
            - final_name: The final filename if the job completed, otherwise None
        """
        for job in self._jobs:
            if job.id == job_id:
                return {
                    "state": job.state,
                    "transferred": job.progress.transferred,
                    "total": job.progress.total,
                    "final_name": job.final_name,
                }
        # Job not found
        raise KeyError(f"Job with ID {job_id} not found")