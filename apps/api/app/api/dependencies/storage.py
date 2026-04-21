from app.infra.storage import StorageInterface, get_storage_backend


def get_storage() -> StorageInterface:
    # Business services depend on the interface, not the local filesystem backend.
    return get_storage_backend()
