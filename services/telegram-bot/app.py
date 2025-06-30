import os
import logging
import httpx
from datetime import datetime
import json
import asyncio
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    ConversationHandler,
)
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configure Telegram bot token
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("No Telegram bot token provided")

# Syntinel Core API URL
OBSERVER_CORE_URL = os.getenv("OBSERVER_CORE_URL", "http://syntinel-core:8000")

# Database setup
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    f"postgresql://{os.getenv('POSTGRES_USER', 'admin')}:"
    f"{os.getenv('POSTGRES_PASSWORD', 'pswd')}@"
    f"{os.getenv('POSTGRES_HOST', 'postgres')}:5432/"
    f"{os.getenv('POSTGRES_DB', 'syntineldb')}"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define states for conversation handlers
SELECTING_ACTION, EDITING_DRAFT, SCHEDULING_POST, CONFIRMING_ACTION = range(4)

# Define database model for bot logs
class BotLog(Base):
    __tablename__ = "bot_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    action = Column(String)
    draft_id = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    details = Column(Text, nullable=True)

# Create tables
Base.metadata.create_all(bind=engine)

# Helper function to log bot actions
def log_action(user_id, action, draft_id=None, details=None):
    """Log user actions in the database"""
    db = SessionLocal()
    try:
        log = BotLog(
            user_id=user_id,
            action=action,
            draft_id=draft_id,
            details=details
        )
        db.add(log)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log action: {e}")
    finally:
        db.close()

async def fetch_drafts():
    """Fetch drafts from Syntinel Core"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{OBSERVER_CORE_URL}/drafts")
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to fetch drafts: {response.text}")
                return []
    except Exception as e:
        logger.error(f"Error fetching drafts: {e}")
        return []

async def publish_draft(draft_id):
    """Publish draft to X via Syntinel Core"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{OBSERVER_CORE_URL}/publish/{draft_id}")
            if response.status_code == 200:
                return True, response.json()
            else:
                logger.error(f"Failed to publish draft: {response.text}")
                return False, {"error": response.text}
    except Exception as e:
        logger.error(f"Error publishing draft: {e}")
        return False, {"error": str(e)}

async def schedule_draft(draft_id, schedule_time):
    """Schedule draft for publication"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{OBSERVER_CORE_URL}/schedule",
                json={"draft_id": draft_id, "publish_time": schedule_time.isoformat()}
            )
            if response.status_code == 200:
                return True, response.json()
            else:
                logger.error(f"Failed to schedule draft: {response.text}")
                return False, {"error": response.text}
    except Exception as e:
        logger.error(f"Error scheduling draft: {e}")
        return False, {"error": str(e)}

# Command handlers
async def start(update: Update, context: CallbackContext):
    """Send a welcome message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_text(
        f"Hello {user.first_name}! Welcome to Observer Bot.\n\n"
        f"Use /drafts to see the latest post drafts."
    )
    log_action(user.id, "start")

async def show_drafts(update: Update, context: CallbackContext):
    """Show available drafts from Syntinel Core."""
    user = update.effective_user
    
    # Show "loading" message
    message = await update.message.reply_text("Fetching latest drafts...")
    
    # Fetch drafts from Syntinel Core API
    drafts = await fetch_drafts()
    
    if not drafts:
        await message.edit_text("No drafts available at the moment.")
        return SELECTING_ACTION
    
    # Store drafts in context for later use
    context.user_data["drafts"] = drafts
    
    # Create message with draft previews
    text = "📝 *Available Drafts*\n\n"
    
    for i, draft in enumerate(drafts):
        # Truncate content if too long
        content = draft["content"]
        if len(content) > 100:
            content = content[:97] + "..."
            
        text += f"*{i+1}. Style: {draft['style']}*\n{content}\n\n"
    
    # Create keyboard with draft options
    keyboard = []
    for i, _ in enumerate(drafts):
        keyboard.append([
            InlineKeyboardButton(f"✅ Publish #{i+1}", callback_data=f"publish_{i}"),
            InlineKeyboardButton(f"⏰ Schedule #{i+1}", callback_data=f"schedule_{i}")
        ])
        # Uncomment when edit functionality is implemented
        # keyboard.append([InlineKeyboardButton(f"📝 Edit #{i+1}", callback_data=f"edit_{i}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Edit the "loading" message with the drafts
    await message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    
    log_action(user.id, "view_drafts", details=f"Viewed {len(drafts)} drafts")
    return SELECTING_ACTION

async def button_callback(update: Update, context: CallbackContext):
    """Handle button presses."""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    data = query.data
    
    if data.startswith("publish_"):
        # Extract draft index
        draft_idx = int(data.split("_")[1])
        draft = context.user_data["drafts"][draft_idx]
        draft_id = draft["id"]
        
        # Show confirmation keyboard
        keyboard = [
            [
                InlineKeyboardButton("✅ Confirm Publish", callback_data=f"confirm_publish_{draft_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"*Publish this draft?*\n\n{draft['content']}\n\nThis will post immediately to X.",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        log_action(user.id, "publish_intent", draft_id=draft_id)
        return CONFIRMING_ACTION
        
    elif data.startswith("schedule_"):
        # Extract draft index
        draft_idx = int(data.split("_")[1])
        draft = context.user_data["drafts"][draft_idx]
        draft_id = draft["id"]
        
        # Store draft_id in context
        context.user_data["scheduling_draft_id"] = draft_id
        
        await query.edit_message_text(
            f"*Schedule this draft:*\n\n{draft['content']}\n\n"
            f"Please send the date and time in format: YYYY-MM-DD HH:MM",
            parse_mode="Markdown"
        )
        
        log_action(user.id, "schedule_intent", draft_id=draft_id)
        return SCHEDULING_POST
        
    elif data.startswith("confirm_publish_"):
        # Extract draft id
        draft_id = int(data.split("_")[2])
        
        # Show publishing message
        await query.edit_message_text("Publishing to X...")
        
        # Publish via Observer Core
        success, result = await publish_draft(draft_id)
        
        if success:
            await query.edit_message_text("✅ Successfully published to X!")
            log_action(user.id, "publish_success", draft_id=draft_id)
        else:
            await query.edit_message_text(f"❌ Failed to publish: {result.get('error', 'Unknown error')}")
            log_action(user.id, "publish_failure", draft_id=draft_id, details=str(result))
            
        # Return to main menu after a delay
        await asyncio.sleep(2)
        return await show_drafts(update, context)
        
    elif data == "cancel":
        await query.edit_message_text("Action cancelled.")
        log_action(user.id, "cancel_action")
        
        # Return to main menu after a delay
        await asyncio.sleep(1)
        return await show_drafts(update, context)
    
    return SELECTING_ACTION

async def handle_schedule_time(update: Update, context: CallbackContext):
    """Handle scheduling time input from user."""
    user = update.effective_user
    text = update.message.text
    draft_id = context.user_data.get("scheduling_draft_id")
    
    if not draft_id:
        await update.message.reply_text("Error: No draft selected for scheduling.")
        log_action(user.id, "schedule_error", details="No draft selected")
        return await show_drafts(update, context)
    
    # Try to parse the datetime
    try:
        schedule_time = datetime.strptime(text, "%Y-%m-%d %H:%M")
        
        # Check if time is in the future
        if schedule_time <= datetime.now():
            await update.message.reply_text("Please provide a future date and time.")
            return SCHEDULING_POST
            
        # Schedule the post
        success, result = await schedule_draft(draft_id, schedule_time)
        
        if success:
            await update.message.reply_text(
                f"✅ Post scheduled for {schedule_time.strftime('%Y-%m-%d %H:%M')}!"
            )
            log_action(user.id, "schedule_success", draft_id=draft_id, details=str(schedule_time))
        else:
            await update.message.reply_text(
                f"❌ Failed to schedule post: {result.get('error', 'Unknown error')}"
            )
            log_action(user.id, "schedule_failure", draft_id=draft_id, details=str(result))
            
        # Clear scheduling draft from context
        if "scheduling_draft_id" in context.user_data:
            del context.user_data["scheduling_draft_id"]
            
        # Return to drafts after a delay
        await asyncio.sleep(1)
        return await show_drafts(update, context)
        
    except ValueError:
        await update.message.reply_text(
            "Invalid format. Please use YYYY-MM-DD HH:MM (e.g., 2025-06-21 16:30)"
        )
        return SCHEDULING_POST

async def help_command(update: Update, context: CallbackContext):
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        "Here's how to use Observer Bot:\n\n"
        "/start - Start the bot\n"
        "/drafts - View latest post drafts\n"
        "/help - Show this help message"
    )
    log_action(update.effective_user.id, "help")

async def error_handler(update: Update, context: CallbackContext):
    """Log errors caused by updates."""
    logger.error(f"Update {update} caused error {context.error}")
    
    # If an update caused an error, notify the user if possible
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "Sorry, something went wrong. Please try again later."
        )

def main():
    """Start the bot."""
    # Create the updater and dispatcher
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher
    
    # Set up conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("drafts", show_drafts)],
        states={
            SELECTING_ACTION: [
                CallbackQueryHandler(button_callback)
            ],
            SCHEDULING_POST: [
                MessageHandler(Filters.text & ~Filters.command, handle_schedule_time)
            ],
            CONFIRMING_ACTION: [
                CallbackQueryHandler(button_callback)
            ],
        },
        fallbacks=[CommandHandler("drafts", show_drafts)],
    )
    
    # Add handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(conv_handler)
    
    # Add error handler
    dispatcher.add_error_handler(error_handler)
    
    # Start the Bot
    updater.start_polling()
    
    # Run the bot until you press Ctrl-C
    updater.idle()

if __name__ == "__main__":
    main()
