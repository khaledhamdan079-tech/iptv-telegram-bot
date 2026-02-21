"""Telegram bot handlers: /start, text (conversation), /cancel."""

import logging
import httpx
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import ContextTypes

from api import (
    search_movies,
    get_movie_stream_url,
    search_series,
    get_series_info,
    get_episode_stream_url,
)
from state import get_state, set_state, clear_state

logger = logging.getLogger(__name__)

# Network/timeout errors: show a friendly "try again" message
NETWORK_ERRORS = (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout)

CHOICE_KEYBOARD = ReplyKeyboardMarkup(
    [["Movie", "Series"]],
    resize_keyboard=True,
    one_time_keyboard=True,
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    clear_state(update.effective_chat.id)
    await update.message.reply_text(
        "Choose what you want to search for:",
        reply_markup=CHOICE_KEYBOARD,
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    clear_state(update.effective_chat.id)
    await update.message.reply_text(
        "Cancelled. Choose what you want to search for:",
        reply_markup=CHOICE_KEYBOARD,
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    text = (update.message.text or "").strip()
    state = get_state(chat_id)

    # No state or empty: treat as choice if "Movie"/"Series", else show menu
    if not state:
        if text == "Movie":
            set_state(chat_id, choice="movie")
            await update.message.reply_text(
                "Enter the movie name:",
                reply_markup=ReplyKeyboardRemove(),
            )
            return
        if text == "Series":
            set_state(chat_id, choice="series")
            await update.message.reply_text(
                "Enter the series name:",
                reply_markup=ReplyKeyboardRemove(),
            )
            return
        await update.message.reply_text(
            "Please choose Movie or Series:",
            reply_markup=CHOICE_KEYBOARD,
        )
        return

    choice = state.get("choice")
    step = state.get("step")

    # Waiting for movie name
    if choice == "movie" and not step:
        if not text:
            await update.message.reply_text("Please enter a movie name.")
            return
        await _handle_movie_search(update, context, chat_id, text)
        return

    # Waiting for series name
    if choice == "series" and not step:
        if not text:
            await update.message.reply_text("Please enter a series name.")
            return
        await _handle_series_search(update, context, chat_id, text)
        return

    # Movie: waiting for user to pick from list (number 1–N)
    if choice == "movie" and step == "movie_choice":
        await _handle_movie_choice(update, context, chat_id, text)
        return

    # Series: waiting for user to pick from list (number 1–N)
    if choice == "series" and step == "series_choice":
        await _handle_series_choice(update, context, chat_id, text)
        return

    # Series: waiting for season number
    if step == "season":
        await _handle_season_input(update, context, chat_id, text)
        return

    # Series: waiting for episode number
    if step == "episode":
        await _handle_episode_input(update, context, chat_id, text)
        return

    await update.message.reply_text(
        "Please choose Movie or Series:",
        reply_markup=CHOICE_KEYBOARD,
    )


async def _handle_movie_search(
    update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int, query: str
) -> None:
    try:
        result = await search_movies(query)
    except NETWORK_ERRORS as e:
        logger.warning("Movie search connection failed: %s", e)
        await update.message.reply_text(
            "The server could not be reached or took too long to respond. Please try again."
        )
        clear_state(chat_id)
        await update.message.reply_text(
            "Choose what you want to search for:",
            reply_markup=CHOICE_KEYBOARD,
        )
        return
    except Exception as e:
        logger.exception("Movie search failed: %s", e)
        await update.message.reply_text("Something went wrong. Please try again.")
        clear_state(chat_id)
        await update.message.reply_text(
            "Choose what you want to search for:",
            reply_markup=CHOICE_KEYBOARD,
        )
        return

    if not result.get("success") or not result.get("data"):
        await update.message.reply_text("Movie not found.")
        clear_state(chat_id)
        await update.message.reply_text(
            "Choose what you want to search for:",
            reply_markup=CHOICE_KEYBOARD,
        )
        return

    results = result["data"][:10]
    if not results:
        await update.message.reply_text("Movie not found.")
        clear_state(chat_id)
        await update.message.reply_text(
            "Choose what you want to search for:",
            reply_markup=CHOICE_KEYBOARD,
        )
        return

    lines = [f"{i}. {item.get('name', 'Unknown')}" for i, item in enumerate(results, 1)]
    n = len(results)
    msg = f"Found {n} result(s):\n" + "\n".join(lines) + f"\n\nReply with the number (1–{n}) of the movie you want."
    set_state(chat_id, movie_results=results, step="movie_choice")
    await update.message.reply_text(msg)


async def _handle_movie_choice(
    update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str
) -> None:
    state = get_state(chat_id)
    results = state.get("movie_results") or []
    if not results:
        await update.message.reply_text("Something went wrong. Please start over.")
        clear_state(chat_id)
        await _offer_again(update)
        return

    try:
        num = int(text.strip()) if text else None
    except (TypeError, ValueError):
        num = None
    n = len(results)
    if num is None or num < 1 or num > n:
        await update.message.reply_text(f"Please reply with a number between 1 and {n}.")
        return

    item = results[num - 1]
    vod_id = item.get("stream_id")
    if not vod_id:
        await update.message.reply_text("Movie not found.")
        clear_state(chat_id)
        await _offer_again(update)
        return

    try:
        url_result = await get_movie_stream_url(str(vod_id))
    except NETWORK_ERRORS as e:
        logger.warning("Get movie stream URL connection failed: %s", e)
        await update.message.reply_text(
            "The server could not be reached or took too long to respond. Please try again."
        )
        clear_state(chat_id)
        await _offer_again(update)
        return
    except Exception as e:
        logger.exception("Get movie stream URL failed: %s", e)
        await update.message.reply_text("Something went wrong getting the stream. Please try again.")
        clear_state(chat_id)
        await _offer_again(update)
        return

    if not url_result.get("success") or not url_result.get("recommended_url"):
        await update.message.reply_text("Movie not found.")
        clear_state(chat_id)
        await _offer_again(update)
        return

    await update.message.reply_text(f"Watch here:\n{url_result['recommended_url']}")
    clear_state(chat_id)
    await _offer_again(update)


async def _handle_series_search(
    update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int, query: str
) -> None:
    try:
        result = await search_series(query)
    except NETWORK_ERRORS as e:
        logger.warning("Series search connection failed: %s", e)
        await update.message.reply_text(
            "The server could not be reached or took too long to respond. Please try again."
        )
        clear_state(chat_id)
        await update.message.reply_text(
            "Choose what you want to search for:",
            reply_markup=CHOICE_KEYBOARD,
        )
        return
    except Exception as e:
        logger.exception("Series search failed: %s", e)
        await update.message.reply_text("Something went wrong. Please try again.")
        clear_state(chat_id)
        await update.message.reply_text(
            "Choose what you want to search for:",
            reply_markup=CHOICE_KEYBOARD,
        )
        return

    if not result.get("success") or not result.get("data"):
        await update.message.reply_text("Series not found.")
        clear_state(chat_id)
        await _offer_again(update)
        return

    results = result["data"][:10]
    if not results:
        await update.message.reply_text("Series not found.")
        clear_state(chat_id)
        await _offer_again(update)
        return

    lines = [f"{i}. {item.get('name', 'Unknown')}" for i, item in enumerate(results, 1)]
    n = len(results)
    msg = f"Found {n} result(s):\n" + "\n".join(lines) + f"\n\nReply with the number (1–{n}) of the series you want."
    set_state(chat_id, series_results=results, step="series_choice")
    await update.message.reply_text(msg)


async def _handle_series_choice(
    update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str
) -> None:
    state = get_state(chat_id)
    results = state.get("series_results") or []
    if not results:
        await update.message.reply_text("Something went wrong. Please start over.")
        clear_state(chat_id)
        await _offer_again(update)
        return

    try:
        num = int(text.strip()) if text else None
    except (TypeError, ValueError):
        num = None
    n = len(results)
    if num is None or num < 1 or num > n:
        await update.message.reply_text(f"Please reply with a number between 1 and {n}.")
        return

    item = results[num - 1]
    series_id = item.get("series_id")
    if not series_id:
        await update.message.reply_text("Series not found.")
        clear_state(chat_id)
        await _offer_again(update)
        return

    try:
        info_result = await get_series_info(str(series_id))
    except NETWORK_ERRORS as e:
        logger.warning("Series info connection failed: %s", e)
        await update.message.reply_text(
            "The server could not be reached or took too long to respond. Please try again."
        )
        clear_state(chat_id)
        await _offer_again(update)
        return
    except Exception as e:
        logger.exception("Series info failed: %s", e)
        await update.message.reply_text("Something went wrong. Please try again.")
        clear_state(chat_id)
        await _offer_again(update)
        return

    if not info_result.get("success"):
        await update.message.reply_text("Series not found.")
        clear_state(chat_id)
        await _offer_again(update)
        return

    data = info_result.get("data", {})
    episodes = data.get("episodes") or {}
    if not episodes:
        await update.message.reply_text("No seasons/episodes found for this series.")
        clear_state(chat_id)
        await _offer_again(update)
        return

    set_state(chat_id, series_id=str(series_id), episodes=episodes, step="season")
    await update.message.reply_text("Enter the season number (e.g. 1):")


async def _handle_season_input(
    update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str
) -> None:
    state = get_state(chat_id)
    episodes = state.get("episodes") or {}
    season_key = text.strip() if text else ""
    if season_key not in episodes:
        await update.message.reply_text("Season not found.")
        return
    set_state(chat_id, step="episode", selected_season=season_key)
    await update.message.reply_text("Enter the episode number (e.g. 1):")


async def _handle_episode_input(
    update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str
) -> None:
    state = get_state(chat_id)
    episodes = state.get("episodes") or {}
    selected_season = state.get("selected_season", "")
    season_episodes = episodes.get(selected_season) or []

    try:
        episode_num = int(text.strip()) if text else None
    except (TypeError, ValueError):
        episode_num = None

    found = None
    for ep in season_episodes:
        if ep.get("episode_num") == episode_num:
            found = ep
            break
    if not found:
        await update.message.reply_text("Episode not found.")
        return

    series_id = state.get("series_id")
    if not series_id:
        await update.message.reply_text("Something went wrong. Please start over.")
        clear_state(chat_id)
        await _offer_again(update)
        return

    try:
        url_result = await get_episode_stream_url(
            str(series_id),
            str(selected_season),
            str(episode_num),
        )
    except NETWORK_ERRORS as e:
        logger.warning("Episode stream URL connection failed: %s", e)
        await update.message.reply_text(
            "The server could not be reached or took too long to respond. Please try again."
        )
        clear_state(chat_id)
        await _offer_again(update)
        return
    except Exception as e:
        logger.exception("Episode stream URL failed: %s", e)
        await update.message.reply_text("Something went wrong getting the stream. Please try again.")
        clear_state(chat_id)
        await _offer_again(update)
        return

    if not url_result.get("success") or not url_result.get("recommended_url"):
        await update.message.reply_text("Episode not found.")
        clear_state(chat_id)
        await _offer_again(update)
        return

    await update.message.reply_text(f"Watch here:\n{url_result['recommended_url']}")
    clear_state(chat_id)
    await _offer_again(update)


async def _offer_again(update: Update) -> None:
    await update.message.reply_text(
        "Choose what you want to search for:",
        reply_markup=CHOICE_KEYBOARD,
    )
