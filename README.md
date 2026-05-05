DocShield is a fully offline tool for detecting, masking, and de-anonymizing sensitive business data. **It is stateless**, meaning it does not require a database to track mappings. It uses **Format Preserving Encryption (FPE)** to scramble data while keeping the document layout clean and LLM-friendly.

## Features & Detection Stack

DocShield uses a modular, plug-and-play detection stack:

1. **Regex Bank**: Configured via `rules/cloud_patterns.yaml`.
2. **Microsoft Presidio**: Industry standard for PII (names, emails, etc.).
3. **Keyword Detector**: Configured via `rules/sensitive_terms.csv`.
4. **GLiNER (Zero-shot NER)**: Smart neural model (disabled by default).
5. **Compact FPE Masking**: Keeps document layout intact and safe for LLMs.

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

## Legacy & Manual Mode

If you prefer to manage your own passphrases or need to process a single file with a specific name, use the legacy flags.

### Manual Anonymization
```bash
uv run docshield anonymize report.docx --output masked.docx --key "my-secret-passphrase"
```

### Manual De-anonymization
```bash
uv run docshield deanonymize masked.docx --output recovered.docx --key "my-secret-passphrase"
```

### Scanning (Audit Mode)
See what entities DocShield detects without actually altering the document.
```bash
uv run docshield scan my_document.docx
```

---

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
       └── spacy_model/      <-- Extract the SpaCy .tar.gz files in here
   ```

You can now zip the `dist/docshield/` folder and share it. Anyone can extract it and run `docshield.exe` immediately without Admin rights or internet access!

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
