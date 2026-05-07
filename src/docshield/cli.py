import typer
import logging
import warnings
import sys
import contextlib
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.text import Text
from rich import box
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

# Global state for verbose mode
state = {"verbose": False}

def set_verbose(enabled: bool):
    """Enable developer mode logging if requested."""
    if enabled:
        state["verbose"] = True
        logging.getLogger().setLevel(logging.DEBUG)
        for logger_name in ["transformers", "huggingface_hub", "presidio-analyzer", "spacy", "easyocr", "gliner"]:
            logging.getLogger(logger_name).setLevel(logging.DEBUG)
        console.print("[dim]Developer Mode: Verbose logging enabled.[/dim]")

@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable developer mode (show all library logs)")
):
    """
    DocShield CLI - Secure, offline document anonymization.
    """
    set_verbose(verbose)

@contextlib.contextmanager
def silence_stderr():
    """Redirect stderr to devnull to hide unsuppressible library warnings, unless in verbose mode."""
    if state["verbose"]:
        yield sys.stderr
        return
        
    new_target = open(os.devnull, "w")
    old_target = sys.stderr
    sys.stderr = new_target
    try:
        yield new_target
    finally:
        sys.stderr = old_target
        new_target.close()

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

@app.command("scan")
@app.command("s", hidden=True)
def scan(
    file_path: Path = typer.Argument(..., help="Path to the document to scan"),
    key: str = typer.Option(None, "--key", "-k", help="Optional key (for future-proofing/consistency)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable developer mode")
):
    """Scan a document for PII and business entities [bold]without[/bold] masking."""
    set_verbose(verbose)
    if not file_path.exists():
        console.print(f"[bold red]Error:[/bold red] File {file_path} not found")
        raise typer.Exit(1)
        
    parser = get_parser(file_path)
    
    with console.status(f"[bold blue]Analyzing {file_path.name}...[/bold blue]") as status:
        def update_status(msg):
            status.update(f"[bold blue]{msg}[/bold blue]")
            
        doc = parser.read(file_path)
        with silence_stderr():
            ds = DocShield(key="dummy") # Key not needed for scan
            spans = ds.scan(doc.text, status_callback=update_status)
        
    if not spans:
        console.print(f"\n[bold yellow]No sensitive entities found in {file_path.name}.[/bold yellow]")
        return

    table = Table(title=f"Detection Report: {file_path.name}", box=box.SIMPLE, header_style="bold magenta")
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
    console.print(f"\n[bold green]✅ Found {len(spans)} sensitive entities.[/bold green]\n")

@app.command("anonymize")
@app.command("a", hidden=True)
def anonymize(
    inputs: list[Path] = typer.Argument(..., help="Path to input document(s) or folder"),
    output: Path = typer.Option(None, "--output", "-o", help="Output path (only for single files)"),
    session: str = typer.Option(None, "--session", "-s", help="Session name (e.g. 'project-x')"),
    key: str = typer.Option(None, "--key", "-k", help="Legacy encryption key"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable developer mode")
):
    """Detect and mask sensitive data. [bold cyan]Supports single files, globs, or folders.[/bold cyan]"""
    set_verbose(verbose)
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
        with silence_stderr():
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
    with silence_stderr():
        ds = DocShield(encryption_key)
    
    console.print(f"\n🚀 [bold cyan]Starting Anonymization Session:[/bold cyan] [reverse] {session_name} [/reverse]")
    console.print(f"📁 [bold]Destination:[/bold] {output_dir}")
    console.print(f"🔑 [bold]Vault Key:[/bold]   {vault_path.name}\n")

    file_results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=None),
        TaskProgressColumn(),
        console=console,
        expand=True
    ) as progress:
        task = progress.add_task("[blue]Processing documents...", total=len(files))
        for i, file_path in enumerate(files, 1):
            new_name = f"{session_name}_{i}{file_path.suffix}"
            dest = output_dir / new_name
            
            steps = []
            def update_progress(msg):
                steps.append(msg)
                progress.update(task, description=f"[bold blue]{file_path.name}[/bold blue]: [dim]{msg}[/dim]")
            
            with silence_stderr():
                count = ds.anonymize_file(file_path, dest, status_callback=update_progress)
            file_results.append((file_path.name, count, steps))
            progress.advance(task)
            
    # Final Summary Table
    summary_table = Table(box=box.SIMPLE, header_style="bold cyan")
    summary_table.add_column("File Name")
    summary_table.add_column("Entities Masked", justify="right")
    summary_table.add_column("Pipeline Steps", style="dim")
    
    for name, count, steps in file_results:
        summary_table.add_row(name, str(count), " → ".join(steps))
    
    console.print("\n[bold green]Processing Complete![/bold green]")
    console.print(summary_table)

    # Attention-seeking key warning
    warning_text = Text.assemble(
        ("IMPORTANT: ", "bold red"),
        "The file ", (f"{session_name}.key", "bold yellow"), 
        " is the ", ("ONLY", "bold underline"), " way to recover your data.\n",
        "If you lose this key, the original data is permanently lost. ",
        ("Do not share it.", "bold red italic")
    )
    console.print(Panel(warning_text, title="[bold red]🔐 SECURITY VAULT KEY[/bold red]", border_style="red", expand=False))
    console.print("")

@app.command("deanonymize")
@app.command("d", hidden=True)
def deanonymize(
    input_path: Path = typer.Argument(..., help="Path to masked document or session folder"),
    output: Path = typer.Option(None, "--output", "-o", help="Output path (optional)"),
    session: str = typer.Option(None, "--session", "-s", help="Session name if key is separate"),
    key: str = typer.Option(None, "--key", "-k", help="Legacy encryption key"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable developer mode")
):
    """Recover original content from masked documents."""
    set_verbose(verbose)
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

    with silence_stderr():
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
    
    file_results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=None),
        TaskProgressColumn(),
        console=console,
        expand=True
    ) as progress:
        task = progress.add_task("[magenta]Restoring originals...", total=len(files_to_process))
        for f in files_to_process:
            out_name = output or f"restored_{f.name}"
            target = dest_dir / out_name
            
            steps = []
            def update_progress(msg):
                steps.append(msg)
                progress.update(task, description=f"[bold magenta]{f.name}[/bold magenta]: [dim]{msg}[/dim]")
                
            with silence_stderr():
                ds.deanonymize_file(f, target, status_callback=update_progress)
            file_results.append((f.name, steps))
            progress.advance(task)
        
    console.print(f"\n[bold green]✅ Restoration Complete![/bold green]")
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
