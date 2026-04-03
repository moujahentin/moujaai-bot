import random
import time
from dataclasses import dataclass
from typing import Optional

from config import (
    GUESS_STATS_FILE,
    NUMBER_GUESS_MAX,
    NUMBER_GUESS_MIN,
    NUMBER_GUESS_TIMEOUT_MINUTES,
)
from utils.storage import load_json, save_json

DIFFICULTIES = {
    "easy": 10,
    "medium": 5,
    "hard": 3,
}


@dataclass
class GuessResult:
    kind: str
    message: str
    payload: Optional[dict] = None


_games: dict[int, dict] = {}



def _cleanup_expired_games() -> None:
    now = time.time()
    timeout_seconds = NUMBER_GUESS_TIMEOUT_MINUTES * 60
    expired = [
        user_id
        for user_id, game in _games.items()
        if now - game["last_activity"] > timeout_seconds
    ]
    for user_id in expired:
        _games.pop(user_id, None)



def _load_stats() -> dict:
    return load_json(GUESS_STATS_FILE, {"users": {}})



def _save_stats(stats: dict) -> None:
    save_json(GUESS_STATS_FILE, stats)



def _update_stats(user_id: int, username: str, won: bool, attempts: Optional[int] = None, elapsed: Optional[float] = None) -> None:
    stats = _load_stats()
    users = stats.setdefault("users", {})
    key = str(user_id)
    user = users.setdefault(
        key,
        {
            "username": username,
            "games_played": 0,
            "wins": 0,
            "losses": 0,
            "best_attempts": None,
            "best_time_seconds": None,
        },
    )

    user["username"] = username
    user["games_played"] += 1
    if won:
        user["wins"] += 1
        if attempts is not None and (user["best_attempts"] is None or attempts < user["best_attempts"]):
            user["best_attempts"] = attempts
        if elapsed is not None and (user["best_time_seconds"] is None or elapsed < user["best_time_seconds"]):
            user["best_time_seconds"] = round(elapsed, 2)
    else:
        user["losses"] += 1

    _save_stats(stats)



def start_game(user_id: int, username: str, difficulty: str) -> GuessResult:
    _cleanup_expired_games()
    difficulty = difficulty.lower()
    if difficulty not in DIFFICULTIES:
        options = ", ".join(DIFFICULTIES.keys())
        return GuessResult("error", f"Διάλεξε difficulty: {options}")

    _games[user_id] = {
        "number": random.randint(NUMBER_GUESS_MIN, NUMBER_GUESS_MAX),
        "chances": DIFFICULTIES[difficulty],
        "attempts": 0,
        "difficulty": difficulty,
        "started_at": time.time(),
        "last_activity": time.time(),
        "username": username,
    }

    return GuessResult(
        "started",
        (
            f"🎮 Νέο game ({difficulty})\n"
            f"Σκέφτομαι αριθμό από {NUMBER_GUESS_MIN} έως {NUMBER_GUESS_MAX}.\n"
            f"Έχεις {DIFFICULTIES[difficulty]} προσπάθειες.\n"
            f"Γράψε `!guess <αριθμός>`"
        ),
        {"difficulty": difficulty, "chances": DIFFICULTIES[difficulty]},
    )



def make_guess(user_id: int, username: str, value: int) -> GuessResult:
    _cleanup_expired_games()
    game = _games.get(user_id)
    if not game:
        return GuessResult("no_game", "Δεν έχεις ενεργό game. Γράψε `!guess_start easy`")

    if value < NUMBER_GUESS_MIN or value > NUMBER_GUESS_MAX:
        return GuessResult("error", f"Βάλε αριθμό από {NUMBER_GUESS_MIN} έως {NUMBER_GUESS_MAX}.")

    game["attempts"] += 1
    game["chances"] -= 1
    game["last_activity"] = time.time()

    number = game["number"]
    if value == number:
        elapsed = round(time.time() - game["started_at"], 2)
        attempts = game["attempts"]
        _games.pop(user_id, None)
        _update_stats(user_id, username, won=True, attempts=attempts, elapsed=elapsed)
        return GuessResult(
            "win",
            f"🎉 Μπράβο! Το βρήκες σε {attempts} προσπάθειες και {elapsed} δευτερόλεπτα.",
            {"attempts": attempts, "elapsed": elapsed, "number": number},
        )

    if game["chances"] <= 0:
        _games.pop(user_id, None)
        _update_stats(user_id, username, won=False)
        return GuessResult("lose", f"💀 Έχασες. Ο αριθμός ήταν {number}.", {"number": number})

    if value < number:
        return GuessResult("higher", f"⬆️ Μεγαλύτερος. Απομένουν {game['chances']} προσπάθειες.", {"remaining": game["chances"]})

    return GuessResult("lower", f"⬇️ Μικρότερος. Απομένουν {game['chances']} προσπάθειες.", {"remaining": game["chances"]})



def cancel_game(user_id: int) -> GuessResult:
    _cleanup_expired_games()
    if user_id in _games:
        _games.pop(user_id, None)
        return GuessResult("cancelled", "Το game ακυρώθηκε.")
    return GuessResult("no_game", "Δεν έχεις ενεργό game.")



def get_active_game(user_id: int) -> Optional[dict]:
    _cleanup_expired_games()
    return _games.get(user_id)



def get_user_stats(user_id: int) -> dict:
    stats = _load_stats()
    return stats.get("users", {}).get(str(user_id), {})



def get_leaderboard(limit: int = 10) -> list[dict]:
    stats = _load_stats()
    users = list(stats.get("users", {}).values())

    ranked = [
        user
        for user in users
        if user.get("wins", 0) > 0 and user.get("best_attempts") is not None
    ]
    ranked.sort(
        key=lambda item: (
            item.get("best_attempts", 999999),
            item.get("best_time_seconds", 999999.0),
            -item.get("wins", 0),
        )
    )
    return ranked[:limit]
