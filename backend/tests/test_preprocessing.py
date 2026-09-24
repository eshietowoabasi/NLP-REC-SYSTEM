import pytest

from app.services.preprocessing import clean_block, clean_blocks, normalize_unicode, preprocess
from app.services.preprocessing.normalize import drop_contents_listing, is_toc_line


class TestNormalize:
    def test_unicode_ligatures_quotes_dashes(self):
        assert normalize_unicode("ﬁrewall “AI” – it’s") == 'firewall "AI" - it\'s'

    def test_invisible_characters_removed(self):
        assert normalize_unicode("data­base​﻿") == "database"

    @pytest.mark.parametrize(
        "line",
        ["PREAMBLE\t5", "SECTION 4: MEMBERSHIP ........ 7", "Chapter Two   12", "1.2 Scope \t\t 103"],
    )
    def test_toc_lines_detected(self, line):
        assert is_toc_line(line)

    @pytest.mark.parametrize("line", ["Students must be in 300 level", "Python 3", "Established in 2020"])
    def test_normal_lines_with_numbers_are_not_toc(self, line):
        assert not is_toc_line(line)

    def test_clean_block_removes_noise(self):
        text = "Apply at https://jobs.example.com or hr@example.com  for the  role"
        assert clean_block(text) == "Apply at or for the role"

    def test_clean_block_dehyphenates_and_drops_letterless(self):
        assert clean_block("machine-\nlearning") == "machinelearning"
        assert clean_block("12") == "" and clean_block("- - -") == ""

    def test_toc_line_inside_multiline_block(self):
        assert clean_block("Intro ..... 3\nReal sentence here.") == "Real sentence here."

    def test_contents_listing_without_page_numbers(self):
        blocks = ["Title", "ARRANGEMENT OF SECTIONS", "PREAMBLE", "CHAPTER ONE", "PREAMBLE", "We the students"]
        assert drop_contents_listing(blocks) == ["Title", "PREAMBLE", "We the students"]

    def test_contents_heading_without_listing_is_dropped(self):
        assert drop_contents_listing(["Contents", "Body text", "More"]) == ["Body text", "More"]

    def test_clean_blocks_combines_rules(self):
        blocks = ["Table of Contents", "Intro\t1", "Intro", "Real body text."]
        assert clean_blocks(blocks) == ["Intro", "Real body text."]


class TestPreprocess:
    def test_sentences_and_tokens(self):
        result = preprocess(
            "The engineers are building secure cloud systems. They shall deploy 3 Kubernetes clusters!\n\n"
            "Contact careers@example.com."
        )
        assert result.sentences[:2] == [
            "The engineers are building secure cloud systems.",
            "They shall deploy 3 Kubernetes clusters!",
        ]
        # Lemmatised, lowercased, no stop words / modals / numbers / punctuation / emails.
        assert {"engineer", "build", "secure", "cloud", "system", "deploy", "kubernetes", "cluster"} <= set(result.tokens)
        assert not {"the", "are", "they", "shall", "3", "!", "careers@example.com"} & set(result.tokens)
        assert result.token_count == len(result.tokens)

    def test_accepts_blocks(self):
        result = preprocess(["Data science roles.", "PREAMBLE\t5"])
        assert result.clean_text == "Data science roles."

    def test_long_block_is_chunked(self):
        block = "Python developers build data pipelines. " * 3000  # ~120k chars
        result = preprocess([block])
        assert result.sentence_count >= 3000
        assert result.tokens.count("pipeline") == 3000

    def test_empty(self):
        result = preprocess("")
        assert result.sentences == [] and result.tokens == []
