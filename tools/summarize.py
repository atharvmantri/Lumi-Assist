"""Text summarization tools."""
from __future__ import annotations

import re

from tools import tool


@tool(
    name="summarize_text",
    description="Summarize text by extracting key sentences (extractive summarization).",
    parameters={
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Text to summarize",
            },
            "max_sentences": {
                "type": "integer",
                "description": "Maximum sentences in summary (default 5)",
            },
        },
        "required": ["text"],
    },
)
def summarize_text(text: str, max_sentences: int = 5) -> str:
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return "No sentences found to summarize."

    if len(sentences) <= max_sentences:
        return "Text is already short:\n" + "\n".join(f"  {s}" for s in sentences)

    # Score sentences by word frequency
    words = re.findall(r'\b\w+\b', text.lower())
    word_freq = {}
    stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                  'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                  'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare',
                  'ought', 'used', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by',
                  'from', 'as', 'into', 'through', 'during', 'before', 'after', 'and',
                  'but', 'or', 'nor', 'not', 'so', 'yet', 'both', 'either', 'neither',
                  'each', 'every', 'all', 'any', 'few', 'more', 'most', 'other', 'some',
                  'such', 'no', 'only', 'own', 'same', 'than', 'too', 'very', 'just',
                  'because', 'if', 'when', 'where', 'how', 'what', 'which', 'who', 'whom',
                  'this', 'that', 'these', 'those', 'it', 'its', 'i', 'me', 'my', 'mine',
                  'we', 'us', 'our', 'ours', 'you', 'your', 'yours', 'he', 'him', 'his',
                  'she', 'her', 'hers', 'they', 'them', 'their', 'theirs'}

    for w in words:
        if w not in stop_words and len(w) > 2:
            word_freq[w] = word_freq.get(w, 0) + 1

    # Score each sentence
    scored = []
    for i, s in enumerate(sentences):
        s_words = re.findall(r'\b\w+\b', s.lower())
        score = sum(word_freq.get(w, 0) for w in s_words if w not in stop_words)
        # Bonus for early sentences
        if i < 3:
            score += 2
        scored.append((score, i, s))

    scored.sort(key=lambda x: -x[0])
    top = scored[:max_sentences]
    top.sort(key=lambda x: x[1])  # Restore original order

    summary = "\n".join(f"  {s}" for _, _, s in top)
    original_words = len(text.split())
    summary_words = sum(len(s.split()) for _, _, s in top)
    compression = (1 - summary_words / original_words) * 100

    return (
        f"Summary ({max_sentences} sentences, {compression:.0f}% compression):\n"
        f"\n{summary}"
    )


@tool(
    name="extract_keywords",
    description="Extract the most important keywords/phrases from text.",
    parameters={
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Text to analyze",
            },
            "limit": {
                "type": "integer",
                "description": "Max keywords to return (default 20)",
            },
        },
        "required": ["text"],
    },
)
def extract_keywords(text: str, limit: int = 20) -> str:
    stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                  'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                  'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare',
                  'ought', 'used', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by',
                  'from', 'as', 'into', 'through', 'during', 'before', 'after', 'and',
                  'but', 'or', 'nor', 'not', 'so', 'yet', 'both', 'either', 'neither',
                  'each', 'every', 'all', 'any', 'few', 'more', 'most', 'other', 'some',
                  'such', 'no', 'only', 'own', 'same', 'than', 'too', 'very', 'just',
                  'because', 'if', 'when', 'where', 'how', 'what', 'which', 'who', 'whom',
                  'this', 'that', 'these', 'those', 'it', 'its', 'i', 'me', 'my', 'mine',
                  'we', 'us', 'our', 'ours', 'you', 'your', 'yours', 'he', 'him', 'his',
                  'she', 'her', 'hers', 'they', 'them', 'their', 'theirs'}

    words = re.findall(r'\b\w{3,}\b', text.lower())
    freq = {}
    for w in words:
        if w not in stop_words:
            freq[w] = freq.get(w, 0) + 1

    # Also look for 2-word phrases
    word_list = [w for w in words if w not in stop_words]
    phrases = {}
    for i in range(len(word_list) - 1):
        phrase = f"{word_list[i]} {word_list[i+1]}"
        phrases[phrase] = phrases.get(phrase, 0) + 1

    # Combine
    all_items = list(freq.items()) + [(k, v * 1.5) for k, v in phrases.items() if v > 1]
    all_items.sort(key=lambda x: -x[1])

    lines = [f"Keywords ({min(limit, len(all_items))}):"]
    for word, score in all_items[:limit]:
        lines.append(f"  {word}: {int(score)}")

    return "\n".join(lines)
