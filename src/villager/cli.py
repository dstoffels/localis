import typer
from typing_extensions import Annotated
from villager.data import MetaStore, Database
from villager import CityRegistry
import villager


app = typer.Typer(help="Villager CLI")
meta = MetaStore()


@app.command()
def load(
    dataset: str,
    confirmed: Annotated[
        bool, typer.Option("--yes", "-y", help="Auto-confirm without prompting")
    ] = False,
    custom_dir: Annotated[
        str,
        typer.Option(
            "--path",
            "-p",
            help="Custom directory to store the database, by default load will copy the sqlite file to your current working directory.",
        ),
    ] = "",
):
    """Load a remote dataset into the database. Use `villager status` to view eligible datasets."""

    DATASETS = {"cities": lambda: villager.cities.load(confirmed, custom_dir)}

    if dataset in DATASETS:
        DATASETS[dataset]()
    else:
        typer.echo(f"Unknown dataset.")
        raise typer.Exit(code=1)


@app.command()
def unload(dataset: str):
    """Drop an eligible table from the database. Use `villager status` to view eligible datasets."""
    DATASETS = {"cities": villager.cities.unload}

    if dataset in DATASETS:
        DATASETS[dataset]()
    else:
        typer.echo(f"Unknown dataset.")
        raise typer.Exit(code=1)


@app.command(hidden=True)
def seturl(url: str):
    meta.set(CityRegistry.META_URL_KEY, url)
    typer.echo(
        f"Fixture url set to: {meta.get(CityRegistry.META_URL_KEY)}",
    )


@app.command()
def status():
    """View the current state of datasets"""
    url_key = CityRegistry.META_URL_KEY
    typer.echo(f"{url_key}: {meta.get(url_key)}")
    typer.echo(f"Current Daabase: {Database.get_db_path()}")
    typer.echo(f"Cities Loaded: {Database.CONFIG_FILE.exists()}")
