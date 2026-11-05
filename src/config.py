"""Application settings independent of Qt and gameplay."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ApplicationConfig:
    """Default desktop window configuration."""

    title: str = "Ludo Game"
    width: int = 1100
    height: int = 800
    minimum_width: int = 640
    minimum_height: int = 480


APP_CONFIG = ApplicationConfig()
