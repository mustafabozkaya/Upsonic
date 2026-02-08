# Upsonic Agent Framework - Developer Guide

This document provides guidelines for AI agents working on the Upsonic codebase.

## Build/Test/Lint Commands

### Running Tests
```bash
# Run all tests
uv run pytest

# Run a single test file
uv run pytest tests/unit_tests/test_model_normalization.py

# Run a specific test class
uv run pytest tests/unit_tests/test_model_normalization.py::TestNormalizeModelId

# Run a specific test method
uv run pytest tests/unit_tests/test_model_normalization.py::TestNormalizeModelId::test_ollama_passthrough_unknown_provider

# Run with async support (required for async tests)
uv run pytest --asyncio-mode=strict

# Run only unit tests (exclude integration tests)
uv run pytest -m "not integration"

# Run tests with coverage
uv run pytest --cov=src/upsonic
```

### Type Checking
```bash
# Run mypy type checker
uv run mypy src/
```

### Dependencies & Environment
```bash
# Sync dependencies
uv sync

# Install with all optional dependencies
uv sync --all-extras

# Install with specific extras
uv sync --extra storage --extra vectordb

# Lock dependencies
uv lock
```

### Pre-commit Hooks
```bash
# Run all hooks
pre-commit run --all-files

# Run specific hook
pre-commit run pytest
```

## Code Style Guidelines

### Python Version & Imports
- **Python**: 3.10+ required
- **Future imports**: Always use `from __future__ import annotations` at the top
- **Type hints**: Use full type annotations; use `TYPE_CHECKING` for heavy imports
- **Import order**: stdlib → third-party → local; use absolute imports

```python
from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from upsonic.models import Model  # Heavy imports here
```

### Naming Conventions
- **Classes**: PascalCase (e.g., `Agent`, `Task`, `ToolMetadata`)
- **Functions/methods**: snake_case (e.g., `normalize_model_id`, `do_async`)
- **Constants**: UPPER_SNAKE_CASE for module-level constants
- **Private members**: Prefix with underscore (e.g., `_client`, `_lazy_imports`)
- **Type variables**: PascalCase with descriptive names

### Formatting
- **Quotes**: Single quotes for strings (e.g., `'ollama'`, `'openai'`)
- **Line length**: Follow existing code patterns (appears ~100-120 chars)
- **Docstrings**: Google-style with triple quotes
- **Type aliases**: Use `TypeAlias` with descriptive names and docstrings

```python
ToolKind: TypeAlias = Literal['function', 'output', 'external', 'unapproved', 'mcp']
"""Type representing the kind of tool."""
```

### Error Handling
- Use custom exceptions from `upsonic.utils.package.exception` (e.g., `UserError`)
- Provide helpful error messages with actionable guidance
- Use assertions for internal invariants, exceptions for external errors

```python
from upsonic.utils.package.exception import UserError

if not base_url:
    raise UserError(
        'Set the `OLLAMA_BASE_URL` environment variable or pass it via `OllamaProvider(base_url=...)`'
    )
```

### Testing Conventions
- Use `pytest` with `pytest-asyncio` for async tests
- Use `unittest.TestCase` for standard unit tests
- Use `@pytest.mark.asyncio` decorator for async test functions
- Use mocks from `unittest.mock` (Mock, AsyncMock, MagicMock, patch)
- Test classes use `Test*` prefix; test methods use `test_*` prefix
- Provide descriptive docstrings for test methods

```python
@pytest.mark.asyncio
async def test_orchestrator_orchestrate_tools(self, mock_agent_class, orchestrator):
    """Test tool orchestration."""
    mock_synthesis_agent = Mock()
    mock_synthesis_agent.do_async = AsyncMock(return_value=Mock(output="synthesis_result"))
```

### Model Provider Format
- Use format: `provider/model-name` (e.g., `ollama/llama3.2:1b`, `openai/gpt-4o`)
- Ollama models: Use `ollama/<model>` format (e.g., `ollama/llama3.2:1b`)
- Environment variables: `OLLAMA_BASE_URL`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`

### Dataclasses & Type Safety
- Use `@dataclass` for data containers with type annotations
- Use `field(default_factory=dict)` for mutable defaults
- Use Optional[] for nullable fields
- Use Literal[] for constrained string values

```python
@dataclass
class ToolMetadata:
    """Universal metadata for all tools."""
    name: str
    description: Optional[str] = None
    kind: ToolKind = 'function'
    custom: Dict[str, Any] = field(default_factory=dict)
```

### Async Patterns
- Prefer async/await for I/O operations
- Use `AsyncMock` for mocking async methods
- Handle both sync and async interfaces where appropriate
- Use `nest-asyncio` for Jupyter/notebook compatibility

### Key Architecture Patterns
- **Provider pattern**: Abstract providers (OllamaProvider, OpenAIProvider)
- **Model inference**: Use `infer_model()` to resolve model strings to Model instances
- **Lazy imports**: Use `_lazy_import()` pattern for expensive imports
- **Profile system**: Model profiles define behavior (JSON schema transformers)

### Pre-commit Requirements
- uv lock file must be updated
- All unit tests must pass
- Dependencies must be synced

## Project Structure
```
src/upsonic/
  agent/         # Agent implementation
  models/        # Model providers and inference
  tools/         # Tool system and orchestration
  tasks/         # Task definitions
  storage/       # Storage backends
  embeddings/    # Embedding providers
  knowledge_base/# RAG and document processing
  safety_engine/ # Content filtering and policies
  ...
tests/
  unit_tests/    # Unit tests
```
