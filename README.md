# health-text-redact

**Remove direct identifiers from English and German health conversations before analysis.**

Patients share a lot in chat: their phone number for a callback, their insurance number, their address for a prescription, their doctor's name. Before conversation text is used for research, quality review or model evaluation, these identifiers need to go. This library is the first, transparent pass. It replaces identifiers with placeholders and leaves the clinical content intact.

Maintained by [ChatDok](https://chatdok.com).

```python
from health_text_redact import redact

result = redact(
    "Hallo, ich heiße Maria. Seit dem 03.10.2026 2 kg mehr, Blutdruck 145/90. "
    "Bitte rufen Sie mich an: 0171 2345678"
)
print(result.text)
# Hallo, ich heiße [NAME]. Seit dem [DATE] 2 kg mehr, Blutdruck 145/90. Bitte rufen Sie mich an: [PHONE]
```

`result.spans` lists each redaction with its type and character offsets in the original text.

## What it catches

| Type | Examples |
|---|---|
| `EMAIL` | `anna@example.org` |
| `URL` | `https://…`, `www.…` |
| `PHONE` | `0171 2345678`, `+49 30 1234567`, `030/12345678`, `+44 (0)20 7946 0000` |
| `IBAN` | IBANs that pass the ISO 13616 checksum |
| `INSURANCE_NUMBER` | German health insurance numbers (one letter plus nine digits) |
| `ADDRESS` | `Hauptstraße 12, 10115 Berlin`, `221 Baker Street` |
| `DATE` | `03.04.1956`, `2026-10-14`, `14. Oktober 2026`, `March 3rd, 2026`. Turn off with `dates=False` |
| `NAME` | Names after a cue: "my name is…", "ich heiße…", "Dr.", "Frau", "Mr" and similar |

It is designed **not** to touch clinical numbers: blood pressure (`128/80`), weights (`78.2 kg`), doses (`2.5 mg`), lab values and step counts.

## What it does not do

**Redaction is not anonymisation.** Removing direct identifiers is one step in protecting privacy. It is not enough on its own to make health data anonymous under the GDPR. In particular:

- **Free-text names without a cue are not detected.** "Peter came with me to the clinic" keeps "Peter". Add a named-entity recognition model for names.
- **Indirect identifiers remain.** A rare condition, a small town, an occupation or an unusual sequence of events can identify someone. These need a disclosure-risk assessment, not pattern matching.
- **Pattern-based means imperfect.** Unusual formats will be missed, and some non-identifiers will be over-redacted. Measure recall on a hand-labelled sample of your own data before relying on it.

Use this as one layer, together with access controls, data minimisation and expert review, in line with your data protection obligations.

## Install

```bash
pip install git+https://github.com/chatdok-health/health-text-redact
```

No dependencies beyond the Python 3.10+ standard library.

## Options

```python
redact(text, dates=False)                 # keep calendar dates
redact(text, placeholder="<{kind}>")      # change the placeholder format
```

## Contributing

Formats from other countries are welcome (phone numbers, insurance and national ID formats), each with tests. Use invented values only, never real identifiers. Run the tests with `python -m pytest`.

## License

[Apache 2.0](LICENSE). © 2026 ChatDok GmbH.
