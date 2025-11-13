import streamlit as st
import asyncio
import random
from datetime import date
from fotmob import FotMob

# ---------------- ASYNC HELPERS ----------------

def run_async(coro):
    """
    Safely run an async coroutine inside Streamlit.
    
    Streamlit runs inside an event loop, so directly calling asyncio.run()
    sometimes causes a RuntimeError. This helper:
      - Tries asyncio.run normally
      - If the event loop is already running (e.g., in Streamlit Cloud),
        it schedules the coroutine on the existing loop instead.
    """
    try:
        return asyncio.run(coro)
    # Streamlit often already has a running loop
    except RuntimeError:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Schedule the coroutine and return its task
            return loop.create_task(coro)
        # Run the coroutine in the current loop
        return loop.run_until_complete(coro)


# ---------------- FETCH TODAY'S GAMES ----------------

async def get_todays_games():
    """
    Fetch all football matches for today's date using the FotMob API.
    
    Steps:
      1. Format today's date as YYYYMMDD (FotMob requires this format).
      2. Call fotmob.get_matches_by_date() to retrieve data.
      3. Validate the response (FotMob sometimes returns unexpected structures).
      4. Extract all matches across all leagues.
      5. Return a cleaned list of match info for dropdown selection.

    Returns:
        list[dict]: A list of matches with names and IDs, or an empty list on error.
    """
    async with FotMob() as fotmob:

        # FotMob expects YYYYMMDD format
        today = date.today().strftime("%Y%m%d")

        # Attempt to fetch matches for today
        try:
            matches_by_date = await fotmob.get_matches_by_date(today)
        except Exception as e:
            st.error(f"⚠️ Error fetching games: {e}")
            return []

        # Validate top-level response
        if not matches_by_date or not isinstance(matches_by_date, dict):
            st.warning("⚠️ Unexpected FotMob response:")
            st.write(matches_by_date)
            return []

        # Extract all leagues included in today's results
        leagues = matches_by_date.get("leagues", [])
        if not leagues:
            st.warning("⚠️ No leagues found for today's matches.")
            return []

        all_matches = []
        # Loop through each league and collect match data
        for league in leagues:
            for match in league.get("matches", []):
                home = match.get("home")
                away = match.get("away")

                # Skip matches missing home/away info
                if not home or not away:
                    continue

                # Build a clean match object for UI dropdowns
                all_matches.append({
                    "label": f"{home.get('name', 'Unknown')} vs {away.get('name', 'Unknown')}",
                    "id": match.get("id"),
                    "home_id": home.get("id"),
                    "home_name": home.get("name"),
                    "away_id": away.get("id"),
                    "away_name": away.get("name"),
                })

        # If no matches were successfully extracted, warn the user
        if not all_matches:
            st.warning("No matches found for today.")
        return all_matches


# ---------------- FETCH PLAYERS ----------------

async def get_players_from_game(game_id):
    """
    Fetch all player names from both teams in a given match.
    
    Steps:
      1. Retrieve match details to get the home/away team IDs.
      2. Fetch each team's squad separately using FotMob.
      3. Extract only player names (exclude coaches/managers).
      4. Return a sorted list of unique player names.
    """
    async with FotMob() as fotmob:
        # Retrieve detailed match info (contains team IDs)
        match_details = await fotmob.get_match_details(game_id)
        general = match_details.get("general", {}) or {}
        home_id = general.get("homeTeam", {}).get("id")
        away_id = general.get("awayTeam", {}).get("id")

        # Use a set to avoid duplicate player names
        players = set()

        async def extract_team_players(team_id):
            """
            Fetch the full squad for a team and extract player names.
            Squad structure example:
              squad -> squad -> groups -> members -> name
              
            Coaches/managers are stored in separate groups, so filter them out.
            """
            team_data = await fotmob.get_team(team_id)
            squad_data = team_data.get("squad", {}).get("squad", [])
            team_players = []

            for group in squad_data:
                # Skip coaching staff groups
                title = group.get("title", "").lower()
                if "coach" in title or "manager" in title:
                    continue
                # Extract names of actual players
                for member in group.get("members", []):
                    name = member.get("name")
                    if name and isinstance(name, str):
                        team_players.append(name.strip())
            return team_players
        
        # Fetch home players
        if home_id:
            players.update(await extract_team_players(home_id))

        # Fetch away players
        if away_id:
            players.update(await extract_team_players(away_id))

        # Return sorted list for consistent dropdown order
        return sorted(players)


# ---------------- BINGO CHECK FUNCTION ----------------

def check_bingo(marked):
    """
    Determine whether a 5×5 bingo grid contains a completed line.
    
    The 'marked' list is expected to contain 25 boolean values:
      True  = cell is marked
      False = cell is unmarked
    
    Checks:
      - All horizontal rows
      - All vertical columns
      - Both diagonals
    """

    # Convert flat list of 25 booleans into a 5x5 grid
    grid = [marked[i:i+5] for i in range(0, 25, 5)]

    # Horizontal
    for row in grid:
        if all(row):
            return True

    # Vertical
    for c in range(5):
        if all(grid[r][c] for r in range(5)):
            return True

    # Diagonals
    if all(grid[i][i] for i in range(5)):
        return True
    if all(grid[i][4 - i] for i in range(5)):
        return True

    # No bingo found
    return False


# ---------------- STREAMLIT UI ----------------

# Set page metadata for Streamlit (title + centered layout)
st.set_page_config(page_title="Soccer Bingo", layout="centered")

# App header
st.title("Soccer Bingo")
st.write("Pick a game, then pick players or events to create your custom bingo board!")

# ---------------- RULES SECTION ----------------
st.subheader("Rules")

# Collapsible expander showing how the game works
with st.expander("Click Here"):
   st.markdown(
       """
       **How to play** 
       1. Pick a game from today's fixtures. 
       2. Create 24 custom bingo squares using players, teams, or game events. 
       3. If a player is substituted before halftime, the substitute counts. 
       4. Click the ✅ below squares as events happen.
       5. For confirmation on the stats, please go to fotmob.com and look for the game(s) you picked. Then look for your player(s) and look for the stat(s)


       ### Example Squares
       - **Vinícius Jr 2+ shots**
       - **Brazil 5+ corners**
       - **3+ goals in match**
       """
   )

# --- Fetch today's games ---
with st.spinner("Loading today's games..."):
    # Asynchronously load today's matches from FotMob
    games_today = run_async(get_todays_games())

# If nothing is returned, stop the app
if not games_today:
    st.error("No games found for today. Try again later!")
    st.stop()

# --- Select a game ---
# Dropdown listing all games (formatted labels)
selected_label = st.selectbox("Select a game", [m["label"] for m in games_today])

# Retrieve the full match dict based on the selected label
selected_game = next(m for m in games_today if m["label"] == selected_label)

# --- Fetch players from selected match ---
with st.spinner("Fetching players..."):

    # Pull player names from both squads
    PLAYERS = run_async(get_players_from_game(selected_game["id"]))

# If automatic player fetch fails, allow manual entry
if not PLAYERS:
    st.warning("No players found automatically. You can manually add them below.")
    PLAYERS = st.text_area("Enter player names (comma-separated)").split(",")
    PLAYERS = [p.strip() for p in PLAYERS if p.strip()]

# List of team names (home + away)
teams = [selected_game["home_name"], selected_game["away_name"]]

# --- Event categories ---
# Different categories available depending on the selection type
PLAYER_EVENTS = [
    "2 shots", "3 shots", "4+ shots", "1 SoT", "2+ SoT",
    "anytime assist", "anytime goalscorer", "3 saves", "4 saves", "5+ saves",
    "3+ tackles", "3 clearances", "4+ clearances", "2 fouls", "3+ fouls",
    "35+ accurate passes", "40+ accurate passes", "50+ attempted passes",
    "90%+ pass accuracy", "2 successful dribbles", "3+ successful dribbles",
    "3+ crosses", "4+ crosses", "yellow card", "red card"
]

TEAM_EVENTS = [
    "8+ shots", "10+ shots", "2+ goals", "1+ set-piece goal", "4 SoT", "5+ SoT",
    "4 corners", "5+ corners", "10+ fouls", "3+ offsides",
    "300+ passes", "400+ passes", "90%+ pass accuracy", "60%+ possession",
    "2+ cards", "red card"
]

GAME_EVENTS = [
    "3 goals", "4+ goals", "penalty goal", "free kick goal",
    "own goal", "20+ fouls", "25+ shots"
]

# ---------------- BINGO BUILDER ----------------
st.subheader("Create 24 Bingo Squares")

# Store user-created squares in session_state
if "bingo_choices" not in st.session_state:
    st.session_state.bingo_choices = []

# Three-column layout for selection UI
col1, col2, col3 = st.columns(3)

with col1:
    # Choose the category type: Player / Team / Game
    choice_type = st.selectbox("Type", ["Player", "Team", "Game"])
with col2:
    # Dynamic UI depending on selected type
    if choice_type == "Player":
        chosen_subject = st.selectbox("Choose player", PLAYERS)
        chosen_event = st.selectbox("Choose event", PLAYER_EVENTS)
    elif choice_type == "Team":
        chosen_subject = st.selectbox("Choose team", teams)
        chosen_event = st.selectbox("Choose event", TEAM_EVENTS)
    else: # Game-wide events
        chosen_subject = st.selectbox("Game event", [selected_game["label"]])
        chosen_event = st.selectbox("Choose event", GAME_EVENTS)
with col3:
    # Add the chosen square to the board
    if st.button("➕ Add to Board"):
        if len(st.session_state.bingo_choices) < 24:
            st.session_state.bingo_choices.append(f"{chosen_subject} {chosen_event}")
        else:
            st.warning("You already have 24 squares!")

# --- Display current squares ---
if st.session_state.bingo_choices:
    st.markdown("### Your Current Bingo Squares")
    # List all 24 user squares
    for idx, choice in enumerate(st.session_state.bingo_choices, start=1):
        st.markdown(f"{idx}. {choice}")
    # Undo button removes the last-added square
    if st.button("↩️ Undo Last"):
        removed = st.session_state.bingo_choices.pop()
        st.success(f"Removed: {removed}")

# --- Generate board ---
if st.button("Generate Bingo Board"):
    # Copy and shuffle the user-created squares
    bingo_lines = st.session_state.bingo_choices.copy()
    random.shuffle(bingo_lines)

    # Final board needs 24 squares + 1 free square
    total_needed = 25 - 1
    bingo_lines = bingo_lines[:total_needed]

    # If fewer than 24 squares exist, pad with empty ones
    while len(bingo_lines) < total_needed:
        bingo_lines.append("")

    # Insert free square in the center
    bingo_lines.insert(12, "⭐FREE SQUARE⭐")

    # Store in session state for later display/interaction
    st.session_state.bingo_board = bingo_lines

    # Track which squares have been marked by the user
    st.session_state.marked = [False] * 25
    st.session_state.marked[12] = True  # Free square is always marked


# ---------------- BINGO BOARD ----------------
# Only show the board once it has been generated
if "bingo_board" in st.session_state:
    st.subheader("Your Bingo Board")

    # Initialize marked squares if missing (25 booleans = 5x5 grid)
    # Center square (#12) is always the free square → starts marked
    if "marked" not in st.session_state:
        st.session_state.marked = [False] * 25
        st.session_state.marked[12] = True

    bingo_triggered = False

    # Render the board 5 squares per row (5 rows total)
    for i in range(0, 25, 5):
        cols = st.columns(5)       # Create a row of 5 equal-width columns

        for j, col in enumerate(cols):
            idx = i + j       # Current cell index (0–24)
            text = st.session_state.bingo_board[idx]     # Text inside the square
            marked = st.session_state.marked[idx]    # Whether this square is marked

            # Background color depends on marked state
            bg_color = "#6EE7B7" if marked else "#F3F4F6"

            with col:
                # Draw the square using HTML/CSS for better styling
                st.markdown(
                    f"""
                    <div style="
                        text-align:center;
                        border:2px solid #ccc;
                        border-radius:12px;
                        background-color:{bg_color};
                        padding:6px;
                        height:110px;
                        display:flex;
                        flex-direction:column;
                        align-items:center;
                        justify-content:center;
                        color:black;
                        ">
                        <span style="font-size:14px; font-weight:bold;">{text}</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                # Button under each square to toggle marked/unmarked
                if st.button("✅", key=f"check_{idx}", use_container_width=True):
                    # Flip the marked state of this square
                    st.session_state.marked[idx] = not marked

                    # Check for bingo after each click
                    if check_bingo(st.session_state.marked):
                        st.session_state["bingo"] = True      # Signal that bingo occurred
                    st.rerun()    # Refresh UI so colors update instantly

# --- Define a Bingo dialog using Streamlit's new modal-style dialog ---
@st.dialog("🎉 BINGO! 🎉")
def bingo_dialog():
    st.markdown(
        """
        ### You've got 5 in a row!  
        Congratulations — your Bingo board has a winner!  

        ---
        #### What to do next:
        - If you **want to continue playing** or accidentally marked a square, just **close this popup** by pressing the **"X"** in the top corner.
        - If you **want to start a new game**, simply **reload the page**.

        """,
        unsafe_allow_html=True,
    )

# --- Trigger the dialog when bingo is detected ---
# If bingo was detected earlier, show the dialog now
if st.session_state.get("bingo"):
    bingo_dialog()
    # Reset the flag so the modal only shows once
    st.session_state["bingo"] = False
