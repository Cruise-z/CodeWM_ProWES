"""Synchronous download queue for video downloader."""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from .transfer import TransferAdapter, TransferResult
from .request import DownloadRequest
from .progress import Progress, CancellationToken


@dataclass
class _Job:
    """Internal representation of a queued job."""

    id: int
    request: DownloadRequest
    progress: Progress
    cancel_token: CancellationToken
    state: str  # "pending", "running", "completed", "failed", "cancelled"
    result: Optional[TransferResult] = None


class DownloadQueue:
    """Synchronous download queue managing job lifecycle and pre-start cancellation."""

    def __init__(self, adapter: TransferAdapter) -> None:
        """
        Initialize the download queue.

        Args:
            adapter: The transfer adapter to use for downloads.
        """
        self._adapter = adapter
        self._jobs: Dict[int, _Job] = {}
        self._next_id = 1

    def enqueue(self, req: DownloadRequest) -> int:
        """
        Enqueue a download request.

        Args:
            req: The download request to enqueue.

        Returns:
            The job ID assigned to the enqueued request.
        """
        job_id = self._next_id
        self._next_id += 1
        
        # Create a progress tracker for this job
        total_bytes = self._adapter.total_bytes(req)
        progress = Progress(total=total_bytes)
        
        # Create a cancellation token for this job
        cancel_token = CancellationToken()
        
        # Create the job object
        job = _Job(
            id=job_id,
            request=req,
            progress=progress,
            cancel_token=cancel_token,
            state="pending"
        )
        
        # Store the job
        self._jobs[job_id] = job
        
        return job_id

    def cancel(self, job_id: int) -> bool:
        """
        Cancel a pending job.

        Args:
            job_id: The ID of the job to cancel.

        Returns:
            True if the job was successfully cancelled, False otherwise.
        """
        if job_id not in self._jobs:
            return False
            
        job = self._jobs[job_id]
        
        # Only allow cancellation of pending jobs
        if job.state != "pending":
            return False
            
        # Mark the job as cancelled
        job.state = "cancelled"
        job.cancel_token.cancel()
        
        # Reset progress for cancelled jobs
        job.progress._transferred = 0
        
        return True

    def process_next(self) -> None:
        """
        Process the next pending job in the queue.
        
        Skips already-cancelled jobs.
        """
        # Find the first pending job
        pending_job = None
        for job in self._jobs.values():
            if job.state == "pending":
                pending_job = job
                break
                
        # If no pending job, do nothing
        if pending_job is None:
            return
            
        # Skip if already cancelled
        if pending_job.state == "cancelled":
            return
            
        # Process the job
        self._process_job(pending_job)

    def process_all(self) -> None:
        """
        Process all pending jobs in the queue.
        """
        while True:
            # Process the next job
            self.process_next()
            
            # Check if there are more pending jobs
            has_pending = any(job.state == "pending" for job in self._jobs.values())
            if not has_pending:
                break

    def get_status(self, job_id: int) -> Dict[str, Any]:
        """
        Get the current status of a job.

        Args:
            job_id: The ID of the job to query.

        Returns:
            A dictionary containing job status information.
        """
        if job_id not in self._jobs:
            raise KeyError(f"Job {job_id} not found")
            
        job = self._jobs[job_id]
        
        # Prepare status dictionary
        status = {
            "state": job.state,
            "transferred": job.progress.transferred,
            "total": job.progress.total,
        }
        
        # Add final_name if available
        if job.result is not None:
            status["final_name"] = job.result.final_name
            
        return status

    def _process_job(self, job: _Job) -> None:
        """
        Internal method to process a job.

        Args:
            job: The job to process.
        """
        # Mark job as running
        job.state = "running"
        
        try:
            # Perform the actual transfer
            result = self._adapter.transfer(
                job.request, job.progress, job.cancel_token
            )
            
            # Record success
            job.state = "completed"
            job.result = result
            
        except Exception as e:
            # Handle failure
            job.state = "failed"
            # Note: We don't store the exception details as per the design
            # which only requires basic status reporting