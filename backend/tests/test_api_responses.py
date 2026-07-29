from app.api.responses import content_disposition, safe_download_filename


def test_safe_download_filename_strips_header_and_path_unsafe_characters():
    assert (
        safe_download_filename('Event: Orders/Backup\r\nbad".xlsx')
        == "Event- Orders-Backup--bad-.xlsx"
    )


def test_content_disposition_includes_safe_ascii_and_encoded_filename():
    header = content_disposition("Leadership Meeting Orders.xlsx")

    assert header.startswith('attachment; filename="Leadership Meeting Orders.xlsx"')
    assert "filename*=UTF-8''Leadership%20Meeting%20Orders.xlsx" in header


def test_content_disposition_supports_inline_preview_downloads():
    assert content_disposition("floor-plan.pdf", "inline").startswith(
        'inline; filename="floor-plan.pdf"'
    )
