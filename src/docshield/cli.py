import typer
import logging
import warnings
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
import os

# Suppress noisy library logs by default
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Suppress warnings
warnings.filterwarnings("ignore")

# Configure standard logging to be quiet
logging.basicConfig(level=logging.ERROR)
# Specifically target known noisy loggers
for logger_name in ["transformers", "huggingface_hub", "presidio-analyzer", "spacy", "easyocr", "gliner"]:
    logging.getLogger(logger_name).setLevel(logging.ERROR)

from .config import config
from . import DocShield, get_parser
from .sessions import SessionManager

app = typer.Typer(
    help="DocShield - Business Document Anonymizer (Offline & Stateless)",
    rich_markup_mode="rich",
    no_args_is_help=True
)
console = Console()

def resolve_vault_key(key: str = None, session_key_path: Path = None) -> str:
    # 1. Session Key File (Highest Priority for Auto-Mode)
    if session_key_path and session_key_path.exists():
        return SessionManager.load_session_key(session_key_path)

    # 2. CLI Arg
    if key:
        return key
    
    # 3. Env Var
    env_key = os.environ.get("DOCSHIELD_KEY")
    if env_key:
        return env_key
        
    # 4. .docshield.key file
    key_file = Path(".docshield.key")
    if key_file.exists():
        return key_file.read_text().strip()
        
    # 5. Prompt
    return typer.prompt("Enter encryption passphrase", hide_input=True)

@app.command()
def scan(
    file_path: Path = typer.Argument(..., help="Path to the document to scan"),
    key: str = typer.Option(None, "--key", "-k", help="Optional key (for future-proofing/consistency)")
):
    """Scan a document for PII and business entities [bold]without[/bold] masking."""
    if not file_path.exists():
        console.print(f"[bold red]Error:[/bold red] File {file_path} not found")
        raise typer.Exit(1)
        
    parser = get_parser(file_path)
    
    with console.status(f"[bold blue]Analyzing {file_path.name}...[/bold blue]"):
        doc = parser.read(file_path)
        ds = DocShield(key="dummy") # Key not needed for scan
        spans = ds.scan(doc.text)
        
    if not spans:
        console.print(f"[yellow]No sensitive entities found in {file_path.name}.[/yellow]")
        return

    table = Table(title=f"Detection Report: {file_path.name}", box=None, header_style="bold magenta")
    table.add_column("Entity Type", style="cyan")
    table.add_column("Text", style="white")
    table.add_column("Position", style="dim")
    table.add_column("Source", style="dim green")
    
    for span in spans:
        table.add_row(
            span.entity_type, 
            span.text, 
            f"{span.start}:{span.end}", 
            span.source
        )
        
    console.print(table)
    console.print(f"\n[bold green]✅ Found {len(spans)} sensitive entities.[/bold green]")

@app.command()
def anonymize(
    inputs: list[Path] = typer.Argument(..., help="Path to input document(s) or folder"),
    output: Path = typer.Option(None, "--output", "-o", help="Output path (only for single files)"),
    session: str = typer.Option(None, "--session", "-s", help="Session name (e.g. 'project-x')"),
    key: str = typer.Option(None, "--key", "-k", help="Legacy encryption key")
):
    """Detect and mask sensitive data. [bold cyan]Supports single files, globs, or folders.[/bold cyan]"""
    # Resolve all files
    files = []
    for p in inputs:
        if p.is_dir():
            files.extend(list(p.glob("*.*")))
        else:
            files.append(p)
    
    files = [f for f in files if f.suffix.lower() in [".docx", ".txt", ".pdf"]]
    
    if not files:
        console.print("[bold red]Error:[/bold red] No supported files found (.docx, .txt, .pdf).")
        raise typer.Exit(1)

    # Determine mode: Legacy Single File vs New Session Mode
    if len(files) == 1 and output and not session and key:
        # Legacy Mode
        encryption_key = resolve_vault_key(key)
        ds = DocShield(encryption_key)
        with console.status(f"[bold blue]Anonymizing {files[0].name}...[/bold blue]"):
            ds.anonymize_file(files[0], output)
        console.print(f"[bold green]Successfully masked:[/bold green] {files[0].name} [bold]→[/bold] {output}")
        return

    # Session Mode
    session_name = session or SessionManager.generate_name()
    base_dir = files[0].parent if files[0].is_file() else files[0]
    output_dir = base_dir / f"{session_name}_output"
    output_dir.mkdir(exist_ok=True)
    
    # Generate and save session key
    vault_path = SessionManager.create_session_vault(session_name, output_dir)
    encryption_key = SessionManager.load_session_key(vault_path)
    ds = DocShield(encryption_key)
    
    console.print(f"\n🚀 [bold cyan]Starting Anonymization Session:[/bold cyan] [reverse]{session_name}[/reverse]")
    console.print(f"📁 [bold]Destination:[/bold] {output_dir}")
    console.print(f"🔑 [bold]Vault Key:[/bold]   {vault_path.name}\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=None),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[blue]Processing documents...", total=len(files))
        for i, file_path in enumerate(files, 1):
            new_name = f"{session_name}_{i}{file_path.suffix}"
            dest = output_dir / new_name
            progress.update(task, description=f"[dim]Masking {file_path.name}...[/dim]")
            ds.anonymize_file(file_path, dest)
            progress.advance(task)
            
    console.print(f"\n[bold green]✅ Successfully processed {len(files)} files.[/bold green]")
    console.print(f"Keep the [bold yellow]{session_name}.key[/bold yellow] file to de-anonymize this batch.\n")

@app.command()
def deanonymize(
    input_path: Path = typer.Argument(..., help="Path to masked document or session folder"),
    output: Path = typer.Option(None, "--output", "-o", help="Output path (optional)"),
    session: str = typer.Option(None, "--session", "-s", help="Session name if key is separate"),
    key: str = typer.Option(None, "--key", "-k", help="Legacy encryption key")
):
    """Recover original content from masked documents."""
    if not input_path.exists():
        console.print("[bold red]Error:[/bold red] Input path not found")
        raise typer.Exit(1)

    # 1. Resolve Encryption Key
    encryption_key = None
    if key:
        encryption_key = resolve_vault_key(key)
    else:
        # Try auto-lookup for session key
        search_dir = input_path if input_path.is_dir() else input_path.parent
        key_files = list(search_dir.glob("*.key"))
        if key_files:
            encryption_key = SessionManager.load_session_key(key_files[0])
            console.print(f"🔑 [bold green]Session vault unlocked:[/bold green] [yellow]{key_files[0].name}[/yellow]")
        else:
            # Fallback to prompt/legacy
            encryption_key = resolve_vault_key()

    ds = DocShield(encryption_key)

    # 2. Process Files
    files_to_process = []
    if input_path.is_dir():
        files_to_process = [f for f in input_path.glob("*.*") if f.suffix.lower() in [".docx", ".txt", ".pdf"]]
        dest_dir = input_path / "restored"
    else:
        files_to_process = [input_path]
        dest_dir = input_path.parent / "restored"

    dest_dir.mkdir(exist_ok=True)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=None),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[magenta]Restoring originals...", total=len(files_to_process))
        for f in files_to_process:
            out_name = output or f"restored_{f.name}"
            target = dest_dir / out_name
            progress.update(task, description=f"[dim]Decrypting {f.name}...[/dim]")
            ds.deanonymize_file(f, target)
            progress.advance(task)
        
    console.print(f"\n[bold green]✅ Successfully deanonymized {len(files_to_process)} file(s).[/bold green]")
    console.print(f"Restored files saved in: [bold blue]{dest_dir}[/bold blue]\n")

@app.command()
def setup():
    """Download required AI models for DocShield."""
    with console.status("[bold blue]Downloading and configuring models...[/bold blue]"):
        DocShield.download_models()
    console.print("[bold green]Setup complete! DocShield is ready for offline use.[/bold green]")

@app.command()
def new_key():
    """Generate a random key and save it to .docshield.key."""
    from .sessions import SessionManager
    key = SessionManager.generate_key()
    Path(".docshield.key").write_text(key)
    console.print("[bold green]Generated new key and saved to .docshield.key[/bold green]")

if __name__ == "__main__":
    app()
