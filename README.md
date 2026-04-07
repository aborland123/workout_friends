# 💪 Squad Sweat — Workout Tracker

A Streamlit workout tracking app for Alli, Andrea, and Liv with streaks, points, weekly challenges, photo uploads, and email notifications.

---

## 🚀 Quick Setup (5 minutes)

### 1. Install Python
Download from [python.org](https://python.org) if you don't have it.

### 2. Install dependencies
Open Terminal (Mac) or Command Prompt (Windows) in the `workout-tracker` folder:
```bash
pip install -r requirements.txt
```

### 3. Run the app
```bash
streamlit run app.py
```
The app opens at `http://localhost:8501` — that's it! ✅

---

## 📧 Setting Up Email Notifications (optional but fun)

Email alerts are sent when someone logs a workout. To enable:

### Step 1: Create a Gmail App Password
1. Go to your Google Account → Security → 2-Step Verification (must be ON)
2. Go to **App Passwords** (search for it in Google Account settings)
3. Create one for "Mail" → copy the 16-character password

### Step 2: Create a `.env` file
Create a file called `.env` in the `workout-tracker` folder:
```
EMAIL_SENDER=your-gmail@gmail.com
EMAIL_PASSWORD=xxxx xxxx xxxx xxxx
EMAIL_ALLI=alli-email@example.com
EMAIL_ANDREA=andrea-email@example.com
EMAIL_LIV=liv-email@example.com
```

### Step 3: Load the `.env` file
Install `python-dotenv`:
```bash
pip install python-dotenv
```

Add this at the very top of `app.py`:
```python
from dotenv import load_dotenv
load_dotenv()
```

---

## 🌐 Deploy Online (Free — Streamlit Cloud)

So all three of you can access it from your phones:

1. Create a free account at [streamlit.io](https://streamlit.io)
2. Push this folder to a **private** GitHub repo
3. Go to Streamlit Cloud → "New app" → connect your repo → Deploy

### Adding your email secrets to Streamlit Cloud:
In your app settings on Streamlit Cloud, go to **Secrets** and add:
```toml
EMAIL_SENDER = "your-gmail@gmail.com"
EMAIL_PASSWORD = "xxxx xxxx xxxx xxxx"
EMAIL_ALLI = "alli@example.com"
EMAIL_ANDREA = "andrea@example.com"
EMAIL_LIV = "liv@example.com"
```

> ⚠️ **Note on photos:** Streamlit Cloud doesn't persist files between sessions. For permanent photo storage, you'll want to upgrade to Supabase storage (see below).

---

## 🗄️ Optional: Supabase for Persistent Photo Storage

If you want photos to persist across deployments:

1. Create a free [Supabase](https://supabase.com) account
2. Create a new project
3. Create a Storage bucket called `workout-photos` (set to public)
4. Add to your secrets:
   ```toml
   SUPABASE_URL = "https://xxxx.supabase.co"
   SUPABASE_KEY = "your-anon-key"
   ```
5. Install: `pip install supabase`

Then update `save_photo()` and `get_photo_b64()` in `app.py` to use the Supabase storage client.

---

## 🏆 Scoring System

| Action | Points |
|--------|--------|
| Solo workout | +10 pts |
| Group workout (together) | +15 pts each |

**Competition categories:**
- 🔥 **Streak** — consecutive days worked out
- 📅 **Weekly Challenge** — most workouts this week (resets Monday)
- 📆 **Monthly Points** — resets every month
- ⭐ **All-Time Points** — lifetime total

---

## 📁 Data Storage

Workout data is stored locally in `data/workouts.json`. Photos go in `data/photos/`. Back these up if you want to keep your history!

---

*Built with Streamlit 🎈*
