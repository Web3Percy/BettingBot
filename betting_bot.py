import requests
from telegram import Bot
from telegram.ext import Application, CommandHandler, ContextTypes
from datetime import datetime, time

# ============================================================
# YOUR KEYS - Already filled in for you!
# ============================================================
TELEGRAM_TOKEN = "8607417189:AAHm8ZJyzfcBYADTB21HPV7Jviqmxz4Zc9c"
CHAT_ID = "5858052827"
ODDS_API_KEY = "cbdfc238862dc052b351de7a553aca44"

ODDS_API_BASE = "https://api.the-odds-api.com/v4"

# Sports to track
FOOTBALL_SPORTS = [
    "soccer_epl",                   # Premier League
    "soccer_spain_la_liga",         # La Liga
    "soccer_uefa_champs_league",    # Champions League
    "soccer_africa_cup_of_nations", # AFCON
]
NBA_SPORT = "basketball_nba"


# ============================================================
# CORE LOGIC - Finding Value Bets
# ============================================================

def get_odds(sport_key):
    """Fetch odds from The Odds API"""
    url = f"{ODDS_API_BASE}/sports/{sport_key}/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "uk,eu",
        "markets": "h2h",
        "oddsFormat": "decimal"
    }
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        print(f"Error fetching odds for {sport_key}: {e}")
        return []


def find_value_bets(games):
    """
    Value bet = when best available odds imply a lower probability
    than the market average. This means a bookmaker is offering
    better odds than the market consensus — that's your edge.
    """
    value_bets = []

    for game in games:
        if not game.get("bookmakers"):
            continue

        home_team = game["home_team"]
        away_team = game["away_team"]
        commence_time = game["commence_time"]

        home_odds_list = []
        away_odds_list = []
        draw_odds_list = []

        for bookmaker in game["bookmakers"]:
            for market in bookmaker["markets"]:
                if market["key"] == "h2h":
                    for outcome in market["outcomes"]:
                        if outcome["name"] == home_team:
                            home_odds_list.append(outcome["price"])
                        elif outcome["name"] == away_team:
                            away_odds_list.append(outcome["price"])
                        elif outcome["name"] == "Draw":
                            draw_odds_list.append(outcome["price"])

        if not home_odds_list or not away_odds_list:
            continue

        best_home = max(home_odds_list)
        best_away = max(away_odds_list)

        avg_home_prob = sum([1/o for o in home_odds_list]) / len(home_odds_list)
        avg_away_prob = sum([1/o for o in away_odds_list]) / len(away_odds_list)

        home_value = avg_home_prob - (1 / best_home)
        away_value = avg_away_prob - (1 / best_away)

        try:
            game_time = datetime.fromisoformat(commence_time.replace("Z", "+00:00"))
            game_time_str = game_time.strftime("%d %b %Y %H:%M UTC")
        except:
            game_time_str = commence_time

        # Threshold: 5% value edge minimum
        if home_value > 0.05:
            value_bets.append({
                "match": f"{home_team} vs {away_team}",
                "time": game_time_str,
                "pick": f"🏠 {home_team} to Win",
                "best_odds": best_home,
                "value": round(home_value * 100, 1),
                "confidence": "HIGH 🔥" if home_value > 0.10 else "MEDIUM ⚡"
            })

        if away_value > 0.05:
            value_bets.append({
                "match": f"{home_team} vs {away_team}",
                "time": game_time_str,
                "pick": f"✈️ {away_team} to Win",
                "best_odds": best_away,
                "value": round(away_value * 100, 1),
                "confidence": "HIGH 🔥" if away_value > 0.10 else "MEDIUM ⚡"
            })

    # Sort by value edge, highest first
    value_bets.sort(key=lambda x: x["value"], reverse=True)
    return value_bets


def format_message(value_bets, sport_name):
    """Format value bets into a clean Telegram message"""
    if not value_bets:
        return f"*{sport_name}*\nNo value bets found right now\\. Check back later\\!\n\n"

    msg = f"*{sport_name} — Value Bets*\n"
    msg += "━━━━━━━━━━━━━━━━━━━━\n\n"

    for i, bet in enumerate(value_bets[:5], 1):
        msg += f"*Bet {i}* — {bet['confidence']}\n"
        msg += f"🆚 {bet['match']}\n"
        msg += f"🕐 {bet['time']}\n"
        msg += f"✅ Pick: {bet['pick']}\n"
        msg += f"💰 Best Odds: {bet['best_odds']}\n"
        msg += f"📈 Value Edge: {bet['value']}%\n\n"

    return msg


async def run_full_analysis(bot):
    """Run full analysis and send results to Telegram"""
    header = (
        "🤖 *DAILY BETTING ANALYSIS*\n"
        f"📅 {datetime.now().strftime('%d %B %Y')}\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "⚠️ _Bet responsibly\\. Max 5% bankroll per bet\\._\n\n"
    )

    # Football
    football_bets = []
    for sport in FOOTBALL_SPORTS:
        games = get_odds(sport)
        football_bets.extend(find_value_bets(games))
    football_bets.sort(key=lambda x: x["value"], reverse=True)

    # NBA
    nba_games = get_odds(NBA_SPORT)
    nba_bets = find_value_bets(nba_games)

    footer = (
        "\n💡 *Quick Rules:*\n"
        "• HIGH confidence = strong bet\n"
        "• Value edge > 10% = best bets\n"
        "• Never chase losses\n"
        "• Max 3 bets per day"
    )

    full_message = (
        header
        + format_message(football_bets, "⚽ FOOTBALL")
        + format_message(nba_bets, "🏀 NBA")
        + footer
    )

    await bot.send_message(
        chat_id=CHAT_ID,
        text=full_message,
        parse_mode="MarkdownV2"
    )


# ============================================================
# TELEGRAM COMMANDS
# ============================================================

async def start_command(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Sports Betting Analysis Bot*\n\n"
        "Welcome\\! Here are your commands:\n\n"
        "/analysis \\- Full daily analysis \\(Football \\+ NBA\\)\n"
        "/football \\- Football value bets only\n"
        "/nba \\- NBA value bets only\n"
        "/help \\- Show this menu\n\n"
        "_Bot sends you daily analysis at 8AM automatically\\._",
        parse_mode="MarkdownV2"
    )


async def analysis_command(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Analyzing markets\\.\\.\\. please wait\\!", parse_mode="MarkdownV2")
    await run_full_analysis(context.bot)


async def football_command(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚽ Fetching football value bets\\.\\.\\.", parse_mode="MarkdownV2")
    football_bets = []
    for sport in FOOTBALL_SPORTS:
        games = get_odds(sport)
        football_bets.extend(find_value_bets(games))
    football_bets.sort(key=lambda x: x["value"], reverse=True)
    message = "⚽ *FOOTBALL VALUE BETS*\n━━━━━━━━━━━━━━━━━━━━\n\n" + format_message(football_bets, "⚽ FOOTBALL")
    await update.message.reply_text(message, parse_mode="MarkdownV2")


async def nba_command(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏀 Fetching NBA value bets\\.\\.\\.", parse_mode="MarkdownV2")
    nba_games = get_odds(NBA_SPORT)
    nba_bets = find_value_bets(nba_games)
    message = "🏀 *NBA VALUE BETS*\n━━━━━━━━━━━━━━━━━━━━\n\n" + format_message(nba_bets, "🏀 NBA")
    await update.message.reply_text(message, parse_mode="MarkdownV2")


async def scheduled_daily(context: ContextTypes.DEFAULT_TYPE):
    """Runs automatically every day at 8AM"""
    await run_full_analysis(context.bot)


# ============================================================
# RUN THE BOT
# ============================================================

def main():
    print("🤖 Betting Bot starting...")
    from telegram.request import HTTPXRequest
request = HTTPXRequest(connect_timeout=60, read_timeout=60)
app = Application.builder().token(TELEGRAM_TOKEN).request(request).build()

    # Register commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", start_command))
    app.add_handler(CommandHandler("analysis", analysis_command))
    app.add_handler(CommandHandler("football", football_command))
    app.add_handler(CommandHandler("nba", nba_command))

    # Schedule daily analysis at 8:00 AM
    app.job_queue.run_daily(
        scheduled_daily,
        time=time(hour=8, minute=0),
        days=(0, 1, 2, 3, 4, 5, 6)
    )

    print("✅ Bot is live! Open Telegram and message your bot.")
    app.run_polling()


if __name__ == "__main__":
    main()