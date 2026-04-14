"""Rate limiting configuration."""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import config

limiter = Limiter(key_func=get_remote_address, default_limits=[config.rate_limit])
