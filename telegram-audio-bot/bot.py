import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, MessageHandler, CommandHandler,
    CallbackQueryHandler, ContextTypes, filters
)

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Manca BOT_TOKEN (variabile d'ambiente).")

conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), "tracks.db"), check_same_thread=False)
cur = conn.cursor()

def get_base_buttons():
    return [
        [
            InlineKeyboardButton("📜 Comandi", callback_data="help_cmd"),
            InlineKeyboardButton("❤️ Preferiti", callback_data="show_favs")
        ],
        [
            InlineKeyboardButton("Condividi 🚀", url="https://t.me/share/url?url=https://t.me/musicfr44bot&text=Ascolta%20e%20scarica%20musica%20con%20questo%20bot!%20🎶")
        ]
    ]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup(get_base_buttons())
    sent_message = await update.message.reply_text(
        "🎧 **BENVENUTO SU MUSIC BOT** 👽🧚‍♂️\n"
        "Ascolta e scarica la tua musica preferita direttamente da Telegram.\n\n"
        "🔍 **Come funziona**\n"
        "Scrivi il **nome della canzone**\n"
        "Premi **Invio**\n"
        "Goditi la tua musica 🎶\n\n"
        "📜 **Comandi disponibili**\n"
        "🎵 **/search** – Cerca una canzone\n"
        "➕ **/add** – Aggiungi una nuova canzone al database\n"
        "📊 **/list** – Visualizza la Top List\n"
        "❤️ **/preferiti** – Le tue canzoni preferite\n\n"
        "Se non trovi una traccia, puoi **richiederla** con /request o **caricarla tu stesso** con /add!",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    
    # Pinna il messaggio per creare una "cartella" / dashboard persistente
    try:
        await context.bot.pin_chat_message(chat_id=update.effective_chat.id, message_id=sent_message.message_id)
    except Exception:
        # Potrebbe fallire se il bot non è admin o se è una chat privata senza permessi (raro in private)
        pass

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup(get_base_buttons())
    await update.message.reply_text(
        "📜 **Comandi disponibili:**\n\n"
        "🎵 **/search** – Cerca una canzone\n"
        "➕ **/add** – Aggiungi una nuova canzone\n"
        "📊 **/list** – Visualizza la Top List\n"
        "❤️ **/preferiti** – Le tue canzoni preferite\n\n"
        "Oppure scrivi direttamente il **nome della canzone** nella chat.",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

async def add_track_instruction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup(get_base_buttons())
    await update.message.reply_text(
        "➕ **Aggiungi una nuova canzone**\n\n"
        "1. Trascina il file audio qui in chat.\n"
        "2. Il bot proverà a leggere automaticamente **Artista** e **Titolo** dai metadati.\n"
        "3. Se il file non ha metadati, aggiungi tu una didascalia: `Artista - Titolo`.",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

async def list_tracks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_tracks_page(update, page=0)

async def show_tracks_page(update_or_query, page=0):
    PAGE_SIZE = 5
    offset = page * PAGE_SIZE
    
    cur.execute("SELECT COUNT(*) FROM tracks")
    row = cur.fetchone()
    total_tracks = row[0] if row else 0
    total_pages = (total_tracks + PAGE_SIZE - 1) // PAGE_SIZE
    
    cur.execute("SELECT id, title FROM tracks ORDER BY title LIMIT ? OFFSET ?", (PAGE_SIZE, offset))
    tracks = cur.fetchall()
    
    if not tracks:
        text = "📭 Database vuoto."
        if isinstance(update_or_query, Update):
             await update_or_query.message.reply_text(text)
        else:
             await update_or_query.answer(text, show_alert=True)
        return

    # Crea bottoni per ogni traccia
    keyboard = []
    for track_id, title in tracks:
        keyboard.append([
            InlineKeyboardButton(f"▶️ {title}", callback_data=f"play_{track_id}"),
            InlineKeyboardButton("❤️", callback_data=f"fav_{track_id}")
        ])

    # Navigazione
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Indietro", callback_data=f"list_page_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Avanti ➡️", callback_data=f"list_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
        
    # Bottoni base
    keyboard.extend(get_base_buttons())

    text = f"🎹 **Libreria Musicale** (Pagina {page+1}/{total_pages})\n\n🎧 *Scegli una traccia da ascoltare:*"
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if isinstance(update_or_query, Update):
        await update_or_query.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update_or_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args)
    if not query:
        keyboard = InlineKeyboardMarkup(get_base_buttons())
        await update.message.reply_text("✏️ Scrivi il nome della canzone che stai cercando e premi Invio", parse_mode="Markdown", reply_markup=keyboard)
        return

    # Riutilizza la logica di ricerca
    await perform_search(update, query)

async def search_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if not text:
        return
    await perform_search(update, text)

async def perform_search(update: Update, query):
    cur.execute(
        "SELECT id, title, file_id FROM tracks WHERE lower(title) LIKE ?",
        (f"%{query.lower()}%",)
    )
    results = cur.fetchall()

    if not results:
        await update.message.reply_text(
            "❌ Nessuna canzone trovata\n"
            "Puoi richiederla o aggiungerla con il comando **/add**",
            parse_mode="Markdown"
        )
        return

    for track_id, title, file_id in results:
        keyboard_list = [
            [InlineKeyboardButton("❤️ Preferiti", callback_data=f"fav_{track_id}")]
        ] + get_base_buttons()
        keyboard = InlineKeyboardMarkup(keyboard_list)
        await update.message.reply_audio(audio=file_id, caption=title, reply_markup=keyboard)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() # Ferma l'animazione di caricamento

    data = query.data
    
    if data.startswith("fav_"):
        user_id = query.from_user.id
        track_id = int(data.split("_", 1)[1])

        try:
            cur.execute(
                "INSERT INTO favorites (user_id, track_id) VALUES (?, ?)",
                (user_id, track_id)
            )
            conn.commit()
            await query.answer("❤️ Canzone aggiunta ai preferiti!", show_alert=True)
        except sqlite3.IntegrityError:
            await query.answer("⚠️ Già nei preferiti", show_alert=True)
            
    elif data == "help_cmd":
        text = (
            "📜 **Comandi disponibili:**\n\n"
            "🎵 **/search** – Cerca una canzone\n"
            "➕ **/add** – Aggiungi una nuova canzone\n"
            "📊 **/list** – Visualizza la Top List\n"
            "❤️ **/preferiti** – Le tue canzoni preferite\n\n"
            "Oppure scrivi direttamente il **nome della canzone** nella chat."
        )
        keyboard = InlineKeyboardMarkup(get_base_buttons())
        await query.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)

    elif data == "show_favs":
        user_id = query.from_user.id
        await show_favorites_page(query, user_id, page=0)

    elif data.startswith("play_"):
        track_id = int(data.split("_", 1)[1])
        
        cur.execute("SELECT title, file_id FROM tracks WHERE id = ?", (track_id,))
        result = cur.fetchone()
        
        if result:
            title, file_id = result
            # Permetti di aggiungere ai preferiti anche da qui
            keyboard_list = [
                [InlineKeyboardButton("❤️ Preferiti", callback_data=f"fav_{track_id}")]
            ] + get_base_buttons()
            keyboard = InlineKeyboardMarkup(keyboard_list)
            await query.message.reply_audio(audio=file_id, caption=title, reply_markup=keyboard)
        else:
            await query.answer("❌ Traccia non trovata (potrebbe essere stata rimossa).", show_alert=True)

    elif data.startswith("list_page_"):
        page = int(data.split("_")[-1])
        await show_tracks_page(query, page=page)

    elif data.startswith("fav_page_"):
        page = int(data.split("_")[-1])
        user_id = query.from_user.id
        await show_favorites_page(query, user_id, page=page)

async def show_favorites(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    await show_favorites_page(update, user_id, page=0)

async def show_favorites_page(update_or_query, user_id, page=0):
    PAGE_SIZE = 5
    offset = page * PAGE_SIZE
    
    # Count total favorites
    cur.execute("SELECT COUNT(*) FROM favorites WHERE user_id = ?", (user_id,))
    total_tracks = cur.fetchone()[0]
    total_pages = (total_tracks + PAGE_SIZE - 1) // PAGE_SIZE
    
    cur.execute("""
        SELECT tracks.id, tracks.title 
        FROM tracks 
        JOIN favorites ON tracks.id = favorites.track_id 
        WHERE favorites.user_id = ? 
        ORDER BY tracks.title 
        LIMIT ? OFFSET ?
    """, (user_id, PAGE_SIZE, offset))
    tracks = cur.fetchall()
    
    if not tracks and page == 0:
        text = "📭 **Non hai ancora canzoni nei preferiti.**\nUsa il tasto ❤️ quando ascolti una canzone per aggiungerla qui!"
        if isinstance(update_or_query, Update):
             await update_or_query.message.reply_text(text, parse_mode="Markdown")
        else:
             await update_or_query.edit_message_text(text, parse_mode="Markdown")
        return

    # Create buttons
    keyboard = []
    for track_id, title in tracks:
        keyboard.append([
            InlineKeyboardButton(f"💿 {title}", callback_data=f"play_{track_id}"),
            InlineKeyboardButton("💔", callback_data=f"unfav_{track_id}")
        ])

    # Navigation buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Indietro", callback_data=f"fav_page_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Avanti ➡️", callback_data=f"fav_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)

    # Aggiungi bottoni base (Comandi, Condividi)
    keyboard.extend(get_base_buttons())

    text = f"❤️ **I tuoi Preferiti** (Pagina {page+1}/{total_pages})\n\n🎧 *Scegli una traccia da ascoltare:*"

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if isinstance(update_or_query, Update):
        await update_or_query.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update_or_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def request_track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    # Supporta sia /richiedi che /request
    text = (update.message.text or "").replace("/richiedi", "").replace("/request", "").strip()

    if not text:
        await update.message.reply_text("⚠️ Scrivi il titolo della traccia dopo il comando.\nEsempio: `/request Nome Canzone`", parse_mode="Markdown")
        return

    cur.execute(
        "INSERT INTO requests (user_id, username, request_text) VALUES (?, ?, ?)",
        (user.id, user.username or user.first_name, text)
    )
    conn.commit()

    keyboard = InlineKeyboardMarkup(get_base_buttons())
    await update.message.reply_text(f"✅ Richiesta inviata: *{text}*\nL'admin la valuterà presto!", parse_mode="Markdown", reply_markup=keyboard)

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.audio:
        audio = update.message.audio
        file_id = audio.file_id
        
        # 1. Prova a prendere i metadati dal file audio
        performer = audio.performer
        title = audio.title
        
        track_name = None
        
        if performer and title:
            track_name = f"{performer} - {title}"
        elif title:
            track_name = title
        
        # 2. Se i metadati mancano, controlla la didascalia (caption)
        if not track_name:
            caption = (update.message.caption or "").strip()
            if caption:
                track_name = caption
        
        # 3. Se ancora non abbiamo un nome, usa il nome del file
        if not track_name and audio.file_name:
             track_name = audio.file_name.rsplit('.', 1)[0] # Rimuove l'estensione

        # Se abbiamo trovato un nome, salviamo
        if track_name:
            try:
                # Controllo duplicati (opzionale ma utile)
                cur.execute("SELECT id FROM tracks WHERE file_id = ?", (file_id,))
                if cur.fetchone():
                     await update.message.reply_text(f"⚠️ Questa traccia è già nel database: **{track_name}**", parse_mode="Markdown")
                     return

                cur.execute("INSERT INTO tracks (title, file_id) VALUES (?, ?)", (track_name, file_id))
                conn.commit()
                keyboard = InlineKeyboardMarkup(get_base_buttons())
                await update.message.reply_text(f"✅ Traccia aggiunta automaticamente:\n**{track_name}**", parse_mode="Markdown", reply_markup=keyboard)
            except Exception as e:
                keyboard = InlineKeyboardMarkup(get_base_buttons())
                await update.message.reply_text(f"❌ Errore durante il salvataggio: {e}", reply_markup=keyboard)
        else:
             await update.message.reply_text(
                "⚠️ **Impossibile rilevare il nome della traccia!**\n\n"
                "Il file non ha metadati (Artista/Titolo) e non hai scritto una didascalia.\n"
                "Riprova inviando il file con una didascalia: `Artista - Titolo`",
                parse_mode="Markdown"
            )

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Comandi
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("add", add_track_instruction))
    app.add_handler(CommandHandler("list", list_tracks))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("preferiti", show_favorites))
    app.add_handler(CommandHandler(["richiedi", "request"], request_track))
    
    # Handler Messaggi
    app.add_handler(MessageHandler(filters.AUDIO, handle_audio))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_text))
    
    # Callback Query (bottoni) - Aggiornato per gestire play_ e fav_
    app.add_handler(CallbackQueryHandler(button_handler))
    
    app.run_polling()

if __name__ == "__main__":
    main()

