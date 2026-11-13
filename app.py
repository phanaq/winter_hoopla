import os
import smtplib
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from email.mime.text import MIMEText
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import streamlit as st

# ---------------------------------------------------------------------------
# Season settings — edit these each year
# ---------------------------------------------------------------------------
TZ = ZoneInfo("America/Chicago")
SEASON_TITLE = "Winter Hoopla - Session 1 (Mixed)"
LOCATION = "ComEd Rec Center Indoor Turf"
FIRST_SESSION = date(2026, 11, 16)  # Mondays
NUM_SESSIONS = 7
START_TIME = time(20, 15)
END_TIME = time(22, 15)
TIME_LABEL = "8:15 - 10:15pm"
PRICE = "$20"
MAX_PLAYERS_PER_SIDE = 10  # 10 MMP + 10 WMP

# Signups open on the Friday before each Monday session at this time.
SIGNUP_OPEN_DAYS_BEFORE = 3
SIGNUP_OPEN_TIME = time(17, 0)
# Weeks whose signups open at a different time than the usual Friday 5pm.
SIGNUP_OPEN_OVERRIDES = {
    date(2026, 11, 16): datetime(2026, 11, 11, 0, 0, tzinfo=TZ),  # week 1 opened early
}

VENMO_HANDLE = "aphan"
VENMO_ENABLED = False  # flip to True once Venmo is set up again
ZELLE_CONTACT = "winterhoopla@gmail.com"  # Zelle option is hidden while blank
CONTACT_EMAIL = "winterhoopla@gmail.com"
APP_URL = "https://winter-hoopla.streamlit.app/"
ORGANIZER_NOTE = ""  # e.g. "Annie and friends are attending but not included in the counts below."

# Designer assets (hosted on Google Drive)
FAVICON_DRIVE_ID = "1hpdyNpeAp5AXoyf4svHIog7X0i8h_FvX"
LOGO_DRIVE_ID = "1hSXQo-9SBkX62tROSl9d_CzjHY3L6zWb"

TABLE = "signups"
GENDER_LABELS = {"mmp": "MMP", "wmp": "WMP"}
PAYMENT_LABELS = {
    "venmo": f"I've paid on Venmo (@{VENMO_HANDLE})",
    "zelle": f"I've paid on Zelle ({ZELLE_CONTACT})",
    "in_person": "I'll pay cash in person at the field",
}

SESSIONS = [FIRST_SESSION + timedelta(weeks=i) for i in range(NUM_SESSIONS)]


# ---------------------------------------------------------------------------
# Config / clients
# ---------------------------------------------------------------------------
def _secret(section: str, key: str, env: str, default=""):
    try:
        if section in st.secrets and key in st.secrets[section]:
            return st.secrets[section][key]
    except Exception:
        pass
    return os.getenv(env, default)


EMAIL_CONFIG = {
    "smtp_server": _secret("email", "smtp_server", "SMTP_SERVER", "smtp.gmail.com"),
    "smtp_port": int(_secret("email", "smtp_port", "SMTP_PORT", 587)),
    "sender_email": _secret("email", "sender_email", "SENDER_EMAIL"),
    "sender_password": _secret("email", "sender_password", "SENDER_PASSWORD"),
    "enabled": str(_secret("email", "enabled", "EMAIL_ENABLED", "false")).lower() == "true",
}


@st.cache_resource
def get_db():
    from supabase import create_client

    url = _secret("supabase", "url", "SUPABASE_URL")
    key = _secret("supabase", "key", "SUPABASE_KEY")
    if not url or not key:
        st.error("Supabase is not configured. Add [supabase] url and key to .streamlit/secrets.toml.")
        st.stop()
    return create_client(url, key)


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def drive_image(file_id: str) -> Optional[bytes]:
    import requests

    try:
        res = requests.get(f"https://drive.google.com/uc?export=view&id={file_id}", timeout=10)
        res.raise_for_status()
        return res.content
    except Exception:
        return None


def now() -> datetime:
    # HOOPLA_NOW="2026-11-13 17:05" lets you preview the app at another time locally.
    override = os.getenv("HOOPLA_NOW")
    if override:
        return datetime.fromisoformat(override).replace(tzinfo=TZ)
    return datetime.now(TZ)


# ---------------------------------------------------------------------------
# Schedule
# ---------------------------------------------------------------------------
def signup_opens_at(session: date) -> datetime:
    if session in SIGNUP_OPEN_OVERRIDES:
        return SIGNUP_OPEN_OVERRIDES[session]
    return datetime.combine(session - timedelta(days=SIGNUP_OPEN_DAYS_BEFORE), SIGNUP_OPEN_TIME, TZ)


def session_ends_at(session: date) -> datetime:
    return datetime.combine(session, END_TIME, TZ)


def current_session(at: datetime) -> Optional[date]:
    """The next session that hasn't finished yet, or None when the season is over."""
    for s in SESSIONS:
        if at < session_ends_at(s):
            return s
    return None


def fmt_day(d: date) -> str:
    return d.strftime("%A, %B ") + str(d.day)


def fmt_dt(dt: datetime) -> str:
    return dt.strftime("%A, %B ") + str(dt.day) + dt.strftime(" at %-I:%M%p").lower()


# ---------------------------------------------------------------------------
# Roster logic
# ---------------------------------------------------------------------------
@dataclass
class Spot:
    row: Dict
    side: Optional[str]  # "mmp" / "wmp" for rostered players, None for waitlisted


def build_roster(rows: List[Dict]) -> Tuple[List[Spot], List[Spot]]:
    """Fill the roster in signup order. MMP and WMP each get MAX_PLAYERS_PER_SIDE spots."""
    counts = {"mmp": 0, "wmp": 0}
    roster, waitlist = [], []
    for row in sorted(rows, key=lambda r: r["id"]):  # ids increase in signup order
        side = row["gender_match"]
        if side not in counts:
            continue
        if counts[side] < MAX_PLAYERS_PER_SIDE:
            counts[side] += 1
            roster.append(Spot(row, side))
        else:
            waitlist.append(Spot(row, None))
    return roster, waitlist


def side_waitlist(waitlist: List[Spot], gender_match: str) -> List[Spot]:
    return [s for s in waitlist if s.row["gender_match"] == gender_match]


def waitlist_position(waitlist: List[Spot], row: Dict) -> int:
    """1-based position among waitlisted players of the same gender match."""
    same_side = side_waitlist(waitlist, row["gender_match"])
    return next(i for i, s in enumerate(same_side, 1) if s.row["id"] == row["id"])


def load_rows(session: date) -> List[Dict]:
    res = (
        get_db()
        .table(TABLE)
        .select("id,name,email,gender_match,payment_method,created_at")
        .eq("session_date", session.isoformat())
        .is_("cancelled_at", "null")
        .execute()
    )
    return res.data or []


def find_active(rows: List[Dict], email: str) -> Optional[Dict]:
    email = email.strip().lower()
    return next((r for r in rows if r["email"].lower() == email), None)


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
def send_email(to_email: str, subject: str, body: str, cc: Optional[str] = None) -> bool:
    if not EMAIL_CONFIG["enabled"] or not EMAIL_CONFIG["sender_email"]:
        return False
    try:
        msg = MIMEText(body, "plain")
        msg["From"] = EMAIL_CONFIG["sender_email"]
        msg["To"] = to_email
        if cc:
            msg["Cc"] = cc
        msg["Subject"] = subject
        with smtplib.SMTP(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"]) as server:
            server.starttls()
            server.login(EMAIL_CONFIG["sender_email"], EMAIL_CONFIG["sender_password"])
            server.send_message(msg)
        return True
    except Exception as e:
        st.warning(f"Couldn't send email to {to_email}: {e}")
        return False


def session_details(session: date) -> str:
    return f"Date/Time: {fmt_day(session)}, {TIME_LABEL}\nLocation: {LOCATION}\n"


def payment_options_text() -> str:
    return (
        f"Please pay {PRICE} using one of these options:\n"
        + (f"- Venmo: @{VENMO_HANDLE} (https://venmo.com/u/{VENMO_HANDLE}). Please include the date of play.\n"
           if VENMO_ENABLED else "")
        + f"- Zelle: {ZELLE_CONTACT}. Please include the date of play.\n"
        "- Cash in person at the field\n"
    )


def payment_reminder(method: Optional[str]) -> str:
    if method == "in_person":
        return "Please remember to pay Annie in person.\n"
    if method in ("venmo", "zelle"):
        return "Thank you for signing up!\n"
    return payment_options_text()  # no payment answer yet (e.g. a spot opened while they signed up)


def refund_note() -> str:
    return (
        f"If you can no longer make it, please remove your signup at {APP_URL} so the next player can join. "
        "You'll get a confirmation email, and Annie will refund your payment as soon as she can if you've already paid.\n"
    )


def email_status(row: Dict, session: date, on_roster: bool, position: Optional[int] = None):
    if on_roster:
        subject = f"Winter Hoopla - You're in for {fmt_day(session)}"
        body = (
            f"Hi {row['name']},\n\n"
            "You're signed up for Mixed Winter Hoopla indoor goaltimate.\n\n"
            f"{session_details(session)}\n"
            f"{payment_reminder(row['payment_method'])}\n"
            f"{refund_note()}\n"
            "See you on the field!\n- Annie\n\n(This is an automated email.)"
        )
    else:
        label = GENDER_LABELS[row["gender_match"]]
        subject = f"Winter Hoopla - Waitlisted for {fmt_day(session)}"
        body = (
            f"Hi {row['name']},\n\n"
            f"You're #{position} on the {label} waitlist for Mixed Winter Hoopla indoor goaltimate. "
            "No payment is needed for now. If a spot opens up, we'll email you with payment options.\n\n"
            f"{session_details(session)}\n"
            f"If you no longer want a spot, please remove yourself from the waitlist at {APP_URL}.\n\n"
            "- Annie\n\n(This is an automated email.)"
        )
    send_email(row["email"], subject, body)


def email_promoted(row: Dict, session: date):
    body = (
        f"Hi {row['name']},\n\n"
        "A spot opened up and you've been moved off the waitlist. You're now signed up for "
        "Mixed Winter Hoopla indoor goaltimate.\n\n"
        f"{session_details(session)}\n"
        f"{payment_options_text()}\n"
        f"{refund_note()}\n"
        "See you on the field!\n- Annie\n\n(This is an automated email.)"
    )
    send_email(row["email"], f"Winter Hoopla - You have a spot for {fmt_day(session)}", body)


CANCEL_PAYMENT_TEXT = {
    "venmo": "Payment: you marked that you paid on Venmo. Annie will refund your payment as soon as she can.",
    "zelle": "Payment: you marked that you paid on Zelle. Annie will refund your payment as soon as she can.",
    "in_person": "Payment: you hadn't paid yet (you planned to pay in person), so there's nothing to refund.",
    None: (
        "Payment: no payment was marked on the signup form. If you already paid on Zelle, "
        "Annie will refund your payment as soon as she can."
    ),
}


def email_cancelled(row: Dict, session: date, was_on_roster: bool, promoted: List[Dict]):
    """Confirm a cancellation to the player. Dropouts from the roster also CC the organizer."""
    label = GENDER_LABELS[row["gender_match"]]
    if was_on_roster:
        moved_up = ", ".join(p["name"] for p in promoted) or "No one (the spot is open)"
        body = (
            f"Hi {row['name']},\n\n"
            f"Your cancellation for {fmt_day(session)} went through. You're no longer signed up.\n\n"
            f"{CANCEL_PAYMENT_TEXT.get(row.get('payment_method'), CANCEL_PAYMENT_TEXT[None])}\n\n"
            "Details:\n"
            f"Name: {row['name']}\n"
            f"Email: {row['email']}\n"
            f"Gender match: {label}\n"
            f"Removed at: {fmt_dt(datetime.now(TZ))}\n"
            f"Moved up from the waitlist: {moved_up}\n\n"
            "Hope to see you another week!\n- Annie\n\n(This is an automated email.)"
        )
        send_email(row["email"], f"Winter Hoopla - Cancellation confirmed for {fmt_day(session)}", body, cc=CONTACT_EMAIL)
    else:
        body = (
            f"Hi {row['name']},\n\n"
            f"You've been removed from the {label} waitlist for {fmt_day(session)}. No payment was taken, so there's nothing to refund.\n\n"
            "Hope to see you another week!\n- Annie\n\n(This is an automated email.)"
        )
        send_email(row["email"], f"Winter Hoopla - Removed from the waitlist for {fmt_day(session)}", body)


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------
def do_signup(session: date, name: str, email: str, gender_match: str, payment: Optional[str]) -> Tuple[bool, str]:
    rows = load_rows(session)
    if find_active(rows, email):
        return False, "That email is already signed up for this week."
    try:
        inserted = (
            get_db()
            .table(TABLE)
            .insert({
                "session_date": session.isoformat(),
                "name": name.strip(),
                "email": email.strip().lower(),
                "gender_match": gender_match,
                "payment_method": payment,
            })
            .execute()
        ).data[0]
    except Exception as e:
        if "duplicate" in str(e).lower() or "23505" in str(e):
            return False, "That email is already signed up for this week."
        raise

    roster, waitlist = build_roster(load_rows(session))
    if any(s.row["id"] == inserted["id"] for s in roster):
        email_status(inserted, session, True)
        if payment is None:  # a spot opened up between loading the page and submitting
            return True, f"Good news, a spot opened up and you're signed up! 🎉 Check your email for payment options."
        return True, "You're signed up! 🎉"
    position = waitlist_position(waitlist, inserted)
    label = GENDER_LABELS[inserted["gender_match"]]
    email_status(inserted, session, False, position)
    return True, f"{label} spots are full, so you've been added to the {label} waitlist (#{position}). No payment needed unless a spot opens up."


def do_cancel(session: date, row: Dict) -> str:
    before, _ = build_roster(load_rows(session))
    before_ids = {s.row["id"] for s in before}
    was_on_roster = row["id"] in before_ids
    get_db().table(TABLE).update({"cancelled_at": datetime.now(TZ).isoformat()}).eq("id", row["id"]).execute()
    after, _ = build_roster(load_rows(session))
    promoted = [s.row for s in after if s.row["id"] not in before_ids]
    for p in promoted:
        email_promoted(p, session)
    email_cancelled(row, session, was_on_roster, promoted)
    if not was_on_roster:
        return "You've been removed from the waitlist. A confirmation email is on its way."
    msg = "Your signup was removed. A confirmation email is on its way, and Annie will refund your payment as soon as she can if you already paid."
    if promoted:
        msg += " The next player on the waitlist has been moved up."
    return msg


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
def render_info():
    st.markdown(
        f"""
Session runs {SESSIONS[0].strftime('%B %-d')} - {SESSIONS[-1].strftime('%B %-d')}

- Up to 20 players per week ({MAX_PLAYERS_PER_SIDE} MMP, {MAX_PLAYERS_PER_SIDE} WMP) on one field, 2:2 gender match ratio.
- **{PRICE} per night**, pay as you go, first come, first served. Signups open **Fridays** for the following Monday.
- We will use the full [USAG ruleset](https://usagoaltimate.usetopscore.com/full-rule-set), which includes **controlled contact**.
- Molded plastic or turf cleats are fine. Bring a light, a dark, and water.
- The first 15-30 minutes may be dedicated to drills depending on interest.
"""
    )


def render_payment_info():
    if VENMO_ENABLED:
        methods = f"Venmo: [@{VENMO_HANDLE}](https://venmo.com/u/{VENMO_HANDLE})  \nZelle: {ZELLE_CONTACT}"
    else:
        methods = f"We currently are accepting Zelle and cash. Venmo is not yet available.  \nZelle: {ZELLE_CONTACT}"
    st.markdown(f"**Suggested payment: {PRICE}**  \n{methods}")


def render_roster(session: date, roster: List[Spot], waitlist: List[Spot]):
    mmp = [s for s in roster if s.side == "mmp"]
    wmp = [s for s in roster if s.side == "wmp"]
    st.subheader("Who's playing")
    if ORGANIZER_NOTE:
        st.caption(ORGANIZER_NOTE)

    col1, col2 = st.columns(2)
    for col, title, spots in ((col1, "MMP", mmp), (col2, "WMP", wmp)):
        with col:
            st.markdown(f"#### {title} ({len(spots)}/{MAX_PLAYERS_PER_SIDE})")
            if spots:
                st.markdown("\n".join(f"{i}. {s.row['name']}" for i, s in enumerate(spots, 1)))
            else:
                st.caption(f"No {title} players yet")
            waiting = side_waitlist(waitlist, title.lower())
            if waiting:
                st.markdown(f"**{title} waitlist ({len(waiting)})**")
                st.markdown("\n".join(f"{i}. {s.row['name']}" for i, s in enumerate(waiting, 1)))

    if waitlist:
        st.caption("When a spot opens, the next player on that side's waitlist is moved up and emailed.")


def render_signup_form(session: date, roster: List[Spot]):
    st.subheader("Sign up")

    # Chosen outside the form so the page can react right away: payment is only
    # asked for when this side still has open spots.
    gm = st.radio(
        "Gender match *",
        options=list(GENDER_LABELS),
        format_func=GENDER_LABELS.get,
        index=None,
        horizontal=True,
        key="signup_gm",
    )
    spot_open = False
    if gm:
        label = GENDER_LABELS[gm]
        open_spots = MAX_PLAYERS_PER_SIDE - sum(1 for s in roster if s.side == gm)
        spot_open = open_spots > 0
        if spot_open:
            st.success(f"{open_spots} {label} spot{'s' if open_spots != 1 else ''} open.")
            render_payment_info()
        else:
            st.info(
                f"{label} spots are full, so you'll be added to the {label} waitlist. No payment needed now. "
                "If a spot opens up, we'll email you with payment options."
            )

    payment_options = (["venmo"] if VENMO_ENABLED else []) + (["zelle"] if ZELLE_CONTACT else []) + ["in_person"]
    with st.form("signup", clear_on_submit=False):
        c1, c2 = st.columns(2)
        name = c1.text_input("Full name *")
        email = c2.text_input("Email *", help="Used to notify you if you're moved up from the waitlist.")
        payment = None
        if spot_open:
            payment = st.radio("Payment *", options=payment_options, format_func=PAYMENT_LABELS.get, index=None)
        commit = st.checkbox("I plan to attend and will remove my signup ASAP if I can't make it.")
        submitted = st.form_submit_button("Join waitlist" if gm and not spot_open else "Sign up", type="primary")

    if submitted:
        errors = []
        if not name.strip():
            errors.append("Enter your name.")
        if "@" not in email or "." not in email.split("@")[-1]:
            errors.append("Enter a valid email address.")
        if not gm:
            errors.append("Choose a gender match.")
        if spot_open and not payment:
            errors.append("Choose how you're paying.")
        if not commit:
            errors.append("Please confirm you plan to attend.")
        if errors:
            for e in errors:
                st.error(e)
            return
        ok, msg = do_signup(session, name, email, gm, payment)
        st.session_state["flash"] = ("success" if ok else "error", msg)
        st.rerun()


def render_manage(session: date, rows: List[Dict], roster: List[Spot], waitlist: List[Spot]):
    st.subheader("Can't make it?")
    st.write("Enter the email you signed up with to remove your signup or waitlist spot.")
    email = st.text_input("Email", key="manage_email", label_visibility="collapsed", placeholder="your.email@example.com")
    if not email:
        return
    row = find_active(rows, email)
    if not row:
        st.info("No signup found for that email this week.")
        return
    if any(s.row["id"] == row["id"] for s in roster):
        st.success(f"{row['name']}, you're signed up as **{GENDER_LABELS[row['gender_match']]}**.")
        st.caption("If you remove your signup, you'll get a confirmation email and Annie will refund your payment as soon as she can if you've already paid.")
    else:
        label = GENDER_LABELS[row["gender_match"]]
        st.info(f"{row['name']}, you're #{waitlist_position(waitlist, row)} on the **{label}** waitlist.")
    if st.button("Remove my signup", type="primary"):
        st.session_state["flash"] = ("success", do_cancel(session, row))
        st.session_state.pop("manage_email", None)
        st.rerun()


def main():
    st.set_page_config(page_title="Mixed Winter Hoopla", page_icon=drive_image(FAVICON_DRIVE_ID) or "🥏", layout="wide")

    at = now()
    session = current_session(at)

    logo = drive_image(LOGO_DRIVE_ID)
    if logo:
        logo_col, header_col = st.columns([1, 4])
        logo_col.image(logo)
    else:
        header_col = st.container()

    with header_col:
        st.title("Session 1 (Mixed)" if logo else SEASON_TITLE)
        if session is None:
            st.success("That's a wrap on Session 1 Mixed — thanks for playing! 🥏")
            st.write(f"Questions or want updates on Session 2? Email {CONTACT_EMAIL}.")
            return
        week = SESSIONS.index(session) + 1
        st.subheader(f"Week {week} of {NUM_SESSIONS}: {fmt_day(session)}, {TIME_LABEL}")
        render_info()
    st.divider()

    opens = signup_opens_at(session)
    if at < opens:
        st.info(f"⏰ Signups for **{fmt_day(session)}** open **{fmt_dt(opens)}**. Check back then!")
        st.write(f"Questions? Email {CONTACT_EMAIL}.")
        return

    if "flash" in st.session_state:
        kind, msg = st.session_state.pop("flash")
        getattr(st, kind)(msg)

    rows = load_rows(session)
    roster, waitlist = build_roster(rows)

    st.warning(
        "If you need to cancel, remove your signup as soon as possible so somebody on the waitlist can join."
    )
    st.caption(
        "If <6 WMP sign up on a given week, MMP may be moved off the waitlist and we will play with no "
        "prescribed ratio. Anyone who is moved up from the waitlist will be notified by email by Monday."
    )

    render_roster(session, roster, waitlist)
    st.divider()

    left, right = st.columns([3, 2], gap="large")
    with left:
        render_signup_form(session, roster)
    with right:
        render_manage(session, rows, roster, waitlist)

    st.divider()
    st.caption(
        f"Questions or feedback? Email {CONTACT_EMAIL}."
        + (" You'll get an email when you sign up or move off the waitlist." if EMAIL_CONFIG["enabled"] else "")
    )


if __name__ == "__main__":
    main()
