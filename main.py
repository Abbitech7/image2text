import logging
import os
import aiofiles
import requests
from telegram import Update, Message, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ChatMemberHandler, filters, ContextTypes
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OCR_API_KEY = os.getenv("OCR_API_KEY")
CHANNEL_ID = "@programmerat"

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Send me an image and I will convert it to text!')

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    processing_message: Message = await update.message.reply_text("Processing, please wait.")
    try:
        photo_file = update.message.photo[-1]
        file = await photo_file.get_file()

        # Download image asynchronously
        async with aiofiles.open('image.jpg', 'wb') as out_file:
            await out_file.write(await file.download_as_bytearray())

        # Send image to OCR API
        with open('image.jpg', 'rb') as image_file:
            response = requests.post(
                'https://api.ocr.space/parse/image',
                headers={'apikey': OCR_API_KEY},
                files={'file': image_file}
            )

        # Process OCR response
        if response.status_code == 200:
            result = response.json()
            if result.get('ParsedResults'):
                text = result['ParsedResults'][0]['ParsedText']
                await update.message.reply_text(text.strip() or "No text found.")
            else:
                await update.message.reply_text("No text found in the image.")
        else:
            await update.message.reply_text("Error processing the image with OCR API.")
            logger.error(f"Error: {response.status_code} - {response.text}")

        # Clean up
        os.remove('image.jpg')
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=processing_message.message_id)

    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        await update.message.reply_text("There was an error processing the photo. Please try again.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Update {update} caused error {context.error}")

async def check_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_status = update.chat_member.new_chat_member.status
    if user_status not in ['member', 'administrator', 'creator']:
        await context.bot.kick_chat_member(chat_id=update.effective_chat.id, user_id=update.effective_user.id)
        await context.bot.send_message(chat_id=update.effective_user.id, text="Please join the channel before using the bot.")
    else:
        await context.bot.send_message(chat_id=update.effective_user.id, text="Welcome to the channel! You can now use the bot.")

def main() -> None:
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Set bot commands
    commands = [
        BotCommand("start", "Start the bot and get instructions"),
    ]
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(ChatMemberHandler(check_member, ChatMemberHandler.MY_CHAT_MEMBER))
    application.add_error_handler(error_handler)

    application.run_polling()

if __name__ == '__main__':
    main()
