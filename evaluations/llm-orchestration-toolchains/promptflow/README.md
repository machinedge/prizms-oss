# Promptflow Evaluation

Evaluation of Microsoft's Promptflow for LLM orchestration.

## Overview

[Promptflow](https://github.com/microsoft/promptflow) is an open-source development tool from Microsoft designed to streamline the development cycle of LLM-based AI applications. It provides tools for building, testing, evaluating, and deploying prompt flows.

## Key Features

- **Flow authoring**: Define LLM workflows as DAGs (Directed Acyclic Graphs) using YAML or Python
- **Prompt management**: Version and manage prompts with Jinja2 templating
- **Built-in tools**: Pre-built tools for LLM calls, Python execution, and external integrations
- **Evaluation framework**: Built-in metrics and custom evaluators for quality assessment
- **Tracing & debugging**: OpenTelemetry-based tracing for debugging and monitoring
- **VS Code extension**: Visual flow editor and debugging support
- **Azure integration**: Deploy to Azure AI Studio / Azure Machine Learning

## Setup

```bash
# Create and activate virtual environment
uv sync

# Activate the environment
source .venv/bin/activate
```

## Installed Packages

- `promptflow` - Core SDK
- `promptflow-core` - Core runtime components
- `promptflow-devkit` - Development tools (CLI, testing)
- `promptflow-tools` - Built-in tool implementations
- `promptflow-tracing` - OpenTelemetry tracing support

## Quick Start

### CLI Commands

```bash
# Initialize a new flow
pf flow init --flow ./my-flow --type standard

# Test a flow locally
pf flow test --flow ./my-flow --inputs question="What is promptflow?"

# Run batch evaluation
pf run create --flow ./my-flow --data ./data.jsonl

# Start the interactive UI
pf flow serve --source ./my-flow --port 8080
```

### Python SDK

```python
from promptflow.core import Prompty

# Load and run a prompty file
prompty = Prompty.load("path/to/prompt.prompty")
result = prompty(question="What is promptflow?")

# Or use the flow API
from promptflow.client import PFClient

client = PFClient()
result = client.test(flow="./my-flow", inputs={"question": "Hello"})
```

## Flow Types

1. **Standard Flow**: Python or YAML-based DAG for general LLM apps
2. **Chat Flow**: Specialized for conversational applications with chat history
3. **Evaluation Flow**: For evaluating other flows with quality metrics

## Resources

- [Documentation](https://microsoft.github.io/promptflow/)
- [GitHub Repository](https://github.com/microsoft/promptflow)
- [VS Code Extension](https://marketplace.visualstudio.com/items?itemName=prompt-flow.prompt-flow)
- [Azure AI Studio Integration](https://learn.microsoft.com/en-us/azure/ai-studio/how-to/prompt-flow)
