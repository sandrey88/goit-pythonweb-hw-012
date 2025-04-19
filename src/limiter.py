from slowapi import Limiter
from slowapi.util import get_remote_address

REGISTER_LIMIT = "5/minute"
ME_LIMIT = "5/minute"

limiter = Limiter(key_func=get_remote_address)
