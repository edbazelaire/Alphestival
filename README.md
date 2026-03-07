# BotCasino

Discord mini-games and virtual betting bot for community engagement.

## Quick Start

1. Create and activate a virtual environment
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and set your bot token
4. Run the bot:
   - `python -m bot.main`

## Project Structure

- `bot/main.py` - Bot bootstrap and cog loading
- `bot/config.py` - Environment configuration
- `bot/database.py` - SQLite database and economy operations
- `bot/cogs/economy.py` - Balance and leaderboard commands
- `bot/cogs/betting.py` - Daily betting question flow
- `bot/cogs/roulette.py` - Weighted roulette events
- `bot/cogs/admin.py` - Admin-only management commands
- `bot/utils/admin_checks.py` - Shared check for the "admin" role

### Admin commands and visibility

Admin commands are restricted to users who have a Discord role named **admin** (case-insensitive). To hide these commands from other members:

1. Create a role named `admin` (or use an existing one).
2. In the server’s **Role** settings for that role, enable **Manage Server**.
3. Only members with that permission will see admin slash commands; the bot also checks that the user has the `admin` role before running them.

## API Documentation

- In-game API guide: `doc/API.md`
