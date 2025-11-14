import typer
from villager.db import MetaStore
from villager import CityRegistry
import villager


app = typer.Typer(help="Villager CLI")
meta = MetaStore()


@app.command()
def load(dataset: str):
    """Load a remote dataset into the database. Use `villager status` to view eligible datasets."""
    DATASETS = {"cities": villager.cities.load}

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
    loaded_key = CityRegistry.META_LOADED_KEY
    typer.echo(f"{url_key}: {meta.get(url_key)}")
    typer.echo(f"{loaded_key}: {meta.get(loaded_key) == '1'}")
