class DiskQuotaException(Exception):
    """Exception for disk quota exceeding."""


class PostProcessingException(Exception):
    """Exception for post-processing failure."""


class InvalidLicenseException(Exception):
    """Exception for invalid license."""


class AccessToDatasetDenied(Exception):
    """Exception for permission denied to access arkimet dataset"""
