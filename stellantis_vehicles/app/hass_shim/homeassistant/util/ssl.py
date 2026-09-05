import ssl
from functools import lru_cache


@lru_cache(maxsize=1)
def client_context() -> ssl.SSLContext:
    return ssl.create_default_context()


@lru_cache(maxsize=1)
def client_context_no_verify() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx
