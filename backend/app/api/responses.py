from urllib.parse import quote


def safe_download_filename(filename: str, fallback: str = "btsp-export") -> str:
    cleaned = "".join(
        "-" if character in '/\\?%*:|"<>;\r\n' else character for character in filename
    ).strip(" .")
    return cleaned or fallback


def content_disposition(filename: str, disposition: str = "attachment") -> str:
    safe_name = safe_download_filename(filename)
    encoded = quote(safe_name)
    return f"{disposition}; filename=\"{safe_name}\"; filename*=UTF-8''{encoded}"
