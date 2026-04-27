# Task File Format Specification

## Overview

The Task File Format is a JSONL (JSON Lines) specification for defining and managing tasks in a structured, machine-readable format. Each line in the file represents a single task with a consistent schema.

## File Format

### JSONL Structure

- **Format**: JSON Lines (JSONL) - one JSON object per line
- **Encoding**: UTF-8
- **Line Termination**: LF (Unix-style) or CRLF (Windows)
- **Max Line Length**: 1,000,000 characters
- **Max File Size**: 100 MB

### Example File

```jsonl
{"id": "task-001", "type": "code_review", "priority": 3, "status": "pending", "description": "Review PR #1234", "assignee": "alice", "due_date": "2024-01-15T23:59:59Z", "metadata": {"repo": "my-project", "pr": 1234}}
{"id": "task-002", "type": "bug_fix", "priority": 1, "status": "in_progress", "description": "Fix memory leak in API handler", "assignee": "bob", "due_date": "2024-01-10T23:59:59Z", "metadata": {"bug_id": "BUG-456", "severity": "high"}}
{"id": "task-003", "type": "feature", "priority": 2, "status": "pending", "description": "Implement dark mode toggle", "assignee": "charlie", "due_date": "2024-01-20T23:59:59Z", "metadata": {"epic": "UI-UX", "story": "STORY-789"}}
```

## Required Fields

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | string | Unique identifier for the task | - Must be non-empty<br>- Must be unique across all tasks<br>- Max 100 characters<br>- Alphanumeric with hyphens/underscores only |
| `type` | string | Task category classification | - Must be one of: `code_review`, `bug_fix`, `feature`, `documentation`, `refactoring`, `testing`, `research`, `other`<br>- Case-sensitive |
| `priority` | integer | Urgency level | - Range: 1-5 (1=urgent, 5=low)<br>- Default: 3 if omitted |
| `status` | string | Current task lifecycle stage | - Must be one of: `pending`, `in_progress`, `blocked`, `completed`, `cancelled`<br>- Default: `pending` |
| `description` | string | Human-readable task description | - Max 10,000 characters<br>- No newlines allowed |
| `assignee` | string | Assigned person/role identifier | - Max 100 characters<br>- Can be username, email, or role name |
| `due_date` | string | ISO 8601 formatted deadline | - Format: `YYYY-MM-DDTHH:MM:SSZ`<br>- Must be valid ISO 8601 datetime |

## Optional Fields

| Field | Type | Description | Default | Constraints |
|-------|------|-------------|---------|-------------|
| `title` | string | Short task title/summary | - | Max 200 characters |
| `tags` | array | Categorization tags | `[]` | - Max 20 items<br>- Each tag: max 50 chars, alphanumeric with hyphens/underscores |
| `parent_id` | string | Reference to parent task ID | `null` | - Must be valid task ID or `null` |
| `dependencies` | array | List of task IDs this task depends on | `[]` | - Max 50 items<br>- Each item: valid task ID |
| `estimated_hours` | number | Time estimation in hours | `null` | - Min: 0.1<br>- Max: 999.99<br>- Precision: 2 decimal places |
| `actual_hours` | number | Time spent tracking | `null` | - Min: 0.1<br>- Max: 999.99<br>- Precision: 2 decimal places |
| `metadata` | object | Free-form additional data | `{}` | - Max 50 keys<br>- Each value: max 10,000 chars |
| `created_at` | string | Timestamp when task was created | ISO 8601 | - Auto-generated if omitted<br>- Format: `YYYY-MM-DDTHH:MM:SSZ` |
| `updated_at` | string | Timestamp of last modification | ISO 8601 | - Auto-updated if omitted<br>- Format: `YYYY-MM-DDTHH:MM:SSZ` |
| `source` | string | Origin of the task | - | Max 100 characters<br>- Examples: `github`, `jira`, `manual`, `api` |
| `external_id` | string | External reference ID | - | Max 100 characters<br>- Used for cross-system linking |

## Field Descriptions & Constraints

### Core Fields

#### `id`
- **Purpose**: Unique identifier for database indexing and API operations
- **Generation**: Can be auto-generated (UUID v4) or manually specified
- **Validation**: Must pass regex `^[a-zA-Z0-9_-]+$`

#### `type`
- **Purpose**: Enables filtering, reporting, and workflow automation
- **Values**: 
  - `code_review`: Code quality and PR review tasks
  - `bug_fix`: Defect resolution tasks
  - `feature`: New functionality implementation
  - `documentation`: Docs, READMEs, API docs
  - `refactoring`: Code restructuring without new features
  - `testing`: Test creation, maintenance, or coverage improvement
  - `research`: Investigation, feasibility studies
  - `other`: Miscellaneous tasks not fitting other categories

#### `priority`
- **Purpose**: Scheduling and resource allocation
- **Scale**: 
  - 1: Critical/Urgent
  - 2: High
  - 3: Medium (default)
  - 4: Low
  - 5: Backlog

#### `status`
- **Purpose**: Workflow state tracking
- **Transitions**:
  - `pending` → `in_progress` (when work begins)
  - `in_progress` → `blocked` (when impediments exist)
  - `in_progress` → `completed` (when done)
  - `pending` → `cancelled` (when no longer needed)
  - `blocked` → `in_progress` (when unblocked)

#### `description`
- **Purpose**: Detailed context for assignees
- **Best Practices**: Use imperative mood ("Implement X" not "Implemented X")
- **Formatting**: Use Markdown for readability

#### `assignee`
- **Purpose**: Accountability and delegation
- **Formats**: 
  - Username: `alice`
  - Email: `alice@example.com`
  - Role: `@frontend-team`

#### `due_date`
- **Purpose**: Deadline tracking and SLA management
- **Timezone**: Always UTC (Z suffix)
- **Grace Period**: Tasks past due date should have `status` updated to `blocked` or `completed`

## Optional Field Details

### `tags`
- **Purpose**: Flexible categorization beyond fixed types
- **Examples**: `"frontend"`, `"performance"`, `"security"`, `"v2.0"`

### `dependencies`
- **Purpose**: Dependency graph for build order and risk assessment
- **Format**: Array of task IDs
- **Example**: `["task-001", "task-005"]`

### `estimated_hours` / `actual_hours`
- **Purpose**: Time tracking and productivity metrics
- **Precision**: 0.1 hour (6 minutes) minimum granularity
- **Rounding**: Round to 2 decimal places

### `metadata`
- **Purpose**: Schema-less extensibility for custom data
- **Common Keys**: `repo`, `pr`, `bug_id`, `epic`, `story`, `component`, `severity`

## Validation Rules

### Structural Validation

1. **JSON Syntax**: Each line must be valid JSON
2. **Line Count**: File must contain at least 1 line
3. **Trailing Whitespace**: Allowed but ignored
4. **Empty Lines**: Allowed and ignored
5. **Comments**: Not supported (use `#` prefix for comments in separate files)

### Field-Level Validation

#### Type Validation
- All fields must be JSON-compatible types (string, number, boolean, object, array, null)
- No special characters in strings except standard JSON escaping

#### Value Validation

**String Fields**:
- Must not exceed specified maximum length
- Must not contain unescaped control characters (except newline in description)
- Must be properly UTF-8 encoded

**Numeric Fields**:
- Must be finite numbers (no NaN, Infinity)
- Must not have more than 2 decimal places
- Must be non-negative where applicable

**Array Fields**:
- Must contain only valid values per schema
- Must not exceed maximum item count
- Each item must be a valid JSON value

**Object Fields**:
- Must not exceed maximum key count
- All keys must be valid JSON strings
- Nested objects must recursively validate

#### Format Validation

**Date/Time Fields**:
- Must match ISO 8601 format: `YYYY-MM-DDTHH:MM:SSZ`
- Must be valid calendar dates (no Feb 30, etc.)
- Must be in UTC (Z suffix required)

**ID Fields**:
- Must match pattern: `^[a-zA-Z0-9_-]+$`
- Must be unique within the file
- Must be non-empty

**Enum Fields**:
- Must be exactly one of the allowed values (case-sensitive)
- No typos or variations allowed

## Error Handling Guide

### Error Categories

#### 1. Parsing Errors

**Invalid JSON Syntax**
```
Error: Invalid JSON at line 42, column 15
Details: Expected ',' or '}' after object members
```

**Malformed Line**
```
Error: Line 15 is not valid JSON
Details: Unexpected token 'function' at position 0
```

**Solution**: Ensure each line is valid JSON. Use a JSON validator or formatter.

#### 2. Schema Validation Errors

**Missing Required Field**
```
Error: Missing required field 'id' at line 23
```

**Invalid Enum Value**
```
Error: Invalid value for 'type' at line 45
Expected: code_review, bug_fix, feature, documentation, refactoring, testing, research, other
Found: bugfix
```

**Type Mismatch**
```
Error: Field 'priority' must be an integer at line 67
Found: 3.5
```

**Constraint Violation**
```
Error: Field 'description' exceeds maximum length of 10000 characters at line 89
Found: 10500 characters
```

**Duplicate ID**
```
Error: Duplicate task ID 'task-001' found at line 102
First occurrence: line 5
```

#### 3. Data Integrity Errors

**Invalid Date Format**
```
Error: Invalid date format for 'due_date' at line 34
Expected: ISO 8601 (YYYY-MM-DDTHH:MM:SSZ)
Found: 2024-01-15 10:30:00
```

**Invalid Numeric Value**
```
Error: Field 'estimated_hours' must be a non-negative number at line 56
Found: -5.5
```

**Invalid Array Item**
```
Error: Invalid item in 'dependencies' array at line 78
Item 3: 'task-999' is not a valid task ID
```

### Error Handling Best Practices

#### For Consumers

1. **Graceful Degradation**: Process valid lines, log errors for invalid ones
2. **Batch Processing**: Don't fail entire file on single line error
3. **Error Context**: Include line number and specific error details
4. **Retry Logic**: For transient parsing errors, retry with different encoding

#### For Writers

1. **Validate Before Write**: Use schema validation libraries
2. **Atomic Writes**: Write to temp file, then rename
3. **Error Logging**: Log all validation errors with context
4. **Backups**: Always backup before overwriting

#### For API Consumers

1. **HTTP Status Codes**:
   - 400 Bad Request: Invalid JSON or schema errors
   - 422 Unprocessable Entity: Business logic validation errors
   - 500 Internal Server Error: Unexpected server errors

2. **Error Response Format**:
```json
{
  "error": {
    "code": "INVALID_TASK_FILE",
    "message": "Failed to parse task file",
    "details": [
      {
        "line": 42,
        "error": "Invalid JSON syntax",
        "suggestion": "Check for missing quotes or commas"
      }
    ],
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

## Usage Examples

### Basic Usage

#### Reading a Task File

```python
import json

def load_tasks(filepath):
    tasks = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                task = json.loads(line)
                tasks.append(task)
            except json.JSONDecodeError as e:
                print(f"Error at line {line_num}: {e}")
    return tasks
```

#### Writing a Task File

```python
import json

def save_tasks(tasks, filepath):
    with open(filepath, 'w', encoding='utf-8') as f:
        for task in tasks:
            # Compact JSON for efficiency
            line = json.dumps(task, separators=(',', ':'))
            f.write(line + '\n')
```

#### Batch Processing

```python
import concurrent.futures

def process_tasks_parallel(filepath, max_workers=4):
    tasks = load_tasks(filepath)
    
    def process_task(task):
        # Your processing logic here
        return task['id']
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(process_task, tasks))
    return results
```

### Advanced Usage

#### Schema Validation

```python
import json
from typing import Any, Dict

def validate_task_schema(task: Dict[str, Any]) -> tuple[bool, str]:
    errors = []
    
    # Check required fields
    required = ['id', 'type', 'priority', 'status', 'description', 'assignee', 'due_date']
    for field in required:
        if field not in task:
            errors.append(f"Missing required field: {field}")
    
    # Validate types
    if 'priority' in task and not isinstance(task['priority'], int):
        errors.append("priority must be an integer")
    
    if 'status' in task and task['status'] not in ['pending', 'in_progress', 'blocked', 'completed', 'cancelled']:
        errors.append(f"Invalid status: {task['status']}")
    
    if errors:
        return False, '; '.join(errors)
    return True, ''
```

#### Data Transformation

```python
def enrich_tasks(tasks: list[Dict]) -> list[Dict]:
    # Add computed fields
    for task in tasks:
        task['word_count'] = len(task.get('description', '').split())
        task['has_dependencies'] = len(task.get('dependencies', [])) > 0
    return tasks
```

#### Migration Example

```python
def migrate_old_format(tasks: list[Dict]) -> list[Dict]:
    migrated = []
    for task in tasks:
        new_task = {
            'id': task.get('id', ''),
            'type': task.get('category', 'other'),
            'priority': task.get('urgency', 3),
            'status': task.get('state', 'pending'),
            'description': task.get('notes', ''),
            'assignee': task.get('owner', ''),
            'due_date': task.get('deadline', ''),
            'metadata': {
                'legacy_source': 'old_format',
                'migrated_at': '2024-01-15T10:00:00Z'
            }
        }
        migrated.append(new_task)
    return migrated
```

## Best Practices

### File Organization

1. **Naming**: Use descriptive filenames (e.g., `tasks_2024-01-15.jsonl`)
2. **Versioning**: Include version in filename if schema changes (e.g., `tasks_v2.jsonl`)
3. **Backups**: Always maintain backups before overwriting
4. **Compression**: Use gzip for large files (`.jsonl.gz`)

### Data Quality

1. **Consistency**: Use consistent naming conventions for IDs and tags
2. **Completeness**: Fill all relevant fields, especially `description` and `metadata`
3. **Accuracy**: Verify dates and external references
4. **Clarity**: Write clear, actionable descriptions

### Performance

1. **Batch Size**: Process in batches of 100-1000 tasks
2. **Memory**: Stream large files line-by-line instead of loading all at once
3. **Indexing**: Create indexes on frequently queried fields
4. **Compression**: Use gzip for storage efficiency

### Security

1. **Sanitization**: Validate and sanitize all external data
2. **Access Control**: Implement proper access controls for sensitive data
3. **Audit Logging**: Log all changes to task data
4. **Backup Encryption**: Encrypt backups containing sensitive information

## Appendix

### Common Errors and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `JSONDecodeError` | Invalid JSON syntax | Check for missing quotes, commas, or brackets |
| `KeyError` | Missing field | Ensure all required fields are present |
| `TypeError` | Type mismatch | Convert values to expected types before use |
| `UnicodeDecodeError` | Encoding issue | Open file with `encoding='utf-8'` |
| `MemoryError` | Loading entire file | Process line-by-line or in chunks |

### Related Resources

- [JSONL Format](https://jsonlines.org/)
- [ISO 8601 Date/Time Format](https://en.wikipedia.org/wiki/ISO_8601)
- [JSON Schema](https://json-schema.org/)
- [Python json module](https://docs.python.org/3/library/json.html)

---

*Last updated: 2024-01-15*
*Version: 1.0*
