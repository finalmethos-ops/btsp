from app.services.upload_validation import content_matches_declared_type


def test_upload_signatures_match_declared_content_types() -> None:
    assert content_matches_declared_type(b"%PDF-1.7", "application/pdf")
    assert content_matches_declared_type(b"\x89PNG\r\n\x1a\ncontent", "image/png")
    assert content_matches_declared_type(b"\xff\xd8\xffcontent", "image/jpeg")
    assert content_matches_declared_type(b"RIFF\x04\x00\x00\x00WEBP", "image/webp")


def test_upload_signatures_reject_mislabeled_or_unknown_content() -> None:
    assert not content_matches_declared_type(b"not-an-image", "image/png")
    assert not content_matches_declared_type(b"RIFF\x04\x00\x00\x00NOPE", "image/webp")
    assert not content_matches_declared_type(b"%PDF-1.7", "image/jpeg")
    assert not content_matches_declared_type(b"content", "text/html")
