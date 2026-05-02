# Task Loader API Reference

## Overview

The Task Loader API provides a programmatic interface for loading, validating, and processing task files in JSONL format. This module handles file I/O, schema validation, and error handling with a focus on robustness and performance.

## Module Structure

```
task_loader/
├── __init__.py
├── loader.py          # Core loading functionality
├── validator.py       # Schema validation
├── errors.py          # Custom exceptions
└── utils.py           # Helper utilities
```

## Core API

### `load_tasks()`

Primary function for loading task files from disk.

#### Signature

```python
def load_tasks(
    filepath: str,
    *,
    validate: bool = True,
    strict: bool = False,
    skip_invalid: bool = False,
    encoding: str = 'utf-8',
    max_lines: int | None = None,
    **kwargs
) -> tuple[list[dict[str, Any]], list[ErrorRecord], bool]
```

#### Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|----------|
| `filepath` | `str` | Path to the JSONL file to load | Required |
| `validate` | `bool` | Whether to validate schema on load | `True` |
| `strict` | `bool` | If True, raise exceptions on any error; if False, return partial results | `False` |
| `skip_invalid` | `bool` | If True, skip invalid lines and continue; if False, raise on first error | `False` |
| `encoding` | `str` | File encoding for reading | `'utf-8'` |
| `max_lines` | `int | None` | Maximum number of lines to process (None = unlimited) | `None` |
| `**kwargs` | `Any` | Additional options passed to validator (see below) | - |

#### Return Values

Returns a tuple of three elements:

1. **tasks**: `list[dict[str, Any]]` - List of successfully loaded and validated task dictionaries
2. **errors**: `list[ErrorRecord]` - List of error records for failed lines (empty if no errors)
3. **success**: `bool` - True if all lines were successfully loaded, False otherwise

#### ErrorRecord

Each error in the errors list contains:

```python
class ErrorRecord:
    line: int          # Line number (1-indexed)
    error_type: str   # 'parsing', 'validation', 'schema', etc.
    message: str      # Human-readable error message
    details: dict | None  # Additional context (optional)
    task_partial: dict | None  # Partially parsed data if available
```

#### Examples

**Basic Loading**

```python
from task_loader import load_tasks

filepath = 'tasks.jsonl'
tasks, errors, success = load_tasks(filepath)

if success:
    print(f"Loaded {len(tasks)} tasks successfully")
else:
    print(f"Loaded {len(tasks)} tasks with {len(errors)} errors:")
    for error in errors:
        print(f"  Line {error.line}: {error.message}")
```

**Strict Mode (Fail Fast)**

```python
try:
    tasks, errors, success = load_tasks(
        'tasks.jsonl',
        strict=True,
        validate=True
    )
except ValidationError as e:
    print(f"Validation failed: {e}")
```

**Skip Invalid Lines**

```python
# Continue processing even if some lines are invalid
tasks, errors, success = load_tasks(
    'tasks.jsonl',
    skip_invalid=True,
    validate=True
)

# Process only valid tasks
for task in tasks:
    process_task(task)
```

**Limit Processing**

```python
# Process first 1000 tasks only
max_tasks = 1000
tasks, errors, success = load_tasks(
    'tasks.jsonl',
    max_lines=max_tasks
)
```

**Custom Validation Options**

```python
# Pass custom validation rules
tasks, errors, success = load_tasks(
    'tasks.jsonl',
    validate=True,
    strict=False,
    # Additional validator options
    allow_future_dates=True,
    require_assignee=True
)
```

#### Error Handling

**Recommended Pattern**

```python
from task_loader import load_tasks, ValidationError, ParseError

def safe_load_tasks(filepath: str) -> tuple[list[dict], list[ErrorRecord], bool]:
    try:
        return load_tasks(filepath, strict=False)
    except ValidationError as e:
        # Log and return with errors
        logger.error(f"Validation error: {e}")
        return [], [e], False
    except ParseError as e:
        # Log and return with errors
        logger.error(f"Parsing error: {e}")
        return [], [e], False
    except FileNotFoundError as e:
        # Handle missing file gracefully
        logger.error(f"File not found: {e}")
        return [], [], False
    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(f"Unexpected error: {e}")
        return [], [], False
```

#### Performance Considerations

- **Streaming**: For large files (>10MB), use `max_lines` to limit memory usage
- **Batch Processing**: Process in batches of 100-1000 tasks
- **Parallel Loading**: Use `concurrent.futures` for multiple files
- **Caching**: Cache loaded tasks if reusing frequently

#### Thread Safety

The `load_tasks()` function is **not thread-safe**. For concurrent access:

```python
import threading
from task_loader import load_tasks

lock = threading.Lock()

def safe_load(filepath):
    with lock:
        return load_tasks(filepath)
```

## Validation API

### `validate_task()`

Validate a single task dictionary against the schema.

#### Signature

```python
def validate_task(
    task: dict[str, Any],
    *,
    strict: bool = False,
    **kwargs
) -> tuple[bool, list[ValidationError], dict[str, Any] | None]
```

#### Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|----------|
| `task` | `dict` | Task dictionary to validate | Required |
| `strict` | `bool` | If True, raise exceptions on errors | `False` |
| `**kwargs` | `Any` | Additional validator options | - |

#### Return Values

Returns a tuple of:
1. `is_valid`: `bool` - True if all validations passed
2. `errors`: `list[ValidationError]` - List of validation errors (empty if valid)
3. `data`: `dict | None` - The validated task data (or None if invalid)

#### ValidationError

```python
class ValidationError(Exception):
    errors: list[ValidationErrorItem]
    
class ValidationErrorItem:
    field: str | None  # Field name or None for document-level errors
    error_type: str   # 'required', 'type', 'enum', 'format', etc.
    message: str      # Human-readable error message
    expected: str | None  # Expected value or type (optional)
    actual: Any | None  # Actual value (optional)
```

#### Examples

**Basic Validation**

```python
from task_loader.validator import validate_task

task = {
    'id': 'task-001',
    'type': 'bug_fix',
    'priority': 1,
    'status': 'pending',
    'description': 'Fix critical bug',
    'assignee': 'alice',
    'due_date': '2024-01-15T23:59:59Z'
}

is_valid, errors, data = validate_task(task)
if is_valid:
    print("Task is valid!")
else:
    print(f"Validation failed with {len(errors)} errors:")
    for error in errors:
        print(f"  {error.message}")
```

**Strict Mode**

```python
try:
    is_valid, errors, data = validate_task(task, strict=True)
except ValidationError as e:
    print(f"Validation error: {e}")
```

#### Custom Validation Rules

Pass custom validation rules via kwargs:

```python
from task_loader.validator import CustomValidator

validator = CustomValidator(
    allow_future_dates=True,
    require_assignee=True,
    max_description_length=5000
)

is_valid, errors, data = validate_task(task, validator=validator)
```

## Error Handling

### Custom Exceptions

The module provides several custom exceptions for specific error conditions:

#### ValidationError

Raised when schema validation fails.

```python
from task_loader.errors import ValidationError

try:
    validate_task(incomplete_task)
except ValidationError as e:
    print(f"Validation failed: {len(e.errors)} errors")
    for error in e.errors:
        print(f"  - {error.message}")
```

#### ParseError

Raised when JSON parsing fails.

```python
from task_loader.errors import ParseError

try:
    load_tasks('corrupted.jsonl')
except ParseError as e:
    print(f"Parsing error at line {e.line}: {e.message}")
```

#### FileNotFoundError

Standard Python exception, but worth handling explicitly.

```python
try:
    load_tasks('nonexistent.jsonl')
except FileNotFoundError:
    print(f"File not found: {filepath}")
```

#### ValidationError

Raised when business logic validation fails.

```python
from task_loader.errors import ValidationError

try:
    validate_task(task_with_invalid_priority)
except ValidationError as e:
    print(f"Business rule violation: {e.message}")
```

#### Error Handling Best Practices

1. **Always validate**: Never assume loaded data is valid
2. **Handle partial failures**: Use `skip_invalid=True` for robustness
3. **Log errors**: Log all errors with context for debugging
4. **Fail fast**: Use `strict=True` in development
5. **Graceful degradation**: Return partial results when possible

#### Error Logging

```python
import logging
from task_loader.errors import ValidationError, ParseError

logger = logging.getLogger(__name__)

def load_with_logging(filepath: str) -> tuple[list[dict], list[ErrorRecord], bool]:
    try:
        tasks, errors, success = load_tasks(filepath, strict=False)
        if errors:
            logger.warning(f"Loaded {len(tasks)} tasks with {len(errors)} errors from {filepath}")
        return tasks, errors, success
    except ValidationError as e:
        logger.error(f"Validation error loading {filepath}: {e}")
        raise
    except ParseError as e:
        logger.error(f"Parse error loading {filepath}: {e}")
        raise
    except Exception as e:
        logger.critical(f"Unexpected error loading {filepath}: {e}", exc_info=True)
        raise
```

## Best Practices

### 1. Always Validate

Never assume loaded data is valid. Always validate before processing:

```python
def process_task_file(filepath: str):
    tasks, errors, success = load_tasks(filepath, validate=True)
    
    if not success:
        # Handle errors appropriately
        return handle_errors(errors)
    
    # Validate each task individually
    validated_tasks = []
    for task in tasks:
        is_valid, validation_errors, data = validate_task(task)
        if is_valid:
            validated_tasks.append(data)
        else:
            logger.warning(f"Skipping invalid task: {task.get('id', 'unknown')}")
    
    return validated_tasks
```

### 2. Use Strict Mode in Development

Enable strict mode during development to catch issues early:

```python
# Development
load_tasks(filepath, strict=True)

# Production
load_tasks(filepath, strict=False, skip_invalid=True)
```

### 3. Handle Large Files Efficiently

For large files, use streaming and batching:

```python
def process_large_file(filepath: str, batch_size: int = 100):
    with open(filepath, 'r', encoding='utf-8') as f:
        batch = []
        for line_num, line in enumerate(f, 1):
            try:
                task = json.loads(line.strip())
                batch.append(task)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON at line {line_num}")
                continue
            
            if len(batch) >= batch_size:
                process_batch(batch)
                batch = []
        
        # Process remaining tasks
        if batch:
            process_batch(batch)
```

### 4. Implement Retry Logic

For network-based or external dependencies, implement retry logic:

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
def load_tasks_with_retry(filepath: str):
    return load_tasks(filepath)
```

### 5. Use Type Hints

Leverage type hints for better IDE support and error catching:

```python
from typing import List, Tuple
from task_loader import load_tasks

def process_tasks(filepath: str) -> Tuple[List[dict], List[ErrorRecord], bool]:
    return load_tasks(filepath)
```

### 6. Validate Before Storage

Always validate before storing tasks in a database:

```python
def save_to_database(filepath: str):
    tasks, errors, success = load_tasks(filepath, validate=True)
    
    if not success:
        logger.error(f"Failed to load tasks from {filepath}")
        return False
    
    # Validate each task before inserting
    for task in tasks:
        is_valid, validation_errors, _ = validate_task(task)
        if not is_valid:
            logger.warning(f"Skipping invalid task: {task.get('id')}")
            continue
    
    # Insert into database
    db.insert_many(tasks)
    return True
```

### 7. Implement Idempotency

Ensure operations are idempotent when possible:

```python
def upsert_tasks(filepath: str):
    tasks, errors, success = load_tasks(filepath)
    
    for task in tasks:
        # Check if task exists
        if task_exists(task['id']):
            update_task(task)
        else:
            create_task(task)
```

### 8. Use Context Managers

For file operations, use context managers to ensure proper cleanup:

```python
def load_and_process(filepath: str):
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            task = json.loads(line)
            process_task(task)
```

### 9. Implement Monitoring

Track loading performance and errors:

```python
def load_with_metrics(filepath: str):
    start_time = time.time()
    tasks, errors, success = load_tasks(filepath)
    
    metrics = {
        'duration': time.time() - start_time,
        'tasks_loaded': len(tasks),
        'errors_count': len(errors),
        'success': success
    }
    
    metrics_logger.log(metrics)
    return tasks, errors, success
```

### 10. Document Your Usage

Document your loading patterns for team consistency:

```python
# TODO: Document loading patterns
# - Always validate loaded data
# - Handle errors gracefully
# - Use strict mode in development
# - Implement retry logic for network operations
```

## Performance Guidelines

### Memory Optimization

- **Stream large files**: Process line-by-line instead of loading entire file
- **Use generators**: Return generators for lazy evaluation
- **Batch processing**: Process in batches of 100-1000 items
- **Limit results**: Use `max_lines` to limit processing

### CPU Optimization

- **Parallel validation**: Use multiprocessing for large datasets
- **Batch validation**: Validate multiple tasks in one call
- **Early exit**: Return early on critical errors

### I/O Optimization

- **Buffer reads**: Use buffered I/O for large files
- **Minimize disk access**: Batch multiple operations
- **Use SSD**: Store task files on SSD for faster reads

## Migration Guide

### From Legacy Format

If migrating from a legacy format:

```python
def migrate_legacy(filepath: str, new_filepath: str):
    with open(filepath, 'r') as f, open(new_filepath, 'w') as out:
        for line_num, line in enumerate(f, 1):
            try:
                task = json.loads(line)
                # Transform legacy fields to new format
                migrated_task = migrate_task_schema(task)
                out.write(json.dumps(migrated_task, separators=(',', ':')) + '\n')
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON at line {line_num}")
```

### Schema Changes

When changing the schema:

1. **Backward compatibility**: Support old schema for a transition period
2. **Migration scripts**: Provide migration scripts for existing data
3. **Documentation**: Update documentation with migration steps
4. **Validation**: Add validation rules for new required fields

## Related Resources

- [JSONL Format Specification](./task_file_format.md)
- [Error Handling Guide](./error_handling.md)
- [Performance Tuning](./performance_tuning.md)

---

*Last updated: 2024-01-15*
*Version: 1.0*
