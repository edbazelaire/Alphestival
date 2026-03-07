# Deploying BotCasino

Your bot runs 24/7 as a single process (Discord bot + FastAPI API). It uses **SQLite** (one file) and config from environment variables. Below are the **easiest** and **cheapest** options.

---

## Option 1: Railway (easiest, ~$0–5/month)

**Best for:** Get online in a few minutes with minimal setup.

1. **Push your code to GitHub** (create a repo, push; do **not** commit `.env` or `*.db`).

2. **Sign up at [railway.app](https://railway.app)** and create a new project.

3. **Deploy from GitHub:**
   - Click **“New” → “GitHub Repo”** and select your BotCasino repo.
   - Railway will detect Python and build. Set the **start command** to:
     ```bash
     python -m bot.main
     ```

4. **Persistent database (important):**
   - In your project, click **“New” → “Volume”**.
   - Mount it at a path, e.g. `/data`.
   - In the **Variables** tab, add:
     - `DATABASE_PATH=/data/botcasino.db`
   - So the SQLite file lives on the volume and survives redeploys.

5. **Environment variables** (Variables tab):
   - `DISCORD_TOKEN` — your bot token (required).
   - `DISCORD_GUILD_ID` — optional; your server ID for faster slash-command sync.
   - `API_SHARED_SECRET` — if your game sends webhooks to the API.
   - Any other vars from your `.env` (e.g. `ACHIEVEMENTS_EVENTS_CHANNEL_ID`, `STARTING_COINS`).

6. **Deploy.** Railway assigns `PORT` automatically; the app already uses it.

**Cost:** Free trial credit, then usage-based. A small bot often stays within a few dollars per month. Check [Railway pricing](https://railway.app/pricing).

---

## Option 2: Render (easy, free tier sleeps / paid for 24/7)

**Best for:** Simple UI and GitHub integration; free tier is for testing (service sleeps when idle).

1. **Push code to GitHub** (no `.env`, no `*.db`).

2. **Sign up at [render.com](https://render.com)** → **New → Background Worker**.

3. **Connect repo**, set:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `python -m bot.main`
   - **Environment:** Add `DISCORD_TOKEN`, `DISCORD_GUILD_ID`, `DATABASE_PATH`, etc.

4. **Database:** On free tier the filesystem is ephemeral, so the SQLite file is lost on restart. For a real deployment use a **Disk** (paid) or switch to a hosted DB later. For a quick test, free tier is fine.

**Cost:** Free tier = worker can sleep; for 24/7 bot you need a paid plan (~$7/mo) and optionally a Disk for SQLite.

---

## Option 3: Oracle Cloud Always Free (free forever, more setup)

**Best for:** $0 long-term; you get a small VM and full control.

1. **Sign up at [Oracle Cloud](https://www.oracle.com/cloud/free/)** (credit card for verification; Always Free is not charged).

2. **Create an Always Free VM** (e.g. Ubuntu 22.04, AMD or ARM).

3. **SSH in** and install Python 3.10+ and git:
   ```bash
   sudo apt update && sudo apt install -y python3 python3-pip python3-venv git
   ```

4. **Clone and run:**
   ```bash
   git clone <your-repo-url> BotCasino && cd BotCasino
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```

5. **Create `.env`** with `DISCORD_TOKEN`, `DISCORD_GUILD_ID`, `DATABASE_PATH` (e.g. `/home/ubuntu/BotCasino/botcasino.db`), etc.

6. **Run in background** (pick one):
   - **systemd (recommended):** create a service file that runs `python -m bot.main` and restarts on failure.
   - **screen/tmux:** `screen -S bot` then `python -m bot.main`.

**Cost:** $0 for Always Free tier (within limits). No credit card charges if you stay in Always Free.

---

## Option 4: Cheap VPS ($4–6/month)

**Best for:** Full control and predictable price.

Use **DigitalOcean**, **Hetzner**, **Vultr**, or **Linode**. Create a small droplet (e.g. 1 GB RAM), then follow the same steps as Oracle (install Python, clone repo, `.env`, run with systemd or screen). Use a **volume** or backup the `*.db` file regularly.

---

## Checklist before going live

- [ ] **Never commit** `.env` or `DISCORD_TOKEN` (use platform env vars or a secret manager).
- [ ] **Back up** `botcasino.db` (and `data/` if you care about those JSON files) — e.g. cron + copy to S3/backup volume.
- [ ] Set `API_SHARED_SECRET` if your game sends webhooks; keep it strong and secret.
- [ ] Optional: set `DISCORD_GUILD_ID` so slash commands sync to your server immediately.

If you tell me which option you prefer (Railway vs Oracle vs VPS), I can give you exact click-by-click or command-by-command steps for that one.
