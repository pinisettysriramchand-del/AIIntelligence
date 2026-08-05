from stratiq.application.auth import AuthService


def test_password_hash_roundtrip():
    hashed = AuthService.hash_password("secret-pass")
    assert hashed != "secret-pass"
    assert AuthService.verify_password("secret-pass", hashed)
    assert not AuthService.verify_password("wrong", hashed)
