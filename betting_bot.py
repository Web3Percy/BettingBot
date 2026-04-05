import requests
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.request import HTTPXRequest
from datetime import datetime, time

# ============================================================
# YOUR KEYS
# ============================================================
TELEGRAM_TOKEN = "8607417189:AAHm8ZJyzfcBYADTB21HPV7JviqmxZ4Zc9o"
CHAT_ID = "5858052827"
ODDS_API_KEY = "cbdfc238862dc052b351de7a553aca44"

ODDS_API_BASE = "https://api.the-odds-api.com/v4"

FOOTBALL_SPORTS = [
    "soccer_epl",
    "soccer_spain_la_liga",
    "soccer_uefa_champs_league",
]
NBA_SPORT = "basketball_nba"


def get_odds(sport_key):
    url = f"{ODDS_API_BASE}/sports/{sport_key}/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "uk,eu",
        "markets": "h2h",
        "oddsFormat": "decimal"
    }
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        print(f"Error: {e}")
        return []


def find_value_bets(games):
    value_bets = []
    for game in games:
        if not game.get("bookmakers"):
            continue
        home_team = game["home_team"]
        away_team = game["away_team"]
        commence_time = game["commence_time"]
        home_odds_list = []
        away_odds_list = []
        for bookmaker in game["bookmakers"]:
            for market in bookmaker["markets"]:
                if market["key"] == "h2h":
                    for outcome in market["outcomes"]:
                        if outcome["name"] == home_team:
                            home_odds_list.append(outcome["price"])
                        elif outcome["name"] == away_team:
                            away_odds_list.append(outcome["price"])
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
        if home_value > 0.05:
            value_bets.append({
                "match": f"{home_team} vs {away_team}",
                "time": game_time_str,
                "pick": f"{home_team} to Win",
                "best_odds": best_home,
                "value": round(home_value * 100, 1),
                "confidence": "HIGH" if home_value > 0.10 else "MEDIUM"
            })
        if away_value > 0.05:
            value_bets.append({
                "match": f"{home_team} vs {away_team}",
                "time": game_time_str,
                "pick": f"{away_team} to Win",
                "best_odds": best_away,
                "value": round(away_value * 100, 1),
                "confidence": "HIGH" if away_value > 0.10 else "MEDIUM"
            })
    value_bets.sort(key=lambda x: x["value"], reverse=True)
    return value_bets


def format_message(value_bets, sport_name):
    if not value_bets:
        return f"{sport_name}: No value bets right now. Check back later!\n\n"
    msg = f"{sport_name} VALUE BETS\n"
    msg += "=" * 25 + "\n\n"
    for i, bet in enumerate(value_bets[:5], 1):
        emoji = "🔥" if bet["confidence"] == "HIGH" else "⚡"
        msg += f"{emoji} Bet {i} - {bet['confidence']}\n"
        msg += f"Match: {bet['match']}\n"
        msg += f"Time: {bet['time']}\n"
        msg += f"Pick: {bet['pick']}\n"
        msg += f"Best Odds: {bet['best_odds']}\n"
        msg += f"Value Edge: {bet['value']}%\n\n"
    return msg


async def start_command(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Sports Betting Bot\n\n"
        "/analysis - Full daily analysis\n"
        "/football - Football bets only\n"
        "/nba - NBA bets only\n"
        "/help - Show this menu"
    )


async def analysis_command(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Analyzing markets... please wait!")
    football_bets = []
    for sport in FOOTBALL_SPORTS:
        games = get_odds(sport)
        football_bets.extend(find_value_bets(games))
    football_bets.sort(key=lambda x: x["value"], reverse=True)
    nba_games = get_odds(NBA_SPORT)
    nba_bets = find_value_bets(nba_games)
    header = f"DAILY ANALYSIS - {datetime.now().strftime('%d %B %Y')}\n\n"
    footer = "\nRules: Max 5% bankroll per bet. Never chase losses."
    full_message = header + format_message(football_bets, "FOOTBALL") + format_message(nba_bets, "NBA") + footer
    await update.message.reply_text(full_message)


async def football_command(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Fetching football bets...")
    football_bets = []
    for sport in FOOTBALL_SPORTS:
        games = get_odds(sport)
        football_bets.extend(find_value_bets(games))
    football_bets.sort(key=lambda x: x["value"], reverse=True)
    await update.message.reply_text(format_message(football_bets, "FOOTBALL"))


async def nba_command(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Fetching NBA bets...")
    nba_games = get_odds(NBA_SPORT)
    nba_bets = find_value_bets(nba_games)
    await update.message.reply_text(format_message(nba_bets, "NBA"))


async def scheduled_daily(context: ContextTypes.DEFAULT_TYPE):
    football_bets = []
    for sport in FOOTBALL_SPORTS:
        games = get_odds(sport)
        football_bets.extend(find_value_bets(games))
    nba_games = get_odds(NBA_SPORT)
    nba_bets = find_value_bets(nba_games)
    message = format_message(football_bets, "FOOTBALL") + format_message(nba_bets, "NBA")
    await context.bot.send_message(chat_id=CHAT_ID, text=message)


def main():
    print("🤖 Betting Bot starting...")
    request = HTTPXRequest(connect_timeout=60, read_timeout=60)
    app = Application.builder().token(TELEGRAM_TOKEN).request(request).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", start_command))
    app.add_handler(CommandHandler("analysis", analysis_command))
    app.add_handler(CommandHandler("football", football_command))
    app.add_handler(CommandHandler("nba", nba_command))
    app.job_queue.run_daily(
        scheduled_daily,
        time=time(hour=8, minute=0),
        days=(0, 1, 2, 3, 4, 5, 6)
    )
    print("✅ Bot is live! Go message your bot on Telegram.")
    app.run_polling()


if __name__ == "__main__":
    main()