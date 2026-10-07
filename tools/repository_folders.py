"""Find this repository's root, and the folders outside it that the tools read.

The site builds from this repository alone, but some tools read folders outside it, and where those are
differs from machine to machine, so no script names them. Scripts ask this module instead:

    from repository_folders import REPOSITORY_ROOT, governance_folder, working_copy_folder

    glossaries_root = os.path.join(REPOSITORY_ROOT, "sources", "glossaries")

The folders, with the environment variable and config key that set each one:

    governance_folder     TFWKB_GOVERNANCE_REPO   governance_repo   a checkout of the governance repository
    working_copy_folder   TFWKB_WORKING_COPY      working_copy      your working copy of the archived sources

Each is looked up in this order, and the first one set wins:

    1. a folder given on the script's command line, for scripts that take one (passed in as `given`)
    2. the environment variable
    3. the key in tfwkb.config.yml at the repository root (setup.sh writes governance_repo)
    4. otherwise none

A relative path from the command line or an environment variable is relative to where the script is run.
A relative path in tfwkb.config.yml is relative to the repository root, so the file still works if the
repository is run from another folder. "~" is expanded in all of them.

tfwkb.config.yml is not committed (it is in .gitignore), since each machine has its own paths.
tfwkb.config.example.yml shows the format.

Each function returns None when nothing is set, and leaves the checks to its caller. A tool that needs
another outside folder adds a function like them, with its own environment variable and config key.
"""

import os
from pathlib import Path

import yaml

# This file is tools/repository_folders.py, so the repository root is two levels up.
REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = REPOSITORY_ROOT / "tfwkb.config.yml"


def governance_folder(given: str | None = None) -> Path | None:
    """Return the governance checkout folder, or None if none is set anywhere."""
    return configured_folder(given, "TFWKB_GOVERNANCE_REPO", "governance_repo")


def working_copy_folder(given: str | None = None) -> Path | None:
    """Return the working-copy folder (archived sources fetched to this machine), or None if none is set."""
    return configured_folder(given, "TFWKB_WORKING_COPY", "working_copy")


def configured_folder(given: str | None, environment_variable: str, config_key: str) -> Path | None:
    """Return the first folder set on the command line, in the environment, or in the config file."""
    if given:
        return Path(given).expanduser()
    if os.environ.get(environment_variable):
        return Path(os.environ[environment_variable]).expanduser()
    config_value = read_config().get(config_key)
    if config_value:
        return REPOSITORY_ROOT / Path(str(config_value)).expanduser()
    return None


def read_config() -> dict:
    """Return the settings in tfwkb.config.yml, or an empty dict if there is no such file or it is empty."""
    if not CONFIG_FILE.is_file():
        return {}
    with CONFIG_FILE.open(encoding="utf-8") as config:
        settings = yaml.safe_load(config)
    if settings is None:
        return {}
    if not isinstance(settings, dict):
        raise SystemExit(f"{CONFIG_FILE} should hold `key: value` lines, like tfwkb.config.example.yml.")
    return settings
