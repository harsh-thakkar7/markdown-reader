"""Tests for Markdown-to-HTML rendering."""

import unittest

from backend.render_helpers import fix_image_paths
from backend.renderer import render_markdown


class TestRenderMarkdown(unittest.TestCase):
    """Exported links should remain clickable and open in a new tab."""

    def test_links_open_in_new_tab(self):
        html = render_markdown("[Project documentation](https://example.com/docs)")

        self.assertIn("<a ", html)
        self.assertIn('href="https://example.com/docs"', html)
        self.assertIn('target="_blank"', html)
        self.assertIn('rel="noopener"', html)

    def test_bare_urls_are_clickable(self):
        html = render_markdown("Read https://example.com/docs.")

        self.assertIn(
            '<a href="https://example.com/docs" target="_blank" rel="noopener">https://example.com/docs</a>.',
            html,
        )

    def test_bare_urls_do_not_wrap_existing_links_or_code(self):
        html = render_markdown(
            "[Docs](https://example.com/docs)\n\n"
            "`https://example.com/code`\n\n"
            "```text\nhttps://example.com/fence\n```"
        )

        self.assertEqual(html.count('href="https://example.com/docs"'), 1)
        self.assertNotIn('href="https://example.com/code"', html)
        self.assertNotIn('href="https://example.com/fence"', html)

    def test_code_block_escapes_html_special_characters(self):
        html = render_markdown("```\nif a < b and c > d and x & y:\n```")

        self.assertIn("<code>if a &lt; b and c &gt; d and x &amp; y:\n</code>", html)

    def test_dollar_signs_inside_code_are_not_treated_as_math(self):
        html = render_markdown(
            "```\nawk '{print $1, $2}'\n```\n\nUse `$1 and $2` here."
        )

        self.assertIn("awk &#x27;{print $1, $2}&#x27;", html)
        self.assertIn("<code>$1 and $2</code>", html)
        self.assertNotIn('class="math-inline"', html)

    def test_math_outside_code_is_still_protected(self):
        html = render_markdown(
            "A line before.\n\n`keep $1`\n\nInline $e^{i\\pi} + 1 = 0$ good"
        )

        self.assertIn("math-inline", html)
        self.assertIn("<code>keep $1</code>", html)

    def test_code_placeholder_names_in_document_are_not_mangled(self):
        html = render_markdown("This is CODEPLACEHOLDER0X text and `real code $x`")

        self.assertIn("<code>real code $x</code>", html)
        self.assertIn("CODEPLACEHOLDER0X", html)
        self.assertNotIn(r"\\(real code", html)

    def test_math_placeholder_names_in_document_are_not_mangled(self):
        html = render_markdown(
            "A doc mentioning MATHPLACEHOLDER0X literally. Math $$5+5$$ here."
        )

        self.assertIn("MATHPLACEHOLDER0X", html)
        self.assertIn("math-display", html)

    def test_no_placeholder_tokens_leak_into_output(self):
        import re

        html = render_markdown("Use `cost is $5` and\n\n```\ntotal $$10$$\n```")

        token = re.compile(r"[A-Z]+PLACEHOLDER[0-9a-f]{12}[0-9]X")
        self.assertIsNone(token.search(html))

    def test_currency_amounts_are_not_treated_as_math(self):
        html = render_markdown(
            "The upgrade costs $5.00 and the plan is $10 per month.\n\n"
            "Save $20 today — regular price is $25.\n\n"
            "$100 total, or $3.50 each."
        )
        body = html.split("<body>")[1].split("</body>")[0]

        self.assertNotIn('class="math-inline"', body)
        self.assertIn("costs $5.00 and the plan is $10 per month.", body)
        self.assertIn("Save $20 today — regular price is $25.", body)
        self.assertIn("$100 total, or $3.50 each.", body)

    def test_dollar_followed_by_digit_does_not_open_math(self):
        html = render_markdown("Balance: $5 and $10 are different.")
        body = html.split("<body>")[1].split("</body>")[0]

        self.assertNotIn('class="math-inline"', body)
        self.assertIn("Balance: $5 and $10 are different.", body)

    def test_escaped_dollars_are_not_math_delimiters(self):
        html = render_markdown(r"The symbol \$ is a literal dollar, not math.")
        body = html.split("<body>")[1].split("</body>")[0]

        self.assertNotIn('class="math-inline"', body)
        # markdown2 keeps the backslash escape as-is; the important part is
        # that the escaped dollar is not converted into a math span.
        self.assertNotIn(r"\(", body)
        self.assertIn("literal dollar", body)

    def test_inline_math_still_renders_next_to_currency(self):
        html = render_markdown("Total $50 with $x^2 + y^2 = z^2$ geometry and more.")
        body = html.split("<body>")[1].split("</body>")[0]

        self.assertIn('class="math-inline"', body)
        self.assertIn("Total $50 with", body)
        self.assertNotIn("$50 with \\(", body)

    def test_digit_leading_math_and_currency_remain_separate(self):
        for expression in ("2x + 1", "5", "2x", "x^2 + y^2 = z^2"):
            with self.subTest(expression=expression):
                html = render_markdown(f"Total $50 with ${expression}$ geometry.")
                body = html.split("<body>")[1].split("</body>")[0]
                self.assertIn("Total $50 with", body)
                self.assertEqual(body.count('class="math-inline"'), 1)
                self.assertIn(
                    '<span class="math-inline">\\(' + expression + r"\)</span>",
                    body,
                )

    def test_math_requires_non_whitespace_at_inner_boundaries(self):
        for source in ("$ b $", "$a $", "$ a$", "$a $b$"):
            with self.subTest(source=source):
                html = render_markdown(source)
                if source == "$a $b$":
                    self.assertIn('<span class="math-inline">' + r"\(b\)</span>", html)
                else:
                    self.assertNotIn('class="math-inline"', html)

    def test_paired_escaped_dollars_are_literal(self):
        for source in (r"\$x\$", r"$x\$", r"\$5 and \$10"):
            with self.subTest(source=source):
                html = render_markdown(source)
                self.assertNotIn('class="math-inline"', html)

    def test_bare_urls_keep_query_strings_with_ampersands(self):
        html = render_markdown("Go to https://example.com/?a=1&b=2 now")

        self.assertIn(
            '<a href="https://example.com/?a=1&amp;b=2" target="_blank" '
            'rel="noopener">https://example.com/?a=1&amp;b=2</a>',
            html,
        )

    def test_ampersand_in_plain_text_is_not_rejoined_into_url(self):
        html = render_markdown("Tom & Jerry https://example.com/a")

        self.assertEqual(html.count("&amp;Jerry"), 0)
        self.assertIn("Tom &amp; Jerry", html)

    def test_bare_url_with_balanced_parentheses_is_fully_linked(self):
        html = render_markdown(
            "See http://en.wikipedia.org/wiki/Bracket_(disambiguation)."
        )

        self.assertIn(
            '<a href="http://en.wikipedia.org/wiki/Bracket_(disambiguation)" '
            'target="_blank" rel="noopener">'
            "http://en.wikipedia.org/wiki/Bracket_(disambiguation)</a>.",
            html,
        )

    def test_bare_url_with_stray_closing_bracket_is_trimmed(self):
        html = render_markdown("Jump to http://example.com/done) now.")

        self.assertIn(
            '<a href="http://example.com/done" target="_blank" rel="noopener">'
            "http://example.com/done</a>) now.",
            html,
        )

    def test_bare_url_in_quotes_leaves_quotes_outside_the_link(self):
        html = render_markdown('Read "https://example.com/foo" for details.')

        self.assertIn(
            '<a href="https://example.com/foo" target="_blank" rel="noopener">'
            "https://example.com/foo</a>",
            html,
        )
        self.assertNotIn('href="https://example.com/foo&quot;"', html)
        self.assertIn("</a>&quot; for details.", html)


class TestImagePathsSkipCodeRegions(unittest.TestCase):
    """Relative image resolution must not rewrite image syntax shown as code.

    ``fix_image_paths`` runs before any code masking, so a Markdown document
    that *demonstrates* image syntax had its own examples rewritten to absolute
    ``file://`` URLs in the rendered preview.
    """

    BASE = "/Users/me/docs"

    def test_image_inside_a_fenced_block_is_left_alone(self):
        html = render_markdown(
            "```markdown\n![diagram](diagram.png)\n```",
            base_dir=self.BASE,
        )
        self.assertIn("diagram.png", html)
        self.assertNotIn(f"file://{self.BASE}/diagram.png", html)

    def test_image_inside_an_inline_code_span_is_left_alone(self):
        html = render_markdown("Use `![alt](shot.png)` to embed.", base_dir=self.BASE)
        self.assertIn("shot.png", html)
        self.assertNotIn(f"file://{self.BASE}/shot.png", html)

    def test_real_image_beside_a_code_sample_is_still_resolved(self):
        html = render_markdown(
            "```markdown\n![diagram](diagram.png)\n```\n\n![chart](chart.png)\n",
            base_dir=self.BASE,
        )
        self.assertIn(f'<img src="file://{self.BASE}/chart.png"', html)
        self.assertNotIn(f"file://{self.BASE}/diagram.png", html)

    def test_tilde_fence_is_treated_as_code(self):
        text = "~~~markdown\n![diagram](diagram.png)\n~~~\n"
        self.assertEqual(fix_image_paths(text, self.BASE), text)

    def test_two_backtick_span_is_treated_as_code(self):
        text = "a ``![d](d.png)`` b"
        self.assertEqual(fix_image_paths(text, self.BASE), text)

    def test_fenced_block_at_end_of_file_without_newline(self):
        text = "intro\n\n```markdown\n![diagram](diagram.png)\n```"
        self.assertEqual(fix_image_paths(text, self.BASE), text)

    def test_ordinary_prose_images_are_unchanged(self):
        text = "![chart](chart.png) and ![abs](/x.png) and ![web](https://e.com/i.png)"
        self.assertEqual(
            fix_image_paths(text, self.BASE),
            f"![chart](file://{self.BASE}/chart.png) and ![abs](/x.png) "
            "and ![web](https://e.com/i.png)",
        )

    def test_no_placeholder_token_leaks_from_the_masking(self):
        html = render_markdown("`![a](b.png)` and ![c](c.png)", base_dir=self.BASE)
        self.assertNotIn("PLACEHOLDER", html)
        self.assertIn("b.png", html)
        self.assertIn(f'<img src="file://{self.BASE}/c.png"', html)
