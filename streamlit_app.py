"""
Daily Draft - Multi-Sport Trivia App
A daily trivia game where users guess statistical leaders in NFL and MLB
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta
import pytz
import uuid

from config import SPORTS, MAX_POINTS_PER_QUESTION

from game_logic import (
    generate_questions_for_round,
    get_player_stat_for_question,
    calculate_score_emojis_and_points,
    get_daily_seed_and_date,
    get_eligible_players_for_autocomplete,
    format_share_text,
    format_combined_share_text,
    get_questions_per_round
)

from storage import (
    save_completed_game,
    get_completed_game,
    get_all_completed_games,
    has_completed_today,
    cleanup_old_games,
    load_games_from_local_storage
)

# --- Page Configuration ---
st.set_page_config(
    page_title="Daily Draft",
    page_icon="🏆",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- User Identification ---
def get_or_create_user_id():
    """Get or create a unique user ID that persists across sessions using localStorage"""
    get_storage_script = """
    <script>
    const userId = localStorage.getItem('dailydraft_user_id');
    if (userId) {
        const params = new URLSearchParams(window.location.search);
        if (!params.has('user_id')) {
            params.set('user_id', userId);
            window.history.replaceState({}, '', `${window.location.pathname}?${params}`);
        }
    }
    </script>
    """
    st.components.v1.html(get_storage_script, height=0)

    query_params = st.query_params
    user_id = query_params.get('user_id', None)

    if user_id:
        save_storage_script = f"""
        <script>
        localStorage.setItem('dailydraft_user_id', '{user_id}');
        </script>
        """
        st.components.v1.html(save_storage_script, height=0)
        return user_id

    new_user_id = str(uuid.uuid4())[:8]

    save_new_script = f"""
    <script>
    localStorage.setItem('dailydraft_user_id', '{new_user_id}');
    const params = new URLSearchParams(window.location.search);
    params.set('user_id', '{new_user_id}');
    window.history.replaceState({{}}, '', `${{window.location.pathname}}?${{params}}`);
    </script>
    """
    st.components.v1.html(save_new_script, height=0)
    st.query_params['user_id'] = new_user_id

    return new_user_id


# --- Session State Initialization ---
def init_session_state():
    """Initialize all session state variables"""
    defaults = {
        'data_cache': {},
        'user_id': None,

        # Sport selection
        'selected_sport': None,  # None = show landing page
        'game_mode': "Daily Challenge",

        # Current game state (used during active play)
        'current_questions': [],
        'user_guesses_ids': {},
        'user_guesses_names': {},
        'results': {},
        'current_question_index': 0,
        'current_round_total_score': 0,
        'current_round_max_score': 0,
        'round_in_progress': False,
        'eligible_players_cache': [],
        'show_result_for_q_index': None,
        'game_date': None,

        # Per-sport completion tracking
        'game_completed': {},  # {sport: bool}
        'daily_total_score': {},  # {sport: int}
        'daily_max_score': {},  # {sport: int}
        'daily_results': {},  # {sport: dict}
        'daily_questions': {},  # {sport: list}
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Get or create user ID
    if not st.session_state.user_id:
        st.session_state.user_id = get_or_create_user_id()

    # Load saved games from browser localStorage
    _, current_date_str = get_daily_seed_and_date()
    load_games_from_local_storage(current_date_str, st.session_state.user_id, list(SPORTS.keys()))

    for sport in SPORTS.keys():
        if sport not in st.session_state.game_completed:
            st.session_state.game_completed[sport] = False
            st.session_state.daily_total_score[sport] = 0
            st.session_state.daily_max_score[sport] = 0
            st.session_state.daily_results[sport] = {}
            st.session_state.daily_questions[sport] = []

        # Check for saved game
        if not st.session_state.game_completed.get(sport, False):
            saved_game = get_completed_game(current_date_str, st.session_state.user_id, sport)
            if saved_game:
                st.session_state.game_completed[sport] = True
                st.session_state.daily_total_score[sport] = saved_game['score']
                st.session_state.daily_max_score[sport] = saved_game['max_score']
                st.session_state.daily_results[sport] = saved_game['results']
                st.session_state.daily_questions[sport] = saved_game.get('questions', [])


def reset_round_state(sport):
    """Reset state for a new game round"""
    questions_per_round = get_questions_per_round(sport)
    st.session_state.user_guesses_ids = {i: None for i in range(questions_per_round)}
    st.session_state.user_guesses_names = {i: "Select a player..." for i in range(questions_per_round)}
    st.session_state.results = {}
    st.session_state.current_question_index = 0
    st.session_state.current_round_total_score = 0
    st.session_state.current_round_max_score = 0
    st.session_state.show_result_for_q_index = None


def prefetch_eligible_players(question_data, sport):
    """Prefetch eligible players for a question"""
    if question_data.get('data_issue', False) or question_data.get('correct_player_id') is None:
        return [("Error loading players", None)]

    position_slot = question_data['position_slot']
    year = question_data['year']

    # For NFL, strip trailing numbers (WR1 -> WR)
    if sport == "nfl":
        position_slot = position_slot.rstrip('12')

    return get_eligible_players_for_autocomplete(position_slot, year, st.session_state.data_cache, sport)


def check_and_update_daily_challenge(sport):
    """Check if it's a new day and handle daily challenge state for a sport."""
    _, current_date_str = get_daily_seed_and_date()

    if not st.session_state.game_completed.get(sport, False):
        saved_game = get_completed_game(current_date_str, st.session_state.user_id, sport)
        if saved_game:
            st.session_state.game_completed[sport] = True
            st.session_state.daily_total_score[sport] = saved_game['score']
            st.session_state.daily_max_score[sport] = saved_game['max_score']
            st.session_state.daily_results[sport] = saved_game['results']
            st.session_state.daily_questions[sport] = saved_game.get('questions', [])
            st.session_state.round_in_progress = False
            return False

    if st.session_state.game_date != current_date_str:
        st.session_state.game_date = current_date_str
        # Reset all sports for new day
        for s in SPORTS.keys():
            st.session_state.game_completed[s] = False
            st.session_state.daily_total_score[s] = 0
            st.session_state.daily_max_score[s] = 0
            st.session_state.daily_results[s] = {}
            st.session_state.daily_questions[s] = []
        st.session_state.round_in_progress = False
        return True

    return False


def start_daily_challenge(sport):
    """Start today's daily challenge for a sport"""
    daily_seed, current_date_str = get_daily_seed_and_date()

    with st.spinner(f"Generating today's {SPORTS[sport]['name']} questions..."):
        st.session_state.current_questions = generate_questions_for_round(
            st.session_state.data_cache,
            sport=sport,
            daily_mode=True,
            daily_seed=daily_seed
        )

    reset_round_state(sport)
    st.session_state.game_date = current_date_str
    st.session_state.round_in_progress = True
    st.session_state.game_completed[sport] = False

    if st.session_state.current_questions:
        st.session_state.eligible_players_cache = prefetch_eligible_players(
            st.session_state.current_questions[0], sport
        )


def start_practice_round(sport):
    """Start a new practice round for a sport"""
    with st.spinner(f"Generating {SPORTS[sport]['name']} practice questions..."):
        st.session_state.current_questions = generate_questions_for_round(
            st.session_state.data_cache,
            sport=sport,
            daily_mode=False
        )

    reset_round_state(sport)
    st.session_state.round_in_progress = True

    if st.session_state.current_questions:
        st.session_state.eligible_players_cache = prefetch_eligible_players(
            st.session_state.current_questions[0], sport
        )


def complete_daily_challenge(sport):
    """Mark daily challenge as completed and save results"""
    st.session_state.game_completed[sport] = True
    st.session_state.daily_total_score[sport] = st.session_state.current_round_total_score
    st.session_state.daily_max_score[sport] = st.session_state.current_round_max_score
    st.session_state.daily_results[sport] = st.session_state.results.copy()
    st.session_state.daily_questions[sport] = st.session_state.current_questions.copy()
    st.session_state.round_in_progress = False

    _, current_date_str = get_daily_seed_and_date()
    save_completed_game(
        current_date_str,
        st.session_state.user_id,
        sport,
        st.session_state.daily_total_score[sport],
        st.session_state.daily_max_score[sport],
        st.session_state.daily_results[sport],
        st.session_state.daily_questions[sport]
    )

    cleanup_old_games()


# --- Initialize ---
init_session_state()

# --- CSS Styling ---
st.markdown("""
<style>
    @media (max-width: 768px) {
        .stButton button {
            width: 100%;
            font-size: 16px !important;
            padding: 0.75rem !important;
            min-height: 48px;
        }
        h1 { font-size: 1.8rem !important; }
        h2 { font-size: 1.4rem !important; }
        h3 { font-size: 1.2rem !important; }
        .stSelectbox select {
            font-size: 16px !important;
            min-height: 48px;
        }
        .stRadio > label { font-size: 16px !important; }
        .element-container { margin-bottom: 1rem; }
        section[data-testid="stSidebar"] { display: none !important; }
        button[kind="header"] { display: none !important; }
        .css-1d391kg, [data-testid="stSidebarNav"] { display: none !important; }
        .streamlit-expanderHeader {
            font-size: 16px !important;
            padding: 0.75rem !important;
        }
    }
    .stButton button {
        border-radius: 8px;
        transition: all 0.3s ease;
    }
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .sport-card {
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)


# --- Landing Page ---
def render_landing_page():
    """Render the sport selection landing page"""
    st.title("🏆 Daily Draft")
    st.subheader("Choose Your Sport")

    _, current_date_str = get_daily_seed_and_date()

    col1, col2 = st.columns(2)

    with col1:
        nfl_config = SPORTS['nfl']
        nfl_completed = st.session_state.game_completed.get('nfl', False)

        st.markdown(f"### {nfl_config['icon']} {nfl_config['name']}")
        st.caption(f"{nfl_config['questions_per_round']} questions")

        if nfl_completed:
            score = st.session_state.daily_total_score.get('nfl', 0)
            st.success(f"Completed! Score: {score:,}")
        else:
            st.info("Not played today")

        if st.button(f"{nfl_config['icon']} Play NFL", type="primary", use_container_width=True, key="btn_nfl"):
            st.session_state.selected_sport = 'nfl'
            st.rerun()

    with col2:
        mlb_config = SPORTS['mlb']
        mlb_completed = st.session_state.game_completed.get('mlb', False)

        st.markdown(f"### {mlb_config['icon']} {mlb_config['name']}")
        st.caption(f"{mlb_config['questions_per_round']} questions")

        if mlb_completed:
            score = st.session_state.daily_total_score.get('mlb', 0)
            st.success(f"Completed! Score: {score:,}")
        else:
            st.info("Not played today")

        if st.button(f"{mlb_config['icon']} Play MLB", type="primary", use_container_width=True, key="btn_mlb"):
            st.session_state.selected_sport = 'mlb'
            st.rerun()

    # Combined results section
    st.markdown("---")

    all_completed = get_all_completed_games(current_date_str, st.session_state.user_id)
    if all_completed:
        total_score = sum(d.get('score', 0) for d in all_completed.values())

        st.markdown("### Today's Combined Score")
        st.metric("Total", f"{total_score:,}")

        # Show combined share text
        if len(all_completed) > 0:
            with st.expander("Share Your Results"):
                base_url = "https://dailydraft.streamlit.app"
                app_url = f"{base_url}/?user_id={st.session_state.user_id}"

                share_text = format_combined_share_text(all_completed, current_date_str, app_url)
                st.code(share_text, language=None)
                st.caption("Click the copy icon in the top-right of the box above!")

    # Time until next challenge
    pacific = pytz.timezone('America/Los_Angeles')
    now_pt = datetime.now(pacific)
    next_midnight_pt = now_pt.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    time_until_next = next_midnight_pt - now_pt
    hours, remainder = divmod(time_until_next.total_seconds(), 3600)
    minutes, _ = divmod(remainder, 60)
    st.caption(f"New challenges in: {int(hours):02d}h {int(minutes):02d}m (Pacific Time)")


# --- Game Page ---
def render_game_page(sport):
    """Render the game page for a specific sport"""
    sport_config = SPORTS[sport]
    questions_per_round = sport_config['questions_per_round']

    # Header with back button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("← Back", key="back_btn"):
            st.session_state.selected_sport = None
            st.session_state.round_in_progress = False
            st.session_state.current_questions = []
            st.rerun()

    st.title(f"{sport_config['icon']} Daily Draft {sport_config['name']} Trivia")
    st.caption(f"Guess the {sport_config['name']} stat leaders. {questions_per_round} questions. 1 game per day.")

    # Sidebar
    with st.sidebar:
        st.header("Game Mode")

        current_mode = st.session_state.game_mode
        selected_mode = st.radio(
            "Choose your challenge:",
            ("Daily Challenge", "Practice Play"),
            index=0 if current_mode == "Daily Challenge" else 1
        )

        if selected_mode != current_mode:
            st.session_state.game_mode = selected_mode
            st.session_state.round_in_progress = False
            st.session_state.current_questions = []
            st.session_state.show_result_for_q_index = None
            st.rerun()

        st.markdown("---")

        with st.expander("How to Play"):
            st.markdown(f"""
            **{questions_per_round} Questions. Guess the stat leaders.**

            **Scoring:**
            - Perfect (10,000 pts)
            - 80-99%
            - 60-79%
            - 40-59%
            - 20-39%
            - 1-19%
            - 0%

            **Daily Challenge:** One game per day, same for everyone!

            **Practice:** Unlimited random games.
            """)

        st.markdown("---")
        st.markdown("### Stats")
        if st.session_state.game_mode == "Daily Challenge" and st.session_state.game_completed.get(sport, False):
            score = st.session_state.daily_total_score.get(sport, 0)
            max_score = st.session_state.daily_max_score.get(sport, 0)
            st.metric("Today's Score", f"{score:,}")
            st.metric("Max Possible", f"{max_score:,}")
            if max_score > 0:
                pct = int((score / max_score) * 100)
                st.metric("Accuracy", f"{pct}%")

    st.markdown("---")

    # Check for new day
    if st.session_state.game_mode == "Daily Challenge":
        check_and_update_daily_challenge(sport)

    _, current_date_str = get_daily_seed_and_date()

    # Daily Challenge Flow
    if st.session_state.game_mode == "Daily Challenge":
        if st.session_state.game_completed.get(sport, False):
            st.success(f"You've completed today's {sport_config['name']} Challenge! ({current_date_str})")
            st.info("Come back tomorrow for a new challenge!")

            pacific = pytz.timezone('America/Los_Angeles')
            now_pt = datetime.now(pacific)
            next_midnight_pt = now_pt.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            time_until_next = next_midnight_pt - now_pt
            hours, remainder = divmod(time_until_next.total_seconds(), 3600)
            minutes, _ = divmod(remainder, 60)
            st.caption(f"Next challenge in: {int(hours):02d}h {int(minutes):02d}m (Pacific Time)")

        elif not st.session_state.round_in_progress:
            st.subheader(f"{current_date_str}")

            if st.button("Start Today's Challenge", type="primary", use_container_width=True, key="start_daily"):
                start_daily_challenge(sport)
                st.rerun()

    # Practice Play Flow
    elif st.session_state.game_mode == "Practice Play":
        if not st.session_state.round_in_progress:
            st.subheader("Practice Mode")

            if st.button("Start Practice Round", type="primary", use_container_width=True, key="start_practice"):
                start_practice_round(sport)
                st.rerun()

    # Question Display
    if st.session_state.round_in_progress:
        q_idx = st.session_state.current_question_index

        if q_idx < len(st.session_state.current_questions):
            q_data = st.session_state.current_questions[q_idx]

            progress = (q_idx + 1) / questions_per_round
            st.progress(progress)
            st.caption(f"Question {q_idx + 1} of {questions_per_round}")

            is_problem_question = (
                not isinstance(q_data, dict) or
                q_data.get('data_issue', False) or
                q_data.get('correct_player_id') is None
            )

            if is_problem_question:
                st.warning(f"Issue with Question {q_idx + 1}")
                st.error(f"{q_data.get('question_text', 'Data unavailable.')}")

                if st.button("Skip Question", key=f"skip_{q_idx}"):
                    st.session_state.results[q_idx] = {
                        'emojis': "⬛⬛⬛⬛⬛",
                        'points': 0,
                        'message': "Question skipped due to data issue."
                    }
                    st.session_state.current_question_index += 1

                    if st.session_state.current_question_index >= questions_per_round:
                        st.session_state.round_in_progress = False
                        if st.session_state.game_mode == "Daily Challenge":
                            complete_daily_challenge(sport)
                    else:
                        next_q = st.session_state.current_questions[st.session_state.current_question_index]
                        st.session_state.eligible_players_cache = prefetch_eligible_players(next_q, sport)

                    st.rerun()

            elif st.session_state.show_result_for_q_index == q_idx:
                result = st.session_state.results.get(q_idx)

                st.subheader(f"Question {q_idx + 1}")
                st.info(f"**{q_data.get('position_slot', 'N/A')} (Year: {q_data.get('year', 'N/A')})**\n\n{q_data.get('question_text', '')}")

                if result:
                    col1, col2 = st.columns([1, 1])

                    with col1:
                        st.markdown("### Your Answer")
                        user_guess = result.get('user_guess_name', "N/A")
                        if result.get('message') == "No player selected.":
                            st.write("No selection")
                        else:
                            st.write(f"**{user_guess}**")
                            stat_display = q_data.get('stat_category', 'N/A')
                            st.caption(f"{stat_display}: {result.get('guessed_stat', 'N/A')}")

                    with col2:
                        st.markdown("### Correct Answer")
                        st.write(f"**{q_data.get('correct_player_name', 'N/A')}**")
                        stat_display = q_data.get('stat_category', 'N/A')
                        st.caption(f"{stat_display}: {q_data.get('correct_stat_value', 'N/A')}")

                    st.markdown("---")
                    st.markdown(f"<div style='text-align: center; font-size: 2rem;'>{result.get('emojis', 'N/A')}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='text-align: center; font-size: 1.5rem; font-weight: bold;'>+{result.get('points', 0):,} points</div>", unsafe_allow_html=True)

                st.markdown("---")

                if st.session_state.current_question_index + 1 < questions_per_round:
                    if st.button("Next Question", type="primary", use_container_width=True):
                        st.session_state.current_question_index += 1
                        st.session_state.show_result_for_q_index = None

                        next_q = st.session_state.current_questions[st.session_state.current_question_index]
                        st.session_state.eligible_players_cache = prefetch_eligible_players(next_q, sport)

                        st.rerun()
                else:
                    if st.button("View Final Results", type="primary", use_container_width=True):
                        st.session_state.round_in_progress = False
                        if st.session_state.game_mode == "Daily Challenge":
                            complete_daily_challenge(sport)
                        st.rerun()

            else:
                st.subheader(f"Question {q_idx + 1}")
                st.info(f"**{q_data.get('position_slot', 'N/A')} (Year: {q_data.get('year', 'N/A')})**\n\n{q_data.get('question_text', '')}")

                if not st.session_state.eligible_players_cache:
                    with st.spinner("Loading players..."):
                        st.session_state.eligible_players_cache = prefetch_eligible_players(q_data, sport)

                options = [opt for opt in st.session_state.eligible_players_cache if opt[1] is not None]
                if not options:
                    options = [("No eligible players found", None)]

                select_options = [("Select a player...", None)] + options

                with st.form(key=f"form_q{q_idx}"):
                    selected_player_tuple = st.selectbox(
                        "Your guess:",
                        options=select_options,
                        format_func=lambda opt: opt[0],
                        key=f"selectbox_q{q_idx}"
                    )

                    submitted = st.form_submit_button("Submit Answer", type="primary", use_container_width=True)

                if submitted:
                    selected_name = selected_player_tuple[0]
                    selected_id = selected_player_tuple[1]

                    st.session_state.user_guesses_ids[q_idx] = selected_id
                    st.session_state.user_guesses_names[q_idx] = selected_name

                    points = 0
                    emojis = "🤷‍♂️"
                    guessed_stat = "N/A"
                    message = ""

                    if selected_id is None or selected_name == "Select a player...":
                        message = "No player selected."
                    else:
                        guessed_stat = get_player_stat_for_question(selected_id, q_data, st.session_state.data_cache, sport)
                        correct_stat = q_data.get('correct_stat_value')
                        is_inverted = q_data.get('is_inverted', False)
                        worst_stat = q_data.get('worst_stat_value')

                        emojis, points = calculate_score_emojis_and_points(
                            guessed_stat, correct_stat, is_inverted, worst_stat
                        )

                    st.session_state.results[q_idx] = {
                        'emojis': emojis,
                        'points': points,
                        'guessed_stat': guessed_stat,
                        'user_guess_name': selected_name,
                        'message': message
                    }

                    st.session_state.current_round_total_score += points
                    st.session_state.current_round_max_score += MAX_POINTS_PER_QUESTION
                    st.session_state.show_result_for_q_index = q_idx
                    st.session_state.eligible_players_cache = []

                    st.rerun()

    # Final Results Display
    if not st.session_state.round_in_progress:
        results_to_show = None
        score_to_show = 0
        max_score_to_show = 0
        header_text = ""
        questions_to_show = []

        if st.session_state.game_mode == "Daily Challenge" and st.session_state.game_completed.get(sport, False):
            results_to_show = st.session_state.daily_results.get(sport, {})
            score_to_show = st.session_state.daily_total_score.get(sport, 0)
            max_score_to_show = st.session_state.daily_max_score.get(sport, 0)
            questions_to_show = st.session_state.daily_questions.get(sport, [])
            header_text = f"Daily Challenge Results: {st.session_state.game_date}"
        elif st.session_state.game_mode == "Practice Play" and st.session_state.results:
            results_to_show = st.session_state.results
            score_to_show = st.session_state.current_round_total_score
            max_score_to_show = st.session_state.current_round_max_score
            questions_to_show = st.session_state.current_questions
            header_text = "Practice Round Results"

        if results_to_show:
            st.markdown("---")
            st.header("Results")
            st.subheader(header_text)

            if st.session_state.game_mode == "Daily Challenge":
                base_url = "https://dailydraft.streamlit.app"
                app_url = f"{base_url}/?user_id={st.session_state.user_id}"

                _, current_date_str = get_daily_seed_and_date()
                share_text = format_share_text(
                    results_to_show,
                    questions_to_show,
                    score_to_show,
                    current_date_str,
                    sport,
                    app_url
                )

                st.markdown("### Share Your Results")
                st.code(share_text, language=None)
                st.caption("Click the copy icon in the top-right of the box above!")

                st.markdown("---")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Score", f"{score_to_show:,}")
            with col2:
                st.metric("Max Possible", f"{max_score_to_show:,}")
            with col3:
                if max_score_to_show > 0:
                    pct = int((score_to_show / max_score_to_show) * 100)
                    st.metric("Accuracy", f"{pct}%")

            st.markdown("---")

            for i, q_data in enumerate(questions_to_show):
                if not isinstance(q_data, dict):
                    continue

                result = results_to_show.get(i) or results_to_show.get(str(i))
                if not result:
                    continue

                with st.expander(f"Question {i + 1}: {q_data.get('position_slot', 'N/A')} ({q_data.get('year', 'N/A')})", expanded=False):
                    st.markdown(f"**{q_data.get('question_text', '')}**")

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown("**Your Answer:**")
                        guess_name = result.get('user_guess_name', "No guess")
                        if guess_name == "Select a player...":
                            guess_name = "No guess"
                        st.write(guess_name)
                        if result.get('message') != "No player selected.":
                            stat_display = q_data.get('stat_category', 'N/A')
                            st.caption(f"{stat_display}: {result.get('guessed_stat', 'N/A')}")

                    with col2:
                        st.markdown("**Correct Answer:**")
                        st.write(q_data.get('correct_player_name', 'N/A'))
                        stat_display = q_data.get('stat_category', 'N/A')
                        st.caption(f"{stat_display}: {q_data.get('correct_stat_value', 'N/A')}")

                    with col3:
                        st.markdown("**Result:**")
                        st.markdown(f"{result.get('emojis', 'N/A')}")
                        st.markdown(f"**{result.get('points', 0):,} pts**")

            if st.session_state.game_mode == "Practice Play":
                st.markdown("---")
                if st.button("Play Another Practice Round", type="primary"):
                    st.session_state.current_questions = []
                    st.session_state.results = {}
                    st.rerun()

    # Footer
    st.markdown("---")
    st.caption(f"{sport_config['icon']} Daily Draft {sport_config['name']} Trivia | Data from {sport_config['data_source']}")


# --- Main Routing ---
if st.session_state.selected_sport is None:
    render_landing_page()
else:
    render_game_page(st.session_state.selected_sport)
