from app.core.shortcode import generate_short_code, ALPHABET


def test_short_code_default_length():
    code = generate_short_code()
    assert len(code) == 7


def test_short_code_custom_length():
    code = generate_short_code(length=10)
    assert len(code) == 10


def test_short_code_uses_valid_alphabet():
    code = generate_short_code()
    assert all(char in ALPHABET for char in code)


def test_short_codes_are_not_predictable_duplicates():
    # Not a proof of uniqueness (this is probabilistic by design), but
    # generating a large batch and checking for collisions is a reasonable
    # smoke test that the RNG isn't degenerate.
    codes = {generate_short_code() for _ in range(10_000)}
    assert len(codes) == 10_000
