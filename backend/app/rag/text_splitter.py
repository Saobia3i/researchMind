def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> list[str]:
    """
    Splits text into smaller, overlapping chunks.
    Attempts to respect paragraph and sentence boundaries, falling back to word-level splits.
    """
    if not text:
        return []

    paragraphs = text.replace("\r\n", "\n").split("\n\n")
    chunks = []
    current_chunk = ""

    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue

        # If adding the next paragraph keeps us under the size limit
        if not current_chunk:
            current_chunk = paragraph
        elif len(current_chunk) + len(paragraph) + 2 <= chunk_size:
            current_chunk += "\n\n" + paragraph
        else:
            # Paragraph makes the chunk too large. Save current and handle the paragraph
            chunks.append(current_chunk)

            # Determine overlap text from the end of the current chunk
            overlap_text = current_chunk[-chunk_overlap:] if len(current_chunk) > chunk_overlap else current_chunk
            space_idx = overlap_text.find(" ")
            if space_idx != -1:
                overlap_text = overlap_text[space_idx:].strip()
            else:
                overlap_text = overlap_text.strip()

            # Check if paragraph itself is larger than chunk_size
            if len(paragraph) > chunk_size:
                # Need to split the paragraph by words
                words = paragraph.split(" ")
                temp_chunk = overlap_text
                for word in words:
                    if not temp_chunk:
                        temp_chunk = word
                    elif len(temp_chunk) + len(word) + 1 <= chunk_size:
                        temp_chunk += " " + word
                    else:
                        chunks.append(temp_chunk)
                        # Create overlap for next word-level chunk
                        overlap_words = temp_chunk.split(" ")
                        sub_overlap = ""
                        for w in reversed(overlap_words):
                            if len(sub_overlap) + len(w) + 1 <= chunk_overlap:
                                sub_overlap = w + " " + sub_overlap
                            else:
                                break
                        temp_chunk = (sub_overlap.strip() + " " + word).strip()
                current_chunk = temp_chunk
            else:
                current_chunk = (overlap_text + "\n\n" + paragraph).strip()

    if current_chunk:
        chunks.append(current_chunk)

    return [c for c in chunks if c.strip()]
