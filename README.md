# minecraft-mod-actions

Reusable GitHub Actions and workflows for Minecraft mod CI: Java quality checks, headless server boot, coverage and complexity gates.

Licensed under the MIT License (see `LICENSE`). The tools these actions download have their own licenses, listed [below](#third-party-tools-and-licenses). **Qlty CLI is Business Source License 1.1, not open source until 2028-12-10.**

## What is in here

| Piece | Type | What it does |
|---|---|---|
| [`.github/workflows/quality.yml`](.github/workflows/quality.yml) | Reusable workflow | Qlty lint and smells (with PMD rules), complexity ratchet, poutine, zizmor, tests with coverage, PIT mutation score, Vale prose |
| [`server-boot`](server-boot) | Composite action | Boots a headless server from a built jar, waits for the ready line, stops it, checks the log, and always kills leftover processes |
| [`complexity-ratchet`](complexity-ratchet) | Composite action | Fails functions above a CCN or cognitive limit, for the whole repository or only for new or worsened functions |
| [`sarif-changed-lines`](sarif-changed-lines) | Composite action | Gates a SARIF report on the lines a pull request changed |
| [`diff-coverage`](diff-coverage) | Composite action | Fails when changed lines are covered below a floor |

The quality workflow is meant for pull requests. Every check compares against the pull request's base branch, so call it from a workflow whose only trigger is `pull_request`. Do not run quality checks on push to your default branch.

## Use the quality workflow

```yaml
name: Quality
on:
  pull_request:
    branches: [main]
permissions:
  contents: read
jobs:
  quality:
    uses: Gorpokki/minecraft-mod-actions/.github/workflows/quality.yml@<40-char-sha> # vX.Y.Z
    with:
      actions-ref: <the same 40-char-sha>
      java-version: '21'
      gradle-test-tasks: build jacocoTestReport
      src-roots: src/main/java
      coverage-min: '80'
      mutation-min: '60'
```

`actions-ref` must be the same commit as the pin on `uses:`. The workflow checks out its composite actions at that commit.

Your repository supplies the configs the jobs read: `.qlty/qlty.toml` and `.qlty/configs/` (including the PMD rule set), `.vale.ini`, and the Gradle tasks you name in the inputs. See the comments at the top of `quality.yml` for every input.

Set `changed-lines-only: true` to gate only changed lines, for example on a pull request that merges upstream code.

### Pin by full commit SHA

Pin every `uses:` to a full 40-character commit SHA with the release in a comment. A tag can be moved or deleted. A SHA cannot. This applies to this repository's actions and to reusable workflow calls too. Let Dependabot bump the pins.

[GitHub's hardening guide](https://docs.github.com/en/actions/reference/security/secure-use) gives the reasoning. Keep `permissions: contents: read` on the caller, as above. A called workflow can lower the token's scope but never raise it.

The action repository's own `uses:` lines follow the same rule.

## Third-party tools and licenses

These actions download and run the tools below. The table is a convenience, not legal advice. Check each project's own license.

| Tool | Used by | License |
|---|---|---|
| **Qlty CLI** | `quality.yml` | **Business Source License 1.1. Not open source.** It changes to GPL-3.0 on 2028-12-10. The Additional Use Grant allows any use except offering a commercial "Code Quality Service" or an "Artificial Intelligence Coding Service". Running it in your own CI is allowed by that grant. Read the license before you use it for anything else. |
| PMD (Qlty plugin) | `quality.yml` | BSD-style, with Apache-2.0 parts |
| lizard | `complexity-ratchet` | MIT-style permission text, with documented exceptions |
| zizmor, `zizmorcore/zizmor-action` | `quality.yml`, `ci.yml` | MIT |
| poutine | `quality.yml` | Apache-2.0 |
| diff-cover | `diff-coverage` | Apache-2.0 |
| PIT (pitest) | your Gradle build | Apache-2.0 |
| JaCoCo | your Gradle build | Eclipse Public License 2.0 |
| Vale, `vale-cli/vale-action` | `quality.yml` | MIT |
| actionlint | `ci.yml` | MIT |
| `actions/checkout`, `actions/setup-java` | `quality.yml` | MIT |
| `gradle/actions/setup-gradle` | `quality.yml` | MIT, with a proprietary vendored caching component. See its `LICENSE` |
| NeoForge (if your `start-command` installs it) | `server-boot` | LGPL-2.1 |

Qlty also runs its own plugins (checkstyle, shellcheck, yamllint, trufflehog, and others). They are chosen in your `.qlty/qlty.toml` and carry their own licenses, some of them copyleft.

## Releases

Releases use semver tags (`vX.Y.Z`) and a moving major tag (`vX`). A renamed or removed input is a new major version. These actions live in subfolders and are not listed on the GitHub Marketplace.
