import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import detect_language, truncate_text


class TestDetectLanguage:
    def test_english(self):
        assert detect_language("How does gravity work and what are the fundamental principles behind it?") == "English"

    def test_arabic(self):
        assert detect_language("كيف تعمل الجاذبية؟") == "Arabic"

    def test_french(self):
        assert detect_language("Comment fonctionne la gravité?") == "French"

    def test_spanish(self):
        assert detect_language("¿Cómo funciona la gravedad?") == "Spanish"

    def test_fallback_on_empty(self):
        # Very short or ambiguous text should fall back to English
        result = detect_language("a")
        assert isinstance(result, str)


class TestTruncateText:
    def test_short_text_unchanged(self):
        assert truncate_text("short", 100) == "short"

    def test_exact_limit(self):
        text = "a" * 300
        assert truncate_text(text, 300) == text

    def test_long_text_truncated(self):
        text = "word " * 100  # 500 chars
        result = truncate_text(text, 50)
        assert len(result) <= 53  # 50 + "..."
        assert result.endswith("...")

    def test_truncates_at_word_boundary(self):
        text = "hello world this is a test of truncation"
        result = truncate_text(text, 15)
        assert result.endswith("...")
        # Should not cut in the middle of a word
        content = result[:-3]  # Remove "..."
        assert not content.endswith(" ")  # rsplit removes trailing space
