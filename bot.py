import asyncio
import logging
import sys
import time
from datetime import datetime, timedelta
import json

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ChatJoinRequestHandler,
    ContextTypes,
)
from telegram.error import Conflict, NetworkError, TimedOut, RetryAfter

import database as db

# ── Logging: force UTF-8 so emoji don't crash Windows cp1252 console ─────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(
            stream=open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False)
        ),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

# ── Init DB ───────────────────────────────────────────────────────────────────
db.init_db()


# ── Handlers ──────────────────────────────────────────────────────────────────


async def cleanup_expired_previews(context: ContextTypes.DEFAULT_TYPE):
    expired = db.get_expired_accesses()
    for access in expired:
        try:
            msg_ids = json.loads(access["message_ids"] or "[]")
            for mid in msg_ids:
                try:
                    await context.bot.delete_message(chat_id=access["chat_id"], message_id=mid)
                except Exception as e:
                    logger.warning(f"Could not delete message {mid} for access {access['id']}: {e}")
            
            # Send expiration notification
            try:
                await context.bot.send_message(chat_id=access["chat_id"], text="Your 15-minute preview has expired.")
            except Exception:
                pass
                
        except Exception as e:
            logger.error(f"Error processing expired access {access['id']}: {e}")
            
        finally:
            db.mark_access_deleted(access["id"])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return
    
    # Check for deep linking (e.g. /start preview_xyz)
    if context.args and len(context.args) > 0:
        preview_id = context.args[0]
        preview = db.get_preview(preview_id)
        
        if preview:
            if not preview["is_active"]:
                await update.message.reply_text("This preview is currently inactive.")
                return
                
            active_access = db.get_active_access(preview_id, user.id)
            if active_access:
                await update.message.reply_text("You already have an active access to this preview. Please check your previous messages.")
                return
                
            # Grant new 15-minute access
            expires_at = (datetime.utcnow() + timedelta(minutes=15)).isoformat()
            
            try:
                msg = None
                if preview["type"] == "url":
                    msg = await update.message.reply_text(f"Here is your preview (expires in 15 mins):\n{preview['content']}")
                elif preview["type"] == "file_id":
                    # Try video, then document, then photo
                    try:
                        msg = await update.message.reply_video(video=preview["content"], caption="Preview (expires in 15 mins)")
                    except Exception:
                        try:
                            msg = await update.message.reply_document(document=preview["content"], caption="Preview (expires in 15 mins)")
                        except Exception:
                            msg = await update.message.reply_photo(photo=preview["content"], caption="Preview (expires in 15 mins)")
                
                if msg:
                    db.record_preview_access(
                        preview_id=preview_id,
                        user_id=user.id,
                        chat_id=msg.chat_id,
                        message_ids=json.dumps([msg.message_id]),
                        accessed_at=datetime.utcnow().isoformat(),
                        expires_at=expires_at
                    )
                    db.log_event("preview_access", user.id, user.username, user.full_name, f"Accessed preview: {preview['name']}")
                    return
            except Exception as e:
                logger.error(f"Failed to send preview {preview_id} to {user.id}: {e}")
                await update.message.reply_text("Sorry, there was an error loading this preview.")
                return
        else:
            await update.message.reply_text("Invalid or expired preview link.")
            return

    # Normal /start behavior below
    try:
        db.upsert_user(user.id, user.username or "", user.full_name or "")
        db.log_event(
            event_type="start",
            user_id=user.id,
            username=user.username,
            full_name=user.full_name,
            detail="/start command received",
        )
    except Exception as e:
        logger.error("DB error on /start for %s: %s", user.id, e)

    channel_link = db.get_config("channel_link") or "https://t.me/+YOUR_INVITE_LINK"
    try:
        await update.message.reply_text(
            f"Hello {user.first_name}! \U0001f44b\n\n"
            "Welcome! You have successfully started the bot.\n\n"
            "Now you can request to join our channel using the link below:\n\n"
            f"{channel_link}"
        )
    except Exception as e:
        logger.error("Failed to reply /start for %s: %s", user.id, e)

async def approve_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    request = update.chat_join_request
    if not request:
        return
    user = request.from_user

    try:
        db.upsert_user(user.id, user.username or "", user.full_name or "")
        db.upsert_join_request(user.id, user.username or "", user.full_name or "")
        db.log_event(
            event_type="join_request",
            user_id=user.id,
            username=user.username,
            full_name=user.full_name,
            detail="Join request received",
        )
    except Exception as e:
        logger.error("DB error for join request %s: %s", user.id, e)

    try:
        await request.approve()
        db.update_join_request_status(user.id, "approved")
        db.log_event(
            event_type="approved",
            user_id=user.id,
            username=user.username,
            full_name=user.full_name,
            detail="Join request auto-approved",
        )
        logger.info("Approved: %s (%s)", user.full_name, user.id)

    except RetryAfter as e:
        logger.warning("Rate limited — sleeping %ss for %s", e.retry_after, user.id)
        await asyncio.sleep(e.retry_after)
        try:
            await request.approve()
            db.update_join_request_status(user.id, "approved")
        except Exception as e2:
            logger.error("Retry approval failed for %s: %s", user.id, e2)

    except (NetworkError, TimedOut) as e:
        logger.warning("Network error approving %s (will retry): %s", user.id, e)

    except Exception as e:
        db.log_event(
            event_type="error",
            user_id=user.id,
            username=user.username,
            full_name=user.full_name,
            detail=f"Approval error: {e}",
        )
        logger.error("ERROR approving %s: %s", user.id, e)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Global PTB error handler — logs but never crashes the bot."""
    err = context.error
    if isinstance(err, Conflict):
        logger.error(
            "Conflict: another bot instance is running! "
            "Make sure only ONE copy of bot.py is running. "
            "Kill all python.exe processes and restart."
        )
    elif isinstance(err, (NetworkError, TimedOut)):
        logger.warning("Network/timeout (auto-retry): %s", err)
    elif isinstance(err, RetryAfter):
        logger.warning("Rate limit — wait %ss", err.retry_after)
    else:
        logger.error("Unhandled error: %s", err, exc_info=err)
        try:
            db.log_event(event_type="error", detail=f"Bot error: {err}")
        except Exception:
            pass


# ── Single run attempt using a brand-new event loop ──────────────────────────

def _run_once(token: str, drop_pending: bool) -> None:
    """
    python-telegram-bot v21 manages its own event loop internally via
    Application.__run().  We must give it a *fresh* event loop every time —
    we cannot reuse a closed one.  The correct pattern is:

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            application.run_polling(...)   # blocks until stopped
        finally:
            loop.close()

    do NOT wrap run_polling() inside asyncio.run() — that fights PTB's
    own loop management and raises "Cannot close a running event loop".
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    application = (
        Application.builder()
        .token(token)
        .build()
    )
    application.add_handler(CommandHandler("start", start))
    application.add_handler(ChatJoinRequestHandler(approve_request))
    application.add_error_handler(error_handler)

    logger.info("Bot polling started.")
    try:
        # run_polling blocks here until stopped
        application.run_polling(
            drop_pending_updates=drop_pending,
            allowed_updates=Update.ALL_TYPES,
        )
    finally:
        # Close the loop only after run_polling has fully wound down
        try:
            if not loop.is_closed():
                loop.close()
        except Exception:
            pass


# ── Auto-restart supervisor loop ─────────────────────────────────────────────

def main() -> None:
    db.init_db()

    token = db.get_config("bot_token") or ""
    if not token or token == "YOUR_BOT_TOKEN":
        logger.critical(
            "Bot token is not configured! "
            "Open the dashboard -> Settings -> paste your real bot token -> Save -> restart bot."
        )
        db.log_event(event_type="error", detail="Bot token not set — bot cannot start")
        sys.exit(1)

    restart_count = 0
    max_delay = 60  # seconds

    while True:
        restart_count += 1
        logger.info("Starting bot (attempt #%d) ...", restart_count)
        db.set_config("bot_status", "running")
        db.log_event(
            event_type="bot_start",
            detail=f"Bot started (attempt #{restart_count})",
        )

        try:
            _run_once(token, drop_pending=(restart_count == 1))

            # run_polling returned — this only happens on a clean shutdown
            logger.info("Bot stopped cleanly.")
            db.set_config("bot_status", "stopped")
            db.log_event(event_type="bot_stop", detail="Bot stopped cleanly")
            break

        except (SystemExit, KeyboardInterrupt):
            logger.info("Bot received stop/interrupt signal.")
            db.set_config("bot_status", "stopped")
            db.log_event(event_type="bot_stop", detail="Bot stopped via signal")
            break

        except Conflict:
            logger.error(
                "Conflict: another bot instance is active. "
                "Waiting 35s for old connection to expire, then retrying..."
            )
            db.set_config("bot_status", "restarting")
            db.log_event(event_type="error", detail="Conflict: duplicate instance. Waiting 35s.")
            time.sleep(35)
            token = db.get_config("bot_token") or token

        except Exception as e:
            delay = min(5 * restart_count, max_delay)
            logger.error(
                "Bot crashed: %s\n  Auto-restarting in %ds (attempt #%d)...",
                e, delay, restart_count,
            )
            db.set_config("bot_status", "restarting")
            db.log_event(
                event_type="error",
                detail=f"Crashed: {e}. Restarting in {delay}s (attempt #{restart_count})",
            )
            time.sleep(delay)
            token = db.get_config("bot_token") or token


if __name__ == "__main__":
    main()