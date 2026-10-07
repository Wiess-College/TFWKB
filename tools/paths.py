"""Find this repository's root, and the folders outside it that the tools read.

The site builds from this repository alone, but tools/import_governance_changes.py reads a checkout of the
Wiess governance repository, and where that is differs from machine to machine, so no script names it.
Scripts ask this module instead:

    from paths import REPOSITORY_ROOT, governance_folder

    glossaries_root = os.path.join(REPOSITORY_ROOT, "sources", "glossaries")

A folder outside the repository is looked up in this order, and the first one set wins:

    1. a folder given on the script's command line, for scripts that take one (passed in as `given`)
    2. an environment variable: TFWKB_GOVERNANCE_REPO
    3. tfwkb.config.yml at the repository root, key `governance_repo` (setup.sh writes it)
    4. otherwise none

A relative path from the command line or an environment variable is relative to where the script is run.
A relative path in tfwkb.config.yml is relative to the repository root, so the file still works if the
repository is run from another folder. "~" is expanded in all of them.

tfwkb.config.yml is not committed (it is in .gitignore), since each machine has its own paths.
tfwkb.config.example.yml shows the format.

governance_folder returns None when nothing is set, and leaves the checks to its caller. A tool that needs
another outside folder (the research corpus, say) adds a function like it, with its own environment
variable and config key.
"""

import os
from pathlib import Path

import yaml

# This file is tools/paths.py, so the repository root is two levels up.
REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = REPOSITORY_ROOT / "tfwkb.config.yml"


def governance_folder(given: str | None = None) -> Path | None:
    """Return the governance checkout folder, or None if none is set anywhere."""
    return configured_folder(given, "TFWKB_GOVERNANCE_REPO", "governance_repo")


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
