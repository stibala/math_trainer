import random
import time
import csv
import os
from datetime import datetime
from collections import defaultdict
import typer

# Initialize Typer
app = typer.Typer()

# File where history is stored
HISTORY_FILE = "math_history.csv"


def save_result(accuracy, avg_time, num_questions, operation, mode):
    """Appends the session stats to a CSV file."""
    file_exists = os.path.isfile(HISTORY_FILE)

    with open(HISTORY_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)
        # Write header if new file
        if not file_exists:
            writer.writerow(["Timestamp", "Accuracy", "AvgTime", "Questions", "Operation", "Mode"])

        # Write data
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            f"{accuracy:.2f}",
            f"{avg_time:.2f}",
            num_questions,
            operation,
            mode
        ])

    typer.secho(f"Stats saved to {HISTORY_FILE}", fg=typer.colors.BRIGHT_BLACK)


@app.command()
def train(
        max_number: int = typer.Option(10, help="Maximum number."),
        num_questions: int = typer.Option(20, help="Total number of questions."),
        mode: str = typer.Option("mixed", help="'standard', 'missing', or 'mixed'."),
        operation: str = typer.Option("both", help="'addition', 'subtraction', or 'both'.")
):
    """
    Start the training session.
    """
    if operation not in ["addition", "subtraction", "both"]:
        typer.secho("Error: Operation must be 'addition', 'subtraction', or 'both'.", fg=typer.colors.RED)
        raise typer.Exit()

    print(f"Starting Training: {operation.capitalize()} | {mode.capitalize()}")
    print("-" * 40)

    start_time = time.time()
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

        # 3. Generate Numbers
        if current_op == "addition":
            a = random.randint(0, max_number)
            b = random.randint(0, max_number)
            result = a + b
            if is_missing_val:
                prompt = f"{a} + _ = {result}"
                correct = b
            else:
                prompt = f"{a} + {b} = "
                correct = result
        else:  # Subtraction
            a = random.randint(0, max_number)
            b = random.randint(0, a)
            result = a - b
            if is_missing_val:
                prompt = f"{a} - _ = {result}"
                correct = b
            else:
                prompt = f"{a} - {b} = "
                correct = result

        # 4. Input & Timing
        q_start = time.time()
        while True:
            try:
                user_input = input(f"Q{question_num}: {prompt} ")
                if not user_input.strip(): continue
                answer = int(user_input)
                break
            except ValueError:
                print("Integers only!")

        q_time = time.time() - q_start
        total_time_per_question.append(q_time)

        # 5. Check Answer
        if answer == correct:
            typer.secho("Correct!", fg=typer.colors.GREEN)
            correct_answers += 1
        else:
            typer.secho(f"Wrong! Answer: {correct}", fg=typer.colors.RED)
            mistakes.append((prompt, answer, correct))
        print("")

    # 6. Stats & Save
    accuracy = (correct_answers / num_questions) * 100
    avg_time = sum(total_time_per_question) / len(total_time_per_question)

    print("=" * 40)
    print(f"Accuracy: {accuracy:.1f}%")
    print(f"Avg Time: {avg_time:.2f}s")

    if mistakes:
        print("\nMistakes:")
        for m in mistakes:
            print(f"  {m[0]} -> You said {m[1]} (Correct: {m[2]})")

    # SAVE TO CSV
    save_result(accuracy, avg_time, num_questions, operation, mode)


@app.command()
def plot():
    """
    Visualizes progress and displays overall lifetime statistics.
    """
    if not os.path.exists(HISTORY_FILE):
        typer.secho("No history found! Run the trainer first.", fg=typer.colors.RED)
        return

    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    dates = []
    accuracies = []
    times = []
    total_q = 0

    with open(HISTORY_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                dt = datetime.strptime(row["Timestamp"], "%Y-%m-%d %H:%M:%S")
                acc = float(row["Accuracy"])
                t = float(row["AvgTime"])
                q = int(row["Questions"])

                dates.append(dt)
                accuracies.append(acc)
                times.append(t)
                total_q += q
            except ValueError:
                continue

    if not dates:
        print("Not enough data to plot.")
        return

    # Calculate Overall Stats
    overall_accuracy = sum(accuracies) / len(accuracies)
    overall_avg_time = sum(times) / len(times)
    total_sessions = len(dates)

    fig, ax1 = plt.subplots(figsize=(11, 7))

    # --- Plotting ---
    color_acc = '#1f77b4'  # Muted Blue
    ax1.set_xlabel('Date & Time of Session')
    ax1.set_ylabel('Accuracy (%)', color=color_acc, fontweight='bold')
    ax1.plot(dates, accuracies, color=color_acc, marker='o', linewidth=2, label='Accuracy')
    ax1.tick_params(axis='y', labelcolor=color_acc)
    ax1.set_ylim(0, 110)

    ax2 = ax1.twinx()
    color_time = '#d62728'  # Muted Red
    ax2.set_ylabel('Avg Time per Question (s)', color=color_time, fontweight='bold')
    ax2.plot(dates, times, color=color_time, linestyle='--', marker='s', linewidth=2, label='Speed')
    ax2.tick_params(axis='y', labelcolor=color_time)

    # --- Add Stats Box ---
    stats_text = (
        f"LIFETIME STATS\n"
        f"--------------\n"
        f"Total Sessions: {total_sessions}\n"
        f"Total Questions: {total_q}\n"
        f"Avg Accuracy: {overall_accuracy:.1f}%\n"
        f"Avg Speed: {overall_avg_time:.2f}s/q"
    )

    # Position the box in the upper left
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
    ax1.text(0.02, 0.95, stats_text, transform=ax1.transAxes, fontsize=10,
             verticalalignment='top', bbox=props)

    # --- Formatting ---
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
    plt.gcf().autofmt_xdate()
    plt.title('Math Progress Dashboard', fontsize=16, pad=20)
    plt.grid(True, alpha=0.3)

    fig.tight_layout()
    print("Displaying progress dashboard...")
    plt.show()


if __name__ == "__main__":
    app()
