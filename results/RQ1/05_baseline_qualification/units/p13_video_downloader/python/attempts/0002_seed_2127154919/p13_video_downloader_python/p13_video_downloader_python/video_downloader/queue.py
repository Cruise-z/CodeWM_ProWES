"""Synchronous download queue with job lifecycle management and pre-start cancellation."""

from typing import List, Optional, Dict, Any
from .transfer import TransferAdapter, TransferResult
from .request import DownloadRequest
from .progress import Progress, CancellationToken


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
    """A synchronous download queue that manages job lifecycle and pre-start cancellation."""

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
            The unique ID of the enqueued job.
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
            True if the job was cancelled, False if the job was not found or was already
            terminal (completed, failed, or cancelled).
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
                    # Job is already terminal
                    return False
        # Job not found
        return False

    def process_next(self) -> None:
        """Process the next pending job.

        Skips already-cancelled jobs. Changes job state from pending to running,
        invokes the transfer adapter, and records the result.
        """
        for job in self._jobs:
            if job.state == "pending":
                # Cancelled jobs are skipped
                if job.cancel_token.is_cancelled():
                    job.state = "cancelled"
                    return

                # Process the job
                job.state = "running"
                try:
                    result = self._adapter.transfer(job.req, job.progress, job.cancel_token)
                    job.result = result
                    job.state = "completed"
                except Exception as e:
                    # Store the exception as the result
                    job.state = "failed"
                    # Note: In a more detailed implementation, we might want to store
                    # the actual exception for later inspection
                return

    def process_all(self) -> None:
        """Process all pending jobs until none remain."""
        while True:
            self.process_next()
            # Check if any pending jobs remain
            if not any(job.state == "pending" for job in self._jobs):
                break

    def get_status(self, job_id: int) -> Dict[str, Any]:
        """Get the status of a job.

        Args:
            job_id: The ID of the job to query.

        Returns:
            A dictionary containing state, transferred, total, and final_name keys.
            State is one of: pending, running, completed, failed, cancelled.
            Transferred and total are integers.
            Final_name is a string or None.
        """
        for job in self._jobs:
            if job.id == job_id:
                # Prepare the response dictionary
                status = {
                    "state": job.state,
                    "transferred": job.progress.transferred,
                    "total": job.progress.total,
                }
                # Add final_name if the job has completed or failed
                if job.state in ("completed", "failed"):
                    # The result is only available for completed or failed jobs
                    if job.result is not None:
                        status["final_name"] = job.result.final_name
                    else:
                        status["final_name"] = None
                elif job.state == "cancelled":
                    # For cancelled jobs, final_name should be None or not included
                    status["final_name"] = None
                else:
                    # For pending/running jobs, we don't have a final_name yet
                    status["final_name"] = None
                return status
        # Job not found
        raise KeyError(f"Job with ID {job_id} not found")