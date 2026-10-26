"""GitHub CLIの呼び出しを扱う。"""

import json
import subprocess
import sys
import time


def run_gh(*arguments: str) -> str:
    """ghの標準出力を取得し、一時的な失敗を再試行する。"""
    attempt = 0
    while True:
        try:
            return subprocess.check_output(["gh", *arguments], encoding="utf-8")
        except subprocess.CalledProcessError as error:
            attempt += 1
            if attempt == 3 or not _is_retryable(error):
                raise
            print("ghを再試行します。", file=sys.stderr)
            time.sleep(1)


def _is_retryable(error: subprocess.CalledProcessError) -> bool:
    """ghの失敗を再試行できるか判定する。"""
    if error.returncode in {2, 4}:
        return False

    try:
        response = json.loads(error.stdout)
    except json.JSONDecodeError:
        return True

    return response.get("status") not in {"400", "401", "404"}
