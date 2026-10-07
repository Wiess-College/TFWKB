"""Find the folders outside this repository that the tools read: the research corpus and the governance checkout.

The site builds from this repository alone, but some tools in tools/ re-derive files from the research corpus
(the "wiess-archive" folder of saved web pages, O-Week book text and so on) or from a checkout of the Wiess
governance repository. Where those folders are differs from machine to machine, so no script names them.
Each script asks this module instead:

    from paths import corpus_folder, governance_folder, REPOSITORY_ROOT

    book_text_folder = corpus_folder() / "historian-collection" / "text-raw"

Each folder is looked up in this order, and the first one set wins:

    1. a folder given on the script's command line, for scripts that take one (passed in as `given`)
    2. an environment variable: TFWKB_CORPUS or TFWKB_GOVERNANCE_REPO
    3. tfwkb.config.yml at the repository root, keys `corpus` and `governance_repo` (setup.sh writes it)
    4. the default: ../wiess-archive next to this repository for the corpus; nothing for governance

A relative path from the command line or an environment variable is relative to where the script is run.
A relative path in tfwkb.config.yml is relative to the repository root, so the file still works if the
repository is run from another folder. "~" is expanded in all of them.

tfwkb.config.yml is not committed (it is in .gitignore), since each machine has its own paths.
tfwkb.config.example.yml shows the format.

corpus_folder stops with SystemExit and a message naming the folder if it does not exist, so a script
fails at once with a clear reason rather than with a FileNotFoundError deep inside. governance_folder
returns None when nothing is set, and leaves the checks to its caller.
"""

import os
from pathlib import Path

import yaml

# This file is tools/paths.py, so the repository root is two levels up.
REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = REPOSITORY_ROOT / "tfwkb.config.yml"
DEFAULT_CORPUS_FOLDER = REPOSITORY_ROOT.parent / "wiess-archive"


def corpus_folder(given: str | None = None) -> Path:
    """Return the research corpus folder, or stop with a message if it is not there."""
    folder = configured_folder(given, "TFWKB_CORPUS", "corpus") or DEFAULT_CORPUS_FOLDER
    if not folder.is_dir():
        raise SystemExit(
            f"Corpus folder not found: {folder}\n"
            "Set it in tfwkb.config.yml (run ./setup.sh), or with TFWKB_CORPUS=/path/to/wiess-archive."
        )
    return folder


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
