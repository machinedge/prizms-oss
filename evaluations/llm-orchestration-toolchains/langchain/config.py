"""Configuration loading and personality discovery."""

import tomllib
from dataclasses import dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent


@dataclass
class Config:
    """Configuration for the Prizms multi-perspective tool."""

    personalities_dir: Path
    output_dir: Path


def load_config(config_path: Path | None) -> Config:
    """Load config from TOML file or return defaults.

    If no config path is provided, uses default directories relative to
    the script location. If a config path is provided, paths in the config
    are resolved relative to the config file's directory.
    """
    if config_path is None:
        return Config(
            personalities_dir=SCRIPT_DIR / "prompts",
            output_dir=SCRIPT_DIR / "outputs",
        )
    with open(config_path, "rb") as f:
        data = tomllib.load(f)
    base = config_path.parent
    return Config(
        personalities_dir=base / data["personalities_dir"],
        output_dir=base / data["output_dir"],
    )


def discover_personalities(personalities_dir: Path) -> list[str]:
    """Discover all personality prompts (*.txt) in directory.

    Returns a sorted list of personality names (file stems without extension).
    """
    return [p.stem for p in sorted(personalities_dir.glob("*.txt"))]


def load_prompt(personalities_dir: Path, name: str) -> str:
    """Load a personality prompt from the personalities directory."""
    return (personalities_dir / f"{name}.txt").read_text()
