import pytest

from health_text_redact import redact

# All identifiers below are invented. The IBAN is the standard documentation
# example and is not a real account.


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Write to anna.example@mail.test please", "Write to [EMAIL] please"),
        ("See https://example.org/my-results?id=7 for details", "See [URL] for details"),
        ("Ruf mich an: 0171 2345678", "Ruf mich an: [PHONE]"),
        ("My number is +49 30 1234567.", "My number is [PHONE]."),
        ("Call +44 (0)20 7946 0000 today", "Call [PHONE] today"),
        ("Tel. 030/12345678", "Tel. [PHONE]"),
        ("IBAN DE89 3704 0044 0532 0130 00 bitte", "IBAN [IBAN] bitte"),
        ("Versichertennummer A123456789", "Versichertennummer [INSURANCE_NUMBER]"),
        ("Ich wohne in der Hauptstraße 12, 10115 Berlin.", "Ich wohne in der [ADDRESS]."),
        ("I live at 221 Baker Street now", "I live at [ADDRESS] now"),
        ("Born on 03.04.1956", "Born on [DATE]"),
        ("Appointment 2026-10-14 at 9", "Appointment [DATE] at 9"),
        ("Termin am 14. Oktober 2026", "Termin am [DATE]"),
        ("since March 3rd, 2026", "since [DATE]"),
        ("My name is Peter Example and I have AF", "My name is [NAME] and I have AF"),
        ("Ich heiße Maria und habe Herzinsuffizienz", "Ich heiße [NAME] und habe Herzinsuffizienz"),
        ("Dr. Mustermann changed my dose", "Dr. [NAME] changed my dose"),
        ("Frau Beispiel hat angerufen", "Frau [NAME] hat angerufen"),
    ],
)
def test_redacts(text, expected):
    assert redact(text).text == expected


@pytest.mark.parametrize(
    "text",
    [
        "BP 128/80 this morning, pulse 72",
        "Blutdruck 135/85, Puls 64, Gewicht 78,2 kg",
        "Weight 78.2 kg, up 2 kg in 3 days",
        "I take 2.5 mg twice a day and walked 10000 steps",
        "Ejection fraction was 35% in 2024",
        "INR 2.4 on Monday",
        "I'm tired and short of breath",
    ],
)
def test_leaves_clinical_text_alone(text):
    assert redact(text).text == text


def test_date_followed_by_a_number_is_not_a_phone_number():
    text = "Seit dem 03.10.2026 2 kg mehr, Blutdruck 145/90."
    assert redact(text).text == "Seit dem [DATE] 2 kg mehr, Blutdruck 145/90."


def test_invalid_iban_checksum_is_not_redacted_as_iban():
    result = redact("Code DE00 1234 5678 9012 3456 78")
    assert all(s.kind != "IBAN" for s in result.spans)


def test_dates_can_be_kept():
    assert redact("Seen on 14.10.2026", dates=False).text == "Seen on 14.10.2026"


def test_custom_placeholder():
    assert redact("mail me at a@b.test", placeholder="<{kind}>").text == "mail me at <EMAIL>"


def test_spans_point_at_original_text():
    text = "Hi, ich heiße Lena, Handy 0151 23456789"
    result = redact(text)
    assert [(s.kind, text[s.start:s.end]) for s in result.spans] == [
        ("NAME", "Lena"),
        ("PHONE", "0151 23456789"),
    ]
