"""Synchronous download queue with pre-start cancellation support."""

from typing import Optional, List, Dict, Any
from .transfer import TransferAdapter, TransferResult
from .request import DownloadRequest
from .progress import Progress, CancellationToken


class _Job:
    """Internal representation of a download job."""

    def __init__(self, job_id: int, request: DownloadRequest, progress: Progress):
        """
        Initialize a job.

        Args:
            job_id: Unique identifier for the job.
            request: The download request.
            progress: Progress tracker for the job.
        """
        self.id = job_id
        self.request = request
        self.progress = progress
        self.state = "pending"  # pending, running, completed, failed, cancelled
        self.result: Optional[TransferResult] = None
        self.cancel_token = CancellationToken()


class DownloadQueue:
    """Synchronous download queue managing job lifecycle and pre-start cancellation."""

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
            The job ID assigned to the request.
        """
        job_id = self._next_id
        self._next_id += 1
        
        # Create progress tracker
        total_bytes = self._adapter.total_bytes(req)
        progress = Progress(total=total_bytes)
        
        # Create and add job
        job = _Job(job_id, req, progress)
        self._jobs.append(job)
        
        return job_id

    def cancel(self, job_id: int) -> bool:
        """
        Cancel a pending job before it starts running.

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
                    # Cancel the token
                    job.cancel_token.cancel()
                    # Reset progress to zero
                    job.progress._transferred = 0
                    return True
                # Job already completed, failed, or cancelled
                return False
        # Job not found
        return False

    def process_next(self) -> None:
        """
        Process the next pending job in the queue.
        
        Skips already-cancelled jobs.
        """
        # Find the first pending job
        pending_job = None
        for job in self._jobs:
            if job.state == "pending":
                pending_job = job
                break
        
        if pending_job is None:
            return
            
        # Skip cancelled jobs
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
            
            # Record result
            pending_job.result = result
            pending_job.state = "completed"
            
        except Exception as e:
            # Record failure
            pending_job.state = "failed"
            # Re-raise the exception so caller can handle it
            raise e

    def process_all(self) -> None:
        """
        Process all pending jobs in the queue.
        
        Continues until no more pending jobs remain.
        """
        while True:
            # Process one job
            self.process_next()
            
            # Check if any pending jobs remain
            has_pending = any(job.state == "pending" for job in self._jobs)
            if not has_pending:
                break

    def get_status(self, job_id: int) -> Dict[str, Any]:
        """
        Get the status of a specific job.

        Args:
            job_id: The ID of the job to query.

        Returns:
            Dictionary with keys: 'state', 'transferred', 'total', 'final_name'.
            State is one of: 'pending', 'running', 'completed', 'failed', 'cancelled'.
        """
        for job in self._jobs:
            if job.id == job_id:
                state = job.state
                transferred = job.progress.transferred
                total = job.progress.total
                
                # Get final name if available
                final_name = None
                if job.result:
                    final_name = job.result.final_name
                elif job.state == "completed" and job.result:
                    final_name = job.result.final_name
                    
                return {
                    "state": state,
                    "transferred": transferred,
                    "total": total,
                    "final_name": final_name
                }
                
        # Job not found
        return {
            "state": "unknown",
            "transferred": 0,
            "total": None,
            "final_name": None
        }