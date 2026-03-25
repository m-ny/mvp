# Agent Pipeline (Modules 1-5)

This repository combines Modules 1 through 5 of the MVP Agent project into a single, cohesive pipeline. The goal is to run an end-to-end agent workflow sequentially from Module 1 to Module 5.

## Project Structure

- `module_1/`: XHS Trend Object Builder
- `module_2/`: (Reserved for future use)
- `module_3/`: Trend Brief Agent
- `module_4/`: Course MVP
- `module_5/`: Yanny MVP
- `config.py`: Global configuration for OpenRouter API keys and default models.
- `main.py`: The entry point script that orchestrates the execution of all modules sequentially.

## Setup

1. **Install Dependencies:**
   Ensure you have Python 3 installed. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure API Keys:**
   Copy the `.env.example` file to `.env` and add your OpenRouter API key:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` to include:
   ```env
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   DEFAULT_MODEL=openai/gpt-4o-mini
   ```

## Running the Pipeline

To run the entire agent pipeline from Module 1 to Module 5 in order, execute the `main.py` script:

```bash
python main.py
```

This script will sequentially execute the primary functionality of each module, passing data between them if necessary.

## Modules Overview

### Module 1: XHS Trend Object Builder
Converts raw Xiaohongshu signals into a strict reusable Trend Object schema (label/category/evidence/metrics/timestamp/summary/confidence).

### Module 2: (Placeholder)
Currently empty, reserved for future pipeline steps.

### Module 3: Trend Brief Agent
Generates trend briefs based on the objects created in Module 1.

### Module 4: Course MVP
Contains the `First_Run.py` script (converted from a Jupyter notebook) which performs the initial data processing or agent setup.

### Module 5: Yanny MVP
The final stage of the pipeline, executing the agent architecture defined in `agent.py`.

## Global Configuration

The `config.py` file provides a centralized way to access the OpenRouter API key and the selected model across all modules. You can import these variables in any module:

```python
from config import OPENROUTER_API_KEY, DEFAULT_MODEL
```
