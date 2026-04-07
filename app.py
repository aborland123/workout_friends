import streamlit as st
import json
import os
import datetime
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from PIL import Image
import io
import base64
import math

# ─── SUPABASE (optional) ──────────────────────────────────────────────────────
# If SUPABASE_URL and SUPABASE_KEY are set, the app uses Supabase for storage.
# Otherwise it falls back to local JSON files (great for local testing).

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
USE_SUPABASE = bool(SUPABASE_URL and SUPABASE_KEY)

_supabase_client = None
def get_supabase():
    global _supabase_client
    if _supabase_client is None and USE_SUPABASE:
        try:
            from supabase import create_client
            _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception:
            pass
    return _supabase_client

# ─── CONFIG ───────────────────────────────────────────────────────────────────

MEMBERS = ["Alli", "Andrea", "Liv"]
MEMBER_COLORS   = {"Alli": "#FF6B9D", "Andrea": "#9B59B6", "Liv": "#3498DB"}
MEMBER_EMOJIS   = {"Alli": "🌸", "Andrea": "💜", "Liv": "💙"}
MEMBER_BG       = {"Alli": "#FFF0F5", "Andrea": "#F5F0FF", "Liv": "#F0F5FF"}

# Emails
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_RECIPIENTS = {
    "Alli":   os.getenv("EMAIL_ALLI",   "aborland123@gmail.com"),
    "Andrea": os.getenv("EMAIL_ANDREA", "nina.policarpom@gmail.com"),
    "Liv":    os.getenv("EMAIL_LIV",    "livcdoland@gmail.com"),
}

# ─── INTENSITY / SCORING ─────────────────────────────────────────────────────
#
#  Points = round(BASE_POINTS[intensity] × DURATION_MULT(minutes)) + group_bonus
#
#  Intensity   Base   Examples
#  ─────────── ──────  ───────────────────────────────────────────────────────
#  😴 Rest Day    0    Active recovery, stretching only
#  🚶 Easy        6    Casual walk, gentle yoga, light stretching
#  🏃 Moderate   12    Jog, yoga flow, cycling at easy pace, light lifting
#  💪 Hard        18   Gym workout, running, group fitness, moderate lifting
#  🔥 Beast       26   Heavy lifting, HIIT, race, intense spin, long run
#
#  Duration multiplier (applied to base):
#    < 20 min  → ×0.6
#    20–30     → ×0.8
#    31–45     → ×1.0
#    46–60     → ×1.2
#    61–90     → ×1.4
#    91–120    → ×1.6
#    120+      → ×1.8
#
#  Group bonus: +4 pts per person (on top of individual totals)
#  Streak bonus: +2 pts/day after a 3-day streak (capped at +10)

INTENSITY_OPTIONS = {
    "😴 Rest Day  (recovery, stretching)":        ("rest",     0),
    "🚶 Easy  (walk, gentle yoga, light movement)": ("easy",    6),
    "🏃 Moderate  (jog, yoga flow, light gym)":    ("moderate", 12),
    "💪 Hard  (gym workout, run, group fitness)":  ("hard",     18),
    "🔥 Beast Mode  (HIIT, heavy lift, race, long run)": ("beast", 26),
}
INTENSITY_LABELS = {v[0]: k for k, v in INTENSITY_OPTIONS.items()}

GROUP_BONUS = 4  # per person

def duration_multiplier(mins: int) -> float:
    if   mins < 20:  return 0.6
    elif mins < 31:  return 0.8
    elif mins < 46:  return 1.0
    elif mins < 61:  return 1.2
    elif mins < 91:  return 1.4
    elif mins < 121: return 1.6
    else:            return 1.8

def calc_points(intensity_key: str, duration: int, is_group: bool) -> int:
    base = dict(v for v in INTENSITY_OPTIONS.values())[intensity_key]
    pts = base * duration_multiplier(duration)
    if is_group:
        pts += GROUP_BONUS
    return max(0, round(pts))

# ─── LOCAL DATA FALLBACK ──────────────────────────────────────────────────────

DATA_FILE   = Path("data/workouts.json")
PHOTOS_DIR  = Path("data/photos")
PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

# ─── DATA HELPERS ─────────────────────────────────────────────────────────────

def load_workouts():
    if USE_SUPABASE:
        try:
            sb = get_supabase()
            res = sb.table("workouts").select("*").order("date", desc=True).execute()
            rows = res.data or []
            # normalise: participants stored as JSON string in Supabase
            for r in rows:
                if isinstance(r.get("participants"), str):
                    r["participants"] = json.loads(r["participants"])
            return rows
        except Exception:
            pass  # fall through to local
    if DATA_FILE.exists():
        with open(DATA_FILE) as f:
            return json.load(f)
    return []

def save_workout(entry: dict):
    if USE_SUPABASE:
        try:
            sb = get_supabase()
            row = dict(entry)
            row["participants"] = json.dumps(entry["participants"])
            sb.table("workouts").upsert(row).execute()
            return
        except Exception:
            pass
    workouts = load_workouts()
    workouts.append(entry)
    with open(DATA_FILE, "w") as f:
        json.dump(workouts, f, indent=2)

def save_photo(uploaded_file, workout_id: str) -> str | None:
    if uploaded_file is None:
        return None
    ext = uploaded_file.name.split(".")[-1].lower()
    filename = f"{workout_id}.{ext}"

    img = Image.open(uploaded_file)
    img.thumbnail((900, 900))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    buf.seek(0)

    if USE_SUPABASE:
        try:
            sb = get_supabase()
            sb.storage.from_("workout-photos").upload(
                filename, buf.read(),
                file_options={"content-type": "image/jpeg"}
            )
            return filename
        except Exception:
            pass  # fall through to local

    path = PHOTOS_DIR / filename
    path.write_bytes(buf.getvalue())
    return filename

def get_photo_url(filename: str) -> str | None:
    if not filename:
        return None
    if USE_SUPABASE:
        try:
            sb = get_supabase()
            res = sb.storage.from_("workout-photos").get_public_url(filename)
            return res
        except Exception:
            pass
    path = PHOTOS_DIR / filename
    if path.exists():
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f"data:image/jpeg;base64,{b64}"
    return None

# ─── COMPETITION LOGIC ────────────────────────────────────────────────────────

def compute_streak(workouts, person: str) -> int:
    dates = sorted(set(
        w["date"] for w in workouts
        if person in w["participants"] and w.get("intensity", "rest") != "rest"
    ), reverse=True)
    if not dates:
        return 0
    today     = datetime.date.today().isoformat()
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    if dates[0] not in (today, yesterday):
        return 0
    streak = 1
    for i in range(1, len(dates)):
        prev = datetime.date.fromisoformat(dates[i - 1])
        curr = datetime.date.fromisoformat(dates[i])
        if (prev - curr).days == 1:
            streak += 1
        else:
            break
    return streak

def streak_bonus(streak: int) -> int:
    return min(max(0, (streak - 3) * 2), 10)

def compute_total_points(workouts, person: str) -> int:
    total = sum(w.get("points", 0) for w in workouts if person in w["participants"])
    total += streak_bonus(compute_streak(workouts, person))
    return total

def compute_weekly_workouts(workouts, person: str) -> int:
    today      = datetime.date.today()
    week_start = today - datetime.timedelta(days=today.weekday())
    return sum(
        1 for w in workouts
        if person in w["participants"]
        and datetime.date.fromisoformat(w["date"]) >= week_start
        and w.get("intensity", "rest") != "rest"
    )

def compute_monthly_points(workouts, person: str) -> int:
    today = datetime.date.today()
    return sum(
        w.get("points", 0) for w in workouts
        if person in w["participants"]
        and datetime.date.fromisoformat(w["date"]).year  == today.year
        and datetime.date.fromisoformat(w["date"]).month == today.month
    )

def get_leaderboard(workouts):
    return {
        person: {
            "streak":          compute_streak(workouts, person),
            "total_points":    compute_total_points(workouts, person),
            "weekly_workouts": compute_weekly_workouts(workouts, person),
            "monthly_points":  compute_monthly_points(workouts, person),
        }
        for person in MEMBERS
    }

def already_logged_today(workouts, person: str, date_str: str) -> bool:
    return any(
        w["date"] == date_str and person in w["participants"]
        for w in workouts
    )

# ─── EMAIL ────────────────────────────────────────────────────────────────────

def send_notification(logger: str, participants: list, workout_type: str,
                      intensity_key: str, duration: int, points: int,
                      notes: str, is_group: bool):
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        return
    recipients = [
        EMAIL_RECIPIENTS[p] for p in MEMBERS
        if p != logger and EMAIL_RECIPIENTS.get(p)
    ]
    if not recipients:
        return

    intensity_label = INTENSITY_LABELS.get(intensity_key, intensity_key).split("(")[0].strip()
    subject = (
        f"🤝 {' + '.join(participants)} worked out together!"
        if is_group else
        f"💪 {logger} just logged a workout!"
    )
    body = f"""
Hey! Just a heads-up 👋

{'🤝 GROUP WORKOUT — everyone gets bonus points!' if is_group else '💪 Solo grind'}

👤 Logged by: {logger}
{'👥 Crew: ' + ', '.join(participants) if is_group else ''}
🏃 Type: {workout_type}
⚡ Intensity: {intensity_label}
⏱ Duration: {duration} min
⭐ Points earned: {points}
📝 Notes: {notes or 'None'}
📅 Date: {datetime.date.today().strftime('%A, %B %d')}

Check the leaderboard! 🏆
    """.strip()
    try:
        msg = MIMEMultipart()
        msg["From"]    = EMAIL_SENDER
        msg["To"]      = ", ".join(recipients)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, recipients, msg.as_string())
    except Exception:
        pass

# ─── UI HELPERS ───────────────────────────────────────────────────────────────

def medal(rank: int) -> str:
    return ["🥇", "🥈", "🥉", "4️⃣"][min(rank, 3)]

def render_workout_card(w: dict):
    participants = w["participants"]
    is_group     = len(participants) > 1
    date_obj     = datetime.date.fromisoformat(w["date"])
    date_str     = date_obj.strftime("%a, %b %d")
    label        = " & ".join(participants) if is_group else participants[0]
    primary      = participants[0]
    color        = MEMBER_COLORS.get(primary, "#888")
    emoji        = "🤝" if is_group else MEMBER_EMOJIS.get(primary, "💪")
    pts          = w.get("points", 0)
    intensity    = w.get("intensity", "")
    int_label    = INTENSITY_LABELS.get(intensity, "").split("(")[0].strip() if intensity else ""

    photo_url = get_photo_url(w.get("photo"))

    with st.container():
        cols = st.columns([1, 4])
        with cols[0]:
            if photo_url:
                st.markdown(
                    f'<img src="{photo_url}" '
                    f'style="width:100%;border-radius:12px;object-fit:cover;aspect-ratio:1/1"/>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div style='font-size:2.8rem;text-align:center;padding-top:0.3rem'>"
                    f"{emoji}</div>",
                    unsafe_allow_html=True,
                )
        with cols[1]:
            st.markdown(
                f"<span style='color:{color};font-weight:700;font-size:1.05rem'>{label}</span> "
                f"<span style='color:#aaa;font-size:0.82rem'>• {date_str}</span>  "
                f"<span style='background:#f0f0f0;border-radius:8px;"
                f"padding:2px 9px;font-size:0.8rem;font-weight:600'>+{pts} pts</span>",
                unsafe_allow_html=True,
            )
            detail = f"{w.get('workout_type','Workout')}"
            if int_label:
                detail += f"  ·  {int_label}"
            detail += f"  ·  ⏱ {w.get('duration','?')} min"
            st.caption(detail)
            if w.get("notes"):
                st.markdown(f"_{w['notes']}_")
            if is_group:
                st.success("🤝 Group workout — everyone got bonus points!", icon=None)
        st.divider()

# ─── PAGES ────────────────────────────────────────────────────────────────────

def page_log(person: str, workouts: list):
    st.header(f"{MEMBER_EMOJIS[person]} Log a Workout")
    today = datetime.date.today()

    if already_logged_today(workouts, person, today.isoformat()):
        st.info("You already logged something today! Feel free to add another entry if you did more. 💪")

    with st.form("log_form", clear_on_submit=True):
        # ── Intensity ──
        st.markdown("#### ⚡ Intensity")
        intensity_display = st.radio(
            "How hard was it?",
            list(INTENSITY_OPTIONS.keys()),
            index=2,
            help="This affects how many points you earn.",
        )
        intensity_key, base_pts = INTENSITY_OPTIONS[intensity_display]

        # ── Workout type & duration ──
        col_a, col_b = st.columns(2)
        with col_a:
            workout_type = st.selectbox("Type", [
                "Gym / Weights", "Running", "Cycling / Spin", "HIIT",
                "Yoga / Pilates", "Swimming", "Sports", "Walk / Hike",
                "Dance / Zumba", "Boxing / Martial Arts", "CrossFit",
                "Rowing", "Stretching / Mobility", "Other",
            ])
        with col_b:
            duration = st.slider("Duration (min)", 10, 180, 45, 5)

        # Live points preview
        preview_pts = calc_points(intensity_key, duration, False)
        group_preview = calc_points(intensity_key, duration, True)
        st.markdown(
            f"<div style='background:#f8f8f8;border-radius:10px;padding:8px 14px;"
            f"font-size:0.9rem;color:#555;margin-bottom:4px'>"
            f"⭐ Solo: <strong>{preview_pts} pts</strong> &nbsp;|&nbsp; "
            f"🤝 Group: <strong>{group_preview} pts</strong> each"
            f"</div>",
            unsafe_allow_html=True,
        )

        notes = st.text_area("Notes / how did it feel?",
                             placeholder="e.g. new PR on squat 🎉, died on the treadmill 💀")

        st.markdown("---")
        is_group = st.checkbox("🤝 We worked out TOGETHER (group workout)")
        group_members = []
        if is_group:
            others = [m for m in MEMBERS if m != person]
            group_members = st.multiselect("Who else was there?", others, default=others)

        photo = st.file_uploader("📸 Upload a photo (optional)", type=["jpg", "jpeg", "png"])

        submitted = st.form_submit_button("💪 Log It!", use_container_width=True)

    if submitted:
        participants = sorted(set([person] + group_members)) if is_group else [person]
        pts          = calc_points(intensity_key, duration, len(participants) > 1)
        workout_id   = f"{person}_{today.isoformat()}_{len(workouts)}"
        photo_file   = save_photo(photo, workout_id)

        entry = {
            "id":           workout_id,
            "date":         today.isoformat(),
            "participants": participants,
            "workout_type": workout_type,
            "intensity":    intensity_key,
            "duration":     duration,
            "notes":        notes,
            "photo":        photo_file,
            "logged_by":    person,
            "points":       pts,
        }
        save_workout(entry)
        st.balloons()
        st.success(f"🎉 Logged! You earned **+{pts} points**.")
        send_notification(
            person, participants, workout_type, intensity_key,
            duration, pts, notes, len(participants) > 1
        )
        st.rerun()


def page_leaderboard(workouts: list):
    st.header("🏆 Leaderboard")
    lb    = get_leaderboard(workouts)
    today = datetime.date.today()
    month = today.strftime("%B")
    week_start = today - datetime.timedelta(days=today.weekday())

    # ── All-time points ──
    st.subheader("⭐ All-Time Points")
    ranked = sorted(MEMBERS, key=lambda p: lb[p]["total_points"], reverse=True)
    max_pts = max((lb[p]["total_points"] for p in MEMBERS), default=1) or 1
    for rank, person in enumerate(ranked):
        pts   = lb[p]["total_points"] if False else lb[person]["total_points"]
        color = MEMBER_COLORS[person]
        pct   = pts / max_pts
        st.markdown(
            f"{medal(rank)} &nbsp; <span style='color:{color};font-weight:700;"
            f"font-size:1.05rem'>{person}</span> &nbsp; "
            f"<span style='font-size:1.2rem;font-weight:700'>{pts}</span>"
            f"<span style='color:#aaa'> pts</span>",
            unsafe_allow_html=True,
        )
        st.progress(pct)

    st.divider()

    # ── Streaks ──
    st.subheader("🔥 Current Streaks")
    streak_ranked = sorted(MEMBERS, key=lambda p: lb[p]["streak"], reverse=True)
    cols = st.columns(3)
    for i, person in enumerate(streak_ranked):
        with cols[i]:
            s     = lb[person]["streak"]
            bonus = streak_bonus(s)
            st.metric(
                label=f"{MEMBER_EMOJIS[person]} {person}",
                value=f"{s} day{'s' if s != 1 else ''}",
                delta=f"+{bonus} streak bonus pts" if bonus > 0 else ("🔥" * min(s, 5) if s else "no streak"),
            )

    st.divider()

    # ── Weekly Challenge ──
    st.subheader(f"📅 Weekly Challenge — week of {week_start.strftime('%b %d')}")
    weekly_ranked = sorted(MEMBERS, key=lambda p: lb[p]["weekly_workouts"], reverse=True)
    for rank, person in enumerate(weekly_ranked):
        ww    = lb[person]["weekly_workouts"]
        crown = " 👑" if rank == 0 and ww > 0 else ""
        st.markdown(
            f"{medal(rank)} &nbsp; **{person}** — "
            f"{ww} workout{'s' if ww != 1 else ''} this week{crown}"
        )

    st.divider()

    # ── Monthly ──
    st.subheader(f"📆 {month} Points")
    monthly_ranked = sorted(MEMBERS, key=lambda p: lb[p]["monthly_points"], reverse=True)
    for rank, person in enumerate(monthly_ranked):
        mp = lb[person]["monthly_points"]
        st.markdown(f"{medal(rank)} &nbsp; **{person}** — {mp} pts this month")

    st.divider()

    # ── Points breakdown explainer ──
    with st.expander("📖 How points work"):
        st.markdown("""
**Base points by intensity:**

| Level | Base pts | Example |
|---|---|---|
| 😴 Rest Day | 0 | Recovery, stretching only |
| 🚶 Easy | 6 | Walk in the park, gentle yoga |
| 🏃 Moderate | 12 | Light jog, yoga flow, casual bike |
| 💪 Hard | 18 | Gym workout, running, group fitness |
| 🔥 Beast Mode | 26 | HIIT, heavy lifting, race, long run |

**Duration multiplier** applied to base:
< 20 min → ×0.6 · 20–30 min → ×0.8 · 31–45 min → ×1.0 · 46–60 min → ×1.2 · 61–90 min → ×1.4 · 90–120 min → ×1.6 · 120+ min → ×1.8

**Bonuses:**
- 🤝 Group workout: +4 pts per person
- 🔥 Streak after 3 days: +2 pts/day (max +10)
        """)


def page_feed(workouts: list):
    st.header("📸 Workout Feed")
    if not workouts:
        st.info("No workouts yet — be the first! 💪")
        return
    recent = sorted(workouts, key=lambda w: w["date"], reverse=True)[:30]
    for w in recent:
        render_workout_card(w)


def page_history(person: str, workouts: list):
    st.header(f"📋 {person}'s History")
    mine = [w for w in workouts if person in w["participants"]]
    if not mine:
        st.info("No workouts logged yet — get moving! 🏃")
        return

    streak  = compute_streak(workouts, person)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Workouts", len(mine))
    col2.metric("Total Points",   compute_total_points(workouts, person))
    col3.metric("This Month",     f"{compute_monthly_points(workouts, person)} pts")
    col4.metric("Streak 🔥",      f"{streak} days")

    # Intensity breakdown
    st.divider()
    st.subheader("⚡ Intensity Breakdown")
    intensity_counts = {}
    for w in mine:
        k = w.get("intensity", "unknown")
        intensity_counts[k] = intensity_counts.get(k, 0) + 1
    for k, cnt in sorted(intensity_counts.items(), key=lambda x: -x[1]):
        label = INTENSITY_LABELS.get(k, k).split("(")[0].strip()
        st.markdown(f"**{label}** — {cnt} workout{'s' if cnt != 1 else ''}")

    st.divider()
    st.subheader("All Workouts")
    for w in sorted(mine, key=lambda x: x["date"], reverse=True):
        render_workout_card(w)


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="Squad Sweat 💪",
        page_icon="💪",
        layout="centered",
    )

    st.markdown("""
    <style>
    .main > div { padding-top: 1rem; }
    [data-testid="stForm"] { border: none !important; padding: 0 !important; }
    .stButton > button {
        background: linear-gradient(135deg, #FF6B9D, #9B59B6);
        color: white !important;
        border: none;
        font-weight: 600;
        transition: opacity 0.2s;
    }
    .stButton > button:hover { opacity: 0.85; }
    div[data-testid="stMetricValue"] { font-size: 1.5rem !important; }
    </style>
    """, unsafe_allow_html=True)

    st.title("💪 Squad Sweat")
    st.caption("Alli · Andrea · Liv — let's get it 🔥")

    # ── Person picker ──
    if "person" not in st.session_state:
        st.session_state.person = None

    if st.session_state.person is None:
        st.markdown("### Who's here?")
        cols = st.columns(3)
        for i, person in enumerate(MEMBERS):
            with cols[i]:
                bg    = MEMBER_BG[person]
                color = MEMBER_COLORS[person]
                st.markdown(
                    f"<div style='background:{bg};border-radius:14px;padding:8px;text-align:center;"
                    f"border:2px solid {color}20'>",
                    unsafe_allow_html=True,
                )
                if st.button(
                    f"{MEMBER_EMOJIS[person]} **{person}**",
                    use_container_width=True,
                    key=f"pick_{person}",
                ):
                    st.session_state.person = person
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
        return

    person   = st.session_state.person
    workouts = load_workouts()

    with st.sidebar:
        color = MEMBER_COLORS[person]
        st.markdown(
            f"<div style='text-align:center'>"
            f"<div style='font-size:2.5rem'>{MEMBER_EMOJIS[person]}</div>"
            f"<h3 style='color:{color};margin:4px 0'>{person}</h3>"
            f"</div>",
            unsafe_allow_html=True,
        )
        lb = get_leaderboard(workouts)
        st.metric("🔥 Streak",    f"{lb[person]['streak']} days")
        st.metric("⭐ Points",    lb[person]["total_points"])
        st.metric("📅 This week", f"{lb[person]['weekly_workouts']} workouts")
        st.divider()

        # Quick-compare mini leaderboard
        st.markdown("**📊 Quick Standings**")
        ranked = sorted(MEMBERS, key=lambda p: lb[p]["total_points"], reverse=True)
        for rank, p in enumerate(ranked):
            mark = "👑 " if p == person else ""
            st.markdown(
                f"{medal(rank)} {mark}{p} — {lb[p]['total_points']} pts",
                unsafe_allow_html=True,
            )
        st.divider()
        if st.button("Switch user", use_container_width=True):
            st.session_state.person = None
            st.rerun()

    tab1, tab2, tab3, tab4 = st.tabs(["Log Workout", "Leaderboard", "Feed", "My History"])
    with tab1:
        page_log(person, workouts)
    with tab2:
        page_leaderboard(workouts)
    with tab3:
        page_feed(workouts)
    with tab4:
        page_history(person, workouts)


if __name__ == "__main__":
    main()
