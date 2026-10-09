const vscode = require('vscode');
const fs = require('fs');
const path = require('path');

// Generated from Documentation/LANGUAGE_REFERENCE.md and libs/*.bs by
// tools/build_vscode_docs.py. Rebuild it after changing either.
const DOCS = require('./docs.json');

const KEYWORDS = {
    cond: 'Start a conditional block. `cond score >= 90:` … `elif` … `else:` … `end`',
    if: 'Alias for `cond`. Starts a conditional block closed by `end`.',
    elif: 'Another condition in a `cond` / `if` block, tried when the earlier ones were false.',
    else: 'Runs when no condition in the block was true. Also used after `catch` for code that runs only when `try` succeeded.',
    while: 'Repeat the block while the condition is true. `while n < 3:` … `end`',
    for: 'Loop over a list, string or `space(...)`. `for item in items:` … `end`',
    in: 'Part of `for name in values`, or a membership test: `"a" in items`.',
    break: 'Leave the nearest loop.',
    continue: 'Skip to the next pass of the nearest loop.',
    end: 'Close a `cond`, `if`, `while`, `for`, `func` or `try` block.',
    func: 'Define a function. `func add(a, b):` … `return a + b` … `end`. Arguments are positional.',
    return: 'Leave the function, optionally with a value. Without a value it returns `null`.',
    add: 'Load a library: `add math`, then call `math.max(1, 2)`.',
    try: 'Run a block and handle errors with `catch`, `else` and `finally`.',
    catch: 'Handle an error from `try`. `catch ValueError as problem:` or `catch:` for any error.',
    finally: 'Runs after `try`, whether it succeeded or failed.',
    raise: 'Raise an error: `raise error("message", "TypeName")`. A bare `raise` re-raises the active error.',
    as: 'Names the caught error: `catch ValueError as problem:`.',
    local: 'At the start of a function, keep the listed names local to this call: `local total, item`.',
    discard: 'Run an expression and ignore its result.',
    and: 'True when both sides are true. The right side is skipped when the left is false.',
    or: 'True when either side is true. The right side is skipped when the left is true.',
    not: 'Boolean negation.',
    true: 'Boolean true.',
    false: 'Boolean false.',
    null: 'The empty value. Falsy; prints as `null`.',
    pi: 'The constant 3.141592653589793.',
};

const KIND_LABELS = {
    string: 'strings', list: 'lists', dictionary: 'dictionaries', store: 'store objects', error: 'caught errors',
};

function code(text) {
    return '```brittainscript\n' + text + '\n```';
}

function entryMarkdown(entries, footer) {
    const md = new vscode.MarkdownString();
    for (const entry of entries) {
        md.appendMarkdown(code(entry.signature) + '\n\n' + entry.doc + '\n\n');
    }
    if (footer) md.appendMarkdown(footer);
    return md;
}

// the name each `add` binds, mapped to what was added: "strings" -> "utils.strings"
function importedModules(document) {
    const modules = new Map();
    for (let i = 0; i < document.lineCount; i++) {
        const match = document.lineAt(i).text.match(/^\s*add\s+([A-Za-z_][\w.]*)/);
        if (match) modules.set(match[1].split('.').pop(), match[1]);
    }
    return modules;
}

// func definitions in some lines, with the # comment lines directly above them
function functionsIn(lines) {
    const functions = {};
    for (let i = 0; i < lines.length; i++) {
        const match = lines[i].match(/^\s*func\s+([A-Za-z_]\w*)\s*\(([^)]*)\)/);
        if (!match) continue;
        const comment = [];
        for (let back = i - 1; back >= 0; back--) {
            const line = lines[back].trim();
            if (!line.startsWith('#')) break;
            comment.unshift(line.replace(/^#\s?/, ''));
        }
        const params = match[2].trim();
        functions[match[1]] = { signature: `func ${match[1]}(${params})`, params, doc: comment.join(' '), line: i + 1 };
    }
    return functions;
}

function userFunctions(document) {
    const lines = [];
    for (let i = 0; i < document.lineCount; i++) lines.push(document.lineAt(i).text);
    return functionsIn(lines);
}

// the file `add dotted` loads from beside this document, as the interpreter looks for it
function localModulePath(document, dotted) {
    if (!document.uri || document.uri.scheme !== 'file') return null;
    const file = path.join(path.dirname(document.uri.fsPath), ...dotted.split('.')) + '.bs';
    return fs.existsSync(file) ? file : null;
}

function bundledModule(name) {
    return { functions: DOCS.modules[name], label: `*${name} library*`, summary: `**${name}** library\n\n${DOCS.libraries[name] || ''}` };
}

// what `receiver.` refers to: a local module file wins over a bundled library
function resolveModule(document, receiver) {
    const dotted = importedModules(document).get(receiver);
    if (dotted) {
        const file = localModulePath(document, dotted);
        if (file) {
            let text;
            try { text = fs.readFileSync(file, 'utf8'); } catch (error) { return null; }
            const functions = {};
            for (const [name, fn] of Object.entries(functionsIn(text.split(/\r?\n/)))) {
                functions[name] = [{ signature: `${receiver}.${name}(${fn.params})`, doc: fn.doc || '*No comment above this function.*' }];
            }
            const shown = path.relative(path.dirname(document.uri.fsPath), file);
            return { functions, label: `*${shown}*`, summary: `**${receiver}**: your module \`${shown}\`` };
        }
        return DOCS.modules[dotted] ? bundledModule(dotted) : null;
    }
    return DOCS.modules[receiver] && DOCS.libraries[receiver] ? bundledModule(receiver) : null;
}

function moduleSummary(module) {
    const md = new vscode.MarkdownString(module.summary + '\n\n');
    const names = Object.keys(module.functions || {}).sort();
    if (names.length) md.appendMarkdown(names.map(f => '`' + f + '`').join(' · '));
    return md;
}

function inferType(document, varName, beforeLine) {
    // the most recent assignment above the cursor decides the type
    const pattern = new RegExp(`^\\s*${varName}\\s*=\\s*(.+)`);
    for (let i = beforeLine; i >= 0; i--) {
        const match = document.lineAt(i).text.match(pattern);
        if (!match) continue;
        const rhs = match[1].trim();
        if (/^[fF]?"/.test(rhs) || /^(input|tostr|readfile)\(/.test(rhs)) return 'string';
        if (rhs.startsWith('[') || /^(list|space|range|readlines)\(/.test(rhs)) return 'list';
        if (rhs.startsWith('{') || /^dict\(/.test(rhs)) return 'dictionary';
        if (/^store\.open\(/.test(rhs)) return 'store';
        return null;
    }
    return null;
}

function provideHover(document, position) {
    const range = document.getWordRangeAtPosition(position, /[A-Za-z_]\w*/);
    if (!range) return;
    const word = document.getText(range);
    const line = document.lineAt(position.line).text;
    const before = line.slice(0, range.start.character);
    if (/#/.test(before.replace(/"(?:\\.|[^"\\])*"/g, '""'))) return;  // inside a comment

    const added = line.match(/^\s*add\s+([A-Za-z_][\w.]*)/);
    if (added && range.start.character >= line.indexOf(added[1])) {
        const module = resolveModule(document, added[1].split('.').pop());
        return module ? new vscode.Hover(moduleSummary(module), range) : undefined;
    }

    // receiver.word: a library function or a method
    const dot = before.match(/([A-Za-z_]\w*)\s*\.\s*$/);
    if (dot) {
        const receiver = dot[1];
        const module = resolveModule(document, receiver);
        if (module) {
            if (module.functions[word]) return new vscode.Hover(entryMarkdown(module.functions[word], module.label), range);
            return;
        }
        const methods = DOCS.methods[word];
        if (!methods) return;
        const type = inferType(document, receiver, position.line);
        const matching = type ? methods.filter(m => m.kind === type) : [];
        const shown = matching.length ? matching : methods;
        const md = new vscode.MarkdownString();
        for (const method of shown) {
            md.appendMarkdown(code(method.signature) + '\n\n' + method.doc + `\n\n*On ${KIND_LABELS[method.kind] || method.kind}*\n\n`);
        }
        return new vscode.Hover(md, range);
    }

    if (KEYWORDS[word] && !/^\s*\($/.test(line.slice(range.end.character, range.end.character + 1))) {
        return new vscode.Hover(new vscode.MarkdownString(`**${word}**\n\n${KEYWORDS[word]}`), range);
    }
    // built-ins run even when a func of the same name exists, so they come first
    if (DOCS.builtins[word]) return new vscode.Hover(entryMarkdown(DOCS.builtins[word], '*Built-in*'), range);
    const own = userFunctions(document)[word];
    if (own) {
        return new vscode.Hover(entryMarkdown([{ signature: own.signature, doc: own.doc || '*No comment above this function.*' }], `*Defined on line ${own.line}*`), range);
    }
    if (importedModules(document).has(word)) {
        const module = resolveModule(document, word);
        if (module) return new vscode.Hover(moduleSummary(module), range);
    }
}

function completionItem(label, kind, entry, snippet) {
    const item = new vscode.CompletionItem(label, kind);
    if (entry) {
        item.detail = entry.signature;
        item.documentation = new vscode.MarkdownString(entry.doc);
    }
    if (snippet) item.insertText = new vscode.SnippetString(`${label}($1)`);
    return item;
}

function provideCompletions(document, position) {
    const prefix = document.lineAt(position).text.slice(0, position.character);
    const Kind = vscode.CompletionItemKind;

    const dot = prefix.match(/([A-Za-z_]\w*)\.(\w*)$/);
    if (dot) {
        const receiver = dot[1];
        const module = resolveModule(document, receiver);
        if (module) {
            return Object.entries(module.functions).map(([name, entries]) => completionItem(name, Kind.Function, entries[0], true));
        }
        const type = inferType(document, receiver, position.line);
        const items = [];
        for (const [name, methods] of Object.entries(DOCS.methods)) {
            const fitting = type ? methods.filter(m => m.kind === type) : methods;
            if (fitting.length) items.push(completionItem(name, Kind.Method, fitting[0], true));
        }
        return items;
    }

    if (/^\s*add\s+\w*$/.test(prefix)) {
        const items = Object.keys(DOCS.libraries).map(name => {
            const item = new vscode.CompletionItem(name, Kind.Module);
            item.documentation = new vscode.MarkdownString(DOCS.libraries[name]);
            return item;
        });
        // .bs files beside this one can be added too
        if (document.uri && document.uri.scheme === 'file') {
            const folder = path.dirname(document.uri.fsPath);
            let files = [];
            try { files = fs.readdirSync(folder); } catch (error) { files = []; }
            for (const file of files) {
                if (!file.endsWith('.bs') || path.join(folder, file) === document.uri.fsPath) continue;
                const item = new vscode.CompletionItem(file.slice(0, -3), Kind.File);
                item.detail = 'Your module ' + file;
                items.push(item);
            }
        }
        return items;
    }

    const items = Object.entries(DOCS.builtins)
        .filter(([name]) => !/^(gui|json)[a-z]/.test(name))  // backend names; prefer the libraries
        .map(([name, entries]) => completionItem(name, Kind.Function, entries[0], true));
    for (const [name, own] of Object.entries(userFunctions(document))) {
        items.push(completionItem(name, Kind.Function, own, true));
    }
    for (const word of Object.keys(KEYWORDS)) {
        const item = new vscode.CompletionItem(word, Kind.Keyword);
        item.documentation = new vscode.MarkdownString(KEYWORDS[word]);
        items.push(item);
    }
    for (const name of importedModules(document).keys()) {
        items.push(new vscode.CompletionItem(name, Kind.Module));
    }
    return items;
}

function activate(context) {
    const run = vscode.commands.registerCommand('brittainscript.run', () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) return;
        const terminal = vscode.window.createTerminal('BrittainScript');
        terminal.show();
        terminal.sendText(`bs "${editor.document.fileName}"`);
    });
    const selector = { language: 'brittainscript' };
    context.subscriptions.push(
        run,
        vscode.languages.registerHoverProvider(selector, { provideHover }),
        vscode.languages.registerCompletionItemProvider(selector, { provideCompletionItems: provideCompletions }, '.'),
    );
}

function deactivate() {}

module.exports = { activate, deactivate };
