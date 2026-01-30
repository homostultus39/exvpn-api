class ServiceError(Exception):
    pass


class DockerServiceError(ServiceError):
    pass


class HostServiceError(ServiceError):
    pass


class AWGServiceError(ServiceError):
    pass


class ConfigServiceError(ServiceError):
    pass


class ConfigParseError(ServiceError):
    pass


class ContainerNotRunningError(ServiceError):
    pass


class ContainerNotFoundError(ServiceError):
    pass


class ImageNotFoundError(ServiceError):
    pass


class FileAccessError(ServiceError):
    pass


class ClientServiceError(ServiceError):
    pass


class ClientNotFoundServiceError(ClientServiceError):
    pass


class ServerNotConfiguredServiceError(ClientServiceError):
    pass

