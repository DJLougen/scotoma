# Example notes for trying Scotoma

All fictional. Open one, copy everything, and paste it into the app's left pane (or copy it and press ⌘⌥S).

- 01–20: notes from the clinical **dev** set, written by DiffusionGemma with planted fake identifiers. Never the sealed test sets.
- 17–20: the same notes with identifier formats our model never trained on.
- 21–24: hand-written hard cases.

| file | style | planted identifiers | notes |
|---|---|---|---|
| 01_chat.txt | chat | 11 | familiar formats |
| 02_chat.txt | chat | 5 | familiar formats |
| 03_dictated.txt | dictated | 11 | familiar formats |
| 04_dictated.txt | dictated | 8 | familiar formats |
| 05_email.txt | email | 6 | familiar formats |
| 06_email.txt | email | 14 | familiar formats |
| 07_form.txt | form | 7 | familiar formats |
| 08_form.txt | form | 9 | familiar formats |
| 09_letter.txt | letter | 10 | familiar formats |
| 10_letter.txt | letter | 13 | familiar formats |
| 11_narrative.txt | narrative | 6 | familiar formats |
| 12_narrative.txt | narrative | 9 | familiar formats |
| 13_notes.txt | notes | 7 | familiar formats |
| 14_notes.txt | notes | 11 | familiar formats |
| 15_ocr.txt | ocr | 9 | familiar formats |
| 16_ocr.txt | ocr | 8 | familiar formats |
| 17_narrative_unusual_formats.txt | narrative | 9 | test-only identifier formats |
| 18_email_unusual_formats.txt | email | 6 | test-only identifier formats |
| 19_notes_unusual_formats.txt | notes | 7 | test-only identifier formats |
| 20_dictated_unusual_formats.txt | dictated | 11 | test-only identifier formats |
| 21_hard_caps_and_bare_names.txt | header + chart note | ~12 | ALL-CAPS `SURNAME, GIVEN`, bare surname, common-word name (June), eponyms that must stay (Graves, Bell's) |
| 22_hard_dictated.txt | speech-to-text | ~10 | everything spelled out, no punctuation |
| 23_hard_ocr_scan.txt | scanned form | ~12 | OCR errors (0/O, l/I) inside identifiers |
| 24_no_identifiers.txt | assessment | 0 | should come back untouched: eponyms, scores, doses, vitals |

Known rough edges these show (as of v1):

- 24: `Babinski sign` gets redacted as a name (false positive).
- 22: some spelled-out phone digits are tagged as ACCOUNT rather than PHONE. Still redacted, just the wrong label.
- 23: the hospital name in the OCR'd header is redacted piecemeal, and the attending's name swallows the line break into `Dx:`.
