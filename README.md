DocShield is a fully offline tool for detecting, masking, and de-anonymizing sensitive business data in text and images. **It is stateless**, meaning it does not require a database to track mappings. It uses **Format Preserving Encryption (FPE)** to scramble data while keeping the document layout clean, visually intact, and LLM-friendly.

## 🚀 Core Features

- **Format Preserving**: Accurately maintains Word document formatting (bold, italics, tables) during redaction using a precise, run-aware parser.
- **Image & Diagram Masking**: (Opt-in) Scans images within documents using AI-based OCR, paints redaction boxes over sensitive text inside the diagrams, and perfectly restores them upon deanonymization.
- **Stateless Architecture**: No external databases required. The entire session state is securely packed into a single `.key` vault file.
- **Robust Encryption**: Uses Format-Preserving Encryption (FPE) and AES-SIV for deterministic, highly secure data masking.
- **Zero-Shot NER**: Integrates GLiNER to detect arbitrary business entities (like project names or cloud resources) without retraining.
- **Standalone Portability**: Designed to be compiled into a single executable that can run in totally air-gapped environments.

### How Image Masking Works
DocShield leverages the fact that `.docx` files are essentially ZIP archives. When enabled, it:
1. Silently unzips the document and extracts all images.
2. Runs **EasyOCR** to identify text strings and their physical coordinates within the diagrams.
3. Passes the extracted text through the standard detection pipeline.
4. Physically draws white redaction boxes over the sensitive pixels and stamps the encrypted token.
5. Saves the pristine, original images into a secure `images.zip` backup file in your vault, and re-zips the document.

**⚠️ Cons to consider before enabling:**
- **Processing Speed**: Running local OCR on high-resolution diagrams is computationally heavy and will slow down the anonymization process.
- **OCR Limitations**: Diagrams with tiny, rotated, or highly distorted text might not be read correctly by the OCR engine, meaning some strings could escape detection.

## Features & Detection Stack

DocShield uses a modular, plug-and-play detection stack:

1. **Regex Bank**: Configured via `rules/cloud_patterns.yaml`.
2. **Microsoft Presidio**: Industry standard for PII (names, emails, etc.).
3. **Keyword Detector**: Configured via `rules/sensitive_terms.csv`.
4. **GLiNER (Zero-shot NER)**: Smart neural model (disabled by default).
5. **EasyOCR (Image Masking)**: AI vision engine to redact text inside embedded diagrams.
6. **Compact FPE Masking**: Keeps document layout intact and safe for LLMs.

## Installation

```bash
uv pip install -e .
uv run docshield setup
```

### Installation from ZIP / Source

If you have downloaded the source code as a ZIP file:

1. Unzip the folder and open a terminal inside it.
2. Run:
   ```bash
   pip install .
   docshield setup
   ```

## Using as a Library

To use DocShield in your Python code, first ensure the models are downloaded:

```python
from docshield import DocShield

# One-time setup to download models
DocShield.download_models()

# Use the library
ds = DocShield(key="your-key")
```

## Hands-free Team Workflow (Recommended)

DocShield now supports a **Session Gateway** mode. This is the easiest way for teams to work together without sharing passwords or managing complex keys.

### 1. Anonymizing a Folder or File
When you run anonymize without a key, DocShield generates a unique, Docker-style session name (e.g., `vibrant-phoenix`) and a high-entropy 32-character key.

```bash
# Anonymize all documents in a folder
uv run docshield anonymize my_docs/
```

**What happens:**
- A subfolder is created: `my_docs/vibrant-phoenix_output/`.
- Original filenames are removed for privacy: `vibrant-phoenix_1.docx`, `vibrant-phoenix_2.pdf`.
- A session key is saved inside: `vibrant-phoenix.key`.

### 2. De-anonymizing a Session Folder
To recover the original content, simply point DocShield at the output folder. It will automatically find the `.key` file and restore all documents.

```bash
uv run docshield deanonymize my_docs/vibrant-phoenix_output/
```
- Restored files are saved in: `my_docs/vibrant-phoenix_output/restored/`.

---

---

## CLI Usage & Shorthands

DocShield provides a high-performance CLI with shorthands for power users and a **Developer Mode** for deep auditing.

### 1. Command Shorthands
You can use single-letter commands for any operation:
- **`a`** instead of `anonymize`
- **`s`** instead of `scan`
- **`d`** instead of `deanonymize`

### 2. Developer Mode (`--verbose` / `-v`)
By default, DocShield is silent and only shows beautiful progress bars. To see all underlying library logs, AI model initialization, and warnings, use the verbose flag:
```bash
uv run docshield -v s Architecture_BRD.docx
```

---

## 🛠️ Operational Modes

### Scanning (Audit Mode)
See what entities DocShield detects without actually altering the document.
```bash
# Standard
uv run docshield scan report.docx

# Shorthand
uv run docshield s report.docx
```

### Manual Anonymization
If you prefer to manage your own passphrases or need to process a single file with a specific name.
```bash
# Standard
uv run docshield anonymize report.docx --output masked.docx --key "my-secret-passphrase"

# Shorthand (using a and -k)
uv run docshield a report.docx -o masked.docx -k "my-secret-passphrase"
```

### Manual De-anonymization
```bash
# Standard
uv run docshield deanonymize masked.docx --output recovered.docx --key "my-secret-passphrase"

# Shorthand
uv run docshield d masked.docx -o recovered.docx -k "my-secret-passphrase"
```

## Using as a Library

You can integrate DocShield directly into your Python applications.

### Basic Text Anonymization
```python
from docshield import DocShield

# 1. Initialize with your secret key
ds = DocShield(key="super-secret-key")

# 2. Anonymize raw text (Compact FPE)
text = "Contact amit@example.com for Project DocShield."
masked = ds.anonymize(text)
print(f"Masked: {masked}")

# 3. Recover original text
original = ds.deanonymize(masked)
```

## Configuring Detectors

Tweak behavior via environment variables:

| Detector | Environment Variable | Default |
|---|---|---|
| **Keyword Detector** | `DOCSHIELD_ENABLE_KEYWORD_DETECTOR` | `true` |
| **Regex Detector** | `DOCSHIELD_ENABLE_REGEX_DETECTOR` | `true` |
| **Presidio (PII)** | `DOCSHIELD_ENABLE_PRESIDIO_DETECTOR` | `true` |
| **GLiNER (Smart NER)** | `DOCSHIELD_ENABLE_GLINER_DETECTOR` | `false` |
| **Image Masking (OCR)** | `DOCSHIELD_ENABLE_IMAGE_MASKING` | `false` |

### Customizing GLiNER Labels
Add or remove AI detection targets in `rules/gliner_labels.txt` (one per line). For example, add `financial projection` to detect financial forecasts automatically.

### Avoiding False Positives (Denylist)
Add terms to `rules/denylist.txt` (one per line) to skip them.

---

## Building a Standalone Executable

You can package DocShield into a portable, standalone executable (e.g., `.exe` for Windows) that does NOT require Python or any setup to run.

1. **Pull the latest code** on the target operating system (e.g., Windows).
2. **Run the build script**:
   ```bash
   uv run build_exe.py
   ```
3. **Configure Portable Models**: PyInstaller will create a `dist/docshield/` folder. For the app to be truly "offline" and "plug and play", create a `models/` folder inside `dist/docshield/` and drop your downloaded models inside. The structure must look like this:

   ```text
   dist/docshield/
   ├── docshield.exe
   └── models/
       ├── gliner_model/     <-- Put your downloaded Hugging Face files here
       ├── spacy_model/      <-- Extract the SpaCy .tar.gz files in here
       └── easyocr/          <-- Put .zip or .pth files from EasyOCR here
   ```

> [!NOTE]
> **Where to get OCR models?**
> EasyOCR models (detection and recognition) can be downloaded from the [EasyOCR Releases page](https://github.com/JaidedAI/EasyOCR/releases). For English, you typically need `english_g2.zip` and `craft_mlt_25k.zip`. Drop the files directly into `models/easyocr/`.

You can now zip the `dist/docshield/` folder and share it. Anyone can extract it and run `docshield.exe` immediately without Admin rights or internet access!

### Running the Executable

**Double-Click Mode (NEW!):**
If you double-click the `docshield.exe` file, it will automatically launch a **Simple Native GUI**. This is perfect for users who aren't comfortable with the command line. It allows you to select files, folders, and keys with a single click.

**Command-Line Mode:**
Because DocShield is also a power-user tool, you can run it from the Command Prompt (or PowerShell) to use the advanced features, globs, and session management.

```cmd
docshield.exe anonymize C:\Users\John\Documents\Confidential\
```

To recover the documents:

```cmd
docshield.exe deanonymize C:\Users\John\Documents\Confidential\vibrant-phoenix_output\
```

> [!TIP]
> **Pro-Tip:** If you add the extracted `dist/docshield/` folder to your Windows **PATH Environment Variable**, you can open a terminal in *any* folder on your computer and simply type `docshield.exe` without having to be in the same folder as the `.exe`!

---

## Appendix: Alternate Thoughts & Evolution

The architecture of DocShield evolved through three distinct phases to reach its current "Compact & Stateless" design.

### Phase 1: The "Database-backed Vault" (Removed)
Initially, DocShield used a central SQLite database.
*   **Design**: Used short random UUIDs in text (e.g., `<<PERSON_3f9a1b2c>>`).
*   **Why we moved away**: Created a "Sync" problem. If the user lost the `vault.db`, the document was permanently unreadable. Managing database files across different teams was too complex.

### Phase 2: The "Stateless AES-SIV" (Legacy)
We moved the data *into* the document to remove the database dependency.
*   **Design**: Encrypted the original text into a Base64 blob: `<<PERSON:lK1bPT...>>`.
*   **Why we evolved**: While secure and stateless, the tokens were very long (~50 characters). This broke document layouts and made the text messy for LLMs. This mode is still available via `mask_old()`.

### Phase 3: The "Compact FPE" Architecture (Current)
The current standard uses **Format Preserving Encryption (FPE)**.
*   **Design**: Scrambles text into tokens of the exact same length (e.g., `Sarah` -> `[P:Rtbtq]`).
*   **The Innovation**: It uses a **Deterministic Keyed Substitution Cipher**. By using the secret key to seed a mathematical shuffle of the alphabet, we can reverse the scramble without any database.
*   **Benefits**: It is 100% LLM-safe (looks like normal text), layout-preserving, and stateless.

---

## Key Management
DocShield resolves your encryption key in this order:
1. CLI: `--key "passphrase"`
2. Env: `export DOCSHIELD_KEY="passphrase"`
3. File: A `.docshield.key` file in the current directory.
4. Prompt: Interactive input.

You can generate a new secure key file using:
```bash
uv run docshield new-key
```
