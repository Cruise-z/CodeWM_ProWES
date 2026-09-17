"""Synchronous download queue for video downloader."""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from .transfer import TransferAdapter, TransferResult
from .request import DownloadRequest
from .progress import Progress, CancellationToken


@dataclass
class _Job:
    """Internal representation of a download job."""

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
        self._jobs: Dict[int, _Job] = {}
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
        
        # Create progress tracker with total bytes from adapter
        total_bytes = self._adapter.total_bytes(req)
        progress = Progress(total=total_bytes)
        
        # Create cancellation token
        cancel_token = CancellationToken()
        
        # Create job
        job = _Job(
            id=job_id,
            request=req,
            progress=progress,
            cancel_token=cancel_token,
            state="pending"
        )
        
        # Store job
        self._jobs[job_id] = job
        
        return job_id

    def cancel(self, job_id: int) -> bool:
        """
        Cancel a pending job before it starts running.

        Args:
            job_id: The ID of the job to cancel.

        Returns:
            True if the job was found and cancelled, False otherwise.
        """
        if job_id not in self._jobs:
            return False
            
        job = self._jobs[job_id]
        
        # Only allow cancellation of pending jobs
        if job.state != "pending":
            return False
            
        # Mark job as cancelled
        job.state = "cancelled"
        job.progress.update(0)  # Ensure progress reflects 0 transferred
        job.cancel_token.cancel()
        
        return True

    def process_next(self) -> None:
        """
        Process the next pending job in the queue.
        
        Skips already-cancelled jobs. Changes pending to running, 
        invokes the adapter, and records completion/cancellation/ failure.
        """
        # Find the first pending job
        pending_job = None
        for job in self._jobs.values():
            if job.state == "pending":
                pending_job = job
                break
        
        # If no pending job, nothing to do
        if pending_job is None:
            return
            
        # Mark as running
        pending_job.state = "running"
        
        try:
            # Perform transfer
            result = self._adapter.transfer(
                pending_job.request,
                pending_job.progress,
                pending_job.cancel_token
            )
            
            # Record completion
            pending_job.state = "completed"
            pending_job.result = result
            
        except Exception as e:
            # Record failure
            pending_job.state = "failed"
            pending_job.result = None

    def process_all(self) -> None:
        """
        Process all pending jobs in the queue.
        
        Repeatedly calls process_next until no more pending jobs remain.
        """
        while True:
            # Try to process next job
            self.process_next()
            
            # Check if there are still pending jobs
            has_pending = any(job.state == "pending" for job in self._jobs.values())
            if not has_pending:
                break

    def get_status(self, job_id: int) -> Dict[str, Any]:
        """
        Get the status of a specific job.

        Args:
            job_id: The ID of the job to query.

        Returns:
            A dictionary with keys 'state', 'transferred', 'total', and 'final_name'.
            State is one of 'pending', 'running', 'completed', 'failed', 'cancelled'.
            Transferred and total are integers representing bytes.
            Final_name is a string if completed, None otherwise.
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
        
        # Add final name if applicable
        if job.state == "completed" and job.result is not None:
            status["final_name"] = job.result.final_name
        else:
            status["final_name"] = None
            
        return status