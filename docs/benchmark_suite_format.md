# Benchmark Suite Format

> Defines the folder layout, registry format, and task metadata conventions
> for Phase 2 benchmark suites.

## Target Directory Tree

```
benchmarks/
  suites.yaml                           -- Suite registry
  coding/
    frontend.jsonl
    backend.jsonl
    misc.jsonl
  reasoning/
    math.jsonl
    real_world.jsonl
    instruction_following.jsonl
  tools/
    json_tool_calling.jsonl
  context/
    long_context.jsonl
  official/
    README.md                           -- Notes on imported benchmarks
```

## Suite Registry

benchmarks/suites.yaml maps suite IDs to their metadata and task files.

```yaml
suites:
  - id: reasoning.math
    name: Math
    category: reasoning
    task_file: benchmarks/reasoning/math.jsonl
    description: Numeric and short-answer math prompts.
    scoring: deterministic

  - id: reasoning.real_world
    name: Real-World Reasoning
    category: reasoning
    task_file: benchmarks/reasoning/real_world.jsonl
    description: Multi-step real-world reasoning tasks.
    scoring: deterministic

  - id: reasoning.instruction_following
    name: Instruction Following
    category: reasoning
    task_file: benchmarks/reasoning/instruction_following.jsonl
    description: Tasks that test adherence to specific formatting or content instructions.
    scoring: deterministic

  - id: coding.frontend
    name: Frontend Coding
    category: coding
    task_file: benchmarks/coding/frontend.jsonl
    description: Frontend (HTML/CSS/JS/TSX) code generation.
    scoring: deterministic + artifact

  - id: coding.backend
    name: Backend Coding
    category: coding
    task_file: benchmarks/coding/backend.jsonl
    description: Backend (Python/API/database) code generation.
    scoring: deterministic + artifact

  - id: coding.misc
    name: Misc Coding
    category: coding
    task_file: benchmarks/coding/misc.jsonl
    description: General scripting and algorithmic coding tasks.
    scoring: deterministic + artifact

  - id: tools.json_tool_calling
    name: JSON Tool Calling
    category: tools
    task_file: benchmarks/tools/json_tool_calling.jsonl
    description: Strict JSON tool-call generation.
    scoring: deterministic

  - id: context.long_context
    name: Long Context
    category: context
    task_file: benchmarks/context/long_context.jsonl
    description: Long-context recall and retrieval tasks.
    scoring: deterministic
```

**Registry fields:**

| Field       | Type   | Description                                                |
|-------------|--------|------------------------------------------------------------|
| id          | string | Unique suite identifier (<category>.<name>)                |
| name        | string | Human-readable display name                                |
| category    | string | Top-level grouping category                                |
| task_file   | string | Path to the JSONL task file (relative to project root)     |
| description | string | One-line description of the suite                          |
| scoring     | string | Scoring approach (deterministic or deterministic + artifact) |

## Suite ID Naming

Pattern: <category>.<name>

- Category and name are lowercase alphanumeric with hyphens.
- Examples: reasoning.math, coding.frontend, tools.json_tool_calling, context.long_context.

Initial categories:

| Category  | Description                                      |
|-----------|--------------------------------------------------|
| reasoning | Math, real-world reasoning, instruction following |
| coding    | Frontend, backend, misc code generation          |
| tools     | Tool calling, structured JSON output             |
| context   | Long-context recall                              |
| official  | Imported open-source/official benchmarks         |

## JSONL Task Format

Task files are JSONL: one JSON object per line.

### Required Fields (Phase 1 Contract)

| Field           | Type   | Description                              |
|-----------------|--------|------------------------------------------|
| id              | string | Unique task identifier within the file   |
| description     | string | The prompt sent to the model             |
| expected_output | string | Reference answer for scoring             |

### Phase 2 Metadata Fields

All fields under metadata are optional in the JSONL but provide richer scoring and artifact handling.

| Field                   | Path                              | Type         | Purpose                                                      |
|-------------------------|-----------------------------------|--------------|--------------------------------------------------------------|
| category                | metadata.category                 | string       | Determines scorer selection (see contract)                   |
| keywords                | metadata.keywords                 | list         | Required keywords for keyword_match scorer                   |
| tolerance               | metadata.tolerance                | float        | Allowed deviation for numeric_close scorer (default 0.01)    |
| threshold               | metadata.threshold                | float        | Fraction of keywords required for keyword_match (default 0.7)|
| expected_tool           | metadata.expected_tool            | string       | Expected tool name for json_valid scorer                     |
| required_argument_keys  | metadata.required_argument_keys   | list         | Required argument keys for json_valid scorer                 |
| artifact_kind           | metadata.artifact_kind            | string       | Type of artifact (e.g., frontend, backend)                   |
| artifact_extension      | metadata.artifact_extension       | string       | File extension for saved artifact (e.g., .tsx, .py)         |
| estimated_context_tokens| metadata.estimated_context_tokens | int          | Estimated context window needed                              |

### Example Tasks

**Math task (deterministic score):**
```json
{
  "id": "math_add",
  "description": "What is 2 + 2? Reply with only the number.",
  "expected_output": "4",
  "metadata": {
    "category": "math"
  }
}
```

**Coding task (deterministic score + artifact):**
```json
{
  "id": "frontend_component_001",
  "description": "Write a React component that fetches and displays user data.",
  "expected_output": "",
  "metadata": {
    "category": "code",
    "keywords": ["fetch", "useEffect", "useState"],
    "artifact_kind": "frontend",
    "artifact_extension": ".tsx"
  }
}
```

**Tool calling task (JSON validation):**
```json
{
  "id": "json_weather_tool",
  "description": "Return only JSON for a tool call to get the weather in Tokyo.",
  "expected_output": "",
  "metadata": {
    "category": "tool",
    "expected_tool": "get_weather",
    "required_argument_keys": ["location"]
  }
}
```

**Long-context task:**
```json
{
  "id": "needle_haystack_001",
  "description": "A long document follows... Based on the above, what was the secret code?",
  "expected_output": "BLUE-42",
  "metadata": {
    "category": "keyword",
    "keywords": ["BLUE-42"],
    "estimated_context_tokens": 8192
  }
}
```

## Scoring Strategy

### Deterministic Scorers (Existing)

| Scorer        | Category              | Behavior                                              |
|---------------|-----------------------|-------------------------------------------------------|
| exact_match   | text, general, fallback | Case-insensitive, whitespace-normalized match        |
| numeric_close | math, numeric         | Extract first number, compare within tolerance        |
| keyword_match | keyword, code         | Check keyword presence fraction against threshold     |
| json_valid    | json, tool            | Parse JSON, validate tool name and argument keys      |

### Coding Benchmark Scoring

Coding benchmarks in Phase 2:

- Save full model outputs as standalone artifact files under artifacts/<suite_id>/.
- Apply lightweight deterministic scoring (keyword_match for structure checks).
- Do **not** pretend to fully solve coding assessment - deeper evaluation (sandbox execution, LLM-as-judge, human review) is explicitly future work.
- Documentation for each coding suite notes the scoring limitations.

## Official/Open-Source Benchmarks

Official benchmark suites live under benchmarks/official/. Each imported benchmark:

- Converts source data into this harness JSONL format.
- Preserves source attribution in metadata.source.
- Documents the import command and data source in benchmarks/official/README.md.
- Avoids committing large downloaded datasets.
- Provides a clear skip/error message when the source data is unavailable.

## Windows Compatibility

- All task file paths use forward slashes in configuration.
- JSONL files use .jsonl extension (Windows associates with text editors).
- Long lines are supported (up to 1,000,000 characters).
- UTF-8 encoding is used for all files.
