"""List all available Groq models via the official SDK."""

import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env", override=True)
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
models = client.models.list()

print(f"{'MODEL ID':<45} {'OWNED BY':<20} {'ACTIVE'}")
print("-" * 75)
for m in sorted(models.data, key=lambda x: x.id):
    print(f"{m.id:<45} {m.owned_by:<20} {m.active}")
