import re

with open('bot.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. We need datetime and timedelta for the bot
if "from datetime import datetime, timedelta" not in content:
    content = content.replace("import time", "import time\nfrom datetime import datetime, timedelta\nimport json")

# 2. Update the start function to handle previews
start_handler_new = """async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
                    msg = await update.message.reply_text(f"Here is your preview (expires in 15 mins):\\n{preview['content']}")
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
            f"Hello {user.first_name}! \\U0001f44b\\n\\n"
            "Welcome! You have successfully started the bot.\\n\\n"
            "Now you can request to join our channel using the link below:\\n\\n"
            f"{channel_link}"
        )
    except Exception as e:
        logger.error("Failed to reply /start for %s: %s", user.id, e)
"""
start_idx = content.find("async def start(")
end_idx = content.find("async def approve_request")
content = content[:start_idx] + start_handler_new + "\\n\\n" + content[end_idx:]

# 3. Add cleanup job
cleanup_job = """
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
"""

if "async def cleanup_expired_previews" not in content:
    content = content.replace("async def start(", cleanup_job + "\n\nasync def start(")

# 4. Schedule the job in run_bot
run_bot_hook = """    app = Application.builder().token(token).build()

    # Schedule cleanup job every 60 seconds
    app.job_queue.run_repeating(cleanup_expired_previews, interval=60)
"""
content = content.replace("    app = Application.builder().token(token).build()", run_bot_hook)


with open('bot.py', 'w', encoding='utf-8') as f:
    f.write(content)
