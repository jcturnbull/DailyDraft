"""
Daily Draft NFL Trivia - Streamlit Web App
A daily trivia game where users guess NFL statistical leaders
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta
import pytz
import uuid
import hashlib

from game_logic import (
    generate_questions_for_round,
    get_player_stat_for_question,
    calculate_score_emojis_and_points,
    get_data_for_year_cached,
    get_daily_seed_and_date,
    get_eligible_players_for_autocomplete,
    format_share_text,
    MAX_POINTS_PER_QUESTION,
    QUESTIONS_PER_ROUND
)

from storage import (
    save_completed_game,
    get_completed_game,
    has_completed_today,
    cleanup_old_games
)

# --- Page Configuration ---
st.set_page_config(
    page_title="Daily Draft NFL Trivia",
    page_icon="🏈",
    layout="centered",  # Better for mobile
    initial_sidebar_state="collapsed"  # Sidebar hidden by default on mobile
)

# --- User Identification ---
def get_or_create_user_id():
    """Get or create a unique user ID that persists across sessions"""
    # Check URL params first
    query_params = st.query_params
    user_id = query_params.get('user_id', None)

    if user_id:
        return user_id

    # Generate new user ID
    new_user_id = str(uuid.uuid4())[:8]  # Short ID

    # Add to URL so it persists
    st.query_params['user_id'] = new_user_id

    return new_user_id


# --- Session State Initialization ---
def init_session_state():
    """Initialize all session state variables"""
    defaults = {
        'data_cache': {},
        'game_mode': "Daily Challenge",
        'current_questions': [],
        'user_guesses_ids': {},
        'user_guesses_names': {},
        'results': {},
        'user_id': None,  # Will be set below

        # Daily Challenge specific
        'game_date_daily': None,
        'game_completed_daily': False,
        'daily_total_score': 0,
        'daily_max_score': 0,
        'daily_results': {},

        # Current round state
        'current_question_index': 0,
        'current_round_total_score': 0,
        'current_round_max_score': 0,
        'round_in_progress': False,
        'eligible_players_cache': [],
        'show_result_for_q_index': None,
        'show_instructions': False,  # Don't show by default
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Get or create user ID
    if not st.session_state.user_id:
        st.session_state.user_id = get_or_create_user_id()

    # Load saved game if exists
    _, current_date_str = get_daily_seed_and_date()
    saved_game = get_completed_game(current_date_str, st.session_state.user_id)

    if saved_game and not st.session_state.game_completed_daily:
        # Restore completed game
        st.session_state.game_completed_daily = True
        st.session_state.daily_total_score = saved_game['score']
        st.session_state.daily_max_score = saved_game['max_score']
        st.session_state.daily_results = saved_game['results']
        st.session_state.game_date_daily = current_date_str


def reset_round_state():
    """Reset state for a new game round"""
    st.session_state.user_guesses_ids = {i: None for i in range(QUESTIONS_PER_ROUND)}
    st.session_state.user_guesses_names = {i: "Select a player..." for i in range(QUESTIONS_PER_ROUND)}
    st.session_state.results = {}
    st.session_state.current_question_index = 0
    st.session_state.current_round_total_score = 0
    st.session_state.current_round_max_score = 0
    st.session_state.show_result_for_q_index = None


def prefetch_eligible_players(question_data):
    """Prefetch eligible players for a question"""
    if question_data.get('data_issue', False) or question_data.get('correct_player_id') is None:
        return [("Error loading players", None)]

    position = question_data['position_slot'].rstrip('12')
    year = question_data['year']

    return get_eligible_players_for_autocomplete(position, year, st.session_state.data_cache)


def check_and_update_daily_challenge():
    """
    Check if it's a new day and handle daily challenge state.
    This is the single source of truth for daily challenge logic.
    """
    _, current_date_str = get_daily_seed_and_date()

    # New day detected - reset daily challenge
    if st.session_state.game_date_daily != current_date_str:
        st.session_state.game_date_daily = current_date_str
        st.session_state.game_completed_daily = False
        st.session_state.daily_total_score = 0
        st.session_state.daily_max_score = 0
        st.session_state.daily_results = {}
        st.session_state.current_questions = []
        st.session_state.round_in_progress = False
        return True  # New day

    return False  # Same day


def start_daily_challenge():
    """Start today's daily challenge"""
    daily_seed, current_date_str = get_daily_seed_and_date()

    with st.spinner("Generating today's questions..."):
        st.session_state.current_questions = generate_questions_for_round(
            st.session_state.data_cache,
            daily_mode=True,
            daily_seed=daily_seed
        )

    reset_round_state()
    st.session_state.game_date_daily = current_date_str
    st.session_state.round_in_progress = True
    st.session_state.game_completed_daily = False

    # Prefetch first question's players
    if st.session_state.current_questions:
        st.session_state.eligible_players_cache = prefetch_eligible_players(
            st.session_state.current_questions[0]
        )


def start_practice_round():
    """Start a new practice round"""
    with st.spinner("Generating practice questions..."):
        st.session_state.current_questions = generate_questions_for_round(
            st.session_state.data_cache,
            daily_mode=False
        )

    reset_round_state()
    st.session_state.round_in_progress = True

    # Prefetch first question's players
    if st.session_state.current_questions:
        st.session_state.eligible_players_cache = prefetch_eligible_players(
            st.session_state.current_questions[0]
        )


def complete_daily_challenge():
    """Mark daily challenge as completed and save results"""
    st.session_state.game_completed_daily = True
    st.session_state.daily_total_score = st.session_state.current_round_total_score
    st.session_state.daily_max_score = st.session_state.current_round_max_score
    st.session_state.daily_results = st.session_state.results.copy()
    st.session_state.round_in_progress = False

    # Save to persistent storage
    _, current_date_str = get_daily_seed_and_date()
    save_completed_game(
        current_date_str,
        st.session_state.user_id,
        st.session_state.daily_total_score,
        st.session_state.daily_max_score,
        st.session_state.daily_results
    )

    # Cleanup old games (keep last 7 days)
    cleanup_old_games(days_to_keep=7)


# --- Initialize ---
init_session_state()

# --- Mobile-Friendly CSS ---
st.markdown("""
<style>
    /* Make everything more compact and touch-friendly on mobile */
    @media (max-width: 768px) {
        /* Larger touch targets */
        .stButton button {
            width: 100%;
            font-size: 16px !important;
            padding: 0.75rem !important;
            min-height: 48px;
        }

        /* Readable text sizes */
        h1 {
            font-size: 1.8rem !important;
        }
        h2 {
            font-size: 1.4rem !important;
        }
        h3 {
            font-size: 1.2rem !important;
        }

        /* Better form elements */
        .stSelectbox select {
            font-size: 16px !important;
            min-height: 48px;
        }

        /* Radio buttons easier to tap */
        .stRadio > label {
            font-size: 16px !important;
        }

        /* Better spacing */
        .element-container {
            margin-bottom: 1rem;
        }

        /* Completely hide sidebar on mobile */
        section[data-testid="stSidebar"] {
            display: none !important;
        }

        /* Hide hamburger menu button on mobile */
        button[kind="header"] {
            display: none !important;
        }

        /* Ensure sidebar doesn't overlay */
        .css-1d391kg, [data-testid="stSidebarNav"] {
            display: none !important;
        }

        /* Make expanders more prominent */
        .streamlit-expanderHeader {
            font-size: 16px !important;
            padding: 0.75rem !important;
        }
    }

    /* Better button styling for all screen sizes */
    .stButton button {
        border-radius: 8px;
        transition: all 0.3s ease;
    }

    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }

    /* Center content better */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# --- Header ---
st.title("🏈 Daily Draft NFL Trivia")
st.caption("Guess the NFL stat leaders. 5 questions. 1 game per day.")

# --- Sidebar (Game Mode & Options) ---
with st.sidebar:
    st.header("Game Mode")

    # Mode selection
    current_mode = st.session_state.game_mode
    selected_mode = st.radio(
        "Choose your challenge:",
        ("Daily Challenge", "Practice Play"),
        index=0 if current_mode == "Daily Challenge" else 1
    )

    # Handle mode change
    if selected_mode != current_mode:
        st.session_state.game_mode = selected_mode
        st.session_state.round_in_progress = False
        st.session_state.current_questions = []
        st.session_state.show_result_for_q_index = None
        st.rerun()

    st.markdown("---")

    # Instructions in sidebar
    with st.expander("📖 How to Play"):
        st.markdown("""
        **5 Questions. Guess the NFL stat leaders.**

        **Scoring:**
        - 🟩🟩🟩🟩🟩 Perfect (10,000 pts)
        - 🟩🟩🟩🟩🟨 80-99%
        - 🟩🟩🟩🟨⬛ 60-79%
        - 🟩🟩🟨⬛⬛ 40-59%
        - 🟩🟨⬛⬛⬛ 20-39%
        - 🟨⬛⬛⬛⬛ 1-19%
        - ⬛⬛⬛⬛⬛ 0%

        **Daily Challenge:** One game per day, same for everyone!

        **Practice:** Unlimited random games.
        """)

    # Stats display
    st.markdown("---")
    st.markdown("### 📊 Stats")
    if st.session_state.game_mode == "Daily Challenge" and st.session_state.game_completed_daily:
        st.metric("Today's Score", f"{st.session_state.daily_total_score:,}")
        st.metric("Max Possible", f"{st.session_state.daily_max_score:,}")
        if st.session_state.daily_max_score > 0:
            pct = int((st.session_state.daily_total_score / st.session_state.daily_max_score) * 100)
            st.metric("Accuracy", f"{pct}%")


# --- Main Game Area ---
st.markdown("---")

# Check for new day if in Daily Challenge mode
if st.session_state.game_mode == "Daily Challenge":
    check_and_update_daily_challenge()

# --- Daily Challenge Flow ---
if st.session_state.game_mode == "Daily Challenge":
    _, current_date_str = get_daily_seed_and_date()

    # Show completion message if already played today
    if st.session_state.game_completed_daily:
        st.success(f"✅ You've completed today's Daily Challenge! ({current_date_str})")
        st.info("Come back tomorrow for a new challenge!")

        # Show time until next challenge (Pacific Time)
        pacific = pytz.timezone('America/Los_Angeles')
        now_pt = datetime.now(pacific)
        next_midnight_pt = now_pt.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        time_until_next = next_midnight_pt - now_pt
        hours, remainder = divmod(time_until_next.total_seconds(), 3600)
        minutes, _ = divmod(remainder, 60)
        st.caption(f"⏰ Next challenge in: {int(hours):02d}h {int(minutes):02d}m (Pacific Time)")

    elif not st.session_state.round_in_progress:
        # Clean start button - no extra text
        st.subheader(f"📅 {current_date_str}")

        if st.button("🎮 Start Today's Challenge", type="primary", use_container_width=True, key="start_daily"):
            start_daily_challenge()
            st.rerun()

# --- Practice Play Flow ---
elif st.session_state.game_mode == "Practice Play":
    if not st.session_state.round_in_progress:
        # Clean start button - no extra text
        st.subheader("🎯 Practice Mode")

        if st.button("🎮 Start Practice Round", type="primary", use_container_width=True, key="start_practice"):
            start_practice_round()
            st.rerun()


# --- Question Display (Active Round) ---
if st.session_state.round_in_progress:
    q_idx = st.session_state.current_question_index

    if q_idx < len(st.session_state.current_questions):
        q_data = st.session_state.current_questions[q_idx]

        # Progress indicator
        progress = (q_idx + 1) / QUESTIONS_PER_ROUND
        st.progress(progress)
        st.caption(f"Question {q_idx + 1} of {QUESTIONS_PER_ROUND}")

        # Check for data issues
        is_problem_question = (
            not isinstance(q_data, dict) or
            q_data.get('data_issue', False) or
            q_data.get('correct_player_id') is None
        )

        if is_problem_question:
            st.warning(f"⚠️ Issue with Question {q_idx + 1}")
            st.error(f"{q_data.get('question_text', 'Data unavailable.')}")

            if st.button("Skip Question ⏭️", key=f"skip_{q_idx}"):
                st.session_state.results[q_idx] = {
                    'emojis': "⬛⬛⬛⬛⬛",
                    'points': 0,
                    'message': "Question skipped due to data issue."
                }
                st.session_state.current_question_index += 1

                # Check if round is complete
                if st.session_state.current_question_index >= QUESTIONS_PER_ROUND:
                    st.session_state.round_in_progress = False
                    if st.session_state.game_mode == "Daily Challenge":
                        complete_daily_challenge()
                else:
                    # Prefetch next question's players
                    next_q = st.session_state.current_questions[st.session_state.current_question_index]
                    st.session_state.eligible_players_cache = prefetch_eligible_players(next_q)

                st.rerun()

        # Show result for current question
        elif st.session_state.show_result_for_q_index == q_idx:
            result = st.session_state.results.get(q_idx)

            st.subheader(f"Question {q_idx + 1}")
            st.info(f"**{q_data.get('position_slot', 'N/A')} (Year: {q_data.get('year', 'N/A')})**\n\n{q_data.get('question_text', '')}")

            if result:
                # Mobile-friendly: columns stack on small screens
                col1, col2 = st.columns([1, 1])

                with col1:
                    st.markdown("### Your Answer")
                    user_guess = result.get('user_guess_name', "N/A")
                    if result.get('message') == "No player selected.":
                        st.write("❌ No selection")
                    else:
                        st.write(f"**{user_guess}**")
                        st.caption(f"{q_data.get('stat_category', 'N/A').replace('_', ' ')}: {result.get('guessed_stat', 'N/A')}")

                with col2:
                    st.markdown("### Correct Answer")
                    st.write(f"**{q_data.get('correct_player_name', 'N/A')}**")
                    st.caption(f"{q_data.get('stat_category', 'N/A').replace('_', ' ')}: {q_data.get('correct_stat_value', 'N/A')}")

                st.markdown("---")
                # Larger emoji display for mobile
                st.markdown(f"<div style='text-align: center; font-size: 2rem;'>{result.get('emojis', 'N/A')}</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='text-align: center; font-size: 1.5rem; font-weight: bold;'>+{result.get('points', 0):,} points</div>", unsafe_allow_html=True)

            st.markdown("---")

            # Navigation buttons
            if st.session_state.current_question_index + 1 < QUESTIONS_PER_ROUND:
                if st.button("Next Question ➡️", type="primary", use_container_width=True):
                    st.session_state.current_question_index += 1
                    st.session_state.show_result_for_q_index = None

                    # Prefetch next question's players
                    next_q = st.session_state.current_questions[st.session_state.current_question_index]
                    st.session_state.eligible_players_cache = prefetch_eligible_players(next_q)

                    st.rerun()
            else:
                if st.button("View Final Results 🎉", type="primary", use_container_width=True):
                    st.session_state.round_in_progress = False
                    if st.session_state.game_mode == "Daily Challenge":
                        complete_daily_challenge()
                    st.rerun()

        # Show question for answering
        else:
            st.subheader(f"Question {q_idx + 1}")
            st.info(f"**{q_data.get('position_slot', 'N/A')} (Year: {q_data.get('year', 'N/A')})**\n\n{q_data.get('question_text', '')}")

            # Load eligible players if not cached
            if not st.session_state.eligible_players_cache:
                with st.spinner("Loading players..."):
                    st.session_state.eligible_players_cache = prefetch_eligible_players(q_data)

            # Prepare options
            options = [opt for opt in st.session_state.eligible_players_cache if opt[1] is not None]
            if not options:
                options = [("No eligible players found", None)]

            select_options = [("Select a player...", None)] + options

            # Answer form
            with st.form(key=f"form_q{q_idx}"):
                selected_player_tuple = st.selectbox(
                    "Your guess:",
                    options=select_options,
                    format_func=lambda opt: opt[0],
                    key=f"selectbox_q{q_idx}"
                )

                submitted = st.form_submit_button("Submit Answer 📝", type="primary", use_container_width=True)

            if submitted:
                selected_name = selected_player_tuple[0]
                selected_id = selected_player_tuple[1]

                st.session_state.user_guesses_ids[q_idx] = selected_id
                st.session_state.user_guesses_names[q_idx] = selected_name

                # Calculate score
                points = 0
                emojis = "🤷‍♂️"
                guessed_stat = "N/A"
                message = ""

                if selected_id is None or selected_name == "Select a player...":
                    message = "No player selected."
                else:
                    guessed_stat = get_player_stat_for_question(selected_id, q_data, st.session_state.data_cache)
                    correct_stat = q_data.get('correct_stat_value')
                    emojis, points = calculate_score_emojis_and_points(guessed_stat, correct_stat)

                # Save result
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

                # Clear cache for next question
                st.session_state.eligible_players_cache = []

                st.rerun()


# --- Final Results Display ---
if not st.session_state.round_in_progress:
    results_to_show = None
    score_to_show = 0
    max_score_to_show = 0
    header_text = ""

    if st.session_state.game_mode == "Daily Challenge" and st.session_state.game_completed_daily:
        results_to_show = st.session_state.daily_results
        score_to_show = st.session_state.daily_total_score
        max_score_to_show = st.session_state.daily_max_score
        header_text = f"Daily Challenge Results: {st.session_state.game_date_daily}"
    elif st.session_state.game_mode == "Practice Play" and st.session_state.results:
        results_to_show = st.session_state.results
        score_to_show = st.session_state.current_round_total_score
        max_score_to_show = st.session_state.current_round_max_score
        header_text = "Practice Round Results"

    if results_to_show:
        st.markdown("---")
        st.header("🎉 Results")
        st.subheader(header_text)

        # Score display
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

        # Question-by-question results
        for i, q_data in enumerate(st.session_state.current_questions):
            if not isinstance(q_data, dict):
                continue

            result = results_to_show.get(i)
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
                        st.caption(f"{q_data.get('stat_category', 'N/A').replace('_', ' ')}: {result.get('guessed_stat', 'N/A')}")

                with col2:
                    st.markdown("**Correct Answer:**")
                    st.write(q_data.get('correct_player_name', 'N/A'))
                    st.caption(f"{q_data.get('stat_category', 'N/A').replace('_', ' ')}: {q_data.get('correct_stat_value', 'N/A')}")

                with col3:
                    st.markdown("**Result:**")
                    st.markdown(f"{result.get('emojis', 'N/A')}")
                    st.markdown(f"**{result.get('points', 0):,} pts**")

        # Share button (Daily Challenge only)
        if st.session_state.game_mode == "Daily Challenge":
            st.markdown("---")
            share_text = format_share_text(
                results_to_show,
                st.session_state.current_questions,
                score_to_show,
                max_score_to_show,
                st.session_state.game_date_daily
            )

            st.markdown("### 📤 Share Your Results")
            st.code(share_text, language=None)
            st.caption("Copy and share your results with friends!")

        # Play again button (Practice only)
        elif st.session_state.game_mode == "Practice Play":
            st.markdown("---")
            if st.button("🔄 Play Another Practice Round", type="primary"):
                st.session_state.current_questions = []
                st.session_state.results = {}
                st.rerun()


# --- Footer ---
st.markdown("---")
st.caption("🏈 Daily Draft NFL Trivia | Data from nfl_data_py")
