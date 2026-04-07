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
import calendar

# ─── CONFIG ───────────────────────────────────────────────────────────────────

MEMBERS = ["Alli", "Andrea", "Liv"]
MEMBER_COLORS = {"Alli": "#FF6B9D", "Andrea": "#9B59B6", "Liv": "#3498DB"}
MEMBER_EMOJIS = {"Alli": "🌸", "Andrea": "💜", "Liv": "💙"}

# Points
SOLO_POINTS = 10
GROUP_POINTS = 15  # per person for a group workout
STREAK_BONUS = 5   # bonus per day of streak (after day 3)

# Email config — fill these in (see README)
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_RECIPIENTS = {
    "Alli": os.getenv("EMAIL_ALLI", ""),
    "Andrea": os.getenv("EMAIL_ANDREA", ""),
    "Liv": os.getenv("EMAIL_LIV", ""),
}

DATA_FILE = Path("data/workouts.json")
PHOTOS_DIR = Path("data/photos")
PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

# ─── DATA HELPERS ─────────────────────────────────────────────────────────────

def load_workouts():
    if DATA_FILE.exists():
        with open(DATA_FILE) as f:
            return json.load(f)
    return []

def save_workouts(workouts):
    with open(DATA_FILE, "w") as f:
        json.dump(workouts, f, indent=2)

def save_photo(uploaded_file, workout_id):
    if uploaded_file is None:
        return None
    ext = uploaded_file.name.split(".")[-1].lower()
    filename = f"{workout_id}.{ext}"
    path = PHOTOS_DIR / filename
    img = Image.open(uploaded_file)
    img.thumbnail((800, 800))
    img.save(path)
    return filename

def get_photo_b64(filename):
    path = PHOTOS_DIR / filename
    if path.exists():
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

# ─── COMPETITION LOGIC ────────────────────────────────────────────────────────

def compute_streak(workouts, person):
    """Count consecutive days worked out ending today or yesterday."""
    dates = sorted(set(
        w["date"] for w in workouts
        if person in w["participants"]
    ), reverse=True)
    if not dates:
        return 0
    today = datetime.date.today().isoformat()
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

def compute_points(workouts, person):
    total = 0
    for w in workouts:
        if person not in w["participants"]:
            continue
        base = GROUP_POINTS if len(w["participants"]) > 1 else SOLO_POINTS
        total += base
    return total

def compute_weekly_workouts(workouts, person):
    today = datetime.date.today()
    week_start = today - datetime.timedelta(days=today.weekday())
    count = 0
    for w in workouts:
        d = datetime.date.fromisoformat(w["date"])
        if d >= week_start and person in w["participants"]:
            count += 1
    return count

def compute_monthly_points(workouts, person):
    today = datetime.date.today()
    total = 0
    for w in workouts:
        d = datetime.date.fromisoformat(w["date"])
        if d.year == today.year and d.month == today.month and person in w["participants"]:
            base = GROUP_POINTS if len(w["participants"]) > 1 else SOLO_POINTS
            total += base
    return total

def get_leaderboard(workouts):
    results = {}
    for person in MEMBERS:
        results[person] = {
            "streak": compute_streak(workouts, person),
            "total_points": compute_points(workouts, person),
            "weekly_workouts": compute_weekly_workouts(workouts, person),
            "monthly_points": compute_monthly_points(workouts, person),
        }
    return results

def already_logged_today(workouts, person, date_str):
    return any(
        w["date"] == date_str and person in w["participants"]
        for w in workouts
    )

# ─── EMAIL ────────────────────────────────────────────────────────────────────

def send_email_notification(logger, participants, workout_type, notes, is_group):
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        return  # email not configured, silently skip
    recipients = [
        EMAIL_RECIPIENTS[p]
        for p in MEMBERS
        if p != logger and EMAIL_RECIPIENTS.get(p)
    ]
    if not recipients:
        return
    subject = f"💪 {logger} just logged a workout!"
    if is_group:
        together = " & ".join(p for p in participants if p != logger)
        subject = f"🏋️ {logger} + {together} worked out together!"
    body = f"""
Hey! Just letting you know:

{'🤝 GROUP WORKOUT — everyone gets bonus points!' if is_group else '💪 Solo workout'}

👤 Logged by: {logger}
{'👥 Team: ' + ', '.join(participants) if is_group else ''}
🏃 Type: {workout_type}
📝 Notes: {notes or 'None'}
📅 Date: {datetime.date.today().strftime('%A, %B %d')}

Check the leaderboard! 🏆
    """.strip()
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_SENDER
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, recipients, msg.as_string())
    except Exception:
        pass  # email failure shouldn't break the app

# ─── UI COMPONENTS ────────────────────────────────────────────────────────────

def render_medal(rank):
    return ["🥇", "🥈", "🥉", "4️⃣"][min(rank, 3)]

def render_workout_card(w, show_full=True):
    participants = w["participants"]
    is_group = len(participants) > 1
    date_obj = datetime.date.fromisoformat(w["date"])
    date_str = date_obj.strftime("%A, %b %d")
    label = " & ".join(participants) if is_group else participants[0]
    emoji = "🤝" if is_group else MEMBER_EMOJIS.get(participants[0], "💪")

    with st.container():
        cols = st.columns([1, 4])
        with cols[0]:
            if w.get("photo"):
                b64 = get_photo_b64(w["photo"])
                if b64:
                    st.markdown(
                        f'<img src="data:image/jpeg;base64,{b64}" '
                        f'style="width:100%;border-radius:12px;object-fit:cover;aspect-ratio:1"/>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(f"<div style='font-size:2.5rem;text-align:center'>{emoji}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='font-size:2.5rem;text-align:center'>{emoji}</div>", unsafe_allow_html=True)
        with cols[1]:
            pts = GROUP_POINTS if is_group else SOLO_POINTS
            color = MEMBER_COLORS.get(participants[0], "#888")
            st.markdown(
                f"<span style='color:{color};font-weight:700'>{label}</span> "
                f"<span style='color:#888;font-size:0.85rem'>• {date_str}</span> "
                f"<span style='background:#f0f0f0;border-radius:8px;padding:2px 8px;font-size:0.8rem'>+{pts} pts</span>",
                unsafe_allow_html=True,
            )
            st.caption(f"🏃 {w.get('workout_type', 'Workout')} · ⏱ {w.get('duration', '?')} min")
            if w.get("notes"):
                st.markdown(f"_{w['notes']}_")
            if is_group:
                st.success("🤝 Group workout — bonus points for everyone!", icon=None)
        st.divider()

# ─── PAGES ────────────────────────────────────────────────────────────────────

def page_log(person, workouts):
    st.header(f"{MEMBER_EMOJIS[person]} Log a Workout")
    today = datetime.date.today()

    if already_logged_today(workouts, person, today.isoformat()):
        st.success(f"✅ You already logged a workout today! Check the feed or log another if you did more.")

    with st.form("log_form", clear_on_submit=True):
        workout_type = st.selectbox("Workout type", [
            "Gym / Weights", "Running", "Cycling", "HIIT", "Yoga / Pilates",
            "Swimming", "Sports", "Walk / Hike", "Dance", "Other"
        ])
        duration = st.slider("Duration (minutes)", 10, 180, 45, 5)
        notes = st.text_area("Notes / how did it go?", placeholder="e.g. crushed leg day 🦵")

        st.markdown("---")
        is_group = st.checkbox("🤝 Group workout (we worked out together!)")
        group_members = []
        if is_group:
            others = [m for m in MEMBERS if m != person]
            group_members = st.multiselect(
                "Who else was there?", others, default=others
            )

        photo = st.file_uploader("📸 Upload a photo (optional)", type=["jpg", "jpeg", "png"])

        submitted = st.form_submit_button("💪 Log Workout", use_container_width=True)

    if submitted:
        participants = [person] + group_members if is_group else [person]
        workout_id = f"{person}_{today.isoformat()}_{len(workouts)}"
        photo_filename = save_photo(photo, workout_id)

        entry = {
            "id": workout_id,
            "date": today.isoformat(),
            "participants": participants,
            "workout_type": workout_type,
            "duration": duration,
            "notes": notes,
            "photo": photo_filename,
            "logged_by": person,
        }
        workouts.append(entry)
        save_workouts(workouts)

        pts = GROUP_POINTS if len(participants) > 1 else SOLO_POINTS
        st.balloons()
        st.success(f"🎉 Logged! You earned **+{pts} points**{'(group bonus!)' if len(participants) > 1 else ''}.")
        send_email_notification(person, participants, workout_type, notes, len(participants) > 1)
        st.rerun()


def page_leaderboard(workouts):
    st.header("🏆 Leaderboard")
    lb = get_leaderboard(workouts)
    today = datetime.date.today()
    week_start = today - datetime.timedelta(days=today.weekday())
    month_name = today.strftime("%B")

    # ── Overall Points ──
    st.subheader("⭐ All-Time Points")
    sorted_total = sorted(MEMBERS, key=lambda p: lb[p]["total_points"], reverse=True)
    for rank, person in enumerate(sorted_total):
        pts = lb[person]["total_points"]
        color = MEMBER_COLORS[person]
        bar_pct = int((pts / max(lb[p]["total_points"] for p in MEMBERS) * 100)) if pts > 0 else 0
        st.markdown(
            f"{render_medal(rank)} **{person}** "
            f"<span style='color:{color};font-size:1.3rem;font-weight:700'>{pts} pts</span>",
            unsafe_allow_html=True,
        )
        st.progress(bar_pct / 100)

    st.divider()

    # ── Streak Battle ──
    st.subheader("🔥 Current Streaks")
    sorted_streak = sorted(MEMBERS, key=lambda p: lb[p]["streak"], reverse=True)
    cols = st.columns(3)
    for i, person in enumerate(sorted_streak):
        with cols[i]:
            streak = lb[person]["streak"]
            flame = "🔥" * min(streak, 5)
            st.metric(
                label=f"{MEMBER_EMOJIS[person]} {person}",
                value=f"{streak} days",
                delta=flame if streak > 0 else "no streak",
            )

    st.divider()

    # ── Weekly Challenge ──
    st.subheader(f"📅 Weekly Challenge — Week of {week_start.strftime('%b %d')}")
    sorted_weekly = sorted(MEMBERS, key=lambda p: lb[p]["weekly_workouts"], reverse=True)
    for rank, person in enumerate(sorted_weekly):
        ww = lb[person]["weekly_workouts"]
        crown = " 👑" if rank == 0 and ww > 0 else ""
        st.markdown(f"{render_medal(rank)} **{person}** — {ww} workout{'s' if ww != 1 else ''} this week{crown}")

    st.divider()

    # ── Monthly Leaderboard ──
    st.subheader(f"📆 {month_name} Points")
    sorted_monthly = sorted(MEMBERS, key=lambda p: lb[p]["monthly_points"], reverse=True)
    for rank, person in enumerate(sorted_monthly):
        mp = lb[person]["monthly_points"]
        st.markdown(f"{render_medal(rank)} **{person}** — {mp} pts this month")


def page_feed(workouts):
    st.header("📸 Workout Feed")
    if not workouts:
        st.info("No workouts logged yet — be the first! 💪")
        return
    recent = sorted(workouts, key=lambda w: w["date"], reverse=True)[:20]
    for w in recent:
        render_workout_card(w)


def page_history(person, workouts):
    st.header(f"📋 {person}'s History")
    my_workouts = [w for w in workouts if person in w["participants"]]
    if not my_workouts:
        st.info("You haven't logged any workouts yet!")
        return

    total = len(my_workouts)
    pts = compute_points(workouts, person)
    streak = compute_streak(workouts, person)
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Workouts", total)
    col2.metric("Total Points", pts)
    col3.metric("Current Streak", f"{streak} 🔥")

    st.divider()
    st.subheader("All Workouts")
    for w in sorted(my_workouts, key=lambda x: x["date"], reverse=True):
        render_workout_card(w)


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="Squad Sweat 💪",
        page_icon="💪",
        layout="centered",
    )

    # Custom styling
    st.markdown("""
    <style>
    .main > div { padding-top: 1rem; }
    .stButton > button {
        background: linear-gradient(135deg, #FF6B9D, #9B59B6);
        color: white;
        border: none;
        font-weight: 600;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #9B59B6, #3498DB);
        color: white;
    }
    div[data-testid="stMetricValue"] { font-size: 1.6rem !important; }
    </style>
    """, unsafe_allow_html=True)

    st.title("💪 Squad Sweat")
    st.caption("Alli · Andrea · Liv — let's get it 🔥")

    # ── Who are you? ──
    if "person" not in st.session_state:
        st.session_state.person = None

    if st.session_state.person is None:
        st.markdown("### Who's here?")
        cols = st.columns(3)
        for i, person in enumerate(MEMBERS):
            with cols[i]:
                color = MEMBER_COLORS[person]
                if st.button(
                    f"{MEMBER_EMOJIS[person]}\n\n**{person}**",
                    use_container_width=True,
                    key=f"pick_{person}",
                ):
                    st.session_state.person = person
                    st.rerun()
        return

    person = st.session_state.person
    workouts = load_workouts()

    # Sidebar
    with st.sidebar:
        color = MEMBER_COLORS[person]
        st.markdown(
            f"<div style='font-size:2rem;text-align:center'>{MEMBER_EMOJIS[person]}</div>"
            f"<h3 style='text-align:center;color:{color}'>{person}</h3>",
            unsafe_allow_html=True,
        )
        lb = get_leaderboard(workouts)
        st.metric("🔥 Streak", f"{lb[person]['streak']} days")
        st.metric("⭐ Points", lb[person]["total_points"])
        st.metric("📅 This week", f"{lb[person]['weekly_workouts']} workouts")
        st.divider()
        if st.button("Switch user", use_container_width=True):
            st.session_state.person = None
            st.rerun()

    # Navigation tabs
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
