import subprocess
from pathlib import Path

def test_pdf():
    # Write a test text file, we can't easily create a PDF in standard python without dependencies
    # Wait, fpdf2 is installed! We can create a test PDF using it!
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    pdf.multi_cell(0, 5, txt="Contact John Doe at john.doe@example.com")
    
    test_file = Path('scratch/test_pdf.pdf')
    test_file.parent.mkdir(exist_ok=True)
    pdf.output(str(test_file))
    print(f"Created {test_file}")
    
    # Anonymize
    print("\nAnonymizing...")
    subprocess.run(["uv", "run", "docshield", "anonymize", str(test_file)])
    
    # Check output
    session_dir = list(Path('scratch').glob('*_output'))[0]
    session_name = session_dir.name.replace('_output', '')
    masked_file = session_dir / f"{session_name}_1.pdf"
    
    assert masked_file.exists(), f"Output should be {masked_file}"
    print(f"\nMasked file created: {masked_file}")
    print("SUCCESS: PDF output maintained the .pdf file extension.")

if __name__ == "__main__":
    import shutil
    for d in Path('scratch').glob('*_output'):
        shutil.rmtree(d)
        
    test_pdf()
