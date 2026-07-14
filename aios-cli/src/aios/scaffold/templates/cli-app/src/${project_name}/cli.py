import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="$description")
console = Console()


@app.command()
def hello(name: str = typer.Argument("World", help="Who to greet")) -> None:
    console.print(f"Hello, [bold green]{name}[/bold green]!")


@app.command()
def version() -> None:
    console.print("$project_name v0.1.0")


if __name__ == "__main__":
    app()
