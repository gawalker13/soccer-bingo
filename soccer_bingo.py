import streamlit as st
import asyncio
import random
from datetime import datetime, timedelta
import pytz
from fotmob import FotMob
from zoneinfo import ZoneInfo

# ----------------------------
# Helper: run async safely
# ----------------------------
def run_async(coro):
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.get_event_loop()
        if not loop.is_running():
            return loop.run_until_complete(coro)

        task = asyncio.ensure_future(coro)
        while not task.done():
            loop.run_until_complete(asyncio.sleep(0.01))
        return task.result()

# ----------------------------
# Timezone selection
# ----------------------------
st.set_page_config(page_title="Soccer Bingo", layout="centered")
st.title("Soccer Bingo")
st.write("Pick a game, then pick players or events to create your custom bingo board!")

user_tz_input = st.selectbox(
    "Select your timezone:",
    pytz.all_timezones,
    index=pytz.all_timezones.index("America/New_York")
)

def to_local(utc_str: str, tz: str):
    dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
    return dt.astimezone(ZoneInfo(tz))

# ----------------------------
# Fetch today's games (async)
# ----------------------------
async def get_todays_games(user_tz: str):
    today_local = datetime.now(ZoneInfo(user_tz)).date()

    today_key = today_local.strftime("%Y%m%d")
    tomorrow_key = (today_local + timedelta(days=1)).strftime("%Y%m%d")

    async with FotMob() as fotmob:
        data_today = await fotmob.get_matches_by_date(today_key)
        data_tomorrow = await fotmob.get_matches_by_date(tomorrow_key)

        combined = {"leagues": []}
        for block in (data_today, data_tomorrow):
            if block and isinstance(block, dict):
                combined["leagues"].extend(block.get("leagues", []))

        leagues_out = []
        for league in combined["leagues"]:
            new_league = dict(league)
            new_matches = []

            for match in league.get("matches", []):
                utc_str = match.get("status", {}).get("utcTime")
                if not utc_str:
                    continue
                local_dt = to_local(utc_str, user_tz)
                if local_dt.date() == today_local:
                    m = dict(match)
                    m["localTime"] = local_dt.strftime("%Y-%m-%d %H:%M %Z")
                    new_matches.append(m)

            if new_matches:
                new_league["matches"] = new_matches
                leagues_out.append(new_league)

        final_matches = []
        for league in leagues_out:
            for match in league["matches"]:
                label = f"{match['home']['name']} vs {match['away']['name']}"
                final_matches.append({
                    "label": label,
                    "id": match["id"],
                    "home_id": match["home"]["id"],
                    "home_name": match["home"]["name"],
                    "away_id": match["away"]["id"],
                    "away_name": match["away"]["name"],
                })

        return final_matches

# ----------------------------
# Fetch players from a match
# ----------------------------
async def get_players_from_game(game_id):
    async with FotMob() as fotmob:
        match_details = await fotmob.get_match_details(game_id)
        general = (match_details or {}).get("general", {}) or {}
        home_id = (general.get("homeTeam") or {}).get("id")
        away_id = (general.get("awayTeam") or {}).get("id")

        players = set()

        async def extract_team_players(team_id):
            if not team_id:
                return []
            team_data = await fotmob.get_team(team_id)
            squad_data = (team_data or {}).get("squad", {}).get("squad", [])
            out = []
            for group in squad_data:
                title = (group.get("title") or "").lower()
                if "coach" in title or "manager" in title:
                    continue
                for member in group.get("members", []):
                    name = member.get("name")
                    if name and isinstance(name, str):
                        out.append(name.strip())
            return out

        if home_id:
            players.update(await extract_team_players(home_id))
        if away_id:
            players.update(await extract_team_players(away_id))

        return sorted(players)

# ----------------------------
# Bingo utilities
# ----------------------------
def check_bingo(marked):
    if len(marked) != 25:
        return False
    grid = [marked[i:i+5] for i in range(0, 25, 5)]

    for row in grid:
        if all(row):
            return True
    for c in range(5):
        if all(grid[r][c] for r in range(5)):
            return True
    if all(grid[i][i] for i in range(5)):
        return True
    if all(grid[i][4 - i] for i in range(5)):
        return True
    return False

# ----------------------------
# Event pools
# ----------------------------
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

# ----------------------------
# Rules / instructions
# ----------------------------
with st.expander("How to play"):
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

# ----------------------------
# Load today's games
# ----------------------------
with st.spinner("Loading today's games..."):
    games_today = run_async(get_todays_games(user_tz_input))

if not games_today:
    st.error("No games found for today. Try again later!")
    st.stop()

selected_label = st.selectbox("Select a game", [m["label"] for m in games_today])
selected_game = next(m for m in games_today if m["label"] == selected_label)

with st.spinner("Fetching players..."):
    PLAYERS = run_async(get_players_from_game(selected_game["id"]))

if not PLAYERS:
    st.warning("No players found automatically. You can manually add them below.")
    manual_players = st.text_area("Enter player names (comma-separated)")
    PLAYERS = [p.strip() for p in manual_players.split(",") if p.strip()]

teams = [selected_game["home_name"], selected_game["away_name"]]

# ----------------------------
# Bingo builder UI
# ----------------------------
st.subheader("Create up to 24 Bingo Squares")

if "bingo_choices" not in st.session_state:
    st.session_state.bingo_choices = []

col1, col2, col3 = st.columns(3)

with col1:
    choice_type = st.selectbox("Type", ["Player", "Team", "Game"])
with col2:
    if choice_type == "Player":
        chosen_subject = st.selectbox("Choose player", PLAYERS)
        chosen_event = st.selectbox("Choose event", PLAYER_EVENTS)
    elif choice_type == "Team":
        chosen_subject = st.selectbox("Choose team", teams)
        chosen_event = st.selectbox("Choose event", TEAM_EVENTS)
    else:
        chosen_subject = st.selectbox("Game event", [selected_game["label"]])
        chosen_event = st.selectbox("Choose event", GAME_EVENTS)
with col3:
    if st.button("➕ Add to List"):
        if len(st.session_state.bingo_choices) < 24:
            new_item = f"{chosen_subject} {chosen_event}"
            if new_item in st.session_state.bingo_choices:
                st.warning("That square is already in your list.")
            else:
                st.session_state.bingo_choices.append(new_item)
        else:
            st.warning("You already have 24 squares!")

# Show current choices
if st.session_state.bingo_choices:
    st.markdown("### Your Current Bingo Squares")
    for idx, choice in enumerate(st.session_state.bingo_choices, start=1):
        st.markdown(f"{idx}. {choice}")
    if st.button("↩️ Undo Last"):
        removed = st.session_state.bingo_choices.pop()
        st.success(f"Removed: {removed}")

# ----------------------------
# Generate board
# ----------------------------
if st.button("Generate Bingo Board"):
    bingo_lines = st.session_state.bingo_choices.copy()
    total_needed = 24

    AUTO_POOL = []

    for p in PLAYERS:
        for ev in PLAYER_EVENTS:
            AUTO_POOL.append(f"{p} {ev}")

    for team in teams:
        for ev in TEAM_EVENTS:
            AUTO_POOL.append(f"{team} {ev}")

    for ev in GAME_EVENTS:
        AUTO_POOL.append(f"{selected_game['label']} {ev}")

    random.shuffle(AUTO_POOL)

    while len(bingo_lines) < total_needed and AUTO_POOL:
        cand = AUTO_POOL.pop()
        if cand not in bingo_lines:
            bingo_lines.append(cand)

    while len(bingo_lines) < total_needed:
        bingo_lines.append("Random event")

    random.shuffle(bingo_lines)

    bingo_lines.insert(12, "⭐FREE SQUARE⭐")

    st.session_state.bingo_board = bingo_lines
    st.session_state.marked = [False] * 25
    st.session_state.marked[12] = True

# ----------------------------
# NEW BINGO POPUP (YOUR VERSION)
# ----------------------------
@st.dialog("🎉 BINGO! 🎉")
def bingo_dialog():
    st.markdown(
        """
        ### You've got 5 in a row!
        Congratulations — your Bingo board has a winner!

        ---
        #### What to do next:
        - If you **want to continue playing** or accidentally marked a square,
          just **close this popup** by pressing the **"X"** in the top corner.
        - If you **want to start a new game**, simply **reload the page**.
        """
    )

if st.session_state.get("bingo"):
    bingo_dialog()
    st.session_state["bingo"] = False

# ----------------------------
# Render Bingo Board
# ----------------------------
if "bingo_board" in st.session_state:
    st.subheader("Your Bingo Board")

    if "marked" not in st.session_state:
        st.session_state.marked = [False] * 25
        st.session_state.marked[12] = True

    for i in range(0, 25, 5):
        cols = st.columns(5)
        for j, col in enumerate(cols):
            idx = i + j
            text = st.session_state.bingo_board[idx]
            marked = st.session_state.marked[idx]

            bg_color = "#6EE7B7" if marked else "#F3F4F6"

            with col:
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
                    unsafe_allow_html=True,
                )

                if st.button("✅", key=f"check_{idx}", use_container_width=True):
                    st.session_state.marked[idx] = not marked

                    if check_bingo(st.session_state.marked):
                        st.session_state["bingo"] = True

                    st.rerun()
