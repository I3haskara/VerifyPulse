import typer

from rich import print

from verifypulse.planner import execute_pipeline

app = typer.Typer(help="VerifyPulse CLI")

@app.command()

def run(requirement: str):

    result = execute_pipeline(requirement)

    print("[bold green]Pipeline complete![/]")

    print(result)

if __name__ == "__main__":

    app()
