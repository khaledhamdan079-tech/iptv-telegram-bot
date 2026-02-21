"""In-memory conversation state per user (chat_id)."""

from typing import Any

# chat_id -> state dict
user_states: dict[int, dict[str, Any]] = {}

# State keys:
# - choice: "movie" | "series"
# - movie_results: list of dicts from API (stream_id, name); length <= 10
# - series_results: list of dicts from API (series_id, name); length <= 10
# - series_id: str (for series, after user picks from list)
# - episodes: dict (data.episodes from series info, keys are season numbers as str)
# - step: "movie_choice" | "series_choice" | "season" | "episode"


def get_state(chat_id: int) -> dict[str, Any]:
    return user_states.get(chat_id, {})


def set_state(chat_id: int, **kwargs: Any) -> None:
    if chat_id not in user_states:
        user_states[chat_id] = {}
    user_states[chat_id].update(kwargs)


def clear_state(chat_id: int) -> None:
    user_states.pop(chat_id, None)
