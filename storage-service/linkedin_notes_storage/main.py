import typer

import linkedin_notes_storage.database
import linkedin_notes_storage.host
import linkedin_notes_storage.register

app = typer.Typer()

def _add_typer(sub_app, name):
    # Workaround because command groups break the auto-one-command behavior
    # https://github.com/tiangolo/typer/issues/243#issuecomment-1319579781
    if len(sub_app.registered_commands) == 1:
        app.command(name)(sub_app.registered_commands[0].callback)
    else:
        app.add_typer(sub_app, name=name)

_add_typer(linkedin_notes_storage.database.app, name="database")
_add_typer(linkedin_notes_storage.host.app, name="run")
_add_typer(linkedin_notes_storage.register.app, name="register")
