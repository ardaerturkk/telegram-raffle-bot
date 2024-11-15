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

TOKEN = "7593027572:AAGKallf8NPo8JQESeh9nJwqbRiZvyHyTEo"
WINNER_COUNT = 16
FIRST_WINNER = "albayimrecel21"
GUARANTEED_WINNERS = ["hidrojoe", "og1331x"]
GIVEAWAY_FILE = 'giveaways.json'
active_giveaways = {}

def save_giveaways():
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
    chat_id = update.effective_chat.id
    
    if len(context.args) < 2:
        await update.message.reply_text('Usage: /giveaway <days> <prize>')
        return

    try:
        days = int(context.args[0])
        prize = ' '.join(context.args[1:])
    except ValueError:
        await update.message.reply_text('Please provide a valid number of days.')
        return

    if chat_id in active_giveaways:
        await update.message.reply_text('There is already an active giveaway in this chat!')
        return

    end_time = datetime.now() + timedelta(days=days)
    active_giveaways[chat_id] = {
        'prize': prize,
        'end_time': end_time,
        'participants': set(),
        'started_by': update.effective_user.id
    }

    save_giveaways()

    await update.message.reply_text(
        f'🎉 Giveaway started!\n'
        f'Prize: {prize}\n'
        f'Duration: {days} days\n'
        f'Winners: {WINNER_COUNT} people will win!\n'
        f'Type !instacekilis to participate!'
    )

    async def end_giveaway():
        await asyncio.sleep(days * 24 * 60 * 60)
        if chat_id in active_giveaways:
            await finish_giveaway(chat_id, context)

    asyncio.create_task(end_giveaway())

async def finish_giveaway(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    giveaway = active_giveaways.pop(chat_id, None)
    save_giveaways()
    
    if giveaway and giveaway['participants']:
        participants = list(giveaway['participants'])
        
        first_winner_id = None
        guaranteed_winner_ids = []
        other_participants = []
        
        # First, find our guaranteed winners
        for participant_id in participants:
            try:
                member = await context.bot.get_chat_member(chat_id, participant_id)
                if member.user.username == FIRST_WINNER:
                    first_winner_id = participant_id
                elif member.user.username in GUARANTEED_WINNERS:
                    guaranteed_winner_ids.append(participant_id)
                else:
                    other_participants.append(participant_id)
            except Exception as e:
                logging.error(f"Error getting participant info: {e}")
                other_participants.append(participant_id)
        
        winner_mentions = []
        
        # Add first winner if participated
        if first_winner_id is not None:
            try:
                winner = await context.bot.get_chat_member(chat_id, first_winner_id)
                winner_mentions.append(f"@{winner.user.username}")
            except Exception as e:
                logging.error(f"Error getting first winner info: {e}")

        # Add other guaranteed winners if participated
        for winner_id in guaranteed_winner_ids:
            try:
                winner = await context.bot.get_chat_member(chat_id, winner_id)
                winner_mentions.append(f"@{winner.user.username}")
            except Exception as e:
                logging.error(f"Error getting guaranteed winner info: {e}")

        # Calculate remaining spots
        remaining_spots = WINNER_COUNT - len(winner_mentions)
        
        # Select remaining winners
        if other_participants and remaining_spots > 0:
            additional_winners = random.sample(other_participants, min(remaining_spots, len(other_participants)))
            for winner_id in additional_winners:
                try:
                    winner = await context.bot.get_chat_member(chat_id, winner_id)
                    winner_mention = f"@{winner.user.username}" if winner.user.username else winner.user.first_name
                    winner_mentions.append(winner_mention)
                except Exception as e:
                    logging.error(f"Error getting winner info: {e}")
                    winner_mentions.append("Unknown User")

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
    save_giveaways()
    
    await update.message.reply_text('You have successfully joined the giveaway! 🎉')

async def giveaway_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id not in active_giveaways:
        await update.message.reply_text('There is no active giveaway in this chat.')
        return

    giveaway = active_giveaways[chat_id]
    time_left = giveaway['end_time'] - datetime.now()
    days_left = int(time_left.total_seconds() / (24 * 60 * 60))

    await update.message.reply_text(
        f'🎁 Current Giveaway Status:\n'
        f'Prize: {giveaway["prize"]}\n'
        f'Time remaining: {days_left} days\n'
        f'Participants: {len(giveaway["participants"])}\n'
        f'Number of winners: {WINNER_COUNT}'
    )

def main():
    load_giveaways()
    
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("giveaway", start_giveaway))
    application.add_handler(CommandHandler("status", giveaway_status))
    
    application.add_handler(MessageHandler(
        filters.Regex(r'^!instacekilis$'), join_giveaway
    ))

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
