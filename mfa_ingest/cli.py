import typer
from .core.settings import settings
from .core.db import make_engine, reflect_sanity_check

app = typer.Typer(no_args_is_help=True)


@app.command()
def env():
    typer.echo(f"APP_ENV={settings.app_env}")
    typer.echo(f"CHUNK_SIZE={settings.chunk_size}")


@app.command()
def ping_db():
    eng = make_engine()
    with eng.connect():
        typer.echo("✅ DB connection OK")


@app.command()
def check_schema():
    eng = make_engine()
    reflect_sanity_check(eng)
    typer.echo("✅ Live schema looks OK (basic check)")


if __name__ == "__main__":
    app()
