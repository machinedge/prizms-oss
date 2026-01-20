# Evaluating LLM Orchestration Toolchains

I'm building a simple multi-perspective LLM tool called "prizms" and using it as a test case to evaluate different orchestration approaches. This repo contains the same functionality implemented three ways: pure Python, LangChain, and Prompt Flow.

The goal is to understand what each toolchain actually does, when it makes sense to use one over another, and whether any of them fit my needs for future projects.

## What I'm Building

A minimal version of prizms:

1. Take a user prompt (a question or problem I'm wrestling with)
2. Send it to the same LLM three times, each with a different "personality" system prompt
3. Save each response to a markdown file for comparison

## The Personality Experiment

I'm curious how different system prompt "personalities" influence the outputs. Drawing from cognitive behavioral therapy concepts, I'm using three inner voices:

| Personality | Description |
|-------------|-------------|
| **Judge** | The internal voice that evaluates and weighs my thoughts and decisions—self-assessment, not external judgment |
| **Chaos Monkey** | The part of my mind that surfaces anxiety and uncertainty—"what if everything falls apart?" |
| **Critic** | The inner critic that questions my competence and finds flaws in my reasoning |

This is an experiment. I don't know yet if these are the right three, or if the system prompts I write will actually produce meaningfully different outputs.

## Tech Stack

- **LLM**: LM Studio running locally with `qwen/qwen3-4b-thinking-2507`
- **Output**: Three markdown files (`judge.md`, `chaos_monkey.md`, `critic.md`)

---

## The Three Implementations

I'm building the same thing three ways to understand the tradeoffs firsthand.

### 1. Pure Python

**Location**: `python/`

Starting here because I want to understand the problem without any framework magic. If I can't build it in plain Python, I don't understand what I'm doing.

### 2. LangChain

**Location**: `langchain/`

LangChain is the most popular LLM framework. I want to understand what it actually provides and when the abstractions help versus get in the way.

### 3. Prompt Flow

**Location**: `promptflow/`

Prompt Flow uses a visual DAG-based approach. I'm interested in whether this makes the orchestration more accessible—especially for collaboration with people who aren't deep in Python.

---

## Getting Started

### Prerequisites

1. **LM Studio installed and running** with a local server on port 1234 (default)

2. **Model loaded**: `qwen/qwen3-4b-thinking-2507`

3. **Python 3.10+**

4. **VS Code or Cursor** (for Prompt Flow)

### Running Each Implementation

```bash
# Python (start here)
cd python/
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
python prizms.py "Your question here"

# LangChain
cd langchain/
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python prizms.py "Your question here"

# Prompt Flow
cd promptflow/
# See folder README for VS Code extension setup
pf flow run --flow . --inputs question="Your question here"
```

---

## Project Structure

```
prizms-eval/
├── README.md (this file)
├── python/
│   ├── requirements.txt
│   ├── prizms.py
│   └── outputs/
│       ├── judge.md
│       ├── chaos_monkey.md
│       └── critic.md
├── langchain/
│   ├── requirements.txt
│   ├── prizms.py
│   └── outputs/
└── promptflow/
    ├── flow.dag.yaml
    ├── requirements.txt
    └── outputs/
```

---

## Notes & Learnings

Space for my observations as I build each implementation...

### Python
- 

### LangChain
- 

### Prompt Flow
- 

---

## References

- [LM Studio](https://lmstudio.ai/)
- [LangChain Documentation](https://python.langchain.com/docs/get_started/introduction)
- [Prompt Flow Documentation](https://microsoft.github.io/promptflow/)