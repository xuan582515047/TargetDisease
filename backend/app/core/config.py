import base64

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    app_name: str = "Target Discovery API"
    database_url: str = "postgresql+psycopg://postgres:postgres@postgres:5432/app"
    secret_key: str = ""
    credential_master_key: str = ""
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    deepseek_base_url: str = "https://api.deepseek.com"

    @model_validator(mode="after")
    def _check_secrets(self):
        if not self.secret_key or self.secret_key == "change-me":
            raise ValueError("secret_key 未配置或仍为占位值 change-me，请在 .env 或进程环境变量中设置真实随机值")
        if not self.credential_master_key:
            raise ValueError("credential_master_key 未配置，请在 .env 或进程环境变量中设置真实随机值")
        try:
            raw = base64.urlsafe_b64decode(self.credential_master_key.encode())
        except Exception:
            raise ValueError("credential_master_key 不是有效的 urlsafe base64 编码")
        if len(raw) != 32:
            raise ValueError("credential_master_key 必须解码为 32 字节（AES-256 密钥）")
        return self


settings = Settings()
