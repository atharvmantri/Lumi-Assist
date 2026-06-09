"""Password generator — create secure random passwords."""
from __future__ import annotations

import secrets
import string

from tools import tool


@tool(
    name="generate_password",
    description="Generate a secure random password with customizable length and character types.",
    parameters={
        "type": "object",
        "properties": {
            "length": {
                "type": "integer",
                "description": "Password length (default 16, max 128)",
            },
            "uppercase": {
                "type": "boolean",
                "description": "Include uppercase letters (default true)",
            },
            "lowercase": {
                "type": "boolean",
                "description": "Include lowercase letters (default true)",
            },
            "digits": {
                "type": "boolean",
                "description": "Include digits (default true)",
            },
            "symbols": {
                "type": "boolean",
                "description": "Include symbols (default true)",
            },
        },
        "required": [],
    },
)
def generate_password(length: int = 16, uppercase: bool = True, lowercase: bool = True, digits: bool = True, symbols: bool = True) -> str:
    length = max(4, min(length, 128))

    charset = ""
    if uppercase:
        charset += string.ascii_uppercase
    if lowercase:
        charset += string.ascii_lowercase
    if digits:
        charset += string.digits
    if symbols:
        charset += "!@#$%^&*()-_=+[]{}|;:,.<>?"

    if not charset:
        return "error: at least one character type must be enabled"

    password = "".join(secrets.choice(charset) for _ in range(length))

    # Ensure at least one of each enabled type
    has_upper = any(c in string.ascii_uppercase for c in password)
    has_lower = any(c in string.ascii_lowercase for c in password)
    has_digit = any(c in string.digits for c in password)
    has_symbol = any(c in "!@#$%^&*()-_=+[]{}|;:,.<>?" for c in password)

    if uppercase and not has_upper or lowercase and not has_lower or digits and not has_digit or symbols and not has_symbol:
        # Regenerate until all types present (usually works first try)
        for _ in range(100):
            password = "".join(secrets.choice(charset) for _ in range(length))
            if all([
                not uppercase or any(c in string.ascii_uppercase for c in password),
                not lowercase or any(c in string.ascii_lowercase for c in password),
                not digits or any(c in string.digits for c in password),
                not symbols or any(c in "!@#$%^&*()-_=+[]{}|;:,.<>?" for c in password),
            ]):
                break

    return f"Generated password ({length} chars): {password}"


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
