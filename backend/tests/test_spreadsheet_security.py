from app.services.spreadsheet_security import spreadsheet_safe_cell, spreadsheet_safe_row


def test_spreadsheet_cells_escape_formula_prefixes() -> None:
    assert spreadsheet_safe_cell('=HYPERLINK("https://example.test")') == (
        '\'=HYPERLINK("https://example.test")'
    )
    assert spreadsheet_safe_cell("  +SUM(1,2)") == "'  +SUM(1,2)"
    assert spreadsheet_safe_cell("@malicious") == "'@malicious"
    assert spreadsheet_safe_cell("ordinary text") == "ordinary text"
    assert spreadsheet_safe_cell(42) == 42


def test_spreadsheet_rows_preserve_non_text_values() -> None:
    assert spreadsheet_safe_row(["-1+2", 3, None]) == ["'-1+2", 3, None]
