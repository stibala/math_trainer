import random
import time
from typing import Tuple

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Reuse persistence utilities from the CLI trainer
from trainer import save_result, get_history_filename


def _choose_operation(requested: str) -> str:
    if requested == "both":
        return random.choice(["addition", "subtraction"])
    return requested


def _choose_missing(mode: str) -> bool:
    # Accept "both" from UI as mixed behavior (random missing/standard)
    if mode in ("mixed", "both"):
        return random.choice([True, False])
    return mode == "missing"


def generate_problem(max_number: int, operation: str, mode: str) -> Tuple[str, int]:
    """
    Create a problem and return (prompt, correct_answer).
    Prompt is rendered with '_' when the missing value should be entered by the user.
    """
    current_op = _choose_operation(operation)
    is_missing_val = _choose_missing(mode)

    if current_op == "addition":
        a, b = random.randint(0, max_number), random.randint(0, max_number)
        result = a + b
        if is_missing_val:
            prompt, correct = f"{a} + _ = {result}", b
        else:
            prompt, correct = f"{a} + {b} = ?", result
    else:
        a = random.randint(0, max_number)
        b = random.randint(0, a)
        result = a - b
        if is_missing_val:
            prompt, correct = f"{a} - _ = {result}", b
        else:
            prompt, correct = f"{a} - {b} = ?", result

    return prompt, correct


def reset_session():
    for key in [
        "started",
        "current_question",
        "correct_count",
        "total_times",
        "mistakes",
        "prompt",
        "correct",
        "q_start",
        "answer_log",
    ]:
        if key in st.session_state:
            del st.session_state[key]


def ensure_session_initialized():
    if "started" not in st.session_state:
        st.session_state.started = False
    if "current_question" not in st.session_state:
        st.session_state.current_question = 0
    if "correct_count" not in st.session_state:
        st.session_state.correct_count = 0
    if "total_times" not in st.session_state:
        st.session_state.total_times = []
    if "mistakes" not in st.session_state:
        st.session_state.mistakes = []
    if "answer_log" not in st.session_state:
        st.session_state.answer_log = []  # list[str] of HTML lines (latest first when rendered)


def start_session(max_number: int, num_questions: int, operation: str, mode: str):
    st.session_state.started = True
    st.session_state.current_question = 1
    st.session_state.correct_count = 0
    st.session_state.total_times = []
    st.session_state.mistakes = []
    st.session_state.answer_log = []
    st.session_state.max_number = max_number
    st.session_state.num_questions = num_questions
    st.session_state.operation = operation
    # Normalize mode: UI allows "both"; persistence expects 'standard'/'missing'/'mixed'
    st.session_state.mode = "mixed" if mode == "both" else mode
    st.session_state.prompt, st.session_state.correct = generate_problem(
        max_number, operation, st.session_state.mode
    )
    st.session_state.q_start = time.time()


def _compact_equation_from_prompt_and_answer(prompt: str, answer: int) -> str:
    # Replace '?' (standard mode) or '_' (missing operand) with user's answer, then compact spaces
    eq_display = prompt.replace("?", str(answer)).replace("_", str(answer))
    return eq_display


def advance_after_answer(user_answer: int):
    q_time = time.time() - st.session_state.q_start
    st.session_state.total_times.append(q_time)

    eq_compact = _compact_equation_from_prompt_and_answer(st.session_state.prompt, user_answer)

    if user_answer == st.session_state.correct:
        st.session_state.correct_count += 1
        # Green log entry with the equation
        st.session_state.answer_log.append(
            f"<div style='color:#16a34a;font-weight:600;'>✔ {eq_compact}</div>"
        )
    else:
        # Red log entry with user's wrong equation and the correct answer in parentheses
        st.session_state.answer_log.append(
            f"<div style='color:#dc2626;font-weight:600;'>✘ {eq_compact} ({st.session_state.correct})</div>"
        )
        st.session_state.mistakes.append(
            (st.session_state.prompt, user_answer, st.session_state.correct)
        )

    if st.session_state.current_question >= st.session_state.num_questions:
        st.session_state.started = False
        return

    # Move to next question
    st.session_state.current_question += 1
    st.session_state.prompt, st.session_state.correct = generate_problem(
        st.session_state.max_number, st.session_state.operation, st.session_state.mode
    )
    st.session_state.q_start = time.time()


def main():
    st.set_page_config(page_title="Math Trainer 2 (Local)", page_icon="🧮", layout="centered")
    st.title("🧮 Local Math Trainer 2")
    st.caption("Practice addition and subtraction. Results are saved per user on this machine.")

    ensure_session_initialized()

    # Sidebar: session controls
    with st.sidebar:
        st.header("Settings")
        user = st.selectbox("User", options=["Julie", "Jasmina"], index=0)
        max_number = st.slider("Max number", min_value=5, max_value=20, value=10)
        num_questions = st.select_slider(
            "Number of questions", options=[5, 10, 15, 20, 25, 30], value=10
        )
        operation = st.radio(
            "Operation",
            options=["addition", "subtraction", "both"],
            index=2,
            horizontal=False,
        )
        mode_ui = st.radio(
            "Mode",
            options=["standard", "missing", "both"],
            index=2,
            help="Standard shows result as input (?); Missing hides one operand (_). Both mixes them.",
        )

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Start", type="primary"):
                reset_session()
                start_session(max_number, num_questions, operation, mode_ui)
        with col_b:
            if st.button("Reset"):
                reset_session()

        st.divider()
        st.caption(
            "Runs only on this machine (localhost). Use Enter to submit answers quickly."
        )

    tab_train, tab_visual = st.tabs(["Train", "Visualization"])

    with tab_train:
        if st.session_state.started:
            q = st.session_state.current_question
            n = st.session_state.num_questions
            st.subheader(f"Question {q} of {n}")
            st.markdown(
                f"<div style='font-size: 2rem; font-weight: 600;'>{st.session_state.prompt}</div>",
                unsafe_allow_html=True,
            )

            # Enter key submits automatically via on_change callback (no submit button)
            def _handle_answer_change():
                entered = st.session_state.get("answer_input", "").strip()
                if entered == "":
                    # Do not advance on empty
                    return
                try:
                    ans_val = int(entered)
                    advance_after_answer(ans_val)
                except ValueError:
                    st.warning("Please enter a valid integer.")
                finally:
                    # Clear input for next question
                    st.session_state.answer_input = ""

            st.text_input(
                "Your answer",
                key="answer_input",
                on_change=_handle_answer_change,
                autocomplete="off",
            )

            # Style tweaks: neutralize red focus border/ring and keep a subtle gray border
            st.markdown(
                """
                <style>
                /* Target only the specific input by its accessible label */
                div[data-baseweb="input"] {
                    border: 1px solid #D1D5DB !important; /* gray-300 */
                }
                input[aria-label="Your answer"]:focus,
                input[aria-label="Your answer"]:focus-visible {
                    outline: none !important;
                    box-shadow: none !important; /* remove themed focus ring (red) */
                    border-color: #9CA3AF !important; /* gray-400 on focus */
                }
                </style>
                """,
                unsafe_allow_html=True,
            )

            # Progress bar
            st.progress((q - 1) / n)

            # Running log of all answers (latest first for visibility)
            if st.session_state.answer_log:
                st.markdown("<hr style='opacity:0.2;'>", unsafe_allow_html=True)
                st.markdown("<div style='font-weight:600;margin-bottom:0.25rem;'>Answers</div>", unsafe_allow_html=True)
                for i, entry in enumerate(reversed(st.session_state.answer_log)):
                    # Highlight the most recent submission (i == 0) with a subtle background
                    if i == 0:
                        st.markdown(
                            (
                                "<div style='background:rgba(245, 245, 245, 0.1);border-left:4px solid #9CA3AF;"
                                "padding:6px 8px;border-radius:6px;margin-bottom:4px;'>"
                                f"{entry}"
                                "</div>"
                            ),
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            f"<div style='padding:2px 0;margin-bottom:2px;'>{entry}</div>",
                            unsafe_allow_html=True,
                        )

        else:
            # If a session was just completed, present results
            if "total_times" in st.session_state and st.session_state.total_times:
                total_q = st.session_state.num_questions
                correct = st.session_state.correct_count
                accuracy = (correct / total_q) * 100
                avg_time = sum(st.session_state.total_times) / len(st.session_state.total_times)

                st.success("Session complete!")
                st.metric("Accuracy", f"{accuracy:.1f}%")
                st.metric("Avg time / question", f"{avg_time:.2f}s")

                if st.session_state.mistakes:
                    with st.expander("Review mistakes"):
                        for p, ans, corr in st.session_state.mistakes:
                            st.write(f"{p} → You: {ans} (Correct: {corr})")

                # Persist results
                try:
                    # Use values from sidebar; mode was normalized in start_session
                    save_result(
                        user=user,
                        accuracy=accuracy,
                        avg_time=avg_time,
                        num_questions=st.session_state.num_questions,
                        operation=st.session_state.operation,
                        mode=st.session_state.mode,
                    )
                    st.caption("Results saved.")
                except Exception as e:
                    st.warning(f"Could not save results: {e}")

                st.button("Do another round", on_click=lambda: start_session(
                    st.session_state.max_number,
                    st.session_state.num_questions,
                    st.session_state.operation,
                    "both" if st.session_state.mode == "mixed" else st.session_state.mode,
                ))
            else:
                st.info("Configure settings on the left and press Start to begin.")

    with tab_visual:
        st.subheader(f"Progress visualization for {user}")

        # Load history once
        try:
            filename = get_history_filename(user)
            df = pd.read_csv(filename)
        except FileNotFoundError:
            df = None
        except Exception as e:
            st.warning(f"Could not load history: {e}")
            df = None

        if df is None or df.empty:
            st.info("No history data available yet for this user.")
        else:
            # Parse timestamp
            try:
                df['Timestamp'] = pd.to_datetime(df['Timestamp'])
            except Exception:
                st.warning("History file has invalid timestamps.")
                st.stop()

            # Show only the Daily aggregates view (session-level visualization removed)
            df_daily = df.copy()
            df_daily['Day'] = df_daily['Timestamp'].dt.date
            daily = df_daily.groupby('Day').agg({
                'Accuracy': 'mean',
                'AvgTime': 'mean',
                'Questions': 'sum'
            }).reset_index()

            fig = make_subplots(specs=[[{"secondary_y": True}]])

            fig.add_trace(
                go.Bar(
                    x=daily['Day'], y=daily['Questions'], name='Questions',
                    marker_color='darkseagreen', opacity=0.4,
                    hovertemplate='<b>Day</b>: %{x}<br><b>Questions</b>: %{y}<extra></extra>'
                ),
                secondary_y=True,
            )

            fig.add_trace(
                go.Scatter(
                    x=daily['Day'], y=daily['Accuracy'], name='Accuracy (%)',
                    mode='lines+markers', line=dict(color='dodgerblue', width=3),
                    hovertemplate='<b>Day</b>: %{x}<br><b>Accuracy</b>: %{y:.1f}%<extra></extra>'
                ),
                secondary_y=False,
            )

            fig.add_trace(
                go.Scatter(
                    x=daily['Day'], y=daily['AvgTime'], name='Avg Time (s/q)',
                    mode='lines+markers', line=dict(color='limegreen', width=3),
                    hovertemplate='<b>Day</b>: %{x}<br><b>Avg Time</b>: %{y:.2f}s<extra></extra>'
                ),
                secondary_y=True,
            )

            total_q = int(daily['Questions'].sum())
            avg_acc = daily['Accuracy'].mean()
            avg_speed = daily['AvgTime'].mean()

            fig.update_layout(
                title={
                    'text': f"Daily Progress: {user} <br><sup>Total Q: {total_q} | Avg Acc: {avg_acc:.1f}% | Avg Time: {avg_speed:.2f}s</sup>",
                    'y': 0.92, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'
                },
                barmode='overlay',
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
                template='plotly_white',
                hovermode='x unified'
            )

            fig.update_yaxes(
                title_text='Accuracy (%)',
                range=[0, 105],
                color='RoyalBlue',
                showgrid=False,
                zeroline=False,
                secondary_y=False,
            )
            fig.update_yaxes(
                title_text='Time (s) / Question',
                color='Crimson',
                showgrid=False,
                zeroline=False,
                secondary_y=True,
            )

            st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
