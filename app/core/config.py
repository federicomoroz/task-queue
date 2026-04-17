from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "sqlite:////data/tasks.db"
    worker_queues: str = "default,high,low"
    brpop_timeout: int = 5
    purge_completed_after_hours: int = 24

    @property
    def queue_names(self) -> list[str]:
        return [q.strip() for q in self.worker_queues.split(",")]

    class Config:
        env_file = ".env"


settings = Settings()
