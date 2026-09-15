"""
Creates and holds the single Supabase client used across the app.

Reads SUPABASE_URL and SUPABASE_KEY from environment variables (loaded
from .env by main.py). Never hardcode these values, and never use the
service_role key here -- only the anon (public) key belongs in this app.
"""
import os

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "SUPABASE_URL and SUPABASE_KEY must be set in your .env file. "
        "Copy .env.example to .env and fill in your project's values."
    )

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
