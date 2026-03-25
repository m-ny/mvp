import os
import sys
import subprocess
from config import OPENROUTER_API_KEY, DEFAULT_MODEL

def run_module(module_dir, script_name, *args):
    print(f"--- Running {module_dir}/{script_name} ---")
    script_path = os.path.join(module_dir, script_name)
    if not os.path.exists(script_path):
        print(f"Script {script_path} not found. Skipping.")
        return False
    
    # Set up environment variables for the subprocess
    env = os.environ.copy()
    env["OPENROUTER_API_KEY"] = OPENROUTER_API_KEY
    env["OPENAI_API_KEY"] = OPENROUTER_API_KEY
    env["ANTHROPIC_API_KEY"] = OPENROUTER_API_KEY
    env["DEEPSEEK_API_KEY"] = OPENROUTER_API_KEY
    env["DEFAULT_MODEL"] = DEFAULT_MODEL
    
    try:
        result = subprocess.run(
            [sys.executable, script_path, *args],
            cwd=module_dir,
            env=env,
            check=True
        )
        print(f"--- Finished {module_dir}/{script_name} successfully ---")
        return True
    except subprocess.CalledProcessError as e:
        print(f"--- Error running {module_dir}/{script_name}: {e} ---")
        return False

def main():
    print("Starting Agent Pipeline (Modules 1-5)")
    print(f"Using Model: {DEFAULT_MODEL}")
    
    # Module 1
    run_module("module_1", "xhs_trend_builder.py")
    
    # Module 2 (Empty)
    print("--- Skipping Module 2 (Empty) ---")
    
    # Module 3
    run_module("module_3/trend_brief_agent", "agent.py")
    
    # Module 4
    run_module("module_4", "First_Run.py")
    
    # Module 5
    run_module("module_5", "agent.py")
    
    print("Pipeline execution completed.")

if __name__ == "__main__":
    main()
