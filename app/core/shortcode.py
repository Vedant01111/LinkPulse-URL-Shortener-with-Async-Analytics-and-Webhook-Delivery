import secrets
import string

from app.core.config import settings

ALPHABET = string.ascii_letters + string.digits  # base62


def generate_short_code(length: int = None) -> str:
    """
    Generates a random base62 short code using a cryptographically secure
    RNG (secrets, not random) so codes aren't guessable/enumerable.

    Collisions are handled at the call site: the caller should retry with a
    fresh code if the DB unique constraint on short_code rejects an insert.
    With 7 chars of base62 (~62^7 ≈ 3.5 trillion combinations), collision
    probability stays negligible even at millions of URLs (birthday bound).
    """
    length = length or settings.short_code_length
    return "".join(secrets.choice(ALPHABET) for _ in range(length))
