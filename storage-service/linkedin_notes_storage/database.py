from pathlib import Path

from loguru import logger
from platformdirs import user_data_dir
from sqlalchemy import Engine
from sqlmodel import Field, Session, SQLModel, create_engine
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
        _db_engine = create_engine(f"sqlite:///{db_path}")
        # Initialize all tables
        SQLModel.metadata.create_all(_db_engine)
    return _db_engine


class Note(SQLModel, table=True):
    profile: str = Field(primary_key=True)
    text: str = ""


def read_note(profile: str) -> str | None:
    logger.info("Reading note for profile: {}", profile)
    engine = get_db_engine()
    with Session(engine) as session:
        note = session.get(Note, profile)
        if note is None:
            logger.info("No note found for profile: {}", profile)
            return None
        else:
            logger.success("Note read successfully.")
            return note.text


def write_note(profile: str, text: str):
    logger.info("Writing note for profile: {}", profile)
    engine = get_db_engine()
    with Session(engine) as session:
        note = session.get(Note, profile)
        if note is None:
            # Create a new note
            note = Note(profile=profile, text=text)
        else:
            # Update the existing note
            note.text = text
        session.add(note)
        session.commit()
        logger.success("Note written successfully.")


@app.command()
def path():
    """Return the path to the database file."""
    print(get_db_path())

@app.command()
def query(profile: str):
    """Query database for a note."""
    pass

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

if __name__ == "__main__":
    app()
