from pydantic import BaseModel, SecretStr
from sqlalchemy import URL


class DatabaseSettings(BaseModel):
    name: str
    user: str
    password: SecretStr
    port: int
    host: str
    driver: str

    @property
    def url(self) -> URL:
        url: URL = URL.create(
            drivername=self.driver,
            username=self.user,
            password=self.password.get_secret_value(),
            host=self.host,
            port=self.port,
            database=self.name,
        )
        return url
