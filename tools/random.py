"""Random picks and decision helpers."""
from __future__ import annotations

import random

from tools import tool


@tool(
    name="pick_random",
    description="Pick a random item from a list. Use when you can't decide between options.",
    parameters={
        "type": "object",
        "properties": {
            "items": {
                "type": "string",
                "description": "Comma-separated list of items to pick from",
            },
            "count": {
                "type": "integer",
                "description": "How many items to pick (default 1)",
            },
        },
        "required": ["items"],
    },
)
def pick_random(items: str, count: int = 1) -> str:
    item_list = [i.strip() for i in items.split(",") if i.strip()]
    if not item_list:
        return "error: no items provided"

    count = min(count, len(item_list))
    picks = random.sample(item_list, count)

    if count == 1:
        return f"Random pick: {picks[0]}"
    return f"Random picks ({count}):\n" + "\n".join(f"  {i+1}. {p}" for i, p in enumerate(picks))


@tool(
    name="roll_dice",
    description="Roll dice. Specify number of dice and sides (e.g. '2d6', '1d20').",
    parameters={
        "type": "object",
        "properties": {
            "dice": {
                "type": "string",
                "description": "Dice notation: 'NdS' where N=number of dice, S=sides (e.g. '2d6', '1d20', '3d8')",
            },
        },
        "required": ["dice"],
    },
)
def roll_dice(dice: str) -> str:
    try:
        parts = dice.lower().split("d")
        num_dice = int(parts[0]) if parts[0] else 1
        sides = int(parts[1]) if len(parts) > 1 and parts[1] else 6

        if num_dice < 1 or num_dice > 100:
            return "error: number of dice must be 1-100"
        if sides < 2 or sides > 1000:
            return "error: sides must be 2-1000"

        rolls = [random.randint(1, sides) for _ in range(num_dice)]
        total = sum(rolls)

        if num_dice == 1:
            return f"🎲 {dice} = {rolls[0]}"
        return f"🎲 {dice} = {rolls} (total: {total})"
    except (ValueError, IndexError):
        return "error: use dice notation like '2d6', '1d20', '3d8'"


@tool(
    name="flip_coin",
    description="Flip a coin.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def flip_coin() -> str:
    return f"🪙 {random.choice(['Heads', 'Tails'])}"


@tool(
    name="shuffle",
    description="Shuffle a list of items randomly.",
    parameters={
        "type": "object",
        "properties": {
            "items": {
                "type": "string",
                "description": "Comma-separated list of items to shuffle",
            },
        },
        "required": ["items"],
    },
)
def shuffle(items: str) -> str:
    item_list = [i.strip() for i in items.split(",") if i.strip()]
    if not item_list:
        return "error: no items provided"

    random.shuffle(item_list)
    lines = ["Shuffled:"]
    for i, item in enumerate(item_list, 1):
        lines.append(f"  {i}. {item}")
    return "\n".join(lines)
