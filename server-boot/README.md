# server-boot

Boots a headless Minecraft server from a jar your job already built, waits for the ready line, sends `stop`, and checks the log.

Run it after your build and `actions/setup-java`, in the same job. It needs a Linux runner (`setsid`, FIFO).
Put the server files in `server-dir` first: installer output, `eula.txt`, and your jars in `mods/`.

| Input | Default | Meaning |
|---|---|---|
| `server-dir` | `.` | Where the start command runs |
| `start-command` | `./run.sh nogui` | Must read commands from standard input |
| `timeout-seconds` | `600` | Wait for the ready line |
| `ready-pattern` | `Done (` | Fixed string |
| `fail-patterns` | Mixin failures, crash report | Regex; a match fails the step |
| `expect-pattern` | empty | Regex the log must match |
| `log-file` | `server.log` | Relative to `server-dir` |

Outputs: `result` (`ready`, `timeout`, `exited`) and `log-path`.

An `always()` step kills the server's process group, so a failed or cancelled job leaves nothing running.

```yaml
- uses: Gorpokki/minecraft-mod-actions/server-boot@<40-char-sha> # vX.Y.Z
  with:
    server-dir: server
    expect-pattern: 'Loaded [0-9]* my-mod entries'
```
