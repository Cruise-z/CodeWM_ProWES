"""Synchronous download queue with job lifecycle management."""

from typing import Optional, List, Dict
from .transfer import TransferAdapter, TransferResult
from .request import DownloadRequest
from .progress import Progress, CancellationToken
from .errors import CancelledError


class _Job:
    """Internal representation of a download job."""

    def __init__(self, job_id: int, req: DownloadRequest, adapter: TransferAdapter) -> None:
        """Initialize a job.

        Args:
            job_id: Unique identifier for the job.
            req: The download request.
            adapter: The transfer adapter to use.
        """
        self.id = job_id
        self.req = req
        self.adapter = adapter
        self.state = "pending"  # pending, running, completed, failed, cancelled
        self.progress = Progress(adapter.total_bytes(req))
        self.cancel_token = CancellationToken()
        self.result: Optional[TransferResult] = None


class DownloadQueue:
    """Synchronous download queue managing job lifecycle."""

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
            The unique job ID assigned to the request.
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
            True if the job was found and cancelled, False otherwise.
        """
        for job in self._jobs:
            if job.id == job_id:
                if job.state in ("pending", "running"):
                    # Mark as cancelled
                    job.state = "cancelled"
                    # Cancel the token if the job is running
                    if job.state == "running":
                        job.cancel_token.cancel()
                    # Reset progress to zero
                    job.progress = Progress(job.progress.total)
                    job.result = None
                    return True
                # Job is already terminal (completed, failed, cancelled)
                return False
        # Job not found
        return False

    def process_next(self) -> None:
        """Process the next pending job.

        Skips already-cancelled jobs.
        """
        # Find the first pending job
        pending_job = None
        for job in self._jobs:
            if job.state == "pending":
                pending_job = job
                break

        # If no pending job, nothing to do
        if pending_job is None:
            return

        # Skip if already cancelled
        if pending_job.state == "cancelled":
            return

        # Start processing
        pending_job.state = "running"
        try:
            result = self._adapter.transfer(
                pending_job.req,
                pending_job.progress,
                pending_job.cancel_token
            )
            pending_job.result = result
            if result.completed:
                pending_job.state = "completed"
            else:
                pending_job.state = "cancelled"
        except CancelledError:
            pending_job.state = "cancelled"
            pending_job.result = None
        except Exception:
            pending_job.state = "failed"
            pending_job.result = None

    def process_all(self) -> None:
        """Process all pending jobs until none remain."""
        while True:
            self.process_next()
            # Check if any pending jobs remain
            has_pending = any(job.state == "pending" for job in self._jobs)
            if not has_pending:
                break

    def get_status(self, job_id: int) -> Dict[str, object]:
        """Get the status of a job.

        Args:
            job_id: The ID of the job to query.

        Returns:
            A dictionary containing the job's status with keys:
            - state: The current state (pending, running, completed, failed, cancelled)
            - transferred: Bytes transferred so far
            - total: Total bytes to transfer, or None if unknown
            - final_name: Final filename, or None if not yet determined
        """
        for job in self._jobs:
            if job.id == job_id:
                result = job.result
                return {
                    "state": job.state,
                    "transferred": job.progress.transferred,
                    "total": job.progress.total,
                    "final_name": result.final_name if result else None
                }
        # Job not found
        raise KeyError(f"Job with ID {job_id} not found")