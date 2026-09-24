# Telegram Bot Manager

A full-stack admin dashboard to manage, monitor, and control your Telegram bot — built with Python (FastAPI + python-telegram-bot) and React (Vite + Tailwind CSS).

## Features

- 📊 **Live Dashboard** — total users, /start clicks, join requests, approved/rejected/pending stats
- 👤 **Users Table** — see every user's name, username, Telegram ID, join date; ban/unban instantly
- 📨 **Join Requests** — approve or reject channel join requests manually or let the bot auto-approve
- 🤖 **Bot Controls** — start/stop the bot remotely, broadcast messages to all users
- 🔴 **Activity Feed** — real-time color-coded event log (auto-polls every 5 seconds)
- ⚙️ **Settings** — change bot token, channel link, and dashboard password — all from the UI
- 🔒 **Password Protected** — SHA-256 hashed password, Bearer token auth on every API endpoint

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Bot | `python-telegram-bot` v21 |
| Backend API | `FastAPI` + `SQLite` |
| Frontend | `React` + `Vite` + `Tailwind CSS` |
| Auth | SHA-256 password hashing + Bearer tokens |

## Project Structure

```
Telegram_Bot_Manager/
├── bot.py              # Telegram bot with auto-restart & crash recovery
├── api.py              # FastAPI REST API (password protected)
├── database.py         # SQLite helper (users, events, join requests, config)
├── requirements.txt    # Python dependencies
├── START_DASHBOARD.bat # One-click launcher (Windows)
└── dashboard/          # React frontend
    ├── src/
    │   ├── App.jsx
    │   └── components/
    │       ├── LoginPage.jsx
    │       ├── StatCard.jsx
    │       ├── UsersTable.jsx
    │       ├── JoinRequests.jsx
    │       ├── BotControls.jsx
    │       └── ActivityFeed.jsx
    ├── package.json
    └── vite.config.js
```

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/HimanshuYadav5998/Telegram_Bot_Manager.git
cd Telegram_Bot_Manager
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Install frontend dependencies

```bash
cd dashboard
npm install
cd ..
```

### 4. Start everything

Double-click **`START_DASHBOARD.bat`** or run manually:

```bash
# Terminal 1 — API server
python api.py

# Terminal 2 — React dashboard
cd dashboard
npm run dev
```

### 5. Open the dashboard

Visit **http://localhost:5173**

> Default password: `admin123` — change it immediately in Settings!

### 6. Configure your bot

1. Go to **Settings** in the dashboard
2. Paste your **Bot Token** (from [@BotFather](https://t.me/BotFather))
3. Set your **Channel Invite Link**
4. Click **Save Changes**
5. Go to **Bot Controls** → click **Start Bot**

## License

MIT
