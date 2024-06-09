from enum import StrEnum
from pathlib import Path
import platform
import stat
import sys
from typing import Self

from jinja2 import Environment, PackageLoader, select_autoescape
from loguru import logger
import typer

app = typer.Typer()
env = Environment(loader=PackageLoader("linkedin_notes_storage"), autoescape=select_autoescape())


class Browser(StrEnum):
    CHROME = "chrome"
    # FIREFOX = "firefox"


class System(StrEnum):
    LINUX = "linux"
    MACOS = "macos"
    # WINDOWS = "windows"

    @classmethod
    def get_current_system(cls) -> Self:
        system = platform.system().lower()
        if system == "linux":
            return cls.LINUX
        elif system == "darwin":
            return cls.MACOS
        elif system == "windows":
            raise NotImplementedError("Windows is not supported.")
            # return cls.WINDOWS
        else:
            raise ValueError(f"Unsupported system: {system}")


HOST_MANIFEST_FILENAME = "com.jayqi.linkedin_notes_storage.json"

# https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging#native-messaging-host-location
# https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/Native_manifests#manifest_location
HOST_MANIFEST_DIRS = {
    System.LINUX: {
        Browser.CHROME: "~/.config/google-chrome/NativeMessagingHosts",
        # Browser.FIREFOX: "~/.mozilla/native-messaging-hosts"
    },
    System.MACOS: {
        Browser.CHROME: "~/Library/Application Support/Google/Chrome/NativeMessagingHosts",
        # Browser.FIREFOX: "~/Library/Application Support/Mozilla/NativeMessagingHosts"
    },
}


def get_host_manifest_path(system: System, browser: Browser) -> Path:
    """Returns path to the host manifest file for the given operating system and browser."""
    host_dir = Path(HOST_MANIFEST_DIRS[system][browser]).expanduser()
    path = host_dir / HOST_MANIFEST_FILENAME
    return path


def get_run_sh_path() -> Path:
    """Returns the path to the run.sh entrypoint. This will be inside the site-packages directory
    for the linkedin_notes_storage package."""
    path = Path(__file__).parent / "run.sh"
    return path


@app.command()
def setup(browser: Browser=Browser.CHROME, overwrite: bool = False, dry_run: bool = False):
    """Set up the native messaging host, which the extension uses to communicate with the storage
    database.
    """
    # Set up run.sh
    run_sh_path = get_run_sh_path()
    logger.info("Writing run.sh entrypoint to {}", run_sh_path)
    if run_sh_path.exists():
        if not overwrite:
            typer.confirm("An existing run.sh was found. Do you want to overwrite it?", abort=True)
        logger.info("Overwriting existing run.sh...")
    run_sh_template = env.get_template("run.sh.jinja")
    if not dry_run:
        with run_sh_path.open("w") as fp:
            fp.write(run_sh_template.render(python_executable=sys.executable))
    # Make run.sh executable
    logger.info("Making run.sh executable...")
    if not dry_run:
        run_sh_path.chmod(run_sh_path.stat().st_mode | stat.S_IXUSR)
    logger.info("Finished setting up run.sh.")

    # Set up host manifest
    system = System.get_current_system()
    manifest_path = get_host_manifest_path(system=system, browser=browser)
    logger.info("Writing host manifest to {}", manifest_path)
    if manifest_path.exists():
        if not overwrite:
            typer.confirm(
                "An existing host manifest file was found. Do you want to overwrite it?",
                abort=True,
            )
        logger.info("Overwriting existing host manifest file.")
    manifest_template = env.get_template(f"{HOST_MANIFEST_FILENAME}.jinja")
    if not dry_run:
        with manifest_path.open("w") as fp:
            fp.write(manifest_template.render(run_sh_path=run_sh_path))
    logger.info("Finished setting up host manifest.")

    logger.success("Successfully registered native messaging host for {}.", browser)
