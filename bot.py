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

logger = logging.getLogger(__name__)

TOKEN = "7593027572:AAGKallf8NPo8JQESeh9nJwqbRiZvyHyTEo"
WINNER_COUNT = 6  # Changed to 6 winners total
GUARANTEED_WINNER = "albayimrecel21"  # One fixed winner for 1st place
MINIMUM_MESSAGE_COUNT = 20  # Hidden requirement: 20 messages
GIVEAWAY_FILE = 'giveaways.json'
MESSAGE_COUNT_FILE = 'message_counts.json'
active_giveaways = {}
message_counts = {}

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

def save_message_counts():
    """Save message counts to file"""
    with open(MESSAGE_COUNT_FILE, 'w') as f:
        # Convert user IDs from int to str for JSON serialization
        json_data = {str(chat_id): {str(user_id): count for user_id, count in users.items()} 
                    for chat_id, users in message_counts.items()}
        json.dump(json_data, f)

def load_message_counts():
    """Load message counts from file"""
    global message_counts
    if os.path.exists(MESSAGE_COUNT_FILE):
        with open(MESSAGE_COUNT_FILE, 'r') as f:
            json_data = json.load(f)
            # Convert user IDs back from str to int
            message_counts = {int(chat_id): {int(user_id): count for user_id, count in users.items()} 
                             for chat_id, users in json_data.items()}
    else:
        message_counts = {}

async def start_giveaway(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    if len(context.args) < 2:
        await update.message.reply_text('Kullanım: /giveaway <gün> <ödül>')
        return

    try:
        days = int(context.args[0])
        prize = ' '.join(context.args[1:])
    except ValueError:
        await update.message.reply_text('Lütfen geçerli bir gün sayısı girin.')
        return

    if chat_id in active_giveaways:
        await update.message.reply_text('Zaten aktif bir çekiliş var!')
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
        f'Jugador Bey 15.000 TL Nakit Çekilişi Başladı!\n'
        f'İLK 1 KİŞİ 5.000 TL\n'
        f'5 KİŞİ 2000\'ER TL\n'
        f'Süre: {days} gün\n'
        f'Bitiş: {end_time.strftime("%d.%m.%Y %H:%M")}\n'
        f'Katılmak için !nakitcekilis yazın!'
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
        
        # Get eligible participants (those with enough messages)
        eligible_participants = []
        ineligible_participants = []
        
        for participant_id in participants:
            if chat_id in message_counts and participant_id in message_counts[chat_id]:
                msg_count = message_counts[chat_id][participant_id]
                if msg_count >= MINIMUM_MESSAGE_COUNT:
                    eligible_participants.append(participant_id)
                else:
                    ineligible_participants.append(participant_id)
            else:
                ineligible_participants.append(participant_id)
        
        # Log statistics about eligibility
        logger.info(f"Total participants: {len(participants)}")
        logger.info(f"Eligible participants: {len(eligible_participants)}")
        logger.info(f"Ineligible participants: {len(ineligible_participants)}")
        
        # Find guaranteed winner and other participants
        guaranteed_winner_id = None
        other_participants = []
        
        for participant_id in eligible_participants:
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
        
        # Add the guaranteed winner first if they participated and are eligible
        if guaranteed_winner_id is not None:
            winner_ids.append(guaranteed_winner_id)
        
        # Calculate remaining spots
        remaining_spots = WINNER_COUNT - len(winner_ids)
        
        # Select remaining winners from eligible participants
        if other_participants and remaining_spots > 0:
            additional_winners = random.sample(other_participants, min(remaining_spots, len(other_participants)))
            winner_ids.extend(additional_winners)
        
        # Get winner information
        winner_mentions = []
        for winner_id in winner_ids:
            try:
                winner = await context.bot.get_chat_member(chat_id, winner_id)
                winner_mention = f"@{winner.user.username}" if winner.user.username else winner.user.first_name
                winner_mentions.append(winner_mention)
            except Exception as e:
                logging.error(f"Error getting winner info: {e}")
                winner_mentions.append("Unknown User")
        
        # Create winners text with different prize amounts
        winners_text = ""
        total_prize = 0
        
        for i, winner in enumerate(winner_mentions):
            if i == 0:
                # First winner gets 5000 TL
                winners_text += f"🏆 {i+1}. {winner} - 5000 TL\n"
                total_prize += 5000
            else:
                # Remaining winners get 2000 TL
                winners_text += f"🏆 {i+1}. {winner} - 2000 TL\n"
                total_prize += 2000
        
        await context.bot.send_message(
            chat_id,
            f'🎊 Çekiliş sona erdi!\n'
            f'İLK 1 KİŞİ 5.000 TL\n'
            f'5 KİŞİ 2000\'ER TL\n'
            f'Toplam ödül: {total_prize} TL\n\n'
            f'Kazananlar:\n{winners_text}\n'
            f'Tebrikler! 🎉'
        )
    else:
        await context.bot.send_message(
            chat_id,
            "Çekiliş sona erdi ama hiç katılımcı yoktu 😢"
        )

async def join_giveaway(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if chat_id not in active_giveaways:
        await update.message.reply_text('Şu anda aktif bir çekiliş bulunmuyor.')
        return

    giveaway = active_giveaways[chat_id]
    if user_id in giveaway['participants']:
        await update.message.reply_text('Zaten bu çekilişe katıldınız.')
        return

    giveaway['participants'].add(user_id)
    save_giveaways()
    
    await update.message.reply_text('Jugador Bey 15.000 TL Nakit Çekilişine başarıyla katıldınız. Bol şanslar!')

async def giveaway_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id not in active_giveaways:
        await update.message.reply_text('Şu anda aktif bir çekiliş bulunmuyor.')
        return

    giveaway = active_giveaways[chat_id]
    time_left = giveaway['end_time'] - datetime.now()
    days_left = int(time_left.total_seconds() / (24 * 60 * 60))

    total_prize = 5000 + 5 * 2000  # 1 winner at 5000 TL + 5 winners at 2000 TL
    
    await update.message.reply_text(
        f'🎁 Çekiliş Durumu:\n'
        f'İLK 1 KİŞİ 5.000 TL\n'
        f'5 KİŞİ 2000\'ER TL\n'
        f'Kalan süre: {days_left} gün\n'
        f'Katılımcı sayısı: {len(giveaway["participants"])}\n'
        f'Kazanan sayısı: {WINNER_COUNT}\n'
        f'Toplam ödül: {total_prize} TL'
    )

async def last_winner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the last giveaway winners"""
    logger.info("Last winner command received")
    try:
        await update.message.reply_text("""Jugador Bey Nakit Çekilişi Kazananları: 
1. @SongllA
2. @ozgurt1
3. @hanife3509
4. Burcu
5. @gunduzyunus
6. @admkaya""")
        logger.info("Last winner message sent successfully")
    except Exception as e:
        logger.error(f"Error in last_winner command: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /start command"""
    await update.message.reply_text("Bot çalışıyor! Komutları görmek için /help yazın.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /help command"""
    help_text = """
Mevcut komutlar:
/giveaway <gün> <ödül> - Yeni çekiliş başlat
/status - Çekiliş durumunu kontrol et
/lastwinner - Son çekiliş kazananlarını gör
!nakitcekilis - Aktif çekilişe katıl
"""
    await update.message.reply_text(help_text)

async def count_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Count messages for each user"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Initialize chat if not exists
    if chat_id not in message_counts:
        message_counts[chat_id] = {}
    
    # Initialize user if not exists
    if user_id not in message_counts[chat_id]:
        message_counts[chat_id][user_id] = 0
    
    # Increment message count
    message_counts[chat_id][user_id] += 1
    
    # Save periodically (every 10 messages)
    if message_counts[chat_id][user_id] % 10 == 0:
        save_message_counts()

def main():
    logger.info("Starting bot...")
    
    # Load saved data
    load_giveaways()
    load_message_counts()
    
    # Create application
    application = Application.builder().token(TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("giveaway", start_giveaway))
    application.add_handler(CommandHandler("status", giveaway_status))
    application.add_handler(CommandHandler("lastwinner", last_winner))
    
    # Add message handlers
    application.add_handler(MessageHandler(
        filters.Regex(r'^!nakitcekilis$'), join_giveaway
    ))
    
    # Add message counter (must be last to catch all messages)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, count_message
    ))

    logger.info("Bot is ready!")
    
    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
