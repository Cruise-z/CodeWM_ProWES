"""Download queue management for video downloader."""

from typing import Optional, List, Dict, Any
from .transfer import TransferAdapter, TransferResult
from .request import DownloadRequest
from .progress import Progress, CancellationToken
from .errors import CancelledError


class _Job:
    """Internal representation of a download job."""

    def __init__(
        self, job_id: int, req: DownloadRequest, adapter: TransferAdapter
    ) -> None:
        """
        Initialize a job.

        Args:
            job_id: Unique identifier for the job.
            req: The download request.
            adapter: The transfer adapter to use.
        """
        self.job_id = job_id
        self.req = req
        self.adapter = adapter
        self.state = "pending"  # pending, running, completed, failed, cancelled
        self.progress = Progress(adapter.total_bytes(req))
        self.cancel_token = CancellationToken()
        self.result: Optional[TransferResult] = None
        self.final_name: Optional[str] = None


class DownloadQueue:
    """A synchronous queue for managing download jobs."""

    def __init__(self, adapter: TransferAdapter) -> None:
        """
        Initialize the download queue.

        Args:
            adapter: The transfer adapter to use for downloads.
        """
        self._adapter = adapter
        self._jobs: List[_Job] = []
        self._next_id = 1

    def enqueue(self, req: DownloadRequest) -> int:
        """
        Add a download request to the queue.

        Args:
            req: The download request to enqueue.

        Returns:
            The job ID assigned to the new job.
        """
        job_id = self._next_id
        self._next_id += 1
        job = _Job(job_id, req, self._adapter)
        self._jobs.append(job)
        return job_id

    def cancel(self, job_id: int) -> bool:
        """
        Cancel a pending job.

        Args:
            job_id: The ID of the job to cancel.

        Returns:
            True if the job was found and cancelled, False otherwise.
        """
        for job in self._jobs:
            if job.job_id == job_id:
                if job.state in ("pending", "running"):
                    job.state = "cancelled"
                    job.progress.update(0)
                    job.cancel_token.cancel()
                    return True
                # Job is already terminal
                return False
        return False

    def process_next(self) -> None:
        """
        Process the next pending job in the queue.

        Skips jobs that are already cancelled.
        """
        # Find the first pending job
        pending_job = None
        for job in self._jobs:
            if job.state == "pending":
                pending_job = job
                break

        if pending_job is None:
            return

        # Cancel if already cancelled
        if pending_job.state == "cancelled":
            return

        # Mark as running
        pending_job.state = "running"

        try:
            # Perform the transfer
            result = self._adapter.transfer(
                pending_job.req, pending_job.progress, pending_job.cancel_token
            )
            pending_job.result = result
            pending_job.final_name = result.final_name
            pending_job.state = "completed"
        except CancelledError:
            pending_job.state = "cancelled"
        except Exception as e:
            pending_job.state = "failed"

    def process_all(self) -> None:
        """
        Process all pending jobs in the queue.
        """
        while True:
            self.process_next()
            # Check if there are any pending jobs left
            if not any(job.state == "pending" for job in self._jobs):
                break

    def get_status(self, job_id: int) -> Dict[str, Any]:
        """
        Get the status of a specific job.

        Args:
            job_id: The ID of the job to query.

        Returns:
            A dictionary containing job status information.
        """
        for job in self._jobs:
            if job.job_id == job_id:
                status = {
                    "state": job.state,
                    "transferred": job.progress.transferred,
                    "total": job.progress.total,
                }
                if job.final_name is not None:
                    status["final_name"] = job.final_name
                return status
        # Job not found
        return {
            "state": "unknown",
            "transferred": 0,
            "total": None,
        }