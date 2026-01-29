from fastapi import HTTPException, status


class ServerNotConfiguredError(HTTPException):
    def __init__(self, detail: str = "Server not configured"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )


class ServerConfigurationError(HTTPException):
    def __init__(self, detail: str = "Server configuration failed"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )


class DockerUnavailableError(HTTPException):
    def __init__(self, detail: str = "Docker is not available"):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail
        )


class ContainerError(HTTPException):
    def __init__(self, detail: str = "Container operation failed"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )
