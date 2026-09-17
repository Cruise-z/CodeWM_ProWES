"""Synchronous download queue with job lifecycle management and pre-start cancellation."""

from dataclasses import dataclass
from typing import Optional, List
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
    state: str  # 'pending', 'running', 'completed', 'failed', 'cancelled'
    result: Optional[TransferResult] = None


class DownloadQueue:
    """A synchronous queue for managing download jobs with pre-start cancellation."""

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
        Enqueue a download request.

        Args:
            req: The download request to enqueue.

        Returns:
            The job ID assigned to the new job.
        """
        job_id = self._next_id
        self._next_id += 1
        
        # Create a progress tracker for this job
        total_bytes = self._adapter.total_bytes(req)
        progress = Progress(total=total_bytes)
        
        # Create a cancellation token for this job
        cancel_token = CancellationToken()
        
        # Create the job
        job = _Job(
            id=job_id,
            request=req,
            progress=progress,
            cancel_token=cancel_token,
            state="pending"
        )
        
        # Add to jobs list
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
            if job.id == job_id:
                # Only cancel pending jobs
                if job.state == "pending":
                    job.state = "cancelled"
                    job.progress.update(0)  # Ensure progress reflects cancellation
                    job.cancel_token.cancel()
                    return True
                # Already processed jobs cannot be cancelled
                return False
        # Job not found
        return False

    def process_next(self) -> None:
        """
        Process the next pending job in the queue.

        Skips any already-cancelled jobs.
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
            
        # Mark as running
        pending_job.state = "running"
        
        try:
            # Perform the transfer
            result = self._adapter.transfer(
                pending_job.request,
                pending_job.progress,
                pending_job.cancel_token
            )
            
            # Record success
            pending_job.result = result
            pending_job.state = "completed"
            
        except Exception as e:
            # Record failure
            pending_job.state = "failed"
            # Re-raise the exception so the caller knows it failed
            raise e

    def process_all(self) -> None:
        """
        Process all pending jobs in the queue.
        """
        while True:
            # Process one job
            self.process_next()
            
            # Check if there are more pending jobs
            has_pending = any(job.state == "pending" for job in self._jobs)
            if not has_pending:
                break

    def get_status(self, job_id: int) -> dict:
        """
        Get the current status of a job.

        Args:
            job_id: The ID of the job to query.

        Returns:
            Dictionary containing state, transferred, total, and final_name.
        """
        for job in self._jobs:
            if job.id == job_id:
                result = {
                    "state": job.state,
                    "transferred": job.progress.transferred,
                    "total": job.progress.total,
                }
                
                # Add final_name if available
                if job.result is not None:
                    result["final_name"] = job.result.final_name
                
                return result
                
        # Job not found
        raise ValueError(f"Job with ID {job_id} not found")