import unittest
from pathlib import Path

from api.pipeline.ingest import (
    IngestError,
    build_sentence_index,
    ingest_file,
    ingest_text,
)
from api.tests.helpers import SAMPLE_PAPER, sample_document, temp_dir


class IngestTests(unittest.TestCase):
    def test_sections_and_title(self):
        doc = sample_document()
        headings = [section.heading for section in doc.sections]
        for expected in ("Abstract", "Introduction", "Method", "Experiments", "Conclusion", "References"):
            self.assertIn(expected, headings)
        self.assertEqual(doc.title, "SparseRoute: Adaptive Sparsity for Efficient Neural Machine Translation")
        self.assertEqual(doc.meta["references"], 2)

    def test_sentence_index_does_not_glue_headings_to_sentences(self):
        doc = sample_document()
        sentences = build_sentence_index(doc)
        self.assertGreater(len(sentences), 8)
        for sentence in sentences:
            self.assertFalse(sentence["text"].startswith(("Method ", "Conclusion ", "Abstract ")))
            self.assertIn("page", sentence)
            self.assertIn("section", sentence)
        normalized = [sentence["text"].lower() for sentence in sentences]
        self.assertEqual(len(normalized), len(set(normalized)))

    def test_headingless_text_gets_a_body_section(self):
        doc = ingest_text(
            "A Short Note\n\n"
            "This note describes a method and reports a result. "
            "The method is simple and the result is positive.",
            "note.txt",
        )
        self.assertEqual([section.heading for section in doc.sections], ["Body"])

    def test_empty_text_is_rejected(self):
        with self.assertRaises(IngestError) as context:
            ingest_text("   \n\n ")
        self.assertEqual(context.exception.code, "EMPTY_DOCUMENT")

    def test_unsupported_extension_is_rejected(self):
        with temp_dir() as tmp:
            path = Path(tmp) / "data.csv"
            path.write_text("a,b", encoding="utf-8")
            with self.assertRaises(IngestError) as context:
                ingest_file(path)
            self.assertEqual(context.exception.code, "UNSUPPORTED_FILE")

    def test_text_file_round_trip(self):
        with temp_dir() as tmp:
            path = Path(tmp) / "paper.txt"
            path.write_text(SAMPLE_PAPER, encoding="utf-8")
            doc = ingest_file(path, "paper.txt")
            self.assertEqual(doc.filename, "paper.txt")
            self.assertGreater(len(doc.full_text), 500)
            self.assertGreater(len(doc.sections), 3)


if __name__ == "__main__":
    unittest.main()
