import tempfile
import unittest
from pathlib import Path

from telc_audio.cli import discover_scenarios
from telc_audio.parser import ScenarioError, count_words, parse_pause, parse_scenario


HEADER = """+++
title = "Test"
artist = "Deutsch A1 TELC"
album = "TELC A1 Schreiben"
language = "de-DE"
lyrics_language = "deu"
voice = "de-DE-KatjaNeural"
output = "test"
+++
"""


class ParserTests(unittest.TestCase):
    def test_pause_units(self):
        self.assertEqual(parse_pause("250ms"), 250)
        self.assertEqual(parse_pause("3.5s"), 3500)

    def test_german_word_count(self):
        self.assertEqual(count_words("Ich möchte E-Mail und Grüße."), 5)

    def test_valid_scenario(self):
        words = "Ich habe heute Zeit und schreibe dir eine kurze Nachricht mit allen wichtigen Informationen für unser gemeinsames Treffen am Samstag bei mir zu Hause mit Kaffee Kuchen Musik und netten Freunden am Abend um achtzehn Uhr"
        body = HEADER + f"""
:::audio id="answer" kind="answer"
Liebe Anna. {{count=false}}
{words}. {{point="1,2,3"}}
Viele Grüße. {{count=false}}
Dein Vorname. {{count=false}}
:::
:::audio id="repeat" kind="repeat" rate="-15%"
Bitte wiederholen.
:::
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "topic.md"
            path.write_text(body, encoding="utf-8")
            topic = parse_scenario(path)
            self.assertEqual(topic.output_name, "test")

    def test_missing_point_is_rejected(self):
        words = "Ich habe heute Zeit und schreibe dir eine kurze Nachricht mit allen wichtigen Informationen für unser gemeinsames Treffen am Samstag bei mir zu Hause mit Kaffee Kuchen Musik und netten Freunden am Abend um achtzehn Uhr"
        body = HEADER + f"""
:::audio id="answer" kind="answer"
{words}. {{point="1,2"}}
:::
:::audio id="repeat" kind="repeat"
Bitte wiederholen.
:::
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "topic.md"
            path.write_text(body, encoding="utf-8")
            with self.assertRaises(ScenarioError):
                parse_scenario(path)

    def test_discovery_ignores_regular_markdown(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("# Documentation\n", encoding="utf-8")
            scenario = root / "topic.md"
            scenario.write_text("+++\ntitle = 'Topic'\n+++\n", encoding="utf-8")
            self.assertEqual(discover_scenarios(root), [scenario])


if __name__ == "__main__":
    unittest.main()
