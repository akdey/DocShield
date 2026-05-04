import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
import os

from .config import config
from . import DocShield, get_parser

app = typer.Typer(help="DocShield - Business Document Anonymizer (Offline & Stateless)")
console = Console()


def resolve_vault_key(key: str = typer.Option(None, "--key", "-k", help="Encryption key")) -> str:
    # 1. CLI Arg
    if key:
        return key
    
    # 2. Env Var
    env_key = os.environ.get("DOCSHIELD_KEY")
    if env_key:
        return env_key
        
    # 3. .vault.key file
    key_file = Path(".docshield.key")
    if key_file.exists():
        return key_file.read_text().strip()
        
    # 4. Prompt
    return typer.prompt("Enter encryption passphrase", hide_input=True)

@app.command()
def scan(
    file_path: Path = typer.Argument(..., help="Path to the document to scan")
):
    """Scan a document for PII and business entities without masking."""
    if not file_path.exists():
        console.print(f"[red]Error: File {file_path} not found[/red]")
        raise typer.Exit(1)
        
    parser = get_parser(file_path)
    
    with console.status(f"Parsing {file_path.name}..."):
        doc = parser.read(file_path)
        
    with console.status(f"Scanning {file_path.name}..."):
        ds = DocShield(key="dummy") # Key not needed for scan
        spans = ds.scan(doc.text)
        
    table = Table("Entity Type", "Text", "Start", "End", "Source")
    for span in spans:
        table.add_row(span.entity_type, span.text, str(span.start), str(span.end), span.source)
        
    console.print(table)
    console.print(f"\n[green]Found {len(spans)} entities.[/green]")

@app.command()
def anonymize(
    input_path: Path = typer.Argument(..., help="Path to the input document"),
    output_path: Path = typer.Option(..., "--output", "-o", help="Path to save the masked document"),
    key: str = typer.Option(None, "--key", "-k", help="Encryption key")
):
    """Detect and mask sensitive data, embedding encrypted original values in tokens."""
    if not input_path.exists():
        console.print(f"[red]Error: Input path {input_path} not found[/red]")
        raise typer.Exit(1)
        
    encryption_key = resolve_vault_key(key)
    ds = DocShield(encryption_key)
    with console.status("Processing..."):
        count = ds.anonymize_file(input_path, output_path)
        
    console.print(f"[green]Successfully masked {count} entities.[/green]")
    console.print(f"Stateless masked output saved to [bold]{output_path}[/bold]")

@app.command()
def deanonymize(
    input_path: Path = typer.Argument(..., help="Path to the masked document"),
    output_path: Path = typer.Option(..., "--output", "-o", help="Path to save the recovered document"),
    key: str = typer.Option(None, "--key", "-k", help="Encryption key")
):
    """Recover original document from a masked version using embedded tokens."""
    if not input_path.exists():
        console.print("[red]Error: Input path not found[/red]")
        raise typer.Exit(1)
        
    encryption_key = resolve_vault_key(key)
    ds = DocShield(encryption_key)
    
    with console.status("Decrypting..."):
        ds.deanonymize_file(input_path, output_path)
        
    console.print(f"[green]Successfully deanonymized document.[/green]")
    console.print(f"Recovered output saved to [bold]{output_path}[/bold]")

@app.command()
def setup():
    """Download required NLP models for DocShield."""
    DocShield.download_models()

@app.command()
def new_key():
    """Generate a random key and save it to .docshield.key."""
    from cryptography.fernet import Fernet
    key = Fernet.generate_key().decode()
    Path(".docshield.key").write_text(key)
    console.print("[green]Generated new key and saved to .docshield.key[/green]")

if __name__ == "__main__":
    app()
