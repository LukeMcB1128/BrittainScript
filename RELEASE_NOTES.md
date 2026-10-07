# 0.6.2

Scripts now print only through explicit output functions such as `push()`.
Bare calls and expressions still run, but their returned values are quiet.
The REPL continues to print the result of a single expression. Function bodies
and blocks remain quiet. Use `push(value)` where a script relied on automatic output.

Assignment syntax in call arguments now raises `TypeError` before any argument
or receiver runs. Keyword arguments are not supported. Use positional arguments.

Caught Python errors retain their original attributes, such as `code`, `errno`,
and `filename`. BS error fields take precedence. The original error remains
available through `cause`, and `args` keeps its original Python value.

GUI callback errors now report the error and leave the event loop running.
Use `gui.onError("handler")` for custom reporting. Use `gui.stopOnError(true)`
to stop on an unhandled callback error and raise it from `gui.run()` as before.

`if` is now an alias for `cond`, including nested blocks and REPL input.
Explicit interpolated strings use `f"..."` with `${expression}`. Ordinary strings
keep their previous behavior. Use `\${...}` for literal text inside an interpolated string.

New app libraries and controls:

- `add http`: HTTP methods with response status, headers, text, bytes, and JSON.
- `server.serve_background()`: a server in the same process as the GUI, with startup errors, stop, and wait.
- `gui.list()`: native list selection with an index callback.
- `add store`: persistent JSON dictionaries with locked updates and transactions.

The Note Vault example combines these features in one script.
