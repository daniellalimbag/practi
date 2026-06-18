def normalize_extracted_text(text: str) -> str:
    """
    Fix slide-exported PDFs where glyphs are spaced like 'P r a c t i c u m'.
    Collapses lines that are mostly single-character tokens.
    """
    lines: list[str] = []
    for line in text.splitlines():
        tokens = line.split()
        if not tokens:
            lines.append("")
            continue
        single_char = sum(1 for t in tokens if len(t) == 1)
        if len(tokens) >= 4 and single_char / len(tokens) > 0.5:
            lines.append("".join(tokens))
        else:
            lines.append(line)
    return "\n".join(lines)
