"""VOICEVOX関連リポジトリのリリースノートを生成する。"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Literal

from github_cli import run_gh


def main() -> None:
    """リリースノートを出力する。"""
    options = parse_args()
    body = (generate_release_note(options) + "\n").encode("utf-8")
    if options.output is None:
        sys.stdout.buffer.write(body)
    else:
        options.output.write_bytes(body)


class Options(argparse.Namespace):
    """コマンドライン引数。"""

    target: Literal["editor", "engine", "core", "resource", "vvm"]
    version: str | None
    previous_version: str | None
    summary: list[str]
    summary_file: Path | None
    output: Path | None
    ref: str


def parse_args() -> Options:
    """コマンドライン引数を解析する。"""
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "target",
        choices=("editor", "engine", "core", "resource", "vvm"),
        help="リリースノートを作る対象。",
    )
    parser.add_argument(
        "--version",
        help="対象のバージョン。省略時は公開日時が最新のリリースになる。",
    )
    parser.add_argument(
        "--previous-version",
        help="GitHubの自動生成リリースノートの比較元バージョン。",
    )

    summary_group = parser.add_mutually_exclusive_group()
    summary_group.add_argument(
        "--summary",
        action="append",
        default=[],
        help="目玉更新内容のMarkdown。複数回指定できる。",
    )
    summary_group.add_argument(
        "--summary-file",
        type=Path,
        help="目玉更新内容のMarkdownファイル。",
    )

    parser.add_argument(
        "--output",
        type=Path,
        help="出力先ファイル。省略時はstdoutに出力する。",
    )
    parser.add_argument(
        "--ref",
        default="main",
        help="coreの主要変更点を取得するGit参照。既定値はmain。",
    )

    return parser.parse_args(namespace=Options())


def read_summary_text(options: Options) -> str:
    """対象に応じて更新内容を読み込む。"""
    if options.summary_file is None:
        text = "\n".join(options.summary).strip()
    else:
        text = options.summary_file.read_text(encoding="utf-8").strip()

    if (text != "") != (options.target in {"editor", "engine", "vvm"}):
        raise ValueError(
            "更新内容はeditor・engine・vvmでは必須で、core・resourceでは指定できません。"
        )
    return text


def generate_release_note(options: Options) -> str:
    """対象に応じたリリースノートを生成する。"""
    summary = read_summary_text(options)

    repository = {
        "editor": "VOICEVOX/voicevox",
        "engine": "VOICEVOX/voicevox_engine",
        "core": "VOICEVOX/voicevox_core",
        "resource": "VOICEVOX/voicevox_resource",
        "vvm": "VOICEVOX/voicevox_vvm",
    }[options.target]
    version = options.version
    if version is None:
        version = get_latest_version(repository)

    match options.target:
        case "core":
            assets = get_release_assets(repository, version)
            return generate_core_release_note(version, options.ref, assets)
        case "editor":
            assets = get_release_assets(repository, version)
            header = join_markdown(
                build_editor_asset_list(version, assets), "## 追加機能", summary
            )
        case "engine":
            assets = get_release_assets(repository, version)
            header = join_markdown(
                summary, "## パッケージ案内", build_engine_asset_list(version, assets)
            )
        case "vvm":
            header = join_markdown(
                "## 内容",
                summary,
                "詳細や利用規約は [README](https://github.com/VOICEVOX/voicevox_vvm/blob/main/README.md) をご参照ください。",
            )
        case "resource":
            header = ""

    notes = generate_github_release_note(repository, version, options.previous_version)
    return join_markdown(header, notes)


def get_latest_version(repository: str) -> str:
    """公開日時が最新のリリースのバージョンを取得する。"""
    releases = json.loads(
        run_gh(
            "release",
            "list",
            "-R",
            repository,
            "--exclude-drafts",
            "--json",
            "tagName,publishedAt",
        )
    )
    return max(releases, key=lambda release: release["publishedAt"])["tagName"]


def get_release_assets(repository: str, version: str) -> dict[str, str]:
    """GitHub Releaseのアセット名とURLを取得する。"""
    response = json.loads(
        run_gh("release", "view", "-R", repository, version, "--json", "assets")
    )
    return {asset["name"]: asset["url"] for asset in response["assets"]}


def generate_github_release_note(
    repository: str, version: str, previous_version: str | None
) -> str:
    """GitHubのリリースノートを自動生成する。"""
    arguments = [
        "api",
        f"repos/{repository}/releases/generate-notes",
        "-f",
        f"tag_name={version}",
    ]
    if previous_version is not None:
        arguments += ["-f", f"previous_tag_name={previous_version}"]
    return json.loads(run_gh(*arguments))["body"].strip()


def build_editor_asset_list(version: str, assets: dict[str, str]) -> str:
    """エディターのアセットを検証してリンク一覧を生成する。"""
    sections = {
        "Windows": [
            (f"VOICEVOX.Web.Setup.{version}.exe", "インストーラー版"),
            (
                f"VOICEVOX-CPU.Web.Setup.{version}.exe",
                "エンジン同梱インストーラー版（CPU）",
            ),
            (
                f"VOICEVOX-DirectML.Web.Setup.{version}.exe",
                "エンジン同梱インストーラー版（GPU/DirectML版）",
            ),
            (
                f"VOICEVOX-CUDA.Web.Setup.{version}.exe",
                "エンジン同梱インストーラー版（GPU/CUDA版）",
            ),
            # 非同梱zipは起動時にエンジンをダウンロードするため、同梱版を案内する。
            # https://github.com/VOICEVOX/voicevox/pull/3095#discussion_r4171853199
            (f"voicevox-windows-cpu-{version}.zip", "zip版（CPU）"),
            (f"voicevox-windows-directml-{version}.zip", "zip版（GPU/DirectML版）"),
            (f"voicevox-windows-nvidia-{version}.zip", "zip版（GPU/CUDA版）"),
        ],
        "Mac": [
            (f"VOICEVOX.{version}-x64.dmg", "インストーラー版 (x64版)"),
            (f"VOICEVOX.{version}-arm64.dmg", "インストーラー版 (arm64版)"),
            (
                f"VOICEVOX-CPU.{version}-x64.dmg",
                "エンジン同梱インストーラー版 (CPU/x64版)",
            ),
            (
                f"VOICEVOX-CPU.{version}-arm64.dmg",
                "エンジン同梱インストーラー版 (CPU/arm64版)",
            ),
            (f"voicevox-macos-cpu-x64-{version}.zip", "zip版 (CPU/x64版)"),
            (f"voicevox-macos-cpu-arm64-{version}.zip", "zip版 (CPU/arm64版)"),
        ],
        "Linux": [
            (f"VOICEVOX.linux-appimage.{version}.sh", "インストーラー版（x64）"),
            (
                f"VOICEVOX.linux-arm64-appimage.{version}.sh",
                "インストーラー版（arm64）",
            ),
            (
                f"VOICEVOX.linux-cpu-x64-appimage.{version}.sh",
                "エンジン同梱インストーラー版（CPU/x64）",
            ),
            (
                f"VOICEVOX.linux-cpu-arm64-appimage.{version}.sh",
                "エンジン同梱インストーラー版（CPU/arm64）",
            ),
            (
                f"VOICEVOX.linux-nvidia-appimage.{version}.sh",
                "エンジン同梱インストーラー版（GPU/CUDA版）",
            ),
            (f"voicevox-linux-cpu-x64-{version}.tar.gz", "tar.gz版（CPU/x64）"),
            (f"voicevox-linux-cpu-arm64-{version}.tar.gz", "tar.gz版（CPU/arm64）"),
            (f"voicevox-linux-nvidia-{version}.tar.gz", "tar.gz版（GPU/CUDA版）"),
        ],
    }

    optional_names = {
        f"voicevox-windows-nvidia-{version}.zip",
        f"voicevox-linux-nvidia-{version}.tar.gz",
    }
    required_names = {
        *(name for items in sections.values() for name, _label in items),
        f"voicevox-{version}-x64.nsis.7z",
        f"voicevox-windows-{version}.zip",
        f"voicevox-macos-x64-{version}.zip",
        f"voicevox-macos-arm64-{version}.zip",
        f"voicevox-linux-{version}.tar.gz",
        f"voicevox-linux-arm64-{version}.tar.gz",
    } - optional_names

    for variant, minimum_count in (("directml", 2), ("cpu", 2), ("cuda", 3)):
        prefix = f"voicevox-{variant}-{version}-x64.nsis.7z"
        required_names.add(f"{prefix}.ini")
        required_names.update(
            collect_asset_parts(
                assets, f"{prefix}.{{}}", first_number=0, minimum_count=minimum_count
            )
        )

    for platform, prefix in (
        ("linux", "VOICEVOX"),
        ("linux-arm64", "VOICEVOX-ARM64"),
        ("linux-cpu-arm64", "VOICEVOX-CPU-ARM64"),
        ("linux-cpu-x64", "VOICEVOX-CPU-X64"),
        ("linux-nvidia", "VOICEVOX-CUDA"),
    ):
        required_names.add(f"{platform}-appimage.7z.txt")
        required_names.update(
            collect_asset_parts(
                assets,
                f"{prefix}.AppImage.7z.{{:03d}}",
                first_number=1,
                minimum_count=1,
            )
        )

    validate_assets(set(assets) - optional_names, required_names)

    lines: list[str] = []
    for title, items in sections.items():
        lines.append(f"* **{title}**")
        for name, label in items:
            if name in assets:
                link = f"[{label}]({assets[name]})"
            else:
                url = f"https://github.com/VOICEVOX/voicevox/releases/download/{version}/{name}"
                link = f"<s>[{label}]({url})</s>"
            lines.append(f"  * {link}")

    return "\n".join(lines)


def build_engine_asset_list(version: str, assets: dict[str, str]) -> str:
    """エンジンのアセットを検証してリンク一覧を生成する。"""
    packages = (
        ("windows-cpu", "Windows（CPU版）"),
        ("windows-directml", "Windows（GPU/DirectML版）"),
        ("windows-nvidia", "Windows（GPU/CUDA版）"),
        ("macos-x64", "macOS（CPU/x64版）"),
        ("macos-arm64", "macOS（CPU/arm64版）"),
        ("linux-cpu-x64", "Linux（CPU/x64版）"),
        ("linux-cpu-arm64", "Linux（CPU/arm64版）"),
        ("linux-nvidia", "Linux（GPU/CUDA版）"),
    )

    required_names: set[str] = set()
    lines: list[str] = []
    for kind, title in (("7z", "エンジン本体"), ("vvpp", "プラグインエンジン（VVPP）")):
        lines.append(f"- {title}")
        for platform, label in packages:
            prefix = f"voicevox_engine-{platform}-{version}"
            is_cuda = platform in {"windows-nvidia", "linux-nvidia"}

            if kind == "7z":
                names = collect_asset_parts(
                    assets,
                    f"{prefix}.7z.{{:03d}}",
                    first_number=1,
                    minimum_count=2 if is_cuda else 1,
                )
            elif is_cuda:
                names = collect_asset_parts(
                    assets, f"{prefix}.{{:03d}}.vvppp", first_number=1, minimum_count=2
                )
            else:
                names = [f"{prefix}.vvpp"]

            required_names.update(names)
            required_names.add(f"{prefix}.{kind}.txt")
            lines.append(f"  - {format_package_link(assets, label, names)}")

    validate_assets(set(assets), required_names)

    return "\n".join(lines)


def format_package_link(assets: dict[str, str], label: str, names: list[str]) -> str:
    """単一または分割アセットのMarkdownリンクを生成する。"""
    if len(names) == 1:
        return f"[{label}]({assets[names[0]]})"

    links = [
        f"[part{index}]({assets[name]})" for index, name in enumerate(names, start=1)
    ]
    return f"{label} {' '.join(links)}"


def collect_asset_parts(
    assets: dict[str, str], template: str, *, first_number: int, minimum_count: int
) -> list[str]:
    """分割アセットを連番が途切れるまで集め、個数を検証する。"""
    names: list[str] = []
    while (name := template.format(first_number + len(names))) in assets:
        names.append(name)

    if len(names) < minimum_count:
        raise ValueError(f"分割アセット数が不足しています: {template}")

    return names


def validate_assets(names: set[str], expected_names: set[str]) -> None:
    """リリースアセットに過不足がないか確認する。"""
    if names != expected_names:
        raise ValueError(
            f"リリースアセットに過不足があります。不足: {sorted(expected_names - names)} 想定外: {sorted(names - expected_names)}"
        )


def generate_core_release_note(version: str, ref: str, assets: dict[str, str]) -> str:
    """VOICEVOX COREの主要変更点とアセットからリリースノートを生成する。"""
    lines = get_core_key_changes(version, ref).splitlines()
    references = [line for line in lines if re.match(r"\[[^\]]+\]: ", line) is not None]
    body = "\n".join(line for line in lines if line not in references)

    head, _, thanks_text = body.partition("\n## 謝辞\n")
    title, _, change_text = head.partition("\n## 変更点\n")
    if title.strip() != f"# {version}":
        raise ValueError(f"VOICEVOX COREの主要変更点の見出しが不正です: {title}")

    thanks_text = re.sub(r"\[(@[^\]]+|#[0-9]+)\]", r"\1", thanks_text.strip())
    thanks_text = re.sub(r"(#[0-9]+)の", r"\1 の", thanks_text)

    return join_markdown(
        "これは VOICEVOX の音声合成コアです。詳細は [ユーザーガイド](https://github.com/VOICEVOX/voicevox_core/blob/main/docs/guide/user/usage.md) をご覧ください。",
        "> [!NOTE]\n> 音声モデル（VVM ファイル）には利用規約が存在します。詳細は [ユーザーガイド](https://github.com/VOICEVOX/voicevox_core/blob/main/docs/guide/user/usage.md) をご覧ください。",
        "## 変更点",
        f"<details><summary>{version}の主要な変更点</summary>\n\n{change_text.strip()}\n</details>",
        "## アセット一覧",
        build_core_asset_list(version, assets),
        "" if thanks_text == "" else f"## 謝辞\n\n{thanks_text}",
        "\n".join(line for line in references if not line.startswith(("[@", "[#"))),
    )


def build_core_asset_list(version: str, assets: dict[str, str]) -> str:
    """VOICEVOX COREのアセットを検証して一覧を生成する。"""
    downloaders = [
        ("Windows", "x64", "download-windows-x64.exe"),
        ("macOS", "x64", "download-osx-x64"),
        ("macOS", "arm64", "download-osx-arm64"),
        ("Linux", "x64", "download-linux-x64"),
        ("Linux", "arm64", "download-linux-arm64"),
    ]

    c_api = [
        ("Windows", "x64", f"voicevox_core-windows-x64-{version}.zip"),
        ("Windows", "x86", f"voicevox_core-windows-x86-{version}.zip"),
        ("macOS", "x64", f"voicevox_core-osx-x64-{version}.zip"),
        ("macOS", "arm64", f"voicevox_core-osx-arm64-{version}.zip"),
        ("Linux", "x64", f"voicevox_core-linux-x64-{version}.zip"),
        ("Linux", "arm64", f"voicevox_core-linux-arm64-{version}.zip"),
        ("Android", "arm64", f"voicevox_core-android-arm64-{version}.zip"),
        ("Android", "x86_64", f"voicevox_core-android-x86_64-{version}.zip"),
        ("iOS", "-", f"voicevox_core-ios-xcframework-cpu-{version}.zip"),
    ]

    python_wheels = [
        ("Windows", "x86_64", f"voicevox_core-{version}-cp310-abi3-win_amd64.whl"),
        ("Windows", "x86", f"voicevox_core-{version}-cp310-abi3-win32.whl"),
        (
            "macOS",
            "x86_64",
            f"voicevox_core-{version}-cp310-abi3-macosx_10_12_x86_64.whl",
        ),
        ("macOS", "arm64", f"voicevox_core-{version}-cp310-abi3-macosx_11_0_arm64.whl"),
        (
            "Linux",
            "x86_64",
            f"voicevox_core-{version}-cp310-abi3-manylinux_2_34_x86_64.whl",
        ),
        (
            "Linux",
            "aarch64",
            f"voicevox_core-{version}-cp310-abi3-manylinux_2_34_aarch64.whl",
        ),
    ]

    validate_assets(
        set(assets),
        {
            "java_packages.zip",
            *(
                name
                for rows in (downloaders, c_api, python_wheels)
                for _os, _arch, name in rows
            ),
        },
    )

    downloader_links = [
        (os_name, architecture, f"[{name}]({assets[name]})")
        for os_name, architecture, name in downloaders
    ]

    return join_markdown(
        format_core_asset_table("ダウンローダ", downloader_links),
        format_core_asset_table("C API", c_api),
        format_core_asset_table("Python wheel", python_wheels),
    )


def format_core_asset_table(title: str, rows: list[tuple[str, str, str]]) -> str:
    """VOICEVOX COREのアセットをMarkdown表に整形する。"""
    return "\n".join(
        [
            f"<details><summary>{title}</summary>",
            "",
            "| OS | ｱｰｷﾃｸﾁｬ | 名前 |",
            "| --- | --- | --- |",
            *(f"| {' | '.join(row)} |" for row in rows),
            "</details>",
        ]
    )


def get_core_key_changes(version: str, ref: str) -> str:
    """VOICEVOX COREの主要変更点のMarkdownをGitHubから取得する。"""
    return run_gh(
        "api",
        "-X",
        "GET",
        "-H",
        "Accept: application/vnd.github.raw+json",
        f"repos/VOICEVOX/voicevox_core/contents/docs/guide/user/key-changes/{version}.md",
        "-f",
        f"ref={ref}",
    )


def join_markdown(*blocks: str) -> str:
    """空でないMarkdown断片を空行で区切って結合する。"""
    return "\n\n".join(block for block in blocks if block != "")


if __name__ == "__main__":
    main()
