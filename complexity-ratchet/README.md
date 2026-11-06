# complexity-ratchet

Fails when a function is above a cyclomatic (CCN) or cognitive complexity limit, measured by [lizard](https://github.com/terryyin/lizard).

- Without `base`, every function in the files matched by `pathspec` is checked.
- With `base`, a function fails only when it is new or got worse, and ends above a limit. Use this to gate a pull request that brings in code you did not write. Moves and renames count as new.
- A reviewed exception is a `// #lizard forgive` comment inside the function.

The checkout needs `fetch-depth: 0` when you set `base`.

| Input | Default | Meaning |
|---|---|---|
| `ccn-max` | `10` | Cyclomatic limit |
| `cognitive-max` | `15` | Cognitive limit |
| `pathspec` | `*.java` | git pathspecs, one per line |
| `base` | empty | Base ref, such as `origin/main` |
| `lizard-version` | `1.24.1` | Installed with pip |

Output: `findings`, the number of functions above a limit.

```yaml
- uses: Gorpokki/minecraft-mod-actions/complexity-ratchet@<40-char-sha> # vX.Y.Z
  with:
    base: origin/${{ github.base_ref }}
```

Lizard 1.24.1 misreads some Java record declarations and then skips a file's functions. Back the gate with a second complexity check in your linter.
