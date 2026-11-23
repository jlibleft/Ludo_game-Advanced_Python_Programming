"""Route setuptools-generated metadata and build files into .cache."""

from pathlib import Path

from setuptools import setup


def main() -> None:
    """Configure generated paths while pyproject.toml supplies package data."""
    cache_root = Path(__file__).resolve().parent / ".cache"
    metadata_path = cache_root / "packaging"
    metadata_path.mkdir(parents=True, exist_ok=True)
    setup(
        options={
            "egg_info": {"egg_base": str(metadata_path)},
            "build": {"build_base": str(cache_root / "build")},
        }
    )


if __name__ == "__main__":
    main()
