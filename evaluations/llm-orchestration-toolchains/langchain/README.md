# LangChain Evaluation

LangChain implementation of the prizms multi-perspective LLM tool.

## Architecture

```mermaid
flowchart LR
    subgraph input [Input]
        Q[Question]
    end
    subgraph parallel [Parallel Streams]
        J[Judge Stream]
        C[Chaos Monkey Stream]
        R[Critic Stream]
    end
    subgraph display [Rich Layout]
        Col1[Column 1]
        Col2[Column 2]
        Col3[Column 3]
    end
    Q --> J & C & R
    J --> Col1
    C --> Col2
    R --> Col3
```

The tool sends your question to three LLM "personalities" in parallel using async streaming. Each personality has its own system prompt stored in the `prompts/` directory, making them easy to refine independently.

### Streaming Multi-Column Display

Using Rich's `Layout` and `Live` components, responses stream in real-time across three side-by-side terminal panels:

```
┌─────────────────┬─────────────────┬─────────────────┐
│     Judge       │  Chaos Monkey   │     Critic      │
├─────────────────┼─────────────────┼─────────────────┤
│ <think>         │ <think>         │ <think>         │
│ Analyzing...    │ What if...      │ Let me examine  │
│ ...streaming... │ ...streaming... │ ...streaming... │
└─────────────────┴─────────────────┴─────────────────┘
```

### Output File Separation

Responses are split into chain-of-thought (COT) and answer files:

- **Chain of Thought** (`*.cot.md`): Content within `<think>...</think>` tags showing the model's reasoning process
- **Answer** (`*.ans.md`): The final response after removing the thinking block

The `langchain-openai` package connects to LM Studio using the OpenAI-compatible API, so no special local LLM package is needed. Everything runs locally with no external accounts required.

## Dependencies

All packages are MIT licensed and require no accounts or API keys:

| Package | Purpose |
|---------|---------|
| `langchain` | Main orchestration framework |
| `langchain-core` | Core abstractions (chains, prompts, output parsers) |
| `langchain-openai` | OpenAI-compatible API (works with LM Studio) |
| `langchain-community` | Community integrations and tools |
| `langgraph` | Graph-based agent workflows |
| `langchain-text-splitters` | Text chunking utilities |
| `rich` | Terminal UI with multi-column streaming display |

## Setup

### Prerequisites

1. [LM Studio](https://lmstudio.ai/) installed and running with local server on port 1234
2. Model loaded: `qwen/qwen3-4b-thinking-2507`
3. Python 3.12+
4. [UV](https://docs.astral.sh/uv/) package manager

### Installation

```bash
# Install dependencies
uv sync

# Copy environment template
cp .env.example .env
```

### Environment Configuration

Edit `.env` if your LM Studio runs on a different port:

```
OPENAI_API_BASE=http://localhost:1234/v1
OPENAI_API_KEY=not-needed
```

## Running

```bash
uv run python main.py "Your question here"
```

## Output

Responses are saved to the `outputs/` directory with separate files for chain-of-thought and answers:

| File | Description |
|------|-------------|
| `judge.cot.md` | Judge's reasoning process |
| `judge.ans.md` | Judge's final answer |
| `chaos_monkey.cot.md` | Chaos Monkey's reasoning process |
| `chaos_monkey.ans.md` | Chaos Monkey's final answer |
| `critic.cot.md` | Critic's reasoning process |
| `critic.ans.md` | Critic's final answer |
