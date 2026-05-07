import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
import os
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
from .config import config
from . import DocShield, get_parser
from .sessions import SessionManager

app = typer.Typer(help="DocShield - Business Document Anonymizer (Offline & Stateless)")
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
    inputs: list[Path] = typer.Argument(..., help="Path to input document(s) or folder"),
    output: Path = typer.Option(None, "--output", "-o", help="Output path (only for single files)"),
    session: str = typer.Option(None, "--session", "-s", help="Session name (e.g. 'project-x')"),
    key: str = typer.Option(None, "--key", "-k", help="Legacy encryption key")
):
    """Detect and mask sensitive data. Supports single files, globs, or folders."""
    # Resolve all files
    files = []
    for p in inputs:
        if p.is_dir():
            files.extend(list(p.glob("*.*")))
        else:
            files.append(p)
    
    files = [f for f in files if f.suffix in [".docx", ".txt", ".pdf"]]
    
    if not files:
        console.print("[red]Error: No supported files found.[/red]")
        raise typer.Exit(1)

    # Determine mode: Legacy Single File vs New Session Mode
    if len(files) == 1 and output and not session and key:
        # Legacy Mode
        encryption_key = resolve_vault_key(key)
        ds = DocShield(encryption_key)
        with console.status(f"Anonymizing {files[0].name}..."):
            ds.anonymize_file(files[0], output)
        console.print(f"[green]Successfully masked {files[0].name} -> {output}[/green]")
        return

    # Session Mode
    session_name = session or SessionManager.generate_name()
    base_dir = files[0].parent
    output_dir = base_dir / f"{session_name}_output"
    output_dir.mkdir(exist_ok=True)
    
    # Generate and save session key
    vault_path = SessionManager.create_session_vault(session_name, output_dir)
    encryption_key = SessionManager.load_session_key(vault_path)
    ds = DocShield(encryption_key)
    
    console.print(f"🚀 Starting session: [bold cyan]{session_name}[/bold cyan]")
    console.print(f"📁 Output directory: [blue]{output_dir}[/blue]")
    console.print(f"🔑 Session key saved to: [yellow]{vault_path.name}[/yellow]\n")

    with console.status("Processing batch...") as status:
        for i, file_path in enumerate(files, 1):
            new_name = f"{session_name}_{i}{file_path.suffix}"
            dest = output_dir / new_name
            status.update(f"Masking {file_path.name} -> {new_name}...")
            ds.anonymize_file(file_path, dest)
            
    console.print(f"\n[green]✅ Successfully processed {len(files)} files.[/green]")
    console.print(f"[bold]Keep the '{session_name}.key' file to de-anonymize this batch.[/bold]")

@app.command()
def deanonymize(
    input_path: Path = typer.Argument(..., help="Path to masked document or session folder"),
    output: Path = typer.Option(None, "--output", "-o", help="Output path (optional)"),
    session: str = typer.Option(None, "--session", "-s", help="Session name if key is separate"),
    key: str = typer.Option(None, "--key", "-k", help="Legacy encryption key")
):
    """Recover original content. Points to a file or a session folder."""
    if not input_path.exists():
        console.print("[red]Error: Input path not found[/red]")
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
            console.print(f"🔑 Using session key: [yellow]{key_files[0].name}[/yellow]")
        else:
            # Fallback to prompt/legacy
            encryption_key = resolve_vault_key()

    ds = DocShield(encryption_key)

    # 2. Process Files
    files_to_process = []
    if input_path.is_dir():
        files_to_process = [f for f in input_path.glob("*.*") if f.suffix in [".docx", ".txt", ".pdf"]]
        dest_dir = input_path / "restored"
    else:
        files_to_process = [input_path]
        dest_dir = input_path.parent / "restored"

    dest_dir.mkdir(exist_ok=True)
    
    with console.status("Decrypting...") as status:
        for f in files_to_process:
            out_name = output or f"restored_{f.name}"
            target = dest_dir / out_name
            status.update(f"Restoring {f.name}...")
            ds.deanonymize_file(f, target)
        
    console.print(f"\n[green]✅ Successfully deanonymized {len(files_to_process)} file(s).[/green]")
    console.print(f"Restored files saved in: [blue]{dest_dir}[/blue]")

@app.command()
def setup():
    """Download required NLP models for DocShield."""
    DocShield.download_models()

@app.command()
def new_key():
    """Generate a random key and save it to .docshield.key."""
    from .sessions import SessionManager
    key = SessionManager.generate_key()
    Path(".docshield.key").write_text(key)
    console.print("[green]Generated new key and saved to .docshield.key[/green]")

if __name__ == "__main__":
    app()

if __name__ == "__main__":
    app()
