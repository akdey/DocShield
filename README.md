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

## How to Use (Stateless Mode)

> [!TIP]
> Always prefix commands with `uv run` to ensure you are using the project's virtual environment.

### 1. Scanning a Document (Audit Mode)
See what entities DocShield detects without actually altering the document.

```bash
uv run docshield scan my_document.docx
```
*Supported formats: `.txt`, `.docx`, `.pdf`*

### 2. Anonymizing a Document
DocShield uses **Compact FPE Mode** by default. Original text is scrambled into a token of the same length: `[T:scrambled]`.

```bash
uv run docshield anonymize my_document.docx --output masked.docx --key "my-secret-passphrase"
```

### 3. De-anonymizing a Document
The program recognizes the compact tags and "un-shuffles" the text back to its original state using your key.

```bash
uv run docshield deanonymize masked.docx --output recovered.docx --key "my-secret-passphrase"
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
# Masked: Contact [E:itbtq.x@hztdmyh.nod] for Project [P:DocShield].

# 3. Recover original text
original = ds.deanonymize(masked)
print(f"Recovered: {original}")
```

### Anonymizing Files

You can also process entire documents (`.docx`, `.pdf`, `.txt`):

```python
from docshield import DocShield

ds = DocShield(key="secret-key")

# Anonymize a Word document
ds.anonymize_file("confidential.docx", "masked.docx")

# Recover the original file
ds.deanonymize_file("masked.docx", "restored.docx")
```

### Advanced Usage (Custom Pipeline)

If you want more control, you can use the internal components:

```python
from docshield import DetectionPipeline, Masker, DocShieldCrypto

crypto = DocShieldCrypto("my-key")
pipeline = DetectionPipeline()
masker = Masker(crypto)

text = "This is a secret."
spans = pipeline.run(text)
# Use the new compact mask
masked = masker.mask(text, spans)
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

If DocShield is masking terms that are not sensitive (like "Project Overview" or "Table of Contents"), you can add them to the **Denylist**.

1. Open `rules/denylist.txt`.
2. Add the terms you want to skip (one per line).
3. These terms will be explicitly ignored by all detectors.

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
