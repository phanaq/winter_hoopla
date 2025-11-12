import streamlit as st
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configuration
DATA_FILE = "signup_data.json"
MAX_PLAYERS_PER_TYPE = 10

# Email configuration (set via environment variables or Streamlit secrets)
EMAIL_CONFIG = {
    "smtp_server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
    "smtp_port": int(os.getenv("SMTP_PORT", "587")),
    "sender_email": os.getenv("SENDER_EMAIL", ""),
    "sender_password": os.getenv("SENDER_PASSWORD", ""),
    "enabled": os.getenv("EMAIL_ENABLED", "false").lower() == "true"
}

# Try to get email config from Streamlit secrets
try:
    if "email" in st.secrets:
        EMAIL_CONFIG.update({
            "smtp_server": st.secrets.email.get("smtp_server", EMAIL_CONFIG["smtp_server"]),
            "smtp_port": st.secrets.email.get("smtp_port", EMAIL_CONFIG["smtp_port"]),
            "sender_email": st.secrets.email.get("sender_email", EMAIL_CONFIG["sender_email"]),
            "sender_password": st.secrets.email.get("sender_password", EMAIL_CONFIG["sender_password"]),
            "enabled": st.secrets.email.get("enabled", EMAIL_CONFIG["enabled"])
        })
except:
    pass


def load_data() -> Dict:
    """Load signup data from JSON file."""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
        # Ensure no_preference exists in all signups and waitlists for backward compatibility
        for week in data.get("signups", {}):
            if "no_preference" not in data["signups"][week]:
                data["signups"][week]["no_preference"] = []
        for week in data.get("waitlists", {}):
            if "no_preference" not in data["waitlists"][week]:
                data["waitlists"][week]["no_preference"] = []
        return data
    return {
        "players": {},  # {player_id: {name, email, type}}
        "signups": {},  # {week: {mmp: [player_ids], wmp: [player_ids], no_preference: [player_ids]}}
        "waitlists": {}  # {week: {mmp: [player_ids], wmp: [player_ids], no_preference: [player_ids]}}
    }


def save_data(data: Dict):
    """Save signup data to JSON file."""
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_week_key(date: datetime) -> str:
    """Get a week key in YYYY-MM-DD format (Monday of the week)."""
    # Get Monday of the week
    days_since_monday = date.weekday()
    monday = date - timedelta(days=days_since_monday)
    return monday.strftime("%Y-%m-%d")


def get_week_display(week_key: str) -> str:
    """Format week key for display."""
    date = datetime.strptime(week_key, "%Y-%m-%d")
    end_date = date + timedelta(days=6)
    return f"Week of {date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"


def get_available_weeks() -> List[str]:
    """Get list of available weeks (current week + next 4 weeks)."""
    today = datetime.now()
    weeks = []
    # Start from Monday of current week
    days_since_monday = today.weekday()
    current_monday = today - timedelta(days=days_since_monday)
    
    for i in range(5):  # Current week + 4 future weeks
        week_date = current_monday + timedelta(weeks=i)
        weeks.append(get_week_key(week_date))
    return weeks


def send_email(to_email: str, subject: str, body: str) -> bool:
    """Send an email notification."""
    if not EMAIL_CONFIG["enabled"] or not EMAIL_CONFIG["sender_email"]:
        return False
    
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_CONFIG["sender_email"]
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        
        server = smtplib.SMTP(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"])
        server.starttls()
        server.login(EMAIL_CONFIG["sender_email"], EMAIL_CONFIG["sender_password"])
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Failed to send email: {str(e)}")
        return False


def get_xmp_category(data: Dict, week: str) -> str:
    """
    Determine which category (MMP or WMP) XMP players count towards for a given week.
    Returns "MMP" or "WMP"
    """
    if week not in data["signups"]:
        return "DOM this week"  # Default
    
    mmp_count = len(data["signups"][week].get("mmp", []))
    wmp_count = len(data["signups"][week].get("wmp", []))
    
    if mmp_count < wmp_count:
        return "DOM this week"
    elif wmp_count < mmp_count:
        return "DOW this week"
    else:
        # If equal, count towards MMP by default
        return "DOM this week"


def get_effective_counts(data: Dict, week: str) -> Tuple[int, int]:
    """
    Calculate effective counts for MMP and WMP, accounting for XMP players.
    XMP players count towards whichever category has fewer players.
    Returns (effective_mmp_count, effective_wmp_count)
    """
    if week not in data["signups"]:
        return (0, 0)
    
    mmp_count = len(data["signups"][week].get("mmp", []))
    wmp_count = len(data["signups"][week].get("wmp", []))
    no_pref_count = len(data["signups"][week].get("no_preference", []))
    
    # Distribute no_preference players to the category with fewer players
    if mmp_count < wmp_count:
        effective_mmp = mmp_count + no_pref_count
        effective_wmp = wmp_count
    elif wmp_count < mmp_count:
        effective_mmp = mmp_count
        effective_wmp = wmp_count + no_pref_count
    else:
        # If equal, distribute to MMP by default
        effective_mmp = mmp_count + no_pref_count
        effective_wmp = wmp_count
    
    return (effective_mmp, effective_wmp)


def signup_player(data: Dict, player_id: str, week: str, player_type: str) -> Tuple[bool, Optional[str]]:
    """
    Sign up a player for a week.
    Returns (success, message)
    """
    if week not in data["signups"]:
        data["signups"][week] = {"mmp": [], "wmp": [], "no_preference": []}
    if week not in data["waitlists"]:
        data["waitlists"][week] = {"mmp": [], "wmp": [], "no_preference": []}
    
    signups = data["signups"][week][player_type]
    waitlist = data["waitlists"][week][player_type]
    
    # Check if already signed up
    if player_id in signups:
        return False, "You are already signed up for this week!"
    
    # Check if already on waitlist
    if player_id in waitlist:
        return False, "You are already on the waitlist for this week!"
    
    # For XMP (no_preference) players, check against the category with fewer players
    if player_type == "no_preference":
        mmp_count = len(data["signups"][week]["mmp"])
        wmp_count = len(data["signups"][week]["wmp"])
        no_pref_count = len(data["signups"][week]["no_preference"])
        
        # Determine which category to count towards (before adding this player)
        if mmp_count < wmp_count:
            # Count towards MMP limit
            # Effective MMP count after adding would be: mmp_count + no_pref_count + 1
            if mmp_count + no_pref_count + 1 <= MAX_PLAYERS_PER_TYPE:
                signups.append(player_id)
                save_data(data)
                return True, f"Successfully signed up for {get_week_display(week)}!"
            else:
                waitlist.append(player_id)
                save_data(data)
                position = len(waitlist)
                return True, f"Added to waitlist (position {position}) for {get_week_display(week)}."
        elif wmp_count < mmp_count:
            # Count towards WMP limit
            # Effective WMP count after adding would be: wmp_count + no_pref_count + 1
            if wmp_count + no_pref_count + 1 <= MAX_PLAYERS_PER_TYPE:
                signups.append(player_id)
                save_data(data)
                return True, f"Successfully signed up for {get_week_display(week)}!"
            else:
                waitlist.append(player_id)
                save_data(data)
                position = len(waitlist)
                return True, f"Added to waitlist (position {position}) for {get_week_display(week)}."
        else:
            # Equal counts, count towards MMP by default
            # Effective MMP count after adding would be: mmp_count + no_pref_count + 1
            if mmp_count + no_pref_count + 1 <= MAX_PLAYERS_PER_TYPE:
                signups.append(player_id)
                save_data(data)
                return True, f"Successfully signed up for {get_week_display(week)}!"
            else:
                waitlist.append(player_id)
                save_data(data)
                position = len(waitlist)
                return True, f"Added to waitlist (position {position}) for {get_week_display(week)}."
    else:
        # For MMP and WMP, use standard logic
        if len(signups) < MAX_PLAYERS_PER_TYPE:
            signups.append(player_id)
            save_data(data)
            return True, f"Successfully signed up for {get_week_display(week)}!"
        else:
            # Add to waitlist
            waitlist.append(player_id)
            save_data(data)
            position = len(waitlist)
            return True, f"Added to waitlist (position {position}) for {get_week_display(week)}."


def remove_player(data: Dict, player_id: str, week: str, player_type: str) -> Tuple[bool, Optional[str]]:
    """
    Remove a player from signup and promote from waitlist if needed.
    Returns (success, message)
    """
    if week not in data["signups"] or week not in data["waitlists"]:
        return False, "No signups found for this week."
    
    signups = data["signups"][week][player_type]
    waitlist = data["waitlists"][week][player_type]
    
    # Check if player is signed up
    if player_id in signups:
        signups.remove(player_id)
        
        # Promote from waitlist if available
        if waitlist:
            promoted_id = waitlist.pop(0)
            signups.append(promoted_id)
            
            # Send email notification to promoted player
            if promoted_id in data["players"]:
                promoted_player = data["players"][promoted_id]
                email = promoted_player.get("email", "")
                if email:
                    subject = f"Winter Hoopla - You've been promoted from the waitlist for {get_week_display(week)}"
                    body = f"Hi {promoted_player['name']},\n\n"
                    body += f"This is an automated email. You've been promoted from the waitlist and are now signed up "
                    body += f"for indoor goaltimate at ComEd Rec Center for the week of {get_week_display(week)}. "
                    body += f"If you can no longer attend, please remove your signup so that the next player on the waitlist can be promoted.\n\n"
                    body += "See you on the field!\n\n"
                    body += "- Annie"
                    send_email(email, subject, body)
            
            save_data(data)
            return True, "Removed from signup. Top waitlist player has been promoted and notified."
        else:
            save_data(data)
            return True, "Successfully removed from signup."
    
    # Check if player is on waitlist
    elif player_id in waitlist:
        waitlist.remove(player_id)
        save_data(data)
        return True, "Removed from waitlist."
    else:
        return False, "You are not signed up for this week."


def main():
    st.set_page_config(page_title="Goaltimate Signup", page_icon="🥏", layout="wide")
    
    st.title("Winter Hoopla - Session 1 (Mixed)")
    st.markdown("---")
    
    # Load data
    data = load_data()
    
    # Get available weeks (used in multiple places)
    weeks = get_available_weeks()
    week_options = {get_week_display(week): week for week in weeks}
    
    # Single week selector for all sections
    selected_week_display = st.selectbox(
        "Select Week",
        options=list(week_options.keys()),
        key="selected_week"
    )
    selected_week = week_options[selected_week_display]
    
    # Show signups for all weeks - no authentication required
    st.header("View Signups")
    
    if selected_week in data["signups"]:
        # Calculate effective counts for display
        effective_mmp, effective_wmp = get_effective_counts(data, selected_week)
        mmp_count = len(data["signups"][selected_week].get("mmp", []))
        wmp_count = len(data["signups"][selected_week].get("wmp", []))
        no_pref_count = len(data["signups"][selected_week].get("no_preference", []))
        
        st.write("XMP (players with no gender matching preference) will count towards whichever category has fewer players for a given week.")

        col1, col2, col3 = st.columns(3)

        
        
        with col1:
            st.subheader(f"MMP ({effective_mmp}/{MAX_PLAYERS_PER_TYPE})")
            if data["signups"][selected_week]["mmp"]:
                for idx, pid in enumerate(data["signups"][selected_week]["mmp"], 1):
                    player_name_display = data["players"].get(pid, {}).get("name", pid)
                    st.write(f"{idx}. {player_name_display}")
            else:
                st.info("No MMP players")
            
            # Show waitlist
            if selected_week in data["waitlists"] and data["waitlists"][selected_week].get("mmp"):
                st.markdown("**MMP Waitlist:**")
                for idx, pid in enumerate(data["waitlists"][selected_week]["mmp"], 1):
                    player_name_display = data["players"].get(pid, {}).get("name", pid)
                    st.write(f"  {idx}. {player_name_display}")
        
        with col2:
            st.subheader(f"WMP ({effective_wmp}/{MAX_PLAYERS_PER_TYPE})")
            if data["signups"][selected_week]["wmp"]:
                for idx, pid in enumerate(data["signups"][selected_week]["wmp"], 1):
                    player_name_display = data["players"].get(pid, {}).get("name", pid)
                    st.write(f"{idx}. {player_name_display}")
            else:
                st.info("No WMP players")
            
            # Show waitlist
            if selected_week in data["waitlists"] and data["waitlists"][selected_week].get("wmp"):
                st.markdown("**WMP Waitlist:**")
                for idx, pid in enumerate(data["waitlists"][selected_week]["wmp"], 1):
                    player_name_display = data["players"].get(pid, {}).get("name", pid)
                    st.write(f"  {idx}. {player_name_display}")
        
        with col3:
            st.subheader(f"XMP ({no_pref_count})")
            if data["signups"][selected_week].get("no_preference"):
                # Determine which category XMP players count towards
                xmp_category = get_xmp_category(data, selected_week)
                for idx, pid in enumerate(data["signups"][selected_week]["no_preference"], 1):
                    player_name_display = data["players"].get(pid, {}).get("name", pid)
                    st.write(f"{idx}. {player_name_display} ({xmp_category})")
            else:
                st.info("No XMP players")
            
            # Show waitlist
            if selected_week in data["waitlists"] and data["waitlists"][selected_week].get("no_preference"):
                st.markdown("**XMP Waitlist:**")
                # For waitlist, determine category based on current signups
                xmp_category = get_xmp_category(data, selected_week)
                for idx, pid in enumerate(data["waitlists"][selected_week]["no_preference"], 1):
                    player_name_display = data["players"].get(pid, {}).get("name", pid)
                    st.write(f"  {idx}. {player_name_display} ({xmp_category})")
    else:
        st.info("No signups for this week yet")
    
    st.markdown("---")
    
    # Player identification section - required for signup/removal
    st.header("Sign Up")
    st.caption("Enter your name and email to sign up or remove your signup. Email is required so that we can notify people who are moved up from the waitlist.")
    
    col_name, col_email = st.columns(2)
    
    with col_name:
        player_name = st.text_input("Your Name *", key="player_name", placeholder="Enter your name")
    
    with col_email:
        player_email = st.text_input("Your Email *", key="player_email", placeholder="your.email@example.com")
    
    # Validate that both name and email are provided
    player_id = None
    can_interact = False
    
    if player_name and player_email:
        # Basic email validation
        if "@" in player_email and "." in player_email.split("@")[1]:
            # Create or get player ID
            player_id = player_name.lower().strip().replace(" ", "_")
            
            # Store player info if not exists or update email
            if player_id not in data["players"]:
                data["players"][player_id] = {
                    "name": player_name,
                    "email": player_email,
                    "type": None
                }
            else:
                data["players"][player_id]["email"] = player_email
                data["players"][player_id]["name"] = player_name
            save_data(data)
            
            can_interact = True
        else:
            st.error("Please enter a valid email address")
    elif player_name or player_email:
        st.warning("⚠️ Both name and email are required to sign up or remove signup")
    
    if can_interact:
        
        
        # Check if player is signed up or on waitlist for the selected week
        is_signed_up = False
        is_on_waitlist = False
        player_type_current = None
        
        if selected_week in data["signups"]:
            if player_id in data["signups"][selected_week].get("mmp", []):
                is_signed_up = True
                player_type_current = "mmp"
            elif player_id in data["signups"][selected_week].get("wmp", []):
                is_signed_up = True
                player_type_current = "wmp"
            elif player_id in data["signups"][selected_week].get("no_preference", []):
                is_signed_up = True
                player_type_current = "no_preference"
        
        if not is_signed_up and selected_week in data["waitlists"]:
            if player_id in data["waitlists"][selected_week].get("mmp", []):
                is_on_waitlist = True
                player_type_current = "mmp"
            elif player_id in data["waitlists"][selected_week].get("wmp", []):
                is_on_waitlist = True
                player_type_current = "wmp"
            elif player_id in data["waitlists"][selected_week].get("no_preference", []):
                is_on_waitlist = True
                player_type_current = "no_preference"
        
        # Consolidated Sign Up / Remove Signup section
        if is_signed_up or is_on_waitlist:
            # Show Remove Signup option
            st.subheader("Remove Signup")
            type_display = "XMP" if player_type_current == "no_preference" else player_type_current.upper()
            if is_signed_up:
                st.warning(f"✅ You are signed up as **{type_display}** for {selected_week_display}")
            elif is_on_waitlist:
                position = data["waitlists"][selected_week][player_type_current].index(player_id) + 1
                st.info(f"⏳ You are on the waitlist (position {position}) as **{type_display}** for {selected_week_display}")
            
            if st.button("Remove Signup", type="primary", key="remove_btn"):
                success, message = remove_player(data, player_id, selected_week, player_type_current)
                if success:
                    st.success(message)
                else:
                    st.error(message)
                st.rerun()
        else:
            # Show Sign Up option
            st.info(f"You are not signed up for {selected_week_display}")
            
            player_type = st.radio(
                "Gender Match",
                options=["MMP", "WMP", "XMP"],
                key="signup_type",
                index=None,
            )
            
            if player_type:
                # Convert display name to internal format
                player_type_internal = "no_preference" if player_type == "XMP" else player_type.lower()
                
                if st.button("Sign Up", type="primary", key="signup_btn"):
                    success, message = signup_player(data, player_id, selected_week, player_type_internal)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
                    st.rerun()
    
    # Footer with email configuration status
    st.markdown("---")
    if EMAIL_CONFIG["enabled"]:
        st.caption("✅ Email notifications enabled")
    else:
        st.caption("ℹ️ Email notifications disabled. Configure email settings to enable waitlist notifications.")


if __name__ == "__main__":
    main()
