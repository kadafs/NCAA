
import subprocess
import sys
import os

# Base paths relative to Project Root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))

def run_command(command, description):
    print(f"\n--- {description} ---")
    try:
        # Check if python or python3 is available
        cmd = [sys.executable] + command
        subprocess.check_call(cmd)
        print("Success")
    except subprocess.CalledProcessError as e:
        print(f"Error running {description}: {e}")
        sys.exit(1)

def main():
    print("Starting NCAA Division 2 (D2) Pipeline...")
    
    # 1. Fetch D2 Stats
    run_command(["ncaa/data_fetcher.py", "--division", "d2"], "Fetching D2 Stats")
    
    # 2. Run Simple Prediction Model
    run_command(["ncaa/predict_simple.py", "--division", "d2"], "Running D2 Simple Model")

if __name__ == "__main__":
    main()
