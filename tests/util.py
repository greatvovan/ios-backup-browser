import random
import string
import re


def generate_random_string(length):
    """Generates a random string of a given length."""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


def normalize_whitespace(s: str) -> str:
    """Normalize whitespace in a string for comparison."""
    return re.sub(r'\s+', ' ', s).strip()
