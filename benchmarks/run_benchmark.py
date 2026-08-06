#!/usr/bin/env python3
"""End-to-end token benchmark: auto-reviewer versus pi-code-agent.

Both arms review the same historical commit with the same LM Studio model.
The auto-reviewer arm reproduces the production prompt construction. The pi
arm runs a fresh coding-agent session and sums usage across every model turn.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from openai import OpenAI

from auto_reviewer import config
from auto_reviewer.ast_analysis import analyze_added_code, extract_parent_scope
from auto_reviewer.main import get_added_line_number_from_diff
from auto_reviewer.template import render_prompt


DEFAULT_COMMITS = [
    # Small Python changes.
    "55f38295ae1b",
    "b94c10048cec",
    "2307f04f256b",
    "622a7758b2b0",
    "485a91d06a1f",
    # Medium Python changes.
    "105730acc162",
    "1225325165c5",
    "2759384a6e2a",
    "0b394479e5fa",
    "449052f8dcc8",
    # Large Python changes.
    "c9759ae9a195",
    "77fb261052d7",
    "1d00eb626e13",
    "7c36d1a322c4",
    "94dddfcb04ab",
]

PI_PROMPT = """Review the changes introduced by HEAD compared with HEAD~1.
Inspect the repository as needed, but do not modify any files. Report only
high-confidence bugs, security issues, and meaningful maintainability or
performance improvements. Output only Markdown list items in this format:
- [Critical] high-severity bug or security issue
- [Optimization] meaningful performance or maintainability improvement
- [Summary] one-sentence description of the core change
If there are no Critical or Optimization findings, output only Summary.
"""


@dataclass
class RunResult:
    case_id: str
    commit: str
    subject: str
    size_bucket: str
    added_lines: int
    deleted_lines: int
    arm: str
    repeat: int
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    total_tokens: int
    model_calls: int
    tool_calls: int
    duration_seconds: float
    response: str
    error: str | None
    prompt_characters: int | None = None


def run_command(
    args: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout: int | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=check,
    )


def git_output(target: Path, *args: str) -> str:
    return run_command(["git", *args], cwd=target).stdout


@contextlib.contextmanager
def working_directory(path: Path) -> Iterator[None]:
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def commit_metadata(target: Path, revision: str) -> dict[str, Any]:
    sha = git_output(target, "rev-parse", revision).strip()
    subject = git_output(target, "show", "-s", "--format=%s", sha).strip()
    author = git_output(target, "show", "-s", "--format=%an", sha).strip()
    message = git_output(target, "show", "-s", "--format=%B", sha).strip()
    numstat = git_output(target, "show", "--format=", "--numstat", sha, "--", "*.py")
    added = 0
    deleted = 0
    for line in numstat.splitlines():
        fields = line.split("\t")
        if len(fields) >= 2 and fields[0].isdigit() and fields[1].isdigit():
            added += int(fields[0])
            deleted += int(fields[1])
    changed = added + deleted
    size_bucket = "small" if changed < 20 else "medium" if changed < 50 else "large"
    return {
        "sha": sha,
        "subject": subject,
        "author": author,
        "message": message,
        "added": added,
        "deleted": deleted,
        "size_bucket": size_bucket,
    }


def build_auto_prompt(target: Path, metadata: dict[str, Any]) -> str:
    no_context_diff = git_output(target, "diff", "-U0", "HEAD~1", "HEAD", "--", "*.py")
    rich_context_diff = git_output(target, "diff", "-U10", "HEAD~1", "HEAD", "--", "*.py")
    added_lines = get_added_line_number_from_diff(no_context_diff)
    related_context: dict[str, list[str]] = {}
    with working_directory(target):
        for filename, line_numbers in added_lines.items():
            analysis = analyze_added_code(filename, line_numbers)
            # Production de-duplicates with a set. Sorting stabilizes repeated
            # runs without changing the actual prompt contents.
            related_context[filename] = sorted(extract_parent_scope(analysis))
    return render_prompt(
        template_name="with_analysis.j2",
        diff_content=rich_context_diff,
        commit_sha=metadata["sha"][:7],
        commit_author=metadata["author"],
        commit_message=metadata["message"],
        language="English",
        related_context=related_context,
    )


def run_auto(
    *,
    target: Path,
    metadata: dict[str, Any],
    client: OpenAI,
    model: str,
    max_tokens: int,
    repeat: int,
) -> RunResult:
    started = time.monotonic()
    prompt = ""
    try:
        prompt = build_auto_prompt(target, metadata)
        request: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
        }
        # Explicitly keep Qwen's native thinking mode enabled in both arms.
        if model.startswith("qwen/") or model == "auto-review-bench-qwen-max":
            request["extra_body"] = {
                "chat_template_kwargs": {
                    "enable_thinking": True,
                    "preserve_thinking": True,
                }
            }
        completion = client.chat.completions.create(**request)
        usage = completion.usage
        response = completion.choices[0].message.content or ""
        details = getattr(usage, "completion_tokens_details", None)
        reasoning_tokens = int(getattr(details, "reasoning_tokens", 0) or 0)
        finish_reason = completion.choices[0].finish_reason
        if not response.strip():
            error = "model produced no visible review"
        elif finish_reason == "length":
            error = "review was truncated at the output limit"
        else:
            error = None
        return RunResult(
            case_id=metadata["sha"][:12], commit=metadata["sha"],
            subject=metadata["subject"], size_bucket=metadata["size_bucket"],
            added_lines=metadata["added"], deleted_lines=metadata["deleted"],
            arm="auto-reviewer", repeat=repeat,
            input_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
            reasoning_tokens=reasoning_tokens,
            total_tokens=int(getattr(usage, "total_tokens", 0) or 0),
            model_calls=1, tool_calls=0,
            duration_seconds=time.monotonic() - started,
            response=response, error=error, prompt_characters=len(prompt),
        )
    except Exception as exc:  # Keep the full benchmark running.
        return RunResult(
            case_id=metadata["sha"][:12], commit=metadata["sha"],
            subject=metadata["subject"], size_bucket=metadata["size_bucket"],
            added_lines=metadata["added"], deleted_lines=metadata["deleted"],
            arm="auto-reviewer", repeat=repeat,
            input_tokens=0, output_tokens=0, reasoning_tokens=0, total_tokens=0,
            model_calls=0, tool_calls=0,
            duration_seconds=time.monotonic() - started,
            response="", error=f"{type(exc).__name__}: {exc}",
            prompt_characters=len(prompt) if prompt else None,
        )


def assistant_text(message: dict[str, Any]) -> str:
    return "\n".join(
        str(item.get("text", ""))
        for item in message.get("content", [])
        if item.get("type") == "text"
    )


def failed_pi_result(
    metadata: dict[str, Any], repeat: int, started: float, error: str
) -> RunResult:
    return RunResult(
        case_id=metadata["sha"][:12], commit=metadata["sha"],
        subject=metadata["subject"], size_bucket=metadata["size_bucket"],
        added_lines=metadata["added"], deleted_lines=metadata["deleted"],
        arm="pi-code-agent", repeat=repeat,
        input_tokens=0, output_tokens=0, reasoning_tokens=0, total_tokens=0,
        model_calls=0, tool_calls=0,
        duration_seconds=time.monotonic() - started,
        response="", error=error,
    )


def run_pi(
    *,
    target: Path,
    metadata: dict[str, Any],
    pi_home: Path,
    model: str,
    timeout: int,
    repeat: int,
) -> RunResult:
    started = time.monotonic()
    env = os.environ.copy()
    env["PI_CODING_AGENT_DIR"] = str(pi_home)
    env["PI_OFFLINE"] = "1"
    command = [
        "pi", "--mode", "json", "--no-session",
        "--model", f"lmstudio/{model}", "--api-key", "lm-studio",
        "--thinking", "max", "--tools", "read,grep,find,ls,bash",
        "--no-extensions", "--no-skills", "--no-prompt-templates",
        "--approve", PI_PROMPT,
    ]
    try:
        process = run_command(command, cwd=target, env=env, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        return failed_pi_result(metadata, repeat, started, f"Timeout after {timeout}s: {exc}")

    input_tokens = output_tokens = reasoning_tokens = total_tokens = 0
    model_calls = tool_calls = 0
    responses: list[str] = []
    final_stop_reason: str | None = None
    parse_errors: list[str] = []
    for line_number, line in enumerate(process.stdout.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            parse_errors.append(f"line {line_number}: {exc}")
            continue
        if event.get("type") == "tool_execution_start":
            tool_calls += 1
        if event.get("type") != "message_end":
            continue
        message = event.get("message", {})
        if message.get("role") != "assistant":
            continue
        usage = message.get("usage") or {}
        final_stop_reason = message.get("stopReason")
        model_calls += 1
        current_input = int(usage.get("input", 0) or 0)
        current_output = int(usage.get("output", 0) or 0)
        cache_read = int(usage.get("cacheRead", 0) or 0)
        cache_write = int(usage.get("cacheWrite", 0) or 0)
        input_tokens += current_input + cache_read + cache_write
        output_tokens += current_output
        total_tokens += int(usage.get(
            "totalTokens", current_input + current_output + cache_read + cache_write
        ) or 0)
        details = usage.get("outputTokensDetails") or {}
        reasoning_tokens += int(details.get("reasoningTokens", 0) or 0)
        text = assistant_text(message)
        if text:
            responses.append(text)

    errors = []
    if process.returncode != 0:
        errors.append(f"pi exited {process.returncode}")
    if parse_errors:
        errors.append("JSON parse errors: " + "; ".join(parse_errors[:3]))
    if process.stderr.strip():
        errors.append("stderr: " + process.stderr.strip()[-1000:])
    if model_calls == 0:
        errors.append("no assistant usage events")
    if not responses or not responses[-1].strip():
        errors.append("model produced no visible review")
    elif final_stop_reason == "length":
        errors.append("review was truncated at the output limit")
    return RunResult(
        case_id=metadata["sha"][:12], commit=metadata["sha"],
        subject=metadata["subject"], size_bucket=metadata["size_bucket"],
        added_lines=metadata["added"], deleted_lines=metadata["deleted"],
        arm="pi-code-agent", repeat=repeat,
        input_tokens=input_tokens, output_tokens=output_tokens,
        reasoning_tokens=reasoning_tokens, total_tokens=total_tokens,
        model_calls=model_calls, tool_calls=tool_calls,
        duration_seconds=time.monotonic() - started,
        response=responses[-1] if responses else "",
        error=" | ".join(errors) if errors else None,
    )


def write_summary(results: list[RunResult], output_path: Path) -> Path:
    by_key: dict[tuple[str, int], dict[str, RunResult]] = {}
    for result in results:
        by_key.setdefault((result.case_id, result.repeat), {})[result.arm] = result
    pairs: list[tuple[RunResult, RunResult, float]] = []
    for arms in by_key.values():
        auto = arms.get("auto-reviewer")
        pi = arms.get("pi-code-agent")
        if not auto or not pi or auto.error or pi.error or pi.total_tokens <= 0:
            continue
        saving = (pi.total_tokens - auto.total_tokens) / pi.total_tokens * 100
        pairs.append((auto, pi, saving))

    auto_total = sum(auto.total_tokens for auto, _, _ in pairs)
    pi_total = sum(pi.total_tokens for _, pi, _ in pairs)
    savings = [saving for _, _, saving in pairs]
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "successful_pairs": len(pairs),
        "failed_runs": [asdict(item) for item in results if item.error],
        "auto_total_tokens": auto_total,
        "pi_total_tokens": pi_total,
        "aggregate_saving_percent": (
            (pi_total - auto_total) / pi_total * 100 if pi_total else None
        ),
        "median_case_saving_percent": statistics.median(savings) if savings else None,
        "min_case_saving_percent": min(savings) if savings else None,
        "max_case_saving_percent": max(savings) if savings else None,
        "auto_total_model_calls": sum(auto.model_calls for auto, _, _ in pairs),
        "pi_total_model_calls": sum(pi.model_calls for _, pi, _ in pairs),
        "pi_total_tool_calls": sum(pi.tool_calls for _, pi, _ in pairs),
        "auto_total_seconds": sum(auto.duration_seconds for auto, _, _ in pairs),
        "pi_total_seconds": sum(pi.duration_seconds for _, pi, _ in pairs),
        "cases": [
            {
                "case_id": auto.case_id,
                "subject": auto.subject,
                "size_bucket": auto.size_bucket,
                "changed_lines": auto.added_lines + auto.deleted_lines,
                "auto_tokens": auto.total_tokens,
                "pi_tokens": pi.total_tokens,
                "pi_model_calls": pi.model_calls,
                "pi_tool_calls": pi.tool_calls,
                "saving_percent": saving,
            }
            for auto, pi, saving in pairs
        ],
    }
    summary_path = output_path.with_name(output_path.stem + "-summary.json")
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    return summary_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--model", default="auto-review-bench-qwen-max")
    parser.add_argument("--base-url", default="http://127.0.0.1:1234/v1")
    parser.add_argument("--max-tokens", type=int, default=262144)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--commits", nargs="*", default=DEFAULT_COMMITS)
    parser.add_argument("--arms", nargs="+", choices=["auto", "pi"], default=["auto", "pi"])
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = args.repo.resolve()
    benchmark_dir = Path(__file__).resolve().parent
    pi_home = benchmark_dir / "pi-agent"
    commits = args.commits[: args.limit] if args.limit else args.commits
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_path = args.output or benchmark_dir / "results" / f"runs-{timestamp}.jsonl"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    config.FILE_PATTERNS = ["*.py"]
    client = OpenAI(base_url=args.base_url, api_key="lm-studio")
    results: list[RunResult] = []

    with tempfile.TemporaryDirectory(prefix="auto-reviewer-bench-") as temp_dir:
        target = Path(temp_dir) / "target"
        print(f"Cloning benchmark target to {target}", flush=True)
        run_command(["git", "clone", "--quiet", str(repo), str(target)], cwd=repo)
        for case_number, revision in enumerate(commits, start=1):
            run_command(["git", "checkout", "--quiet", "--detach", revision], cwd=target)
            metadata = commit_metadata(target, "HEAD")
            print(
                f"[{case_number}/{len(commits)}] {metadata['sha'][:12]} "
                f"{metadata['size_bucket']} {metadata['subject']}", flush=True,
            )
            for repeat in range(1, args.repeats + 1):
                arms = list(args.arms)
                if (case_number + repeat) % 2:
                    arms.reverse()
                for arm in arms:
                    print(f"  repeat {repeat}: {arm}...", end="", flush=True)
                    if arm == "auto":
                        result = run_auto(
                            target=target, metadata=metadata, client=client,
                            model=args.model, max_tokens=args.max_tokens, repeat=repeat,
                        )
                    else:
                        result = run_pi(
                            target=target, metadata=metadata, pi_home=pi_home,
                            model=args.model, timeout=args.timeout, repeat=repeat,
                        )
                    results.append(result)
                    with output_path.open("a", encoding="utf-8") as output_file:
                        output_file.write(json.dumps(asdict(result), ensure_ascii=False) + "\n")
                    status = f"ERROR {result.error}" if result.error else f"{result.total_tokens} tokens"
                    print(f" {status} ({result.duration_seconds:.1f}s)", flush=True)

    summary_path = write_summary(results, output_path)
    print(f"Raw results: {output_path}")
    print(f"Summary: {summary_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
