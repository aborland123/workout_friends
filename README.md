# 💪 Squad Sweat — Workout Tracker
*Alli · Andrea · Liv*

---

## 🚀 Local Setup (test before deploying)

### 1. Install Python
Download from [python.org](https://python.org) if you don't have it.

### 2. Install dependencies
Open Terminal in this folder:
```bash
pip install -r requirements.txt
```

### 3. Run
```bash
streamlit run app.py
```
Opens at `http://localhost:8501` — photos and data save locally in the `data/` folder.

---

## 🌐 Deploy to Streamlit Cloud (free, shareable link for all three of you)

1. Push this folder to a **private** GitHub repo
2. Go to [share.streamlit.io](https://share.streamlit.io) → sign in with GitHub
3. Click **New app** → select your repo → set main file to `app.py` → Deploy
4. You'll get a URL like `https://yourapp.streamlit.app` — works on phones too!

### Add secrets in Streamlit Cloud
Go to your app → ⋮ → **Settings → Secrets** and paste:

```toml
EMAIL_SENDER   = "the-gmail-sending-notifications@gmail.com"
EMAIL_PASSWORD = "xxxx xxxx xxxx xxxx"   # Gmail App Password (see below)

EMAIL_ALLI   = "aborland123@gmail.com"
EMAIL_ANDREA = "nina.policarpom@gmail.com"
EMAIL_LIV    = "livcdoland@gmail.com"

SUPABASE_URL = "https://xxxxxxxxxxxx.supabase.co"
SUPABASE_KEY = "your-anon-public-key"
```

---

## 📧 Gmail App Password Setup

The `EMAIL_SENDER` can be any Gmail — one of yours or a shared `squadsweat@gmail.com`.

1. Go to [myaccount.google.com](https://myaccount.google.com) for the sending account
2. **Security → 2-Step Verification** (must be ON)
3. Search for **App Passwords** → create one for "Mail"
4. Copy the 16-character password → use as `EMAIL_PASSWORD`

---

## 🗄️ Supabase Setup (for persistent photos + data)

Without Supabase, photos disappear whenever Streamlit Cloud redeploys. With it, everything persists forever.

### Step 1: Create project
1. Go to [supabase.com](https://supabase.com) → New project (free tier is plenty)
2. Note your **Project URL** and **anon/public API key** (Settings → API)

### Step 2: Run the SQL
1. In your Supabase project → **SQL Editor**
2. Paste the contents of `supabase_setup.sql` → Run

### Step 3: Create the storage bucket
1. Supabase dashboard → **Storage** → **New bucket**
2. Name: `workout-photos`
3. Toggle **Public bucket** ON → Create

### Step 4: Install the Python client
```bash
pip install supabase
```
Add `supabase>=2.0.0` to `requirements.txt` too.

That's it — once `SUPABASE_URL` and `SUPABASE_KEY` are in your secrets, the app automatically uses Supabase for everything.

---

## ⭐ Scoring System

Points = **Base × Duration Multiplier** + group/streak bonuses

### Base points by intensity

| | Level | Base | Examples |
|---|---|---|---|
| 😴 | Rest Day | 0 pts | Active recovery, stretching only |
| 🚶 | Easy | 6 pts | Walk in the park, gentle yoga |
| 🏃 | Moderate | 12 pts | Light jog, yoga flow, casual bike ride |
| 💪 | Hard | 18 pts | Gym workout, running, group fitness class |
| 🔥 | Beast Mode | 26 pts | HIIT, heavy lifting, race, long run |

### Duration multiplier

| Duration | Multiplier |
|---|---|
| Under 20 min | ×0.6 |
| 20–30 min | ×0.8 |
| 31–45 min | ×1.0 |
| 46–60 min | ×1.2 |
| 61–90 min | ×1.4 |
| 90–120 min | ×1.6 |
| 120+ min | ×1.8 |

### Bonuses
- **🤝 Group workout** — +4 pts per person
- **🔥 Streak bonus** — after a 3-day streak, +2 pts/day (max +10)

### Example scores
| Workout | Points |
|---|---|
| 20 min walk (Easy) | 5 pts |
| 45 min yoga flow (Moderate) | 12 pts |
| 60 min gym session (Hard) | 22 pts |
| 90 min HIIT (Beast) | 42 pts |
| 60 min group gym sesh (Hard) | 26 pts each |

---

## 📁 Files

```
workout-tracker/
├── app.py                  ← the whole app
├── requirements.txt
├── supabase_setup.sql      ← run this in Supabase SQL editor
├── README.md
└── data/                   ← local data (only used without Supabase)
    ├── workouts.json
    └── photos/
```
