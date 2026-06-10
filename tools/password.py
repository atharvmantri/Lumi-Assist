"""Password generator — create secure random passwords."""
from __future__ import annotations

import secrets
import string

from tools import tool


from tools.security import generate_password


@tool(
    name="password_strength",
    description="Estimate the strength of a password. Returns a rating and suggestions.",
    parameters={
        "type": "object",
        "properties": {
            "password": {
                "type": "string",
                "description": "The password to check",
            },
        },
        "required": ["password"],
    },
)
def password_strength(password: str) -> str:
    score = 0
    feedback = []

    length = len(password)
    if length >= 8:
        score += 1
    if length >= 12:
        score += 1
    if length >= 16:
        score += 1

    if any(c.islower() for c in password):
        score += 1
    if any(c.isupper() for c in password):
        score += 1
    if any(c.isdigit() for c in password):
        score += 1
    if any(c in "!@#$%^&*()-_=+[]{}|;:,.<>?" for c in password):
        score += 1

    # Penalize common patterns
    common_words = ["password", "123456", "qwerty", "abc123", "letmein", "admin"]
    for w in common_words:
        if w in password.lower():
            score -= 1
            feedback.append(f"Avoid common word: '{w}'")

    if len(set(password)) < length * 0.5:
        feedback.append("Low character diversity — use more unique characters")

    ratings = ["Very Weak", "Weak", "Fair", "Good", "Strong", "Very Strong", "Excellent"]
    rating = ratings[min(score, len(ratings) - 1)]

    bits = length * len(set(password)).bit_length() if length > 0 else 0
    entropy_bits = length * 4  # rough estimate

    result = f"Password strength: {rating} (score: {score}/7)\n"
    result += f"  Length: {length} chars\n"
    result += f"  Estimated entropy: ~{entropy_bits} bits\n"

    if feedback:
        result += "  Suggestions:\n"
        for f in feedback:
            result += f"    - {f}\n"

    if score >= 5:
        result += "  This password is strong enough for most uses."

    return result
