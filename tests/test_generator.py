import unittest
from pathlib import Path

from telc_audio.generator import cover_mime_type, group_blocks, lrc_timestamp
from telc_audio.model import AudioBlock, Utterance


class GeneratorTests(unittest.TestCase):
    def test_adjacent_compatible_blocks_are_grouped(self):
        utterance = Utterance("Hallo.", 100)
        blocks = [
            AudioBlock("one", "task", "+0%", "voice", [utterance]),
            AudioBlock("two", "answer", "+0%", "voice", [utterance]),
            AudioBlock("three", "repeat", "-15%", "voice", [utterance]),
        ]
        self.assertEqual([len(group) for group in group_blocks(blocks)], [2, 1])

    def test_lrc_timestamp(self):
        self.assertEqual(lrc_timestamp(62_340), "01:02.34")

    def test_cover_mime_type(self):
        self.assertEqual(cover_mime_type(Path("cover.jpg")), "image/jpeg")
        self.assertEqual(cover_mime_type(Path("cover.png")), "image/png")


if __name__ == "__main__":
    unittest.main()
