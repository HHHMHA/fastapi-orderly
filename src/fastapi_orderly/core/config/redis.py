from pydantic import BaseModel, Field, RedisDsn


class RedisSettings(BaseModel):
    url: RedisDsn = Field(default=RedisDsn("redis://localhost:6379/0"))
    max_connections: int = Field(default=20, gt=0)
    socket_connect_timeout: float = Field(default=2.0, gt=0)
    socket_timeout: float = Field(default=2.0, gt=0)
    health_check_interval: int = Field(default=30, ge=0)
