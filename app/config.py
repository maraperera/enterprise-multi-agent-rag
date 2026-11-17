from functools import lru_cache
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_mode: str = "demo"  # demo | azure
    auth_mode: str = "demo"  # demo | entra
    azure_openai_endpoint: str = ""
    azure_openai_chat_deployment: str = ""
    azure_openai_embedding_deployment: str = ""
    azure_openai_api_version: str = "2024-10-21"
    azure_search_endpoint: str = ""
    azure_search_index: str = ""
    azure_search_semantic_config: str = "semantic-config"
    azure_client_id: str = ""
    entra_tenant_id: str = ""
    entra_api_audience: str = ""
    entra_required_scope: str = "Research.Read"
    max_question_chars: int = 2000
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def validate_configuration(self):
        if self.app_mode not in {"demo", "azure"} or self.auth_mode not in {"demo", "entra"}:
            raise ValueError("APP_MODE must be demo/azure and AUTH_MODE must be demo/entra")
        if self.app_env == "production" and self.auth_mode != "entra":
            raise ValueError("Production requires Entra authentication")
        if self.app_mode == "azure":
            required = ["azure_openai_endpoint", "azure_openai_chat_deployment", "azure_openai_embedding_deployment", "azure_search_endpoint", "azure_search_index"]
            missing = [key for key in required if not getattr(self, key)]
            if missing:
                raise ValueError(f"Missing Azure configuration: {', '.join(missing)}")
        if self.auth_mode == "entra" and not (self.entra_tenant_id and self.entra_api_audience):
            raise ValueError("Entra authentication requires ENTRA_TENANT_ID and ENTRA_API_AUDIENCE")
        if self.app_mode == "azure" and self.auth_mode != "entra":
            raise ValueError("Azure mode requires Entra authentication")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
