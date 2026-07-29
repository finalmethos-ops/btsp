def content_matches_declared_type(content: bytes, content_type: str) -> bool:
    if content_type in {"application/pdf", "application/x-pdf"}:
        return content.startswith(b"%PDF-")
    if content_type == "image/png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/jpeg":
        return content.startswith(b"\xff\xd8\xff")
    if content_type == "image/webp":
        return len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP"
    return False
