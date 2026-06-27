import tempfile
import unittest
from pathlib import Path

from mutagen.id3 import ID3

from telc_audio.generator import add_apple_music_id3_tags, topic_track_number, transcript_text
from telc_audio.parser import parse_scenario


HEADER = """+++
title = "Aufgabe 01: Geburtstag"
artist = "Deutsch A1 TELC"
album = "TELC A1 Schreiben"
language = "de-DE"
lyrics_language = "deu"
voice = "de-DE-KatjaNeural"
output = "01_Geburtstag"
+++
"""


class GeneratorTests(unittest.TestCase):
    def test_apple_music_metadata_defaults(self):
        body = HEADER + """
:::audio id="answer" kind="answer"
Liebe Anna. {count=false}
Ich habe heute Zeit und schreibe dir eine kurze Nachricht mit allen wichtigen Informationen für unser gemeinsames Treffen am Samstag bei mir zu Hause mit Kaffee Kuchen Musik und netten Freunden am Abend um achtzehn Uhr. {point="1,2,3"}
Viele Grüße. {count=false}
Dein Vorname. {count=false}
:::

:::audio id="repeat" kind="repeat" rate="-15%"
Bitte wiederholen.
:::
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "topic.md"
            path.write_text(body, encoding="utf-8")
            topic = parse_scenario(path)

        tags = ID3()
        add_apple_music_id3_tags(tags, topic)

        self.assertEqual(topic_track_number(topic), 1)
        self.assertEqual(str(tags["TPE2"]), "Deutsch A1 TELC")
        self.assertEqual(str(tags["TCOM"]), "Deutsch A1 TELC")
        self.assertEqual(str(tags["TIT1"]), "Deutsch A1 TELC / TELC A1 Schreiben")
        self.assertEqual(str(tags["TCON"]), "Education")
        self.assertEqual(str(tags["TDRC"]), "2026")
        self.assertEqual(str(tags["TRCK"]), "1/20")
        self.assertEqual(str(tags["TPOS"]), "1/1")
        self.assertEqual(str(tags["TCMP"]), "0")
        self.assertEqual(
            tags.getall("COMM")[0].text[0],
            "TELC A1 Schreiben: Aufgabe, Musterantwort und langsame Wiederholung.",
        )

    def test_transcript_uses_exam_form(self):
        body = HEADER + """
:::audio id="task" kind="task"
Erster Teil.
Die Aufgabe.
Aufgabe eins: Geburtstag.
Sie haben am Samstag Geburtstag.
Schreiben Sie eine E-Mail an Ihren Freund oder Ihre Freundin.
Schreiben Sie.
Erstens: Wann ist die Party?
Zweitens: Wo ist die Party?
Drittens: Was machen Sie auf der Party?
:::

:::audio id="answer" kind="answer"
Liebe Anna. {count=false}
Ich habe heute Zeit und schreibe dir eine kurze Nachricht mit allen wichtigen Informationen für unser gemeinsames Treffen am Samstag bei mir zu Hause mit Kaffee Kuchen Musik und netten Freunden am Abend um achtzehn Uhr. {point="1,2,3"}
Viele Grüße. {count=false}
Dein Vorname. {count=false}
:::

:::audio id="repeat" kind="repeat" rate="-15%"
Bitte wiederholen.
:::
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "topic.md"
            path.write_text(body, encoding="utf-8")
            topic = parse_scenario(path)

        self.assertEqual(
            transcript_text(topic),
            "Aufgabe eins: Geburtstag.\n"
            "Sie haben am Samstag Geburtstag.\n"
            "Schreiben Sie eine E-Mail an Ihren Freund oder Ihre Freundin.\n"
            "\n"
            "1. Wann ist die Party?\n"
            "2. Wo ist die Party?\n"
            "3. Was machen Sie auf der Party?\n"
            "\n"
            "Liebe Anna.\n"
            "Ich habe heute Zeit und schreibe dir eine kurze Nachricht mit allen wichtigen Informationen für unser gemeinsames Treffen am Samstag bei mir zu Hause mit Kaffee Kuchen Musik und netten Freunden am Abend um achtzehn Uhr.\n"
            "Viele Grüße.\n"
            "[Dein Vorname].\n",
        )


if __name__ == "__main__":
    unittest.main()
