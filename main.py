import asyncio
import logging
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from config import Config
from database import (
    init_db, add_note, get_notes, search_notes, 
    delete_note, get_note_by_id, update_note,
    get_tags, get_notes_by_tag, get_stats
)
from ai import AIHelper

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize AI helper
ai_helper = AIHelper()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = f"""
📚 Welcome {user.first_name} to Personal Knowledge Base Bot!

I help you store, organize, and retrieve your personal knowledge.

📋 Commands:
/add <title> | <content>    - Add a new note (use | as separator)
/search <keyword>           - Search your notes
/list                       - List all your notes
/tag <tag>                  - Get notes by tag
/delete <id>                - Delete a note by ID
/get <id>                   - Get a specific note
/update <id> | <content>    - Update a note
/stats                      - Show your knowledge base stats
/export                     - Export all your notes
/help                       - Show this message

💡 Pro Tip: Use tags like #important, #work, #personal
Example: /add #work | Meeting notes | Discussed project timeline
"""
    keyboard = [
        [InlineKeyboardButton("📝 Add Note", callback_data="add")],
        [InlineKeyboardButton("🔍 Search", callback_data="search")],
        [InlineKeyboardButton("📊 Stats", callback_data="stats")],
        [InlineKeyboardButton("🏷️ Tags", callback_data="tags")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def add_note_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "📝 How to add a note:\n"
            "Use the format: /add Title | Content\n\n"
            "Examples:\n"
            "/add #work | Meeting notes | Discussed Q4 goals\n"
            "/add #personal | Recipe | Pasta with tomato sauce\n"
            "/add #code | Python snippet | print('Hello World')"
        )
        return
    
    # Join all args and split by |
    full_text = ' '.join(context.args)
    parts = full_text.split('|')
    
    if len(parts) < 2:
        await update.message.reply_text(
            "❌ Invalid format!\n"
            "Use: /add Title | Content\n"
            "The | separates title from content."
        )
        return
    
    title = parts[0].strip()
    content = '|'.join(parts[1:]).strip()
    
    # Extract tags from title
    tags = []
    words = title.split()
    for word in words:
        if word.startswith('#'):
            tags.append(word[1:])
    
    # Extract tags from content
    content_words = content.split()
    for word in content_words:
        if word.startswith('#'):
            tag = word[1:]
            if tag not in tags:
                tags.append(tag)
    
    note_id = add_note(user_id, title, content, tags)
    
    if note_id:
        tag_text = f"🏷️ Tags: {', '.join(tags)}" if tags else "No tags"
        await update.message.reply_text(
            f"✅ Note saved successfully!\n\n"
            f"📌 ID: {note_id}\n"
            f"📝 Title: {title}\n"
            f"{tag_text}\n"
            f"💾 Saved at: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
    else:
        await update.message.reply_text("❌ Failed to save note. Please try again.")

async def list_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    notes = get_notes(user_id)
    
    if not notes:
        await update.message.reply_text("📭 You don't have any notes yet!\nUse /add to create your first note.")
        return
    
    message = "📚 Your Notes:\n\n"
    for i, note in enumerate(notes, 1):
        tags = f"[{', '.join(note['tags'])}]" if note.get('tags') else ""
        message += f"{i}. ID:{note['id']} {tags}\n   📝 {note['title'][:50]}\n   📅 {note['created_at'][:10]}\n\n"
    
    # Paginate if too many
    if len(notes) > 10:
        message += f"\nShowing first 10 of {len(notes)} notes.\nUse /list to see more."
    
    await update.message.reply_text(message[:4000])  # Telegram limit

async def search_notes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text("🔍 What do you want to search for?\nExample: /search python")
        return
    
    query = ' '.join(context.args)
    results = search_notes(user_id, query)
    
    if not results:
        await update.message.reply_text(f"❌ No results found for '{query}'")
        return
    
    message = f"🔍 Results for '{query}':\n\n"
    for result in results[:10]:
        message += f"📌 ID: {result['id']}\n"
        message += f"📝 {result['title']}\n"
        preview = result['content'][:100] + "..." if len(result['content']) > 100 else result['content']
        message += f"📄 {preview}\n"
        message += f"📅 {result['created_at'][:10]}\n\n"
    
    if len(results) > 10:
        message += f"\nShowing first 10 of {len(results)} results."
    
    await update.message.reply_text(message[:4000])

async def get_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text("❌ Please provide a note ID.\nExample: /get 123")
        return
    
    try:
        note_id = int(context.args[0])
        note = get_note_by_id(user_id, note_id)
        
        if not note:
            await update.message.reply_text(f"❌ Note with ID {note_id} not found.")
            return
        
        message = f"""
📌 Note #{note['id']}

📝 Title: {note['title']}
📄 Content: {note['content']}
🏷️ Tags: {', '.join(note['tags']) if note.get('tags') else 'None'}
📅 Created: {note['created_at']}
🔄 Updated: {note['updated_at']}

Commands: /update {note['id']} | new content  /delete {note['id']}
"""
        await update.message.reply_text(message)
        
    except ValueError:
        await update.message.reply_text("❌ Invalid ID. Please provide a number.\nExample: /get 123")

async def delete_note_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text("❌ Please provide a note ID.\nExample: /delete 123")
        return
    
    try:
        note_id = int(context.args[0])
        success = delete_note(user_id, note_id)
        
        if success:
            await update.message.reply_text(f"✅ Note #{note_id} deleted successfully!")
        else:
            await update.message.reply_text(f"❌ Note #{note_id} not found or already deleted.")
            
    except ValueError:
        await update.message.reply_text("❌ Invalid ID. Please provide a number.\nExample: /delete 123")

async def update_note_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "📝 How to update a note:\n"
            "Use: /update 123 | new content\n\n"
            "Example: /update 45 | Updated meeting notes"
        )
        return
    
    full_text = ' '.join(context.args)
    parts = full_text.split('|')
    
    if len(parts) < 2:
        await update.message.reply_text(
            "❌ Invalid format!\n"
            "Use: /update 123 | new content"
        )
        return
    
    try:
        note_id = int(parts[0].strip())
        content = '|'.join(parts[1:]).strip()
        
        success = update_note(user_id, note_id, content)
        
        if success:
            await update.message.reply_text(f"✅ Note #{note_id} updated successfully!")
        else:
            await update.message.reply_text(f"❌ Note #{note_id} not found.")
            
    except ValueError:
        await update.message.reply_text("❌ Invalid ID. Please provide a number.\nExample: /update 123 | new content")

async def tag_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not context.args:
        # Show all tags
        tags = get_tags(user_id)
        if not tags:
            await update.message.reply_text("📭 You don't have any tags yet!")
            return
        
        message = "🏷️ Your Tags:\n\n"
        for tag, count in tags.items():
            message += f"#{tag} ({count} notes)\n"
        await update.message.reply_text(message)
        return
    
    tag = context.args[0].lstrip('#')
    notes = get_notes_by_tag(user_id, tag)
    
    if not notes:
        await update.message.reply_text(f"❌ No notes found with tag #{tag}")
        return
    
    message = f"🏷️ Notes with tag #{tag}:\n\n"
    for note in notes[:10]:
        message += f"📌 ID: {note['id']} - {note['title']}\n"
        message += f"📅 {note['created_at'][:10]}\n\n"
    
    if len(notes) > 10:
        message += f"\nShowing first 10 of {len(notes)} notes."
    
    await update.message.reply_text(message[:4000])

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stats = get_stats(user_id)
    
    if not stats:
        await update.message.reply_text("📭 You don't have any notes yet!")
        return
    
    message = f"""
📊 Your Knowledge Base Stats

📚 Total Notes: {stats['total_notes']}
🏷️ Total Tags: {stats['total_tags']}
📅 Created Today: {stats['today_notes']}
🔥 Most Used Tag: #{stats['most_used_tag']} ({stats['most_used_count']} notes)
📝 Average Note Length: {stats['avg_length']} characters

📈 Keep learning and saving knowledge!
"""
    
    # Show recent tags
    if stats.get('tags'):
        message += "\n🏷️ Your Tags:\n"
        for tag, count in list(stats['tags'].items())[:5]:
            message += f"#{tag} ({count})\n"
    
    await update.message.reply_text(message)

async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    notes = get_notes(user_id)
    
    if not notes:
        await update.message.reply_text("📭 No notes to export!")
        return
    
    # Create JSON export
    export_data = {
        'user_id': user_id,
        'export_date': datetime.now().isoformat(),
        'total_notes': len(notes),
        'notes': notes
    }
    
    # Save to file
    filename = f'knowledge_base_{user_id}_{datetime.now().strftime("%Y%m%d")}.json'
    with open(filename, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    # Send file
    await update.message.reply_document(
        document=open(filename, 'rb'),
        filename=filename,
        caption=f"📚 Exported {len(notes)} notes from your knowledge base!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📚 Personal Knowledge Base Bot Help

📝 Adding Notes:
/add Title | Content - Save a note
Use #tags in title or content for organization

🔍 Finding Notes:
/search keyword - Search your notes
/tag #tagname - Get notes by tag
/list - List all your notes
/get 123 - Get specific note by ID

📝 Managing Notes:
/update 123 | new content - Update a note
/delete 123 - Delete a note

📊 Analytics:
/stats - View your knowledge stats
/export - Export all notes as JSON

💡 Pro Tips:
• Use #tags: #work #personal #code #ideas
• Be descriptive in titles for better search
• Update notes as you learn more
• Export your knowledge base regularly

📌 Example:
/add #programming | Python Tips | Use list comprehensions for cleaner code
"""
    await update.message.reply_text(help_text)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "add":
        await query.edit_message_text(
            "📝 Send your note:\n\n"
            "Format: Title | Content\n"
            "Example: #work | Meeting | Discussed Q4 goals\n\n"
            "Use /add Title | Content"
        )
    
    elif query.data == "search":
        await query.edit_message_text(
            "🔍 What do you want to search for?\n"
            "Use: /search your_keyword"
        )
    
    elif query.data == "stats":
        await stats_command(update, context)
    
    elif query.data == "tags":
        await tag_command(update, context)

def main():
    Config.validate()
    init_db()
    logger.info("✅ Database initialized")
    
    application = Application.builder().token(Config.BOT_TOKEN).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("add", add_note_command))
    application.add_handler(CommandHandler("list", list_notes))
    application.add_handler(CommandHandler("search", search_notes_command))
    application.add_handler(CommandHandler("get", get_note))
    application.add_handler(CommandHandler("delete", delete_note_command))
    application.add_handler(CommandHandler("update", update_note_command))
    application.add_handler(CommandHandler("tag", tag_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("export", export_command))
    
    # Button handler
    application.add_handler(CallbackQueryHandler(button_handler))
    
    logger.info("🚀 Starting Knowledge Base Bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
