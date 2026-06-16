import unittest

from app.content.blocks import BlockValidationError, excerpt_from_blocks, normalize_blocks, render_blocks


class ContentBlockTests(unittest.TestCase):
    def test_normalizes_supported_blocks_and_excerpt(self):
        blocks = normalize_blocks([
            {"type": "heading", "level": 2, "text": "标题"},
            {"type": "paragraph", "text": "第一段正文"},
            {"type": "list", "ordered": False, "items": ["甲", "乙"]},
        ])
        self.assertEqual(blocks[0]["level"], 2)
        self.assertIn("第一段正文", excerpt_from_blocks(blocks))

    def test_rejects_unknown_blocks_and_malformed_nesting(self):
        with self.assertRaises(BlockValidationError):
            normalize_blocks([{"type": "iframe", "html": "x"}])
        with self.assertRaises(BlockValidationError):
            normalize_blocks([{"type": "list", "items": [["nested"]]}])

    def test_rejects_dangerous_links_and_invalid_media_ids(self):
        with self.assertRaises(BlockValidationError):
            normalize_blocks([{"type": "external_link", "url": "javascript:alert(1)", "text": "x"}])
        with self.assertRaises(BlockValidationError):
            normalize_blocks([{"type": "image", "media_id": "../../secret"}])

    def test_rejects_oversized_documents(self):
        with self.assertRaises(BlockValidationError):
            normalize_blocks([{"type": "paragraph", "text": "x" * 500_001}])

    def test_render_strips_scripts_events_and_adds_safe_link_rel(self):
        blocks = normalize_blocks([
            {"type": "paragraph", "text": '<img src=x onerror="alert(1)"><script>x</script>正文'},
            {"type": "external_link", "url": "https://example.com/a", "text": "原文"},
        ])
        html = render_blocks(blocks, lambda _: None)
        self.assertNotIn("script", html.lower())
        self.assertNotIn("onerror", html.lower())
        self.assertIn('rel="noopener noreferrer"', html)

    def test_renders_media_from_lookup_only(self):
        media_id = "a" * 32
        blocks = normalize_blocks([{"type": "image", "media_id": media_id, "alt": "封面"}])
        html = render_blocks(blocks, lambda value: {"public_url": "/content/a.webp"} if value == media_id else None)
        self.assertIn('/content/a.webp', html)
        with self.assertRaises(BlockValidationError):
            render_blocks(blocks, lambda _: None)


if __name__ == "__main__":
    unittest.main()
