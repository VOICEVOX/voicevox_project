# リリース作業用ツール

## 貢献者の取得

比較元と比較先のタグやコミットIDを指定し、その間の貢献者のGitHubユーザー名を1行ずつ表示します。
対象リポジトリをcloneしたディレクトリで実行します。

```bash
cd /path/to/voicevox_engine
uv run /path/to/voicevox_project/tools/get_contributors.py 0.25.0 0.26.0
```

## リリースノートの生成

GitHub Releaseの本文を生成します。
対象には`editor`・`engine`・`resource`・`vvm`を指定できます。
`editor`・`engine`・`vvm`では目玉更新内容を`--summary`か`--summary-file`で指定します。
`--output`を省略すると標準出力に表示します。

```bash
uv run tools/generate_release_note.py engine \
  --version 0.26.0 \
  --previous-version 0.25.0 \
  --summary '- Windows・Linuxで性能の高いCPUコアを優先して使うように変更' \
  --summary '- ストリーミングで音声合成するAPIを追加' \
  --summary '- Mac版に署名を追加' \
  --output /tmp/voicevox-engine-0.26.0-release-note.md
```
