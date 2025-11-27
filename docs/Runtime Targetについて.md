# Runtime Targetについて

実行環境の識別子をRuntime Targetと呼んでいます。
`(os, arch, device)`の組で構成し、どのバイナリやハードウェア（GPUなど）などを対象にしているかを示しています。

## 基本ルール

- 表記は`os-arch-device`の順でハイフン区切り。
- フィールドの値の例
  - `os`：`windows`、`linux`、`macos`
  - `arch`：`x64`、`x86`、`arm64`
  - `device`：`cpu`、`cuda`、`directml`

### 例

- `windows-x64-cpu`
- `macos-arm64-cpu`
- `linux-x64-cuda`
