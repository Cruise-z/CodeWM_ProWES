"""Synchronous download queue with job lifecycle management and pre-start cancellation."""

from typing import Optional, Dict, List
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
                    job.cancel_token.cancel()
                    # Reset progress for cancelled jobs
                    job.progress = Progress(job.progress.total)
                    return True
                # Already terminal state
                return False
        
        return False

    def process_next(self) -> None:
        """Process the next pending job if any."""
        # Find the first pending job
        pending_job = None
        for job in self._jobs:
            if job.state == "pending":
                pending_job = job
                break
                
        if pending_job is None:
            return
            
        # Check if already cancelled
        if pending_job.state == "cancelled":
            return
            
        # Mark as running
        pending_job.state = "running"
        
        try:
            # Perform the transfer
            result = self._adapter.transfer(
                pending_job.req, 
                pending_job.progress, 
                pending_job.cancel_token
            )
            
            # Record result
            pending_job.result = result
            pending_job.state = "completed"
        except CancelledError:
            # Job was cancelled during transfer
            pending_job.state = "cancelled"
        except Exception as e:
            # Any other error
            pending_job.state = "failed"
            # Note: We don't store exception info as per design

    def process_all(self) -> None:
        """Process all pending jobs until none remain."""
        while True:
            self.process_next()
            
            # Check if any jobs are still pending
            still_pending = any(job.state == "pending" for job in self._jobs)
            if not still_pending:
                break

    def get_status(self, job_id: int) -> Dict[str, object]:
        """
        Get the status of a specific job.

        Args:
            job_id: The ID of the job to query.

        Returns:
            A dictionary containing job status information.
            Keys: state, transferred, total, final_name.
        """
        for job in self._jobs:
            if job.job_id == job_id:
                # Build response
                status = {
                    "state": job.state,
                    "transferred": job.progress.transferred,
                    "total": job.progress.total,
                }
                
                # Add final name if available
                if job.result is not None:
                    status["final_name"] = job.result.final_name
                    
                return status
                
        # Job not found
        raise ValueError(f"Job {job_id} not found")