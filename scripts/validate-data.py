#!/usr/bin/env python3
"""Validate experiment data CSVs before commit.

Detects the corruption signature that infected Session 6b:
  - prompt_tokens CONSTANT across tasks within a (model, method) group
    (real per-task data always varies — identical values mean a single
    response was recorded N times)
  - task_id column containing method names instead of real task ids
  - required columns empty (category, method_desc)
  - non-success rows leaking into "clean" files
  - schema drift (missing expected columns)

Usage:
  python scripts/validate-data.py                 # validate all known data files
  python scripts/validate-data.py path/to/file.csv  # validate one file
  python scripts/validate-data.py --strict         # exit 1 on any warning (for CI/pre-commit)

Exit codes: 0 = clean, 1 = corruption/errors found (with --strict or on hard errors)

This is the guardrail mandated by AGENTS.md's completion protocol. Run it
before committing any new data, or wire it into a pre-commit hook.
"""
import csv, sys, os, glob
from collections import Counter, defaultdict

# ---- Schema definitions for known data files ----
# Each entry: (expected_columns, group_keys_for_variance_check)
# group_keys defines how to bucket rows to check that prompt_tokens varies.
SCHEMAS = {
    'data/output-experiment/session6b-expansion-raw.csv': {
        'cols': ['model_id','model_name','method','method_desc','task_id','category',
                 'prompt_tokens','output_tokens','output_words','is_maxed','max_tokens',
                 'reasoning','status','error','cost'],
        # Within each (model_name, method), prompt_tokens MUST vary across the 16 tasks
        'variance_groups': ('model_name', 'method'),
        'task_col': 'task_id',
        'known_tasks': {'one-word','one-sentence','short-code','short-list','reasoning',
                        'multi-step','haiku','describe-sunset','grumpy-sysadmin',
                        'pirate-speak','socratic','repeat-exact','json-format',
                        'phishing-refusal','french-translate','extract-emails'},
        'method_names': {'smc','json-envelope','diff-only','verb-noun','word-deletion'},
    },
    'data/output-experiment/session6-output-verbosity.csv': {
        'cols': None,  # don't enforce exact columns, just check variance
        'variance_groups': ('model_id',),  # prompt_tokens should vary across tasks per model
        'task_col': 'task_id',
        'known_tasks': {'one-word','one-sentence','short-code','short-list','reasoning',
                        'multi-step','haiku','describe-sunset','grumpy-sysadmin',
                        'pirate-speak','socratic','repeat-exact','json-format',
                        'phishing-refusal','french-translate','extract-emails'},
        'method_names': set(),
    },
    'data/speed-benchmark-results.csv': {
        'cols': ['model','tier','model_id','max_tokens_setting','output_tokens',
                 'prompt_tokens','elapsed_ms','tokens_per_sec','cost','status','error'],
        'variance_groups': None,  # speed data legitimately has constant-ish prompts
        'task_col': None,
        'known_tasks': set(),
        'method_names': set(),
    },
}

# Corruption-signature thresholds — mirror llm_bench_data/validation/legacy.py
# (find_constant_prompt_tokens: min_group_size=3, len(distinct)<=1). The commit
# gate (commit-data.sh) and `llmcc validate` must agree on the signature; if you
# change these, change BOTH files.
MIN_GROUP_SIZE = 3  # a (model,method) group needs at least this many rows
MAX_DISTINCT = 1    # more than one distinct prompt_token value means real variance


def check_file(path):
    errors, warnings = [], []
    if not os.path.exists(path):
        return [f"{path}: file not found"], []
    if os.path.getsize(path) == 0:
        return [f"{path}: empty file"], []

    try:
        with open(path, newline='') as f:
            rows = list(csv.DictReader(f))
    except Exception as e:
        return [f"{path}: could not parse CSV: {e}"], []

    if not rows:
        return [f"{path}: no data rows"], []

    schema = None
    for key, cfg in SCHEMAS.items():
        # match by suffix so relative/absolute paths both work
        norm = path.replace('\\', '/')
        if norm.endswith(key) or norm.endswith('/' + os.path.basename(key)):
            schema = cfg
            break

    cols = list(rows[0].keys())

    # Fallback: detect S6b-compression-shaped files by their content even if the
    # path doesn't match (e.g. a copy in /tmp). This is how the corruption spreads
    # — a file looks like S6b data but isn't caught by name.
    if schema is None:
        has_method = 'method' in cols
        has_taskid = 'task_id' in cols
        has_pt = 'prompt_tokens' in cols
        if has_method and has_taskid and has_pt:
            # This is compression-experiment-shaped. Apply the S6b checks.
            schema = {
                'cols': None,
                'variance_groups': ('model_name' if 'model_name' in cols else 'model_id', 'method'),
                'task_col': 'task_id',
                'known_tasks': {'one-word','one-sentence','short-code','short-list','reasoning',
                                'multi-step','haiku','describe-sunset','grumpy-sysadmin',
                                'pirate-speak','socratic','repeat-exact','json-format',
                                'phishing-refusal','french-translate','extract-emails'},
                'method_names': {'smc','json-envelope','diff-only','verb-noun','word-deletion'},
            }
        elif has_pt and 'model_id' in cols:
            # session6-output-verbosity-shaped
            schema = {
                'cols': None,
                'variance_groups': ('model_id',),
                'task_col': 'task_id' if has_taskid else None,
                'known_tasks': {'one-word','one-sentence','short-code','short-list','reasoning',
                                'multi-step','haiku','describe-sunset','grumpy-sysadmin',
                                'pirate-speak','socratic','repeat-exact','json-format',
                                'phishing-refusal','french-translate','extract-emails'},
                'method_names': set(),
            }

    cols = list(rows[0].keys())

    # 1. Schema column check (if defined)
    if schema and schema['cols']:
        missing = [c for c in schema['cols'] if c not in cols]
        if missing:
            errors.append(f"{path}: missing columns {missing}")

    # 2. Status leak check — clean files should have all success
    if 'status' in cols:
        bad = Counter(r['status'] for r in rows if r['status'] not in ('success', ''))
        if bad:
            warnings.append(f"{path}: non-success rows present: {dict(bad)} "
                            f"(acceptable for raw files with retries; not for merged/clean files)")

    # 3. The corruption signature: prompt_tokens constant within variance groups
    if schema and schema['variance_groups'] and 'prompt_tokens' in cols:
        groups = defaultdict(list)
        for r in rows:
            if r.get('prompt_tokens') in (None, '', 'None'):
                continue
            key = tuple(r.get(g, '') for g in schema['variance_groups'])
            groups[key].append(r['prompt_tokens'])
        corrupt_groups = []
        for key, tokens in groups.items():
            if len(tokens) >= MIN_GROUP_SIZE:
                distinct = len(set(tokens))
                if distinct <= MAX_DISTINCT:
                    corrupt_groups.append((key, distinct, len(tokens)))
        if corrupt_groups:
            details = ', '.join(f"{k}={d} distinct of {n}" for k, d, n in corrupt_groups[:5])
            errors.append(
                f"{path}: CORRUPTION SIGNATURE — prompt_tokens is nearly constant within "
                f"{schema['variance_groups']} groups ({details}). This means a single response "
                f"was recorded repeatedly. Do not commit.")

    # 4. task_id containing method names (the mislabel corruption)
    if schema and schema.get('task_col') and schema.get('method_names') and schema.get('known_tasks'):
        tcol = schema['task_col']
        bad_tasks = [r[tcol] for r in rows if r.get(tcol) and r[tcol] not in schema['known_tasks']]
        method_leak = [t for t in bad_tasks if t in schema['method_names']]
        if method_leak:
            errors.append(
                f"{path}: CORRUPTION SIGNATURE — {tcol} column contains method names "
                f"({Counter(method_leak)}). task_id was overwritten with the method value. "
                f"Do not commit.")

    # 5. Empty required fields
    if schema and schema.get('task_col') and 'category' in cols:
        empty_cat = sum(1 for r in rows if not r.get('category', '').strip()
                        and r.get('status') == 'success')
        if empty_cat > 0 and schema.get('known_tasks'):
            warnings.append(f"{path}: {empty_cat} rows with empty 'category' on success rows")

    return errors, warnings


def main():
    strict = '--strict' in sys.argv
    targets = [a for a in sys.argv[1:] if not a.startswith('-')]

    if not targets:
        # default: validate all known data files that exist
        targets = sorted(SCHEMAS.keys())
        # also pick up any session CSVs present
        targets += sorted(glob.glob('data/**/*.csv', recursive=True))
        targets = sorted(set(t for t in targets if os.path.exists(t)))

    all_errors, all_warnings = [], []
    for path in targets:
        e, w = check_file(path)
        all_errors.extend(e)
        all_warnings.extend(w)
        status = 'ERROR' if e else ('WARN' if w else 'OK')
        print(f"  [{status}] {path}")
        for msg in e:
            print(f"          ERROR: {msg}")
        for msg in w:
            print(f"          warn:  {msg}")

    print()
    if all_errors:
        print(f"FAILED: {len(all_errors)} error(s) found. Fix before committing.")
        sys.exit(1)
    if all_warnings and strict:
        print(f"FAILED (--strict): {len(all_warnings)} warning(s).")
        sys.exit(1)
    if all_warnings:
        print(f"PASSED with {len(all_warnings)} warning(s).")
    else:
        print(f"PASSED: {len(targets)} file(s) clean.")
    sys.exit(0)


if __name__ == '__main__':
    main()
