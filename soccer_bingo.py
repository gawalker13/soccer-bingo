import streamlit as st
import asyncio
import random
from datetime import datetime, timedelta
import pytz
from fotmob import FotMob
from zoneinfo import ZoneInfo

# ----------------------------
# Page config
# ----------------------------
st.set_page_config(page_title="Soccer Bingo", layout="centered")

# ----------------------------
# Global CSS
# ----------------------------
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@400;500;600&display=swap');

  :root {
    --pitch:         #0a3d1f;
    --pitch-mid:     #0f5c2e;
    --grass:         #16a34a;
    --lime:          #a3e635;
    --chalk:         #f0fdf4;
    --marked:        #bbf7d0;
    --marked-border: #22c55e;
    --free:          #fef08a;
    --free-border:   #eab308;
    --radius:        14px;
  }

  html, body, [data-testid="stAppViewContainer"] {
    background: linear-gradient(160deg, #0a3d1f 0%, #0f5c2e 60%, #166534 100%) !important;
    min-height: 100vh;
  }
  [data-testid="stAppViewContainer"] > .main { background: transparent !important; }

  /* Hide Streamlit chrome */
  #MainMenu, footer, header { visibility: hidden; }
  [data-testid="stToolbar"] { display: none; }

  /* ── Hero ── */
  .bingo-hero {
    text-align: center;
    padding: 2.5rem 1rem 1rem;
  }
  .bingo-hero h1 {
    font-family: 'Bebas Neue', sans-serif;
    font-size: clamp(3rem, 8vw, 5.5rem);
    letter-spacing: 0.06em;
    color: var(--lime);
    line-height: 1;
    text-shadow: 0 4px 20px rgba(0,0,0,0.4);
    margin: 0;
  }
  .bingo-hero p {
    font-family: 'DM Sans', sans-serif;
    color: #bbf7d0cc;
    font-size: 1.05rem;
    margin-top: 0.4rem;
  }

  /* ── Section headings ── */
  .section-heading {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.35rem;
    letter-spacing: 0.08em;
    color: var(--lime);
    margin: 1.5rem 0 0.5rem;
    text-shadow: 0 2px 8px rgba(0,0,0,0.3);
  }

  /* ── Widget labels — light on green ── */
  div[data-testid="stSelectbox"] label,
  div[data-testid="stTextArea"] label,
  div[data-testid="stSelectbox"] > label {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.85rem !important;
    font-weight: 700 !important;
    color: #f0fdf4 !important;
  }

  /* Select box — dark bg so text is always readable */
  div[data-testid="stSelectbox"] > div > div {
    border-radius: 10px !important;
    border-color: #a3e635 !important;
    background-color: #0f5c2e !important;
    color: #f0fdf4 !important;
    font-family: 'DM Sans', sans-serif !important;
  }

  /* Caption text */
  div[data-testid="stCaptionContainer"] p {
    color: #bbf7d0aa !important;
    font-family: 'DM Sans', sans-serif !important;
  }

  /* ── Buttons ── */
  .stButton > button {
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    border-radius: 10px !important;
    transition: all 0.18s ease !important;
    background: var(--pitch-mid) !important;
    color: var(--lime) !important;
    border: 1px solid #a3e63544 !important;
  }
  .stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 18px rgba(0,0,0,0.25) !important;
    border-color: var(--lime) !important;
  }

  /* Generate board button */
  .big-btn .stButton > button {
    background: linear-gradient(90deg, #16a34a, #a3e635) !important;
    color: #14532d !important;
    border: none !important;
    font-family: 'Bebas Neue', sans-serif !important;
    font-size: 1.4rem !important;
    letter-spacing: 0.1em !important;
    padding: 0.75rem !important;
  }

  /* ── Choice list ── */
  .choice-item {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.45rem 0.75rem;
    background: #ffffff18;
    border-radius: 8px;
    margin-bottom: 0.4rem;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.9rem;
    color: #f0fdf4;
    border: 1px solid #ffffff18;
  }
  .choice-num {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1rem;
    color: var(--lime);
    min-width: 1.4rem;
  }

  /* ── Bingo board ── */
  .bingo-header-row {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 8px;
    padding: 0.5rem 0 0;
  }
  .bingo-letter {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 2.2rem;
    color: var(--lime);
    text-align: center;
    text-shadow: 0 2px 10px rgba(0,0,0,0.3);
    letter-spacing: 0.05em;
  }
  .bingo-cell {
    background: #fff;
    border-radius: 10px;
    padding: 8px 6px 4px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 110px;
    text-align: center;
    border: 2px solid transparent;
    transition: background 0.2s, border-color 0.2s, transform 0.15s;
  }
  .bingo-cell.marked {
    background: var(--marked);
    border-color: var(--marked-border);
    transform: scale(0.97);
  }
  .bingo-cell.free-square {
    background: var(--free);
    border-color: var(--free-border);
  }
  .bingo-cell-text {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.72rem;
    font-weight: 600;
    color: #1f2937;
    line-height: 1.35;
    word-break: break-word;
  }
  .bingo-cell.marked .bingo-cell-text { color: #14532d; }

  /* ── Misc ── */
  div[data-testid="stAlert"] {
    border-radius: 10px !important;
    font-family: 'DM Sans', sans-serif !important;
  }
  hr { border-color: #ffffff22 !important; margin: 1rem 0 !important; }
  h2, h3 {
    font-family: 'Bebas Neue', sans-serif !important;
    color: var(--lime) !important;
    letter-spacing: 0.06em !important;
  }
</style>
""", unsafe_allow_html=True)


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
# Hero
# ----------------------------
st.markdown("""
<div class="bingo-hero">
  <h1>⚽ SOCCER BINGO</h1>
  <p>Pick a game · Build your board · Mark as it happens</p>
</div>
""", unsafe_allow_html=True)


# ----------------------------
# How to play
# ----------------------------
with st.expander("📋 How to play"):
    st.markdown("""
1. **Select your timezone** to see today's fixtures.
2. **Pick a match** from the dropdown.
3. **Add up to 24 custom squares** using player, team, or game events.
4. Fewer than 24? The board auto-fills the rest randomly.
5. The **center square is free**.
6. Click **✅** under each square as events happen — get **5 in a row** to win!
    """)


# ----------------------------
# Timezone
# ----------------------------
st.markdown('<div class="section-heading">🌍 Your Timezone</div>', unsafe_allow_html=True)
user_tz_input = st.selectbox(
    "Timezone",
    pytz.all_timezones,
    index=pytz.all_timezones.index("America/New_York"),
    label_visibility="collapsed",
)


# ----------------------------
# Async helpers
# ----------------------------
def to_local(utc_str: str, tz: str):
    dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
    return dt.astimezone(ZoneInfo(tz))


async def get_todays_games(user_tz: str):
    today_local  = datetime.now(ZoneInfo(user_tz)).date()
    today_key    = today_local.strftime("%Y%m%d")
    tomorrow_key = (today_local + timedelta(days=1)).strftime("%Y%m%d")

    async with FotMob() as fotmob:
        data_today    = await fotmob.get_matches_by_date(today_key)
        data_tomorrow = await fotmob.get_matches_by_date(tomorrow_key)

        combined = {"leagues": []}
        for block in (data_today, data_tomorrow):
            if block and isinstance(block, dict):
                combined["leagues"].extend(block.get("leagues", []))

        leagues_out = []
        for league in combined["leagues"]:
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
                new_league = dict(league)
                new_league["matches"] = new_matches
                leagues_out.append(new_league)

        final_matches = []
        for league in leagues_out:
            for match in league["matches"]:
                label = f"{match['home']['name']} vs {match['away']['name']}"
                final_matches.append({
                    "label":     label,
                    "id":        match["id"],
                    "home_id":   match["home"]["id"],
                    "home_name": match["home"]["name"],
                    "away_id":   match["away"]["id"],
                    "away_name": match["away"]["name"],
                })
        return final_matches


async def get_players_from_game(home_id, away_id):
    """Fetch squads directly by team ID — avoids the blocked matchDetails endpoint."""
    async with FotMob() as fotmob:
        players = set()

        async def extract_team_players(team_id):
            if not team_id:
                return []
            team_data  = await fotmob.get_team(team_id)
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

        players.update(await extract_team_players(home_id))
        players.update(await extract_team_players(away_id))
        return sorted(players)


# ----------------------------
# Bingo logic
# ----------------------------
def check_bingo(marked):
    if len(marked) != 25:
        return False
    grid = [marked[i:i+5] for i in range(0, 25, 5)]
    for row in grid:
        if all(row): return True
    for c in range(5):
        if all(grid[r][c] for r in range(5)): return True
    if all(grid[i][i]     for i in range(5)): return True
    if all(grid[i][4 - i] for i in range(5)): return True
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
    "3+ crosses", "4+ crosses", "yellow card", "red card",
]
TEAM_EVENTS = [
    "8+ shots", "10+ shots", "2+ goals", "1+ set-piece goal", "4 SoT", "5+ SoT",
    "4 corners", "5+ corners", "10+ fouls", "3+ offsides",
    "300+ passes", "400+ passes", "90%+ pass accuracy", "60%+ possession",
    "2+ cards", "red card",
]
GAME_EVENTS = [
    "3 goals", "4+ goals", "penalty goal", "free kick goal",
    "own goal", "20+ fouls", "25+ shots",
]


# ----------------------------
# Load today's games
# ----------------------------
with st.spinner("Loading today's fixtures..."):
    games_today = run_async(get_todays_games(user_tz_input))

if not games_today:
    st.error("No games found for today. Try again later!")
    st.stop()


# ----------------------------
# Match selector
# ----------------------------
st.markdown('<div class="section-heading">🏟️ Select a Match</div>', unsafe_allow_html=True)
selected_label = st.selectbox("Match", [m["label"] for m in games_today], label_visibility="collapsed")
selected_game  = next(m for m in games_today if m["label"] == selected_label)

with st.spinner("Fetching squad info..."):
    PLAYERS = run_async(get_players_from_game(selected_game["home_id"], selected_game["away_id"]))

if not PLAYERS:
    st.warning("No players found automatically. Enter them manually below.")
    manual_players = st.text_area("Player names (comma-separated)")
    PLAYERS = [p.strip() for p in manual_players.split(",") if p.strip()]

teams = [selected_game["home_name"], selected_game["away_name"]]


# ----------------------------
# Bingo builder
# ----------------------------
st.markdown('<div class="section-heading">🎯 Build Your Squares</div>', unsafe_allow_html=True)
st.caption("Add up to 24 custom squares. The rest will be auto-filled.")

if "bingo_choices" not in st.session_state:
    st.session_state.bingo_choices = []

col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    choice_type = st.selectbox("Type", ["Player", "Team", "Game"])
with col2:
    if choice_type == "Player":
        chosen_subject = st.selectbox("Player", PLAYERS)
        chosen_event   = st.selectbox("Event",  PLAYER_EVENTS)
    elif choice_type == "Team":
        chosen_subject = st.selectbox("Team",  teams)
        chosen_event   = st.selectbox("Event", TEAM_EVENTS)
    else:
        chosen_subject = st.selectbox("Game",  [selected_game["label"]])
        chosen_event   = st.selectbox("Event", GAME_EVENTS)
with col3:
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    if st.button("➕ Add", use_container_width=True):
        if len(st.session_state.bingo_choices) >= 24:
            st.warning("Board is full (24 squares max).")
        else:
            new_item = f"{chosen_subject} — {chosen_event}"
            if new_item in st.session_state.bingo_choices:
                st.warning("Already added!")
            else:
                st.session_state.bingo_choices.append(new_item)
                st.rerun()

# Current choices list
if st.session_state.bingo_choices:
    st.markdown("<hr>", unsafe_allow_html=True)
    count = len(st.session_state.bingo_choices)
    st.markdown(
        f'<div style="font-family:\'DM Sans\',sans-serif;font-size:0.8rem;'
        f'color:#bbf7d0aa;margin-bottom:0.5rem;">{count}/24 custom squares added</div>',
        unsafe_allow_html=True,
    )
    items_html = "".join([
        f'<div class="choice-item"><span class="choice-num">{i}.</span>{c}</div>'
        for i, c in enumerate(st.session_state.bingo_choices, 1)
    ])
    st.markdown(items_html, unsafe_allow_html=True)
    if st.button("↩️ Undo Last"):
        removed = st.session_state.bingo_choices.pop()
        st.success(f"Removed: {removed}")
        st.rerun()


# ----------------------------
# Generate board
# ----------------------------
st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)
st.markdown('<div class="big-btn">', unsafe_allow_html=True)
if st.button("⚽ GENERATE BINGO BOARD", use_container_width=True):
    bingo_lines = st.session_state.bingo_choices.copy()

    AUTO_POOL = []
    for p in PLAYERS:
        for ev in PLAYER_EVENTS:
            AUTO_POOL.append(f"{p} — {ev}")
    for team in teams:
        for ev in TEAM_EVENTS:
            AUTO_POOL.append(f"{team} — {ev}")
    for ev in GAME_EVENTS:
        AUTO_POOL.append(f"{selected_game['label']} — {ev}")

    random.shuffle(AUTO_POOL)
    while len(bingo_lines) < 24 and AUTO_POOL:
        cand = AUTO_POOL.pop()
        if cand not in bingo_lines:
            bingo_lines.append(cand)
    while len(bingo_lines) < 24:
        bingo_lines.append("Random event")

    random.shuffle(bingo_lines)
    bingo_lines.insert(12, "⭐ FREE SQUARE ⭐")

    st.session_state.bingo_board = bingo_lines
    st.session_state.marked      = [False] * 25
    st.session_state.marked[12]  = True
    st.session_state["bingo"]    = False
    st.rerun()
st.markdown("</div>", unsafe_allow_html=True)


# ----------------------------
# Bingo popup
# ----------------------------
@st.dialog("🎉 BINGO!")
def bingo_dialog():
    st.markdown("""
### You've got 5 in a row!
Congratulations — your Bingo board has a winner!

---
- **Keep playing?** Close this popup with the ✕ button.
- **New game?** Reload the page.
    """)

if st.session_state.get("bingo"):
    bingo_dialog()
    st.session_state["bingo"] = False


# ----------------------------
# Render board
# ----------------------------
if "bingo_board" in st.session_state:
    st.markdown("<hr>", unsafe_allow_html=True)

    # B-I-N-G-O letters
    st.markdown("""
    <div class="bingo-header-row">
      <div class="bingo-letter">B</div>
      <div class="bingo-letter">I</div>
      <div class="bingo-letter">N</div>
      <div class="bingo-letter">G</div>
      <div class="bingo-letter">O</div>
    </div>
    """, unsafe_allow_html=True)

    if "marked" not in st.session_state:
        st.session_state.marked     = [False] * 25
        st.session_state.marked[12] = True

    for row in range(5):
        cols = st.columns(5)
        for col_idx, col in enumerate(cols):
            idx     = row * 5 + col_idx
            text    = st.session_state.bingo_board[idx]
            marked  = st.session_state.marked[idx]
            is_free = (idx == 12)

            cell_class   = "bingo-cell" + (" free-square" if is_free else " marked" if marked else "")
            status_emoji = "⭐" if is_free else ("✅" if marked else "")

            with col:
                st.markdown(
                    f'<div class="{cell_class}">'
                    f'<div class="bingo-cell-text">{text}</div>'
                    f'<div style="font-size:1.2rem;margin-top:4px">{status_emoji}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if not is_free:
                    btn_label = "✅" if not marked else "↩️"
                    if st.button(btn_label, key=f"cell_{idx}", use_container_width=True):
                        st.session_state.marked[idx] = not marked
                        if check_bingo(st.session_state.marked):
                            st.session_state["bingo"] = True
                        st.rerun()

    # Progress bar
    marked_count = sum(st.session_state.marked) - 1
    pct = int(marked_count / 24 * 100)
    st.markdown(f"""
    <div style="margin-top:1.5rem;text-align:center;">
      <div style="font-family:'DM Sans',sans-serif;color:#bbf7d0;font-size:0.85rem;margin-bottom:0.4rem;">
        {marked_count} / 24 squares marked
      </div>
      <div style="background:#0a3d1f;border-radius:99px;height:10px;overflow:hidden;border:1px solid #ffffff22;">
        <div style="background:linear-gradient(90deg,#16a34a,#a3e635);width:{pct}%;height:100%;
                    border-radius:99px;transition:width 0.4s ease;"></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<div class="footer"><div style="text-align:center"><small>Created By: Garrett Walker</small></div>', unsafe_allow_html=True)
