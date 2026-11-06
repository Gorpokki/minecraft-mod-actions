# sarif-changed-lines

Gates a SARIF report. Without `base`, any result fails. With `base`, only results that overlap a line the pull request changed fail.

Tools such as `qlty smells --upstream` report every finding in each changed file. This action keeps a pull request from failing on code it did not touch. Uses Python's standard library only.

| Input | Default | Meaning |
|---|---|---|
| `sarif-file` | required | SARIF file to gate |
| `base` | empty | Base ref, such as `origin/main`. Needs `fetch-depth: 0` |
| `skip-overridden-rules` | empty | Rule ids, one per line, ignored on `@Override` declarations |

Output: `findings`, the number of results that fail the gate.

```yaml
- uses: Gorpokki/minecraft-mod-actions/sarif-changed-lines@<40-char-sha> # vX.Y.Z
  with:
    sarif-file: smells.sarif
    base: origin/${{ github.base_ref }}
```
