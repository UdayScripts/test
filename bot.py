import telebot
from pytube import YouTube
import os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import BOT_TOKEN  # Import the bot token from config.py

bot = telebot.TeleBot(BOT_TOKEN)

# Dictionary to store user data
user_data = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Welcome! Send me a YouTube video link, and I'll download it for you.")
    
@bot.message_handler(func=lambda message: True)
def handle_url(message):
    url = message.text.strip()
    
    # Validate URL
    if not url.startswith("https://www.youtube.com/") and not url.startswith("https://youtu.be/"):
        bot.reply_to(message, "Please send a valid YouTube URL.")
        return

    # Store the URL in user data
    user_data[message.chat.id] = {"url": url}

    # Create inline keyboard for format selection
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Video", callback_data="format_video"))
    keyboard.add(InlineKeyboardButton("Audio", callback_data="format_audio"))
    
    # Send the format selection message with inline keyboard
    bot.send_message(message.chat.id, "Choose the format to download:", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("format_"))
def handle_format_selection(call):
    format_choice = call.data.split("_")[1]  # Extract 'video' or 'audio'
    chat_id = call.message.chat.id
    
    user_data[chat_id]["format"] = format_choice
    url = user_data[chat_id]["url"]
    yt = YouTube(url)
    
    if format_choice == "video":
        # List available video streams with resolution
        streams = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc()
        response = "Available video resolutions:\n"
        for i, stream in enumerate(streams):
            response += f"{i + 1}. {stream.resolution} - {round(stream.filesize / (1024 * 1024), 2)} MB\n"
        response += "Please choose a resolution by number:"
        user_data[chat_id]["streams"] = streams
    else:
        # List available audio streams with bitrate
        streams = yt.streams.filter(only_audio=True).order_by('abr').desc()
        response = "Available audio bitrates:\n"
        for i, stream in enumerate(streams):
            response += f"{i + 1}. {stream.abr} - {round(stream.filesize / (1024 * 1024), 2)} MB\n"
        response += "Please choose a bitrate by number:"
        user_data[chat_id]["streams"] = streams
    
    bot.send_message(chat_id, response)

@bot.message_handler(func=lambda message: message.chat.id in user_data and "resolution" not in user_data[message.chat.id])
def handle_quality_selection(message):
    try:
        choice = int(message.text.strip()) - 1
        chat_id = message.chat.id
        streams = user_data[chat_id]["streams"]
        
        if choice < 0 or choice >= len(streams):
            bot.send_message(chat_id, "Please choose a valid number.")
            return

        selected_stream = streams[choice]
        bot.send_message(chat_id, "Downloading the selected format...")
        
        # Download the selected video or audio
        filename = selected_stream.download(filename='downloaded_video.mp4' if user_data[chat_id]["format"] == "video" else 'downloaded_audio.mp3')
        
        # Send the file to the user
        with open(filename, 'rb') as file:
            if user_data[chat_id]["format"] == "video":
                bot.send_video(chat_id, file)
            else:
                bot.send_audio(chat_id, file)
        
        # Clean up and delete the file
        os.remove(filename)
        bot.send_message(chat_id, "Download complete!")
        
        # Clear user data
        del user_data[chat_id]

    except Exception as e:
        bot.send_message(message.chat.id, "An error occurred. Please try again.")
        print(e)

# Start polling to listen for messages
bot.polling()
