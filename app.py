import streamlit as st
import json
import os
from typing import Dict, Optional, Tuple
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# VARIABLES
WEEK_NUMBER = 2
STATIC_TIME = "7-8:30pm"

# Configuration
DATA_FILE = "signup_data.json"
MAX_PLAYERS_PER_TYPE = 10
DATES = ["Tuesday November 18", "Tuesday November 25", "Tuesday December 2", "Tuesday December 9", "Tuesday December 16", "Tuesday December 23"]
STATIC_WEEK = f"week_{WEEK_NUMBER}"
STATIC_DATE = DATES[1]
TABLE_NAME = "app_data"

# Supabase configuration
SUPABASE_CONFIG = {
    "url": os.getenv("SUPABASE_URL", ""),
    "key": os.getenv("SUPABASE_KEY", ""),
    "enabled": os.getenv("SUPABASE_ENABLED", "false").lower() == "true"
}

# Try to get Supabase config from Streamlit secrets
try:
    if "supabase" in st.secrets:
        SUPABASE_CONFIG.update({
            "url": st.secrets.supabase.get("url", SUPABASE_CONFIG["url"]),
            "key": st.secrets.supabase.get("key", SUPABASE_CONFIG["key"]),
            "enabled": st.secrets.supabase.get("enabled", SUPABASE_CONFIG["enabled"])
        })
except:
    pass

# Initialize Supabase client if configured
supabase_client = None
if SUPABASE_CONFIG["enabled"] and SUPABASE_CONFIG["url"] and SUPABASE_CONFIG["key"]:
    try:
        from supabase import create_client, Client
        supabase_client: Optional[Client] = create_client(SUPABASE_CONFIG["url"], SUPABASE_CONFIG["key"])
    except Exception as e:
        st.warning(f"⚠️ Supabase connection failed: {str(e)}. Falling back to local file storage.")
        supabase_client = None
else:
    supabase_client = None

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
    """Load signup data from Supabase or JSON file."""
    # Try Supabase first if enabled
    if supabase_client:
        try:
            # Fetch data from Supabase
            response = supabase_client.table(TABLE_NAME).select("*").eq("id", "main").execute()
            
            if response.data and len(response.data) > 0:
                existing_data = response.data[0]["data"]
            else:
                existing_data = {}
            
            if STATIC_WEEK in existing_data:
                data = existing_data[STATIC_WEEK]
            else:
                # Initialize empty data structure
                data = {
                    "players": {},
                    "signups": {"mmp": [], "wmp": [], "no_preference": []},
                    "waitlists": {"mmp": [], "wmp": [], "no_preference": []}
                }
                # Save initial structure to Supabase
                save_data(data)
                return data
            
            # Ensure structure is correct (migrate if needed)
            data = _normalize_data_structure(data)
            return data
        except Exception as e:
            st.warning(f"⚠️ Failed to load from Supabase: {str(e)}. Falling back to local file.")
    
    # Fallback to JSON file
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
        data = _normalize_data_structure(data)
        return data
    
    # Return empty structure
    return {
        "players": {},
        "signups": {"mmp": [], "wmp": [], "no_preference": []},
        "waitlists": {"mmp": [], "wmp": [], "no_preference": []}
    }


def _normalize_data_structure(data: Dict) -> Dict:
    """Normalize data structure to ensure it has the correct format."""
    # Migrate old week-based structure to flat structure
    if "signups" in data and data["signups"] and isinstance(data["signups"], dict):
        # Check if it's the old structure (has week keys)
        # Old structure: {week: {mmp: [], wmp: [], no_preference: []}}
        # New structure: {mmp: [], wmp: [], no_preference: []}
        if data["signups"]:
            first_key = next(iter(data["signups"]))
            if first_key and isinstance(data["signups"][first_key], dict) and "mmp" in data["signups"][first_key]:
                # Old structure detected - migrate to new structure
                # For simplicity, we'll just reset to empty since data is reset each week
                data["signups"] = {"mmp": [], "wmp": [], "no_preference": []}
            elif "mmp" not in data["signups"]:
                # Ensure structure exists
                data["signups"] = {"mmp": [], "wmp": [], "no_preference": []}
        else:
            # Empty dict, initialize new structure
            data["signups"] = {"mmp": [], "wmp": [], "no_preference": []}
    else:
        data["signups"] = {"mmp": [], "wmp": [], "no_preference": []}
    
    if "waitlists" in data and data["waitlists"] and isinstance(data["waitlists"], dict):
        if data["waitlists"]:
            first_key = next(iter(data["waitlists"]))
            if first_key and isinstance(data["waitlists"][first_key], dict) and "mmp" in data["waitlists"][first_key]:
                # Old structure detected
                data["waitlists"] = {"mmp": [], "wmp": [], "no_preference": []}
            elif "mmp" not in data["waitlists"]:
                data["waitlists"] = {"mmp": [], "wmp": [], "no_preference": []}
        else:
            # Empty dict, initialize new structure
            data["waitlists"] = {"mmp": [], "wmp": [], "no_preference": []}
    else:
        data["waitlists"] = {"mmp": [], "wmp": [], "no_preference": []}
    
    # Ensure all required keys exist
    if "players" not in data:
        data["players"] = {}
    
    for key in ["mmp", "wmp", "no_preference"]:
        if key not in data["signups"]:
            data["signups"][key] = []
        if key not in data["waitlists"]:
            data["waitlists"][key] = []
    
    return data


def save_data(data: Dict):
    """Save signup data to Supabase or JSON file."""
    # Try Supabase first if enabled
    if supabase_client:
        try:
            # Load existing data from Supabase
            response = supabase_client.table(TABLE_NAME).select("*").eq("id", "main").execute()
            if response.data and len(response.data) > 0:
                existing_data = response.data[0]["data"]
            else:
                existing_data = {}

            # Update only the current week
            existing_data[STATIC_WEEK] = data

            # Upsert the updated data back to Supabase
            supabase_client.table(TABLE_NAME).upsert({
                "id": "main",
                "data": existing_data
            }).execute()
            return
        except Exception as e:
            st.warning(f"⚠️ Failed to save to Supabase: {str(e)}. Falling back to local file.")
    
    # Fallback to JSON file
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)




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


def get_xmp_category(data: Dict) -> str:
    """
    Determine which category (MMP or WMP) XMP players count towards.
    Returns "MMP" or "WMP"
    """
    mmp_count = len(data["signups"].get("mmp", []))
    wmp_count = len(data["signups"].get("wmp", []))
    
    if mmp_count < wmp_count:
        return "DOM this week"
    elif wmp_count < mmp_count:
        return "DOW this week"
    else:
        # If equal, count towards MMP by default
        return "DOM this week"


def get_effective_counts(data: Dict) -> Tuple[int, int]:
    """
    Calculate effective counts for MMP and WMP, accounting for XMP players.
    XMP players count towards whichever category has fewer players.
    Returns (effective_mmp_count, effective_wmp_count)
    """
    mmp_count = len(data["signups"].get("mmp", []))
    wmp_count = len(data["signups"].get("wmp", []))
    no_pref_count = len(data["signups"].get("no_preference", []))
    
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


def signup_player(data: Dict, player_id: str, player_type: str) -> Tuple[bool, Optional[str]]:
    """
    Sign up a player.
    Returns (success, message)
    """
    signups = data["signups"][player_type]
    waitlist = data["waitlists"][player_type]
    
    # Check if already signed up
    if player_id in signups:
        return False, "You are already signed up!"
    
    # Check if already on waitlist
    if player_id in waitlist:
        return False, "You are already on the waitlist!"
    
    # For XMP (no_preference) players, check against the category with fewer players
    if player_type == "no_preference":
        mmp_count = len(data["signups"]["mmp"])
        wmp_count = len(data["signups"]["wmp"])
        no_pref_count = len(data["signups"]["no_preference"])

        
        # Determine which category to count towards (before adding this player)
        if mmp_count < wmp_count:
            # Count towards MMP limit
            # Effective MMP count after adding would be: mmp_count + no_pref_count + 1
            if mmp_count + no_pref_count + 1 <= MAX_PLAYERS_PER_TYPE:
                signups.append(player_id)
                save_data(data)
                return True, "Successfully signed up!"
            else:
                waitlist.append(player_id)
                save_data(data)
                position = len(waitlist)
                return True, f"Added to waitlist (position {position})."
        elif wmp_count < mmp_count:
            # Count towards WMP limit
            # Effective WMP count after adding would be: wmp_count + no_pref_count + 1
            if wmp_count + no_pref_count + 1 <= MAX_PLAYERS_PER_TYPE:
                signups.append(player_id)
                save_data(data)
                return True, "Successfully signed up!"
            else:
                waitlist.append(player_id)
                save_data(data)
                position = len(waitlist)
                return True, f"Added to waitlist (position {position})."
        else:
            # Equal counts, count towards MMP by default
            # Effective MMP count after adding would be: mmp_count + no_pref_count + 1
            if mmp_count + no_pref_count + 1 <= MAX_PLAYERS_PER_TYPE:
                signups.append(player_id)
                save_data(data)
                return True, "Successfully signed up!"
            else:
                waitlist.append(player_id)
                save_data(data)
                position = len(waitlist)
                return True, f"Added to waitlist (position {position})."
    else:
        # For MMP and WMP, use standard logic
        if len(signups) < MAX_PLAYERS_PER_TYPE:
            signups.append(player_id)
            save_data(data)
            return True, "Successfully signed up!"
        else:
            # Add to waitlist
            waitlist.append(player_id)
            save_data(data)
            position = len(waitlist)
            return True, f"Added to waitlist (position {position})."


def remove_player(data: Dict, player_id: str, player_type: str) -> Tuple[bool, Optional[str]]:
    """
    Remove a player from signup and promote from waitlist if needed.
    Returns (success, message)
    """
    signups = data["signups"][player_type]
    waitlist = data["waitlists"][player_type]
    
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
                    subject = f"Winter Hoopla - You have a spot for {STATIC_DATE} {STATIC_TIME}"
                    body = f"Hi {promoted_player['name']},\n\n"
                    body += f"This is an automated email. You've been promoted from the waitlist and are now signed up "
                    body += f"to attend indoor goaltimate at ComEd Rec Center.\n\n"
                    body += f"Session Details:\n"
                    body += f"Date/Time: {STATIC_DATE}, {STATIC_TIME}\n"
                    body += f"Location: ComEd Rec Center\n\n"
                    body += f"If you can no longer attend, please remove your signup so that the next player on the waitlist can be promoted.\n"
                    body += f"You can manage your signup at: https://winter-hoopla.streamlit.app/\n\n"
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
        return False, "You are not signed up."


def main():
    st.set_page_config(page_title="Goaltimate Signup", page_icon="🥏", layout="wide")
    
    st.title("Winter Hoopla - Session 1 (Mixed)")
    
    # Load data
    data = load_data()
    
    # Display static date and location
    st.subheader(f"Week {WEEK_NUMBER}: **{STATIC_DATE}, {STATIC_TIME} at ComEd Rec Center**")
    st.write("- 7-7:15pm: Drills or small-sided reps")
    st.write("- 7:15-8:29pm: Scrimmage")
    st.write("- 8:29-8:30pm: Clean up :)")
    st.write("Indoor turf field. Molded plastic cleats and turf cleats are fine. No metal spikes allowed. Please bring a light, dark, and water.")

    st.markdown("---")
    
    # Show signups - no authentication required
    st.subheader("Current Signups and Waitlist")
    st.write(":red[Please do not sign up unless you plan to attend. If you need to cancel, please remove your signup ASAP to allow others to join.]")
    st.write("**:red[Please do not wait until Tuesday to cancel your signup.]**")
    st.write("If there are fewer than 6 WMP signed up for a given week, I will take MMP off the waitlist and we will run a game with no prescribed ratio. If this occurs I will notify players that are being moved up from the waitlist around noon the day of.")
    
    # Calculate effective counts for display
    effective_mmp, effective_wmp = get_effective_counts(data)
    no_pref_count = len(data["signups"].get("no_preference", []))

    st.write(":blue[Annie, Graham, and Tuc are attending this week but we are not including ourselves in the counts below.]")
    col1, col2, col3 = st.columns(3)
    st.write("XMP (players with no gender matching preference) will count towards whichever category has fewer players.")
    

    with col1:
        st.subheader(f"MMP ({effective_mmp}/{MAX_PLAYERS_PER_TYPE})")
        if data["signups"]["mmp"]:
            for idx, pid in enumerate(data["signups"]["mmp"], 1):
                player_name_display = data["players"].get(pid, {}).get("name", pid)
                st.write(f"{idx}. {player_name_display}")
        else:
            st.info("No MMP players")
        
        # Show waitlist
        if data["waitlists"].get("mmp"):
            st.markdown("**MMP Waitlist:**")
            for idx, pid in enumerate(data["waitlists"]["mmp"], 1):
                player_name_display = data["players"].get(pid, {}).get("name", pid)
                st.write(f"  {idx}. {player_name_display}")
    
    with col2:
        st.subheader(f"WMP ({effective_wmp}/{MAX_PLAYERS_PER_TYPE})")
        if data["signups"]["wmp"]:
            for idx, pid in enumerate(data["signups"]["wmp"], 1):
                player_name_display = data["players"].get(pid, {}).get("name", pid)
                st.write(f"{idx}. {player_name_display}")
        else:
            st.info("No WMP players")
        
        # Show waitlist
        if data["waitlists"].get("wmp"):
            st.markdown("**WMP Waitlist:**")
            for idx, pid in enumerate(data["waitlists"]["wmp"], 1):
                player_name_display = data["players"].get(pid, {}).get("name", pid)
                st.write(f"  {idx}. {player_name_display}")
    
    with col3:
        st.subheader(f"XMP ({no_pref_count})")
        if data["signups"].get("no_preference"):
            # Determine which category XMP players count towards
            xmp_category = get_xmp_category(data)
            for idx, pid in enumerate(data["signups"]["no_preference"], 1):
                player_name_display = data["players"].get(pid, {}).get("name", pid)
                st.write(f"{idx}. {player_name_display} ({xmp_category})")
        else:
            st.info("No XMP players")
        
        # Show waitlist
        if data["waitlists"].get("no_preference"):
            st.markdown("**XMP Waitlist:**")
            # For waitlist, determine category based on current signups
            xmp_category = get_xmp_category(data)
            for idx, pid in enumerate(data["waitlists"]["no_preference"], 1):
                player_name_display = data["players"].get(pid, {}).get("name", pid)
                st.write(f"  {idx}. {player_name_display} ({xmp_category})")
    
    st.markdown("---")
    
    # Player identification section - required for signup/removal
    st.subheader("Sign Up or Manage Sign Up / Waitlist")
    st.write("* **:blue[Sign Up]**: enter your name and email. Email is required so that we can automatically notify people who are moved up from the waitlist.")
    st.write("* **:red[Remove Your Signup or Waitlist Entry]:** To remove your signup or waitlist entry, enter the same name and email you used to sign up. You will see an option to remove yourself.")
    
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
        
        # Check if player is signed up or on waitlist
        is_signed_up = False
        is_on_waitlist = False
        player_type_current = None
        
        if player_id in data["signups"].get("mmp", []):
            is_signed_up = True
            player_type_current = "mmp"
        elif player_id in data["signups"].get("wmp", []):
            is_signed_up = True
            player_type_current = "wmp"
        elif player_id in data["signups"].get("no_preference", []):
            is_signed_up = True
            player_type_current = "no_preference"
        
        if not is_signed_up:
            if player_id in data["waitlists"].get("mmp", []):
                is_on_waitlist = True
                player_type_current = "mmp"
            elif player_id in data["waitlists"].get("wmp", []):
                is_on_waitlist = True
                player_type_current = "wmp"
            elif player_id in data["waitlists"].get("no_preference", []):
                is_on_waitlist = True
                player_type_current = "no_preference"
        
        # Consolidated Sign Up / Remove Signup section
        if is_signed_up or is_on_waitlist:
            # Show Remove Signup option
            st.subheader("Remove Signup")
            type_display = "XMP" if player_type_current == "no_preference" else player_type_current.upper()
            if is_signed_up:
                st.warning(f"✅ You are signed up as **{type_display}**")
            elif is_on_waitlist:
                position = data["waitlists"][player_type_current].index(player_id) + 1
                st.info(f"⏳ You are on the waitlist (position {position}) as **{type_display}**")
            
            if st.button("Remove Signup", type="primary", key="remove_btn"):
                success, message = remove_player(data, player_id, player_type_current)
                if success:
                    st.success(message)
                else:
                    st.error(message)
                st.rerun()
        else:
            # Show Sign Up option
            st.info("You are not signed up")
            
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
                    success, message = signup_player(data, player_id, player_type_internal)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
                    st.rerun()
    
    # Footer with email configuration status
    st.markdown("---")
    st.write("If you have any feedback or questions, please email Annie: winterhoopla@gmail.com")
    if EMAIL_CONFIG["enabled"]:
        st.caption("Email notifications enabled. You will receive an email if you are moved up from the waitlist.")
    else:
        st.caption("ℹ️ Email notifications disabled. Configure email settings to enable waitlist notifications.")


if __name__ == "__main__":
    main()
