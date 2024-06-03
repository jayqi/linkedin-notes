from enum import StrEnum
from pathlib import Path
import struct
import sys
from typing import Self

from loguru import logger
from pydantic import BaseModel
import typer

from linkedin_notes_storage.database import read_note, write_note

app = typer.Typer()

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

@app.command()
def main():
    """Start Native Messaging host."""
    # Loop to listen for queries from native messaging
    while True:
        query = Query.receive()
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

if __name__ == "__main__":
    app()
