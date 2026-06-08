"""
Time Guard — ensures the factory NEVER runs during/near trading market hours.

Trading market opens 16:30 Saudi time (Asia/Riyadh).
Factory is only allowed to run BEFORE the daily cutoff (default 14:00),
giving a safety buffer before the market opens.

This is a hard safety gate: if the current time is outside the allowed
window, video production is blocked entirely — protecting the trading bot.
"""
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo

# ─── Configuration ───────────────────────────────────────────
TIMEZONE = ZoneInfo("Asia/Riyadh")

# Factory may only run before this time each day (24h format).
DAILY_CUTOFF = dtime(14, 0)          # 2:00 PM Saudi time

# Market opens at this time — factory must be fully idle well before this.
MARKET_OPEN = dtime(16, 30)          # 4:30 PM Saudi time

# Earliest the factory may start (avoid overnight surprises).
DAILY_START = dtime(2, 0)            # 2:00 AM Saudi time


def now_riyadh() -> datetime:
    return datetime.now(TIMEZONE)


def is_safe_to_run() -> tuple[bool, str]:
    """
    Returns (allowed, reason).
    True  → safe to produce videos.
    False → blocked (with explanation).
    """
    now = now_riyadh()
    current = now.time()

    if current < DAILY_START:
        return False, (
            f"⛔ BLOCKED: It's {current.strftime('%H:%M')} Saudi time — "
            f"before daily start ({DAILY_START.strftime('%H:%M')})."
        )

    if current >= DAILY_CUTOFF:
        return False, (
            f"⛔ BLOCKED: It's {current.strftime('%H:%M')} Saudi time — "
            f"past the daily cutoff ({DAILY_CUTOFF.strftime('%H:%M')}). "
            f"Market opens at {MARKET_OPEN.strftime('%H:%M')}. "
            f"Protecting the trading bot — no video work allowed now."
        )

    # Inside safe window
    minutes_left = (
        DAILY_CUTOFF.hour * 60 + DAILY_CUTOFF.minute
        - current.hour * 60 - current.minute
    )
    return True, (
        f"✅ Safe to run. {current.strftime('%H:%M')} Saudi time — "
        f"{minutes_left} min until cutoff ({DAILY_CUTOFF.strftime('%H:%M')})."
    )


def estimate_fits_in_window(estimated_minutes: int) -> tuple[bool, str]:
    """
    Check whether a job of `estimated_minutes` can finish before the cutoff.
    Use this before starting a long production run.
    """
    now = now_riyadh()
    cutoff_dt = now.replace(
        hour=DAILY_CUTOFF.hour, minute=DAILY_CUTOFF.minute, second=0, microsecond=0
    )
    minutes_available = (cutoff_dt - now).total_seconds() / 60

    if minutes_available < estimated_minutes:
        return False, (
            f"⛔ Not enough time: ~{estimated_minutes} min needed, "
            f"only {int(minutes_available)} min until cutoff. Skipping."
        )
    return True, f"✅ {int(minutes_available)} min available for ~{estimated_minutes} min job."


if __name__ == "__main__":
    # Quick manual check
    allowed, reason = is_safe_to_run()
    print(reason)
    print(f"Current Riyadh time: {now_riyadh().strftime('%Y-%m-%d %H:%M:%S %Z')}")
