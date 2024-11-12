import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import random
import asyncio
from datetime import datetime, timedelta
import json
import os

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Replace with your bot token from BotFather
TOKEN = "7593027572:AAGKallf8NPo8JQESeh9nJwqbRiZvyHyTEo"

# Number of winners
WINNER_COUNT = 10

# Guaranteed winner's username
GUARANTEED_WINNER = "Leckone"

# File to store giveaway data
GIVEAWAY_FILE = 'giveaways.json'

# Store active giveaways
active_giveaways = {}

def save_giveaways():
    """Save giveaways to file"""
    save_data = {}
    for chat_id, giveaway in active_giveaways.items():
        save_data[str(chat_id)] = {
            'prize': giveaway['prize'],
            'end_time': giveaway['end_time'].isoformat(),
            'participants': list(giveaway['participants']),
            'started_by': giveaway['started_by']
        }
    
    with open(GIVEAWAY_FILE, 'w') as f:
        json.dump(save_data, f)

def load_giveaways():
    """Load giveaways from file"""
    if os.path.exists(GIVEAWAY_FILE):
        with open(GIVEAWAY_FILE, 'r') as f:
            save_data = json.load(f)
        
        for chat_id, giveaway in save_data.items():
            active_giveaways[int(chat_id)] = {
                'prize': giveaway['prize'],
                'end_time': datetime.fromisoformat(giveaway['end_time']),
                'participants': set(giveaway['participants']),
                'started_by': giveaway['started_by']
            }

async def start_giveaway(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start a giveaway with specified duration and prize"""
    chat_id = update.effective_chat.id
    
    if len(context.args) < 2:
        await update.message.reply_text('Usage: /giveaway <minutes> <prize>')
        return

    try:
        duration = int(context.args[0])
        prize = ' '.join(context.args[1:])
    except ValueError:
        await update.message.reply_text('Please provide a valid number of minutes.')
        return

    if chat_id in active_giveaways:
        await update.message.reply_text('There is already an active giveaway in this chat!')
        return

    end_time = datetime.now() + timedelta(minutes=duration)
    active_giveaways[chat_id] = {
        'prize': prize,
        'end_time': end_time,
        'participants': set(),
        'started_by': update.effective_user.id
    }

    # Save to file
    save_giveaways()

    await update.message.reply_text(
        f'🎉 Giveaway started!\n'
        f'Prize: {prize}\n'
        f'Duration: {duration} minutes\n'
        f'Winners: {WINNER_COUNT} people will win!\n'
        f'Type !cekilis to participate!'
    )

    # Schedule giveaway end
    async def end_giveaway():
        await asyncio.sleep(duration * 60)
        if chat_id in active_giveaways:
            await finish_giveaway(chat_id, context)

    asyncio.create_task(end_giveaway())

async def finish_giveaway(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """End the giveaway and select winners"""
    giveaway = active_giveaways.pop(chat_id, None)
    save_giveaways()
    
    if giveaway and giveaway['participants']:
        participants = list(giveaway['participants'])
        
        # Get all participants' info to find Leckone's ID
        guaranteed_winner_id = None
        other_participants = []
        
        for participant_id in participants:
            try:
                member = await context.bot.get_chat_member(chat_id, participant_id)
                if member.user.username == GUARANTEED_WINNER:
                    guaranteed_winner_id = participant_id
                else:
                    other_participants.append(participant_id)
            except Exception as e:
                logging.error(f"Error getting participant info: {e}")
                other_participants.append(participant_id)
        
        winner_ids = []
        winner_mentions = []
        
        # If Leckone participated, add them as a winner
        if guaranteed_winner_id is not None:
            winner_ids.append(guaranteed_winner_id)
            remaining_spots = WINNER_COUNT - 1
            # Select other winners
            if other_participants and remaining_spots > 0:
                additional_winners = random.sample(other_participants, min(remaining_spots, len(other_participants)))
                winner_ids.extend(additional_winners)
        else:
            # If Leckone didn't participate, select winners normally
            possible_winners = min(WINNER_COUNT, len(participants))
            winner_ids = random.sample(participants, possible_winners)
        
        # Get winner information
        for winner_id in winner_ids:
            try:
                winner = await context.bot.get_chat_member(chat_id, winner_id)
                winner_mention = f"@{winner.user.username}" if winner.user.username else winner.user.first_name
                winner_mentions.append(winner_mention)
            except Exception as e:
                logging.error(f"Error getting winner info: {e}")
                winner_mentions.append("Unknown User")

        # Randomize the order of winners to make it less obvious
        random.shuffle(winner_mentions)
        winners_text = "\n".join(f"🏆 {i+1}. {winner}" for i, winner in enumerate(winner_mentions))
        
        await context.bot.send_message(
            chat_id,
            f'🎊 Giveaway ended!\n'
            f'Prize: {giveaway["prize"]}\n\n'
            f'Winners:\n{winners_text}\n\n'
            f'Congratulations! 🎉'
        )
    else:
        await context.bot.send_message(
            chat_id,
            "Giveaway ended with no participants 😢"
        )

async def join_giveaway(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Join the active giveaway using !cekilis"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if chat_id not in active_giveaways:
        await update.message.reply_text('There is no active giveaway in this chat.')
        return

    giveaway = active_giveaways[chat_id]
    if user_id in giveaway['participants']:
        await update.message.reply_text('You have already joined this giveaway!')
        return

    giveaway['participants'].add(user_id)
    # Save updated participants
    save_giveaways()
    
    await update.message.reply_text('You have successfully joined the giveaway! 🎉')

async def giveaway_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check the status of the current giveaway"""
    chat_id = update.effective_chat.id

    if chat_id not in active_giveaways:
        await update.message.reply_text('There is no active giveaway in this chat.')
        return

    giveaway = active_giveaways[chat_id]
    time_left = giveaway['end_time'] - datetime.now()
    minutes_left = int(time_left.total_seconds() / 60)

    await update.message.reply_text(
        f'🎁 Current Giveaway Status:\n'
        f'Prize: {giveaway["prize"]}\n'
        f'Time remaining: {minutes_left} minutes\n'
        f'Participants: {len(giveaway["participants"])}\n'
        f'Number of winners: {WINNER_COUNT}'
    )

def main():
    """Start the bot"""
    # Load any saved giveaways
    load_giveaways()
    
    # Create the Application and pass it your bot's token
    application = Application.builder().token(TOKEN).build()

    # Only add giveaway-related commands
    application.add_handler(CommandHandler("giveaway", start_giveaway))
    application.add_handler(CommandHandler("status", giveaway_status))
    
    # Add !cekilis handler
    application.add_handler(MessageHandler(
        filters.Regex(r'^!cekilis$'), join_giveaway
    ))

    # Start the Bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()