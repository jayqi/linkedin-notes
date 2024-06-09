import datetime
from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse

from loguru import logger
from platformdirs import user_data_dir
from pydantic import AfterValidator, StringConstraints, TypeAdapter
from sqlalchemy import Engine, func
from sqlmodel import Field, Session, SQLModel, create_engine, select
import typer

_db_engine: Engine | None = None
app = typer.Typer(no_args_is_help=True)


def get_db_path() -> Path:
    base_dir = user_data_dir("linkedin-notes-storage", ensure_exists=True)
    db_path = Path(base_dir) / "linkedin_notes.db"
    return db_path


def get_db_engine() -> Engine:
    global _db_engine
    if _db_engine is None:
        db_path = get_db_path()
        logger.info("Connecting to database: {}", db_path)
        if not db_path.exists():
            logger.info("Database does not exist. A new one will be created.")
        _db_engine = create_engine(f"sqlite:///{db_path}")
        # Initialize all tables
        SQLModel.metadata.create_all(_db_engine)
    return _db_engine


def parse_url_validator(url: str):
    parse_result = urlparse(url)
    if parse_result.netloc and not parse_result.netloc.endswith("linkedin.com"):
        raise ValueError("URL must be a LinkedIn profile URL.")
    return parse_result.path


def profile_format_validator(s: str):
    s = s.strip("/")
    if "/" not in s:
        # Username only, add "in/" prefix
        s = "in/" + s
    elif not s.startswith("in/"):
        # Has a slash but not starting with "in/", invalid
        raise ValueError("Profile identifier should be in the format 'in/username/'")
    # Add trailing slash
    return s + "/"


PROFILE_PATTERN = r"^in/[^/]+/$"

Profile = Annotated[
    str,
    AfterValidator(parse_url_validator),
    AfterValidator(profile_format_validator),
    StringConstraints(pattern=PROFILE_PATTERN),
]


def now():
    return datetime.datetime.now(datetime.UTC)


class Note(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    profile: Profile = Field(index=True)
    text: str = ""
    created_at: datetime.datetime = Field(default_factory=now, index=True)


def query_notes(profile: str, all: bool = False):
    engine = get_db_engine()
    with Session(engine) as session:
        statement = select(Note).where(Note.profile == profile).order_by(Note.created_at.desc())
        results = session.exec(statement)
        if not all:
            return results.first()
        else:
            return results.all()


def read_note(profile: str) -> str | None:
    """Returns the text for the latest note for the given profile."""
    logger.info("Reading note for profile: {}", profile)
    note = query_notes(profile=profile, all=False)
    if note is None:
        logger.info("No note found for profile: {}", profile)
        return None
    else:
        logger.success("Note read successfully.")
        return note.text


def write_note(profile: str, text: str):
    """Writes a new note containing the given text for the given profile."""
    logger.info("Writing note for profile: {}", profile)
    engine = get_db_engine()
    with Session(engine) as session:
        note = Note(profile=profile, text=text)
        session.add(note)
        session.commit()
        logger.success("Note written successfully.")


@app.callback()
def _docs_callback():
    """Manage the storage database."""
    pass


@app.command()
def path():
    """Return the path to the database file."""
    print(get_db_path())


@app.command()
def query(profile: str, all: bool = False):
    """Query database for a note."""
    logger.debug("all: {}", all)
    adapter = TypeAdapter(Profile)
    profile = adapter.validate_python(profile)
    results = query_notes(profile=profile, all=all)
    if all:
        for note in results:
            print(note.model_dump_json())
    else:
        print(results.model_dump_json())


@app.command()
def list():
    """List all profiles in the database."""
    engine = get_db_engine()
    with Session(engine) as session:
        statement = select(Note.profile)
        results = sorted(set(session.exec(statement)))
        for profile in results:
            print(profile)


@app.command()
def counts():
    engine = get_db_engine()
    with Session(engine) as session:
        statement = select(Note.profile, func.count(Note.id)).group_by(Note.profile)
        results = session.exec(statement)
        for profile, count in results:
            print(profile, count)


@app.command()
def delete():
    """Delete the database file."""
    db_path = get_db_path()
    if db_path.exists():
        logger.info("Deleting database: {}", db_path)
        typer.confirm("Are you sure you want to delete it?", abort=True)
        db_path.unlink()
        logger.success("Database deleted.")
    else:
        logger.warning("Database does not exist.")


@app.command()
def export():
    """Export all notes in database in JSONL format."""
    engine = get_db_engine()
    with Session(engine) as session:
        results = session.exec(select(Note))
        for note in results:
            print(note.model_dump_json())


if __name__ == "__main__":
    app()
