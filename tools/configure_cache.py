"""Keep generated Python and pip caches local to this project's environment."""

import sys
import sysconfig
from configparser import ConfigParser
from pathlib import Path


def configure_cache() -> Path:
    """Configure this project's virtual environment to use one cache folder.

    Returns:
        The absolute path to the project's .cache directory.
    """
    project_root = Path(__file__).resolve().parents[1]
    site_packages = Path(sysconfig.get_path("purelib"))
    if sys.prefix == sys.base_prefix or not site_packages.is_relative_to(
        project_root
    ):
        raise RuntimeError(
            "Run this script with a virtual environment inside the project."
        )

    cache_root = project_root / ".cache"
    cache_root.mkdir(exist_ok=True)
    bytecode_path = str(cache_root / "python")
    startup_file = site_packages / "00_ludo_cache.pth"
    startup_file.write_text(
        "import os, sys; "
        f"os.environ['PYTHONPYCACHEPREFIX'] = {bytecode_path!r}; "
        f"sys.pycache_prefix = {bytecode_path!r}\n",
        encoding="utf-8",
    )
    sys.pycache_prefix = bytecode_path

    filename = "pip.ini" if sys.platform == "win32" else "pip.conf"
    pip_config = Path(sys.prefix) / filename
    settings = ConfigParser(interpolation=None)
    settings.read(pip_config, encoding="utf-8")
    if not settings.has_section("global"):
        settings.add_section("global")
    settings.set("global", "cache-dir", str(cache_root / "pip"))
    with pip_config.open("w", encoding="utf-8") as config_file:
        settings.write(config_file)
    return cache_root


def main() -> None:
    """Configure the active project environment and display its cache path."""
    print(f"Generated caches will use: {configure_cache()}")


if __name__ == "__main__":
    main()
