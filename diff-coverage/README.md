# diff-coverage

Fails when the lines a pull request changes are covered below a floor. It runs [diff-cover](https://github.com/Bachmann1234/diff_cover) on a JaCoCo or Cobertura XML report.

Run your tests with coverage first, in the same job, on a checkout with `fetch-depth: 0`.

| Input | Default | Meaning |
|---|---|---|
| `report` | required | Coverage XML path |
| `compare-branch` | required | Branch to diff against, such as `origin/main` |
| `src-roots` | `src/main/java` | Source roots, space or line separated |
| `fail-under` | `80` | Minimum percent of changed lines covered |
| `diff-cover-version` | `10.6.0` | Run with `pipx` |

Output: `passed` (`true` or `false`).

```yaml
- uses: Gorpokki/minecraft-mod-actions/diff-coverage@<40-char-sha> # vX.Y.Z
  with:
    report: build/reports/jacoco/test/jacocoTestReport.xml
    compare-branch: origin/${{ github.base_ref }}
```
