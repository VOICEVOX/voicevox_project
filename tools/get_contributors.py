"""指定したコミット範囲の貢献者を取得します。"""

import argparse
import json
import subprocess
import sys

from github_cli import run_gh


def main() -> None:
    """貢献者のGitHubユーザー名を表示します。"""
    options = parse_args()
    for contributor in get_contributors(options.base, options.head):
        print(contributor)


class Options(argparse.Namespace):
    """コマンドライン引数。"""

    base: str
    head: str


def parse_args() -> Options:
    """コマンドライン引数を解析します。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", help="比較元のコミット・タグ・ブランチです。")
    parser.add_argument("head", help="比較先のコミット・タグ・ブランチです。")
    return parser.parse_args(namespace=Options())


def get_contributors(base: str, head: str) -> list[str]:
    """base..headの貢献者のGitHubユーザー名を取得します。"""
    commits = subprocess.check_output(
        ["git", "rev-list", f"{base}..{head}"], text=True
    ).splitlines()

    contributors: set[str] = set()
    for commit in commits:
        response = json.loads(
            run_gh("api", f"repos/{{owner}}/{{repo}}/commits/{commit}")
        )
        if response["author"] is None:
            print(
                f"警告: コミット{commit}にはGitHubユーザーが紐付いていないため除外します。",
                file=sys.stderr,
            )
        elif response["author"]["login"] not in {"github-actions[bot]", "Copilot"}:
            contributors.add(response["author"]["login"])

    return sorted(contributors)


if __name__ == "__main__":
    main()
