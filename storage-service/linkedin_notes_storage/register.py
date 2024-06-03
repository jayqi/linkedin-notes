from pathlib import Path
import platform
import stat
import sys

from jinja2 import Environment, PackageLoader, select_autoescape
from loguru import logger
import typer

app = typer.Typer()
env = Environment(
    loader=PackageLoader("linkedin_notes_storage"),
    autoescape=select_autoescape()
)


HOST_MANIFEST_FILENAME = "com.jayqi.linkedin_notes_storage.json"

HOST_MANIFEST_DIRS = {
    "linux": {
        "chrome": "~/.config/google-chrome/NativeMessagingHosts",
        "firefox": "~/.mozilla/native-messaging-hosts"
    },
    "darwin": { # macOS
        "chrome": "~/Library/Application Support/Google/Chrome/NativeMessagingHosts",
        "firefox": "~/Library/Application Support/Mozilla/NativeMessagingHosts"
    },
}

def get_host_manifest_path(browser: str) -> Path:
    dir = Path(HOST_MANIFEST_DIRS[platform.system().lower()][browser.lower()]).expanduser()
    path = dir / HOST_MANIFEST_FILENAME
    return path

def get_run_sh_path() -> Path:
    path = Path(__file__).parent / "run.sh"
    return path

@app.command()
def register(browser: str):
    # Set up run.sh
    run_sh_path = get_run_sh_path()
    logger.info("Writing run.sh entrypoint to {}", run_sh_path)
    run_sh_template = env.get_template("run.sh.jinja")
    with run_sh_path.open("w") as fp:
        fp.write(run_sh_template.render(python_executable=sys.executable))
    # Make run.sh executable
    logger.info("Making run.sh executable...")
    run_sh_path.chmod(run_sh_path.stat().st_mode | stat.S_IXUSR)
    logger.info("Finished setting up run.sh.")

    # Set up host manifest
    manifest_path = get_host_manifest_path(browser)
    logger.info("Writing host manifest to {}", manifest_path)
    manifest_template = env.get_template(f"{HOST_MANIFEST_FILENAME}.jinja")
    with manifest_path.open("w") as fp:
        fp.write(manifest_template.render(run_sh_path=run_sh_path))
    logger.info("Finished setting up host manifest.")

    logger.success("Successfully registered native messaging host for {}.", browser)
