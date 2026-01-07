import random
import time
import csv
import os
from datetime import datetime
import typer
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Initialize Typer
app = typer.Typer(help="A math trainer for children to practice addition and subtraction.")


def get_history_filename(user: str):
    """Generates a unique filename per user."""
    safe_name = "".join(x for x in user if x.isalnum()).lower()
    return f"math_history_{safe_name}.csv"


def save_result(user: str, accuracy, avg_time, num_questions, operation, mode):
    """Appends the session stats to a user-specific CSV file."""
    filename = get_history_filename(user)
    file_exists = os.path.isfile(filename)

    with open(filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["Timestamp", "Accuracy", "AvgTime", "Questions", "Operation", "Mode"])

        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            f"{accuracy:.2f}",
            f"{avg_time:.2f}",
            num_questions,
            operation,
            mode
        ])
    typer.secho(f"\nStats saved to {filename}", fg=typer.colors.BRIGHT_BLACK)


@app.command()
def train(
        user: str = typer.Option("default", help="Name of the person practicing."),
        max_number: int = typer.Option(10, help="Maximum number for operands."),
        num_questions: int = typer.Option(20, help="Number of questions in this session."),
        mode: str = typer.Option("mixed", help="Pattern: 'standard' (4+2=?), 'missing' (4+_ =6), or 'mixed'."),
        operation: str = typer.Option("both", help="Math Type: 'addition', 'subtraction', or 'both'.")
):
    """
    Starts a math training session.
    """
    if operation not in ["addition", "subtraction", "both"]:
        typer.secho("Error: Operation must be 'addition', 'subtraction', or 'both'.", fg=typer.colors.RED)
        raise typer.Exit()

    typer.secho(f"--- Welcome, {user.capitalize()}! ---", fg=typer.colors.MAGENTA, bold=True)
    print(f"Goal: {num_questions} questions | Range: 0-{max_number}")
    print("-" * 40)

    correct_answers = 0
    total_time_per_question = []
    mistakes = []

    for question_num in range(1, num_questions + 1):
        # 1. Determine Operation
        current_op = operation
        if operation == "both":
            current_op = random.choice(["addition", "subtraction"])

        # 2. Determine Pattern
        is_missing_val = False
        if mode == "missing":
            is_missing_val = True
        elif mode == "mixed":
            is_missing_val = random.choice([True, False])

        # 3. Generate Problem
        if current_op == "addition":
            a, b = random.randint(0, max_number), random.randint(0, max_number)
            result = a + b
            if is_missing_val:
                prompt, correct = f"{a} + _ = {result}", b
            else:
                prompt, correct = f"{a} + {b} = ", result
        else:
            a = random.randint(0, max_number)
            b = random.randint(0, a)
            result = a - b
            if is_missing_val:
                prompt, correct = f"{a} - _ = {result}", b
            else:
                prompt, correct = f"{a} - {b} = ", result

        # 4. Input Loop
        q_start = time.time()
        while True:
            try:
                user_input = input(f"Q{question_num}/{num_questions}: {prompt} ")
                if not user_input.strip(): continue
                answer = int(user_input)
                break
            except ValueError:
                print("Please enter a number!")

        q_time = time.time() - q_start
        total_time_per_question.append(q_time)

        # 5. Feedback
        if answer == correct:
            typer.secho("Correct!", fg=typer.colors.GREEN)
            correct_answers += 1
        else:
            typer.secho(f"Wrong! The answer was {correct}.", fg=typer.colors.RED)
            mistakes.append((prompt, answer, correct))
        print("")

    # 6. Session Results
    accuracy = (correct_answers / num_questions) * 100
    avg_time = sum(total_time_per_question) / len(total_time_per_question)

    print("=" * 40)
    print(f"Session Complete, {user.capitalize()}!")
    print(f"Accuracy: {accuracy:.1f}%")
    print(f"Avg Speed: {avg_time:.2f}s per question")

    if mistakes:
        print("\nReview your mistakes:")
        for p, ans, corr in mistakes:
            print(f"  {p} -> You said {ans} (Correct: {corr})")

    save_result(user, accuracy, avg_time, num_questions, operation, mode)


@app.command()
def plot(user: str = typer.Option("default", help="Name of the child to visualize.")):
    """
    Visualizes the training history for a specific user using an interactive Plotly chart.
    """
    filename = get_history_filename(user)
    if not os.path.exists(filename):
        typer.secho(f"No history found for '{user}'.", fg=typer.colors.RED)
        return

    # Load data using Pandas
    df = pd.read_csv(filename)
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])

    # Calculate Lifetime Stats for the title/annotation
    total_q = df['Questions'].sum()
    life_acc = df['Accuracy'].mean()
    life_speed = df['AvgTime'].mean()

    # Create figure with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Add Accuracy Trace
    fig.add_trace(
        go.Scatter(
            x=df['Timestamp'],
            y=df['Accuracy'],
            name="Accuracy (%)",
            mode='lines+markers',
            line=dict(color='RoyalBlue', width=3),
            hovertemplate='<b>Date</b>: %{x}<br><b>Accuracy</b>: %{y}%<extra></extra>'
        ),
        secondary_y=False,
    )

    # Add Speed Trace
    fig.add_trace(
        go.Scatter(
            x=df['Timestamp'],
            y=df['AvgTime'],
            name="Avg Speed (s)",
            mode='lines+markers',
            line=dict(color='Crimson', width=3, dash='dash'),
            hovertemplate='<b>Date</b>: %{x}<br><b>Speed</b>: %{y}s/q<extra></extra>'
        ),
        secondary_y=True,
    )

    # Update Layout
    fig.update_layout(
        title={
            'text': f"Math Progress Dashboard: {user.capitalize()}<br><sup>Total Questions: {total_q} | Avg Acc: {life_acc:.1f}% | Avg Speed: {life_speed:.2f}s</sup>",
            'y':0.95, 'x':0.5, 'xanchor': 'center', 'yanchor': 'top'
        },
        xaxis_title="Training Date",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white",
        hovermode="x unified"
    )

    # Set y-axes titles
    fig.update_yaxes(title_text="<b>Accuracy</b> (%)", color="RoyalBlue", secondary_y=False, range=[0, 105])
    fig.update_yaxes(title_text="<b>Speed</b> (seconds)", color="Crimson", secondary_y=True)

    print(f"Opening interactive dashboard for {user} in your browser...")
    fig.show()


if __name__ == "__main__":
    app()
