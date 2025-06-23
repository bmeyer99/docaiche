# src/enrichment/exceptions.py

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