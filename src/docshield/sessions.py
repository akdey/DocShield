import random
import secrets
import string
import json
from pathlib import Path
from datetime import datetime

ADJECTIVES = [
    "serene", "vibrant", "bold", "quiet", "dazzling", "swift", "brave", "calm",
    "clever", "eager", "gentle", "happy", "jolly", "kind", "lively", "nice",
    "proud", "silly", "witty", "zealous", "arcane", "frosty", "golden", "iron"
]

NOUNS = [
    "phoenix", "hopper", "turing", "curie", "darwin", "nightingale", "lovelace",
    "einstein", "newton", "galileo", "tesla", "bardeen", "franklin", "mendel",
    "pasteur", "kepler", "hubble", "hawking", "sagan", "bohr", "planck"
]

class SessionManager:
    @staticmethod
    def generate_name() -> str:
        """Generates a Docker-style session name: adjective-noun."""
        return f"{random.choice(ADJECTIVES)}-{random.choice(NOUNS)}"

    @staticmethod
    def generate_key(length: int = 32) -> str:
        """Generates a high-entropy random alphanumeric key."""
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))

    @staticmethod
    def create_session_vault(session_name: str, output_dir: Path) -> Path:
        """Creates a .key file containing the session metadata."""
        vault_path = output_dir / f"{session_name}.key"
        key = SessionManager.generate_key()
        
        vault_data = {
            "session_id": session_name,
            "key": key,
            "created_at": datetime.now().isoformat(),
            "version": "0.3.0"
        }
        
        with open(vault_path, "w") as f:
            json.dump(vault_data, f, indent=4)
            
        return vault_path

    @staticmethod
    def load_session_key(vault_path: Path) -> str:
        """Loads the raw key from a .key vault file."""
        if not vault_path.exists():
            raise FileNotFoundError(f"Session vault not found at {vault_path}")
            
        with open(vault_path, "r") as f:
            data = json.load(f)
            return data["key"]
