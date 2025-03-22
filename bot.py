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
WINNER_COUNT = 20
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
        f'BetTicket Özel Çekilişimiz Başladı!\n'
        f'Ödül 20 kişiye 500\'er TL\n'
        f'Süre: {days} gün\n'
        f'Bitiş: {end_time.strftime("%d.%m.%Y %H:%M")}\n'
        f'Katılmak için !betticketcekilis yazın!'
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
        
        # If we have fewer participants than winners, adjust
        possible_winners = min(WINNER_COUNT, len(participants))
        
        # Select random winners
        winner_ids = random.sample(participants, possible_winners)
        winner_mentions = []
        
        for winner_id in winner_ids:
            try:
                winner = await context.bot.get_chat_member(chat_id, winner_id)
                winner_mention = f"@{winner.user.username}" if winner.user.username else winner.user.first_name
                winner_mentions.append(winner_mention)
            except Exception as e:
                logging.error(f"Error getting winner info: {e}")
                winner_mentions.append("Unknown User")

        winners_text = "\n".join(f"🏆 {i+1}. {winner} - 500TL" for i, winner in enumerate(winner_mentions))
        
        await context.bot.send_message(
            chat_id,
            f'🎊 Çekiliş sona erdi!\n'
            f'Kişi başı ödül: 500TL\n'
            f'Toplam ödül: {len(winner_mentions) * 500}TL\n\n'
            f'Kazananlar:\n{winners_text}\n\n'
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
    
    await update.message.reply_text('BetTicket x JUGADOR BEY Çekilişine başarıyla katıldınız. Bol şanslar!')

async def giveaway_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id not in active_giveaways:
        await update.message.reply_text('Şu anda aktif bir çekiliş bulunmuyor.')
        return

    giveaway = active_giveaways[chat_id]
    time_left = giveaway['end_time'] - datetime.now()
    days_left = int(time_left.total_seconds() / (24 * 60 * 60))

    await update.message.reply_text(
        f'🎁 Çekiliş Durumu:\n'
        f'Ödül: Kişi başı 500TL\n'
        f'Kalan süre: {days_left} gün\n'
        f'Katılımcı sayısı: {len(giveaway["participants"])}\n'
        f'Kazanan sayısı: {WINNER_COUNT}\n'
        f'Toplam ödül: {WINNER_COUNT * 500}TL'
    )

async def last_winner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the last giveaway winners"""
    logger.info("Last winner command received")
    try:
        await update.message.reply_text("""14 ŞUBAT SEVGİLİLER GÜNÜ ÇEKİLİŞİ KAZANANLARI (200'ER TL)
1. @Vazoltoptan
2. @desert121315
3. @TcloozY74
4. @SongllA
5. Furkan Şahin
6. Poyraz
7. @Ramoxn7
8. @gunduzyunus
9. @andres5151
10. @ozcan4610""")
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
!betticketcekilis - Aktif çekilişe katıl
"""
    await update.message.reply_text(help_text)

def main():
    logger.info("Starting bot...")
    
    # Load saved giveaways
    load_giveaways()
    
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
        filters.Regex(r'^!betticketcekilis$'), join_giveaway
    ))

    logger.info("Bot is ready!")
    
    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()