import re

from pymax.static.enum import FormattingType
from pymax.types import Element


class Formatting:
    MARKUP_BLOCK_PATTERN = re.compile(
        (
            r"\*\*(?P<strong>.+?)\*\*|"
            r"\*(?P<italic>.+?)\*|"
            r"__(?P<underline>.+?)__|"
            r"~~(?P<strike>.+?)~~"
        ),
        re.DOTALL,
    )

    @staticmethod
    def get_elements_from_markdown(text: str) -> tuple[list[Element], str]:
        """
        Extracts formatting spans from Markdown-style markup and returns structured elements alongside the plain text with markup removed.
        
        Parses the input for bold (`**text**`), italic (`*text*`), underline (`__text__`), and strikethrough (`~~text~~`) blocks, producing Element records that indicate the formatting type, start offset in the cleaned text, and span length. When a formatted block is immediately followed by a newline or ends the string, the element's length includes that single trailing newline and the newline is preserved in the cleaned text.
        
        Parameters:
            text (str): Input text potentially containing Markdown-style formatting.
        
        Returns:
            tuple[list[Element], str]: A pair where the first item is a list of Elements describing formatted spans in the cleaned text, and the second item is the cleaned text with markup removed (preserving single newlines that followed formatted blocks).
        """
        text = text.strip("\n")
        elements: list[Element] = []
        clean_parts: list[str] = []
        current_pos = 0

        last_end = 0
        for match in Formatting.MARKUP_BLOCK_PATTERN.finditer(text):
            between = text[last_end : match.start()]
            if between:
                clean_parts.append(between)
                current_pos += len(between)

            inner_text = None
            fmt_type = None
            if match.group("strong") is not None:
                inner_text = match.group("strong")
                fmt_type = FormattingType.STRONG
            elif match.group("italic") is not None:
                inner_text = match.group("italic")
                fmt_type = FormattingType.EMPHASIZED
            elif match.group("underline") is not None:
                inner_text = match.group("underline")
                fmt_type = FormattingType.UNDERLINE
            elif match.group("strike") is not None:
                inner_text = match.group("strike")
                fmt_type = FormattingType.STRIKETHROUGH

            if inner_text is not None and fmt_type is not None:
                next_pos = match.end()
                has_newline = (next_pos < len(text) and text[next_pos] == "\n") or (
                    next_pos == len(text)
                )

                length = len(inner_text) + (1 if has_newline else 0)
                elements.append(Element(type=fmt_type, from_=current_pos, length=length))

                clean_parts.append(inner_text)
                if has_newline:
                    clean_parts.append("\n")

                current_pos += length

                if next_pos < len(text) and text[next_pos] == "\n":
                    last_end = match.end() + 1
                else:
                    last_end = match.end()
            else:
                last_end = match.end()

        tail = text[last_end:]
        if tail:
            clean_parts.append(tail)

        clean_text = "".join(clean_parts)
        return elements, clean_text