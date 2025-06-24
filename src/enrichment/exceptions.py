"""
Enrichment Exceptions - PRD-010
Complete exception hierarchy for enrichment operations.
"""


class EnrichmentException(Exception):
    """Base exception for enrichment-related errors."""
    pass


class GapAnalysisException(EnrichmentException):
    """Exception raised during gap analysis failures."""
    pass


class ContentAcquisitionException(EnrichmentException):
    """Exception raised during content acquisition failures."""
    pass


class BackgroundTaskException(EnrichmentException):
    """Exception raised during background enrichment task failures."""
    pass


class TaskExecutionError(EnrichmentException):
    """Exception raised when task execution fails."""
    
    def __init__(self, message: str, task_id: str = None, execution_stage: str = None):
        super().__init__(message)
        self.task_id = task_id
        self.execution_stage = execution_stage


class EnrichmentTimeoutError(EnrichmentException):
    """Exception raised when enrichment operations timeout."""
    
    def __init__(self, message: str, timeout_seconds: float = None, operation: str = None, content_id: str = None, error_context: dict = None):
        super().__init__(message)
        self.timeout_seconds = timeout_seconds
        self.operation = operation
        self.content_id = content_id
        self.error_context = error_context or {}


class QueueError(EnrichmentException):
    """Exception raised for queue-related errors."""
    
    def __init__(self, message: str, queue_size: int = None, operation: str = None):
        super().__init__(message)
        self.queue_size = queue_size
        self.operation = operation


class TaskProcessingError(EnrichmentException):
    """Exception raised during task processing."""
    pass


class EnrichmentError(EnrichmentException):
    """General enrichment error - alias for EnrichmentException."""
    pass