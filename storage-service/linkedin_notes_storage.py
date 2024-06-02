from enum import StrEnum
from pathlib import Path
import struct
import sys
from typing import Self

from loguru import logger
from platformdirs import user_data_dir
from pydantic import BaseModel
from sqlalchemy import Engine
from sqlmodel import Field, Session, SQLModel, create_engine


def get_db_path() -> Path:
    base_dir = user_data_dir("linkedin-notes-storage", ensure_exists=True)
    db_path = Path(base_dir) / "linkedin_notes.db"
    return db_path

_db_engine: Engine | None = None

def get_db_engine() -> Engine:
    global _db_engine
    if _db_engine is None:
        db_path = get_db_path()
        logger.info("Connecting to database: {}", db_path)
        _db_engine = create_engine(f"sqlite:///{db_path}")
    return _db_engine


class Note(SQLModel, table=True):
    profile: str = Field(primary_key=True)
    text: str = ""


def on_startup():
    engine = get_db_engine()
    SQLModel.metadata.create_all(engine)


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

class Mode(StrEnum):
    READ = "read"
    WRITE = "write"

class Query(BaseModel):
    profile: str
    mode: Mode
    text: str | None = None

    @classmethod
    def receive(cls) -> Self:
        raw_length = sys.stdin.buffer.read(4)
        if len(raw_length) == 0:
            sys.exit(0)
        message_length = struct.unpack("@I", raw_length)[0]
        message_content = sys.stdin.buffer.read(message_length).decode("utf-8")
        instance = cls.model_validate_json(message_content)
        logger.debug("Received query: {}", instance)
        return instance

class ReadResponsePayload(BaseModel):
    text: str | None

class WriteResponsePayload(BaseModel):
    success: bool

class Response(BaseModel):
    mode: Mode
    payload: ReadResponsePayload | WriteResponsePayload

    def send(self):
        logger.debug("Sending response: {}", self)
        encoded_content = self.model_dump_json().encode("utf-8")
        encoded_length = struct.pack("@I", len(encoded_content))
        sys.stdout.buffer.write(encoded_length)
        sys.stdout.buffer.write(encoded_content)
        sys.stdout.buffer.flush()


if __name__ == "__main__":
    on_startup()

    while True:
        query = Query.receive()
        with Path("log.txt").open("a") as f:
            f.write(query.model_dump_json() + "\n")
        logger.info("Received query: {}", query)
        if query.mode == Mode.READ:
            text = read_note(query.profile)
            response = Response(mode=Mode.READ, payload=ReadResponsePayload(text=text))
        else:
            try:
                write_note(query.profile, query.text)
                response = Response(mode=Mode.WRITE, payload=WriteResponsePayload(success=True))
            except Exception as e:
                logger.error("Failed to write note: {}", e)
                response = Response(mode=Mode.WRITE, payload=WriteResponsePayload(success=False))
        response.send()
