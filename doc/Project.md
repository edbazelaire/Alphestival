# Discord Mini Games & Betting Bot

## Project Documentation

------------------------------------------------------------------------

## 1. Project Overview

This project is a custom Discord bot built in Python that provides daily
mini-games and betting mechanics for a game testing community.\
The goal is to increase engagement and celebrate the official game
release through interactive prediction events.

The bot includes: 
    - Virtual coin economy 
    - Daily betting questions 
    - A mini game of coinflips (double or loose all each time)
    - Weighted roulette system 
    - Leaderboards 
    - Admin management tools

⚠️ Important: The currency is virtual only and has no real-world
monetary value.

------------------------------------------------------------------------

## 2. Core Features

### 2.1 Virtual Economy

-   Every user starts with 100 coins
-   Coins are stored in a database
-   Users can:
    -   Bet on daily questions
    -   Participate in roulette events
-   Leaderboard ranks users by total coins

------------------------------------------------------------------------

### 2.2 Daily Betting Questions

Admins can: 
- Create a question 
- Open and close betting (like a pool)
- Resolve the question with the correct answer

Users can: 
    - Bet coins on an answer 
    - Receive payouts if correct

------------------------------------------------------------------------

### 2.3 Weighted Roulette

Users bet coins into a shared pool.

Winning probability is proportional to the amount bet.

Example: - User A bets 3 coins - User B bets 1 coin

Total = 4 coins\
User A has 75% chance\
User B has 25% chance

Winner receives the full pool (or configurable reward).

------------------------------------------------------------------------

## 3. Technical Stack

### Language

-   Python 3.10+

### Discord Library

-   discord.py (v2.x with slash commands)

### Database

-   SQLite (initial version)
-   Optional future migration to PostgreSQL

### Hosting Options

-   Railway
-   Render
-   VPS
-   Docker container

------------------------------------------------------------------------

## 4. Architecture

Project structure:

bot/ │ ├── main.py ├── config.py ├── database.py │ ├── cogs/ │ ├──
economy.py │ ├── betting.py │ ├── roulette.py │ └── admin.py │ └──
utils/ └── helpers.py

### Separation of Concerns

-   economy.py → Coin management
-   betting.py → Question betting system
-   roulette.py → Weighted roulette logic
-   admin.py → Admin-only commands

------------------------------------------------------------------------

## 5. Database Schema

### users

-   user_id (PRIMARY KEY)
-   coins (INTEGER)

### questions

-   id (PRIMARY KEY)
-   question (TEXT)
-   status (open / closed / resolved)
-   correct_answer (TEXT)
-   created_at (TIMESTAMP)

### bets

-   id (PRIMARY KEY)
-   question_id (FOREIGN KEY)
-   user_id (FOREIGN KEY)
-   answer (TEXT)
-   amount (INTEGER)

------------------------------------------------------------------------

## 6. Security & Anti-Abuse

-   Prevent negative bets
-   Prevent betting more coins than owned
-   Lock questions when closed
-   Log admin actions
-   Use SQL transactions for financial operations

Optional improvements: - Daily betting limits - Anti-spam cooldown -
Audit log table

------------------------------------------------------------------------

## 7. Future Improvements

-   Web dashboard for admins
-   Animated roulette via web interface
-   Seasonal events
-   Achievements system
-   Persistent user statistics
-   Role rewards for top players

------------------------------------------------------------------------

## 8. Roadmap

Phase 1: - Core economy - Basic betting - Roulette system - Leaderboard

Phase 2: - Automation of daily questions - Improved UI messages -
Logging and moderation tools

Phase 3: - Web integration - Advanced statistics - Game-data driven
questions

------------------------------------------------------------------------

## 9. Objective

Create a fun, engaging, automated daily event system that: - Builds hype
around the game release - Encourages community interaction - Rewards
active testers - Remains lightweight and maintainable

------------------------------------------------------------------------

End of Document
