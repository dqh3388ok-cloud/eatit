from app.infra.cache import CacheInterface, get_cache_backend


def get_cache() -> CacheInterface:
    return get_cache_backend()
