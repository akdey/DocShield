import PyInstaller.__main__
import os
from pathlib import Path

def build():
    print("Building DocShield standalone executable...")
    
    # Get absolute paths
    base_dir = Path(__file__).parent.absolute()
    cli_script = base_dir / "src" / "docshield" / "cli.py"
    rules_dir = base_dir / "rules"
    
    # Path separator for PyInstaller --add-data is platform dependent
    # ';' on Windows, ':' on POSIX
    data_sep = os.pathsep
    
    PyInstaller.__main__.run([
        str(cli_script),
        '--name=docshield',
        '--onedir', # Create a directory (Option 2) instead of a massive single file
        '--noconfirm', # Overwrite output directory without asking
        '--clean',
        
        # Include the rules folder
        f'--add-data={rules_dir}{data_sep}rules',
        
        # Hidden imports that PyInstaller might miss because they are dynamically loaded
        '--hidden-import=spacy',
        '--hidden-import=gliner',
        '--hidden-import=cryptography',
        '--hidden-import=presidio_analyzer',
        '--hidden-import=presidio_anonymizer',
        
        # Output paths
        f'--distpath={base_dir / "dist"}',
        f'--workpath={base_dir / "build"}'
    ])
    
    print("\n✅ Build complete!")
    print(f"Check the 'dist/docshield' folder.")

if __name__ == "__main__":
    build()
