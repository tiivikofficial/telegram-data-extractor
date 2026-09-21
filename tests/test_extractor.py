import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extractor import CyberScraper, clean_extracted_value, is_valid_credit_card, is_valid_ipv4


def test_ipv4_validation():
    assert is_valid_ipv4("192.168.1.1")
    assert not is_valid_ipv4("999.1.1.1")


def test_credit_card_luhn():
    assert is_valid_credit_card("4111 1111 1111 1111")
    assert not is_valid_credit_card("4111 1111 1111 1112")


def test_normalization_and_deduplication():
    scraper = object.__new__(CyberScraper)
    values = scraper.extract_from_text(
        "Contact TEST@Example.COM and test@example.com. "
        "Valid IP 192.168.1.1 and invalid IP 999.1.1.1."
    )
    assert ("email", "test@example.com") in values
    assert values.count(("email", "test@example.com")) == 1
    assert ("ip_v4", "192.168.1.1") in values
    assert ("ip_v4", "999.1.1.1") not in values


def test_trailing_url_punctuation_is_cleaned():
    assert clean_extracted_value("url", "https://example.com/path).") == "https://example.com/path"
