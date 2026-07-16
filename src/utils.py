"""Simple helpers."""

import json
import logging
import re
import sys
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Callable, TypeVar

import yaml

T = TypeVar('T')
R = TypeVar('R')


# ============================================================================
# Constants
# ============================================================================

# Log message formatting
LOG_MSG_WIDTH = 60    # Max characters per line in log message content
LOG_MAX_LINES = 3     # Maximum lines for wrapped content

# Tree-style prefixes for structured logging
TREE_BRANCH = "├─"    # Intermediate step
TREE_LAST = "└─"      # Final step in a group
TREE_CONT = "│ "      # Continuation line under a branch

# ANSI color codes for terminal output
COLORS = {
    # Log levels
    'DEBUG': '\033[90m',      # Gray
    'INFO': '\033[36m',       # Cyan
    'WARNING': '\033[33m',    # Yellow
    'ERROR': '\033[31m',      # Red
    'CRITICAL': '\033[1;31m', # Bold Red
    # Modifiers
    'RESET': '\033[0m',
    'BOLD': '\033[1m',
    'DIM': '\033[2m',
    'GREEN': '\033[32m',
    'LIGHT_RED': '\033[91m',  # Light red for lower oncogenic scores
    'LIGHT_GREEN': '\033[92m',  # Light green for lower benign scores
}

# Unicode symbols for visual output
SYMBOLS = {
    'success': '✓',
    'failure': '✗',
}

# Prompts directory
PROMPTS_DIR = Path('./prompts')


# ============================================================================
# Log Message Formatting
# ============================================================================

def wrap_log_message(
    text: str,
    width: int = LOG_MSG_WIDTH,
    max_lines: int = LOG_MAX_LINES,
    prefix: str = "",
    continuation_prefix: str = ""
) -> List[str]:
    """
    Wrap long text for logging with continuation prefix.

    Args:
        text: Text to wrap
        width: Max characters per line
        max_lines: Maximum number of lines (truncate with ... if exceeded)
        prefix: Prefix for first line (e.g., "├─ ")
        continuation_prefix: Prefix for continuation lines (e.g., "│    ")

    Returns:
        List of formatted lines ready for logging
    """
    if not text:
        return [prefix] if prefix else []

    # Collapse whitespace and newlines
    text = ' '.join(text.split())

    # Account for prefix lengths in available width
    first_width = width - len(prefix)
    cont_width = width - len(continuation_prefix)

    lines = []
    remaining = text

    # First line
    if len(remaining) <= first_width:
        lines.append(f"{prefix}{remaining}")
        return lines

    # Wrap first line
    split_pos = remaining[:first_width].rfind(' ')
    if split_pos <= 0:
        split_pos = first_width
    lines.append(f"{prefix}{remaining[:split_pos]}")
    remaining = remaining[split_pos:].lstrip()

    # Continuation lines
    while remaining and len(lines) < max_lines:
        if len(remaining) <= cont_width:
            lines.append(f"{continuation_prefix}{remaining}")
            remaining = ""
        else:
            split_pos = remaining[:cont_width].rfind(' ')
            if split_pos <= 0:
                split_pos = cont_width
            lines.append(f"{continuation_prefix}{remaining[:split_pos]}")
            remaining = remaining[split_pos:].lstrip()

    # Truncate if needed
    if remaining:
        last_line = lines[-1]
        if len(last_line) > 3:
            lines[-1] = last_line[:-3] + "..."
        else:
            lines[-1] = last_line + "..."

    return lines


# ============================================================================
# Logging
# ============================================================================

def _normalize_module_name(name: str) -> str:
    """Normalize logger name for consistent output across TTY and non-TTY."""
    if name.startswith('src.'):
        name = name[4:]  # Remove 'src.' prefix
    if name.startswith('mol.'):
        name = name[4:]  # Remove 'mol.' prefix

    # Abbreviate long module names to fit 11-char column
    abbrevs = {
        'computational': 'compute',
        'variant_type': 'var_type',
        'functional': 'func',
        'enrichment': 'enrich',
        'population': 'pop',
    }
    name = abbrevs.get(name, name)
    if name in ('root', 'rag'):
        return 'main'
    return name


class ColoredFormatter(logging.Formatter):
    """Formatter with ANSI colors for log levels and special patterns."""

    def format(self, record):
        reset = COLORS['RESET']
        dim = COLORS['DIM']
        bold = COLORS['BOLD']

        # Timestamp with date for context
        timestamp = self.formatTime(record, '%Y-%m-%d %H:%M:%S')

        # Level with color, fixed width (7 chars fits WARNING)
        level_color = COLORS.get(record.levelname, '')
        level = f"{level_color}{record.levelname:7}{reset}"

        # Module name - normalized for consistency
        module = _normalize_module_name(record.name)

        # Format message
        message = record.getMessage()

        # Highlight molecular classification patterns (clinical outcome perspective)
        # Section marker: === GENE aa_change === (cyan/bold)
        if message.startswith('==='):
            message = f"{COLORS['INFO']}{bold}{message}{reset}"

        # Criteria format: "[+N]" or "[-N]" or "(+N)" or "(-N)"
        # Positive points toward oncogenic (red = bad clinical outcome)
        # Negative points toward benign (green = good clinical outcome)
        elif match := re.search(r'\[\+(\d+)\]', message):
            points = int(match.group(1))
            if points >= 4:
                message = f"{COLORS['ERROR']}{message}{reset}"  # Bold red for high oncogenic
            else:
                message = f"{COLORS['LIGHT_RED']}{message}{reset}"  # Light red for low oncogenic

        # Negative criterion: points toward benign (green = good outcome)
        elif match := re.search(r'\[-(\d+)\]', message):
            points = int(match.group(1))
            if points >= 4:
                message = f"{COLORS['GREEN']}{message}{reset}"  # Green for high benign
            else:
                message = f"{COLORS['LIGHT_GREEN']}{message}{reset}"  # Light green for low benign

        # Final summary: => GENE: Classification (clinical outcome perspective)
        # Oncogenic = Red (bad for patient), Benign = Green (good), VUS = Yellow
        elif message.startswith('=>'):
            if '(+' in message or 'Oncogenic' in message:
                message = f"{COLORS['ERROR']}{bold}{message}{reset}"  # Red = bad outcome
            elif '(-' in message or 'Benign' in message:
                message = f"{COLORS['GREEN']}{bold}{message}{reset}"  # Green = good outcome
            else:
                message = f"{COLORS['WARNING']}{bold}{message}{reset}"  # Yellow = uncertain

        formatted = f"{dim}{timestamp}{reset} | {level} | {dim}{module:11}{reset} | {message}"

        # Handle exception info (critical for logger.exception() and exc_info=True)
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            if exc_text:
                formatted += '\n' + exc_text

        # Handle stack info if present
        if record.stack_info:
            formatted += '\n' + record.stack_info

        return formatted


class PlainFormatter(logging.Formatter):
    """Plain text formatter with normalized module names for non-TTY output."""

    def __init__(self):
        super().__init__(
            '%(asctime)s | %(levelname)-7s | %(module_name)-11s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    def format(self, record):
        # Add normalized module name to record
        record.module_name = _normalize_module_name(record.name)
        formatted = super().format(record)

        # Handle exception info
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            if exc_text:
                formatted += '\n' + exc_text

        # Handle stack info if present
        if record.stack_info:
            formatted += '\n' + record.stack_info

        return formatted


def setup_logging(level: str = "INFO", color: bool = True) -> logging.Logger:
    """
    Setup logging with optional colors.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        color: Enable colored output (auto-disabled for non-TTY)

    Returns:
        Logger instance
    """
    # Auto-detect TTY (disable colors when piping/redirecting)
    use_color = color and sys.stdout.isatty()

    if use_color:
        formatter = ColoredFormatter()
    else:
        formatter = PlainFormatter()

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper()))
    root.handlers = [handler]

    logging.getLogger('httpx').setLevel(logging.WARNING)
    return root


def log_result(
    logger: logging.Logger,
    success: bool,
    message: str,
    metrics: Dict[str, Any] = None
) -> None:
    """
    Log operation completion with success/failure indicator.

    Args:
        logger: Logger instance
        success: Whether operation succeeded
        message: Result description
        metrics: Optional dict of metrics to include

    Output:
        ✓ Extracted 15 documents (mol_info=3)
        ✗ PubMed search failed: rate limit exceeded
    """
    indicator = SYMBOLS['success'] if success else SYMBOLS['failure']

    metrics_str = ""
    if metrics:
        items = [f"{k}={v}" for k, v in metrics.items()]
        metrics_str = f" ({', '.join(items)})"

    full_message = f"{indicator} {message}{metrics_str}"

    if success:
        logger.info(full_message)
    else:
        logger.error(full_message)


# ============================================================================
# File I/O
# ============================================================================

def load_json(file_path: Path) -> Dict:
    """Load JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(file_path: Path, data: Any, indent: int = 2):
    """Save data as JSON file."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)


def find_files(directory: Path, pattern: str) -> List[Path]:
    """
    Find files matching pattern in directory.

    Args:
        directory: Directory to search
        pattern: Glob pattern (e.g., "*.docx", "*.pdf")

    Returns:
        List of file paths
    """
    return list(directory.glob(pattern))


# ============================================================================
# Prompts
# ============================================================================

def load_prompts(name: str) -> Dict:
    """
    Load prompts from prompts/ directory.

    Args:
        name: Prompt file name without .yaml extension
              e.g., 'extraction_myeloma', 'enrichment', 'agent', 'decision'

    Returns:
        Dict containing prompt templates

    Example:
        >>> prompts = load_prompts('enrichment')
        >>> filled = prompts['question_long'].format(
        ...     main_diagnosis="...",
        ...     history="...",
        ...     question="..."
        ... )
    """
    prompts_file = PROMPTS_DIR / f"{name}.yaml"
    with open(prompts_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def sanitize_model_name(model: str) -> str:
    """Sanitize model name for filename (replace special chars)."""
    if not model:
        return 'unknown'
    return model.replace(":", "-").replace("/", "-")


def save_prompt(
    case_id: str,
    prompt_name: str,
    prompt: str,
    response: str = None,
    output_dir: str = 'agent_prompts',
    model: str = None,
    run_id: int = None
):
    """Save prompt (and optionally response) to file for debugging.

    Filename: {case_id}__{model}__{prompt_name}__run_{run_id}.txt
    """
    prompt_output_dir = Path(f'./results/{output_dir}')
    prompt_output_dir.mkdir(parents=True, exist_ok=True)

    model_safe = sanitize_model_name(model)
    filename = f"{case_id}__{model_safe}__{prompt_name}__run_{run_id}.txt"

    content = f"=== PROMPT ===\n{prompt}\n"
    if response:
        content += f"\n=== RESPONSE ===\n{response}\n"

    (prompt_output_dir / filename).write_text(content, encoding='utf-8')


# ============================================================================
# Data Utilities
# ============================================================================

def format_prior_treatments(sections: dict) -> str:
    """Format prior_treatments from sections dict to comma-separated string.

    Handles str (JSON), list, or missing values robustly.
    Returns 'keine Therapien' if empty or unparseable.
    """
    raw = sections.get('prior_treatments', '[]')
    if isinstance(raw, list):
        treatments = raw
    elif isinstance(raw, str):
        try:
            treatments = json.loads(raw) or []
        except (json.JSONDecodeError, TypeError):
            treatments = []
    else:
        treatments = []
    return ", ".join(treatments) or "keine Therapien"


def extract_patient_id(filename: str) -> str:
    """
    Extract patient ID (numeric identifier) from filename.

    Extracts the first sequence of digits found before the first dot in the filename.
    Returns empty string if no numeric identifier is found.

    Args:
        filename: Filename to extract patient ID from

    Returns:
        Patient ID as string, or empty string if no numeric identifier found

    Examples:
        >>> extract_patient_id('patient_123.docx')
        '123'
        >>> extract_patient_id('case_456_tumor.docx')
        '456'
        >>> extract_patient_id('789.docx')
        '789'
        >>> extract_patient_id('report.docx')
        ''
    """
    # Extract filename stem (part before first dot)
    stem = filename.split('.')[0] if '.' in filename else filename

    # Find first sequence of digits
    match = re.search(r'\d+', stem)

    return match.group() if match else ''


def get_cache_path(input_path: Path, cache_dir: Path) -> Path:
    """
    Get cache file path for extracted document.

    Args:
        input_path: Original document path
        cache_dir: Cache directory

    Returns:
        Path to cache file
    """
    return cache_dir / f"{input_path.stem}.json"


def supports_temperature(model: str) -> bool:
    """Check if model supports custom temperature values.

    Note: This list needs periodic updates as new OpenAI models are released.
    Current models that don't support temperature: gpt-5, o1, o3, o4 series.
    """
    no_temp_models = ('gpt-5', 'o1', 'o3', 'o4')
    return not any(m in model.lower() for m in no_temp_models)


def validate_query_extractions(
    query_dir: Path,
    cache_dir: Path
) -> tuple[bool, set[str], set[str], List[Path]]:
    """
    Validate all query files have been extracted.

    Compares query case files (.docx/.txt) in query_dir with .json files in cache_dir.
    Returns validation results without side effects (no logging, no sys.exit).

    Args:
        query_dir: Directory containing query case files
        cache_dir: Directory containing extracted .json files

    Returns:
        Tuple of (is_valid, missing_stems, extra_stems, extracted_files):
        - is_valid: True if all query files have extractions
        - missing_stems: Set of file stems without extractions
        - extra_stems: Set of cached files without corresponding queries
        - extracted_files: List of paths to extracted .json files
    """
    query_files = find_files(query_dir, "*.docx") + find_files(query_dir, "*.txt")
    query_files = [f for f in query_files if not f.name.startswith('~')]
    query_stems = {f.stem for f in query_files}

    # Check if cache directory exists
    if not cache_dir.exists():
        return (False, query_stems, set(), [])

    # Find extracted .json files
    extracted_files = list(cache_dir.glob("*.json"))
    extracted_stems = {f.stem for f in extracted_files}

    # Compare
    missing = query_stems - extracted_stems
    extra = extracted_stems - query_stems
    is_valid = len(missing) == 0

    return (is_valid, missing, extra, extracted_files)


# ============================================================================
# Batch Processing
# ============================================================================

def process_items_batch(
    items: List[T],
    process_fn: Callable[[T], R],
    parallel: bool = False,
    max_workers: int = 100,
    logger: logging.Logger = None,
    item_name_fn: Callable[[T], str] = None
) -> tuple[List[R], List[tuple[T, str]]]:
    """
    Process items with automatic parallel/sequential execution.

    Args:
        items: List of items to process
        process_fn: Function that takes an item and returns a result.
                    Should raise an exception on failure.
        parallel: If True, use ThreadPoolExecutor; otherwise process sequentially
        max_workers: Max concurrent workers for parallel mode (default: 100)
        logger: Optional logger for progress updates
        item_name_fn: Optional function to get display name from item for logging

    Returns:
        Tuple of (successful_results, failed_items):
        - successful_results: List of results from successful process_fn calls
        - failed_items: List of (item, error_message) tuples for failures
    """
    results = []
    failures = []
    total = len(items)

    def get_name(item):
        return item_name_fn(item) if item_name_fn else "item"

    if parallel:
        # Parallel processing with controlled submission (only max_workers active at a time)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_item = {}
            items_iter = iter(items)
            completed_count = 0

            # Submit initial batch (up to max_workers)
            for _ in range(min(max_workers, total)):
                try:
                    item = next(items_iter)
                    future = executor.submit(process_fn, item)
                    future_to_item[future] = item
                except StopIteration:
                    break

            # Process completed futures and submit new ones
            while future_to_item:
                # Wait for any future to complete
                done, _ = wait(future_to_item.keys(), return_when=FIRST_COMPLETED)

                for future in done:
                    item = future_to_item.pop(future)
                    completed_count += 1
                    try:
                        result = future.result()
                        results.append(result)
                        if logger:
                            logger.info(f"[{completed_count}/{total}] ✓ {get_name(item)}")
                    except Exception as e:
                        failures.append((item, str(e)))
                        if logger:
                            logger.warning(f"[{completed_count}/{total}] ⚠️  {get_name(item)}: {e}")

                    # Submit next item if available
                    try:
                        next_item = next(items_iter)
                        future = executor.submit(process_fn, next_item)
                        future_to_item[future] = next_item
                    except StopIteration:
                        pass
    else:
        # Sequential processing
        for i, item in enumerate(items, 1):
            try:
                result = process_fn(item)
                results.append(result)
                if logger:
                    logger.info(f"[{i}/{total}] ✓ {get_name(item)}")
            except Exception as e:
                failures.append((item, str(e)))
                if logger:
                    logger.error(f"[{i}/{total}] ❌ {get_name(item)}: {e}")

    return results, failures
