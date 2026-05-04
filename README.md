# DocShield — Business Document Anonymizer (Offline & Stateless)

DocShield is a fully offline tool for detecting, masking, and de-anonymizing sensitive business data. **It is stateless**, meaning it does not require a database to track mappings. Instead, it securely embeds the encrypted original data directly within the document's tokens.

## Features & Detection Stack

DocShield uses a modular, plug-and-play detection stack:

1. **Regex Bank**: Configured via `rules/cloud_patterns.yaml`.
2. **Microsoft Presidio**: Industry standard for PII (names, emails, etc.).
3. **Keyword Detector**: Configured via `rules/sensitive_terms.csv`.
4. **GLiNER (Zero-shot NER)**: Smart neural model (disabled by default).

## Installation

```bash
uv pip install -e .
uv run python -m spacy download en_core_web_lg
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
DocShield uses **AES-SIV** (Deterministic Encryption). The original text is encrypted and placed inside the token: `<<TYPE:ENCRYPTED_BLOB>>`.

```bash
uv run docshield anonymize my_document.docx --output masked.docx --key "my-secret-passphrase"
```
*No vault file is needed!*

### 3. De-anonymizing a Document
The program extracts the encrypted blobs from the document and restores the original text using your key.

```bash
uv run docshield deanonymize masked.docx --output recovered.docx --key "my-secret-passphrase"
```

## Configuring Detectors

Tweak behavior via environment variables:

| Detector | Environment Variable | Default |
|---|---|---|
| **Keyword Detector** | `DOCSHIELD_ENABLE_KEYWORD_DETECTOR` | `true` |
| **Regex Detector** | `DOCSHIELD_ENABLE_REGEX_DETECTOR` | `true` |
| **Presidio (PII)** | `DOCSHIELD_ENABLE_PRESIDIO_DETECTOR` | `true` |
| **GLiNER (Smart NER)** | `DOCSHIELD_ENABLE_GLINER_DETECTOR` | `false` |

---

## Appendix: Alternate Thoughts & Evolution

During development, we explored two distinct architectures. We eventually chose the **Stateless** approach, but the **Vault** approach remains a viable alternative for different use cases.

### Approach A: The "Stateless" Architecture (Current)
This is the current implementation. It stores the encrypted "secret" directly inside the document.

*   **Implementation**: Uses `AES-SIV` to generate a deterministic ciphertext of the original data, which is then Base64 encoded and placed in the token (e.g., `<<PERSON:lK1bPT...>>`).
*   **Why we chose it**: It removes the "lost database" risk. The document is its own source of truth. If you have the key, you can always recover the data, even years later, without searching for a specific `.db` file.
*   **Trade-off**: The tokens are longer (~50 characters), which may occasionally affect the visual layout of very tight tables.

### Approach B: The "Database-backed Vault" (Removed)
This was the initial prototype. It separated the "masked document" from the "sensitive data."

*   **Implementation**:
    *   **Tokens**: Used short, random UUIDs (e.g., `<<PERSON_3f9a1b2c>>`).
    *   **Storage**: A local SQLite database (`vault.db`) contained a table with two columns: `token` (Primary Key) and `encrypted_text`.
    *   **Security**: The SQLite database was itself encrypted using AES-Fernet.
*   **Why we moved away**: While it produced very clean, short tokens, it created a "Sync" problem. If a user shared the masked DOCX but forgot to share the `vault.db`, the document was permanently unreadable. For a small team working on various projects, managing hundreds of vault files was deemed too complex.
*   **When to revert**: If you find that the long tokens are consistently breaking your document layouts, you may want to re-implement the `vault.py` module and use short 8-character random IDs again.

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
