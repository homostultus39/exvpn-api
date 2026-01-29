from fastapi import HTTPException, status


class ClientNotFoundError(HTTPException):
    def __init__(self, detail: str = "Client not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )


class ClientAlreadyExistsError(HTTPException):
    def __init__(self, detail: str = "Client already exists"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail
        )


class ClientConfigNotFoundError(HTTPException):
    def __init__(self, detail: str = "Client configuration not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )


class ClientOperationError(HTTPException):
    def __init__(self, detail: str = "Client operation failed"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )

