const vscode = require('vscode');

const STRING_METHODS = [
    { label: 'upper()',     detail: '→ string', doc: 'Converts the string to uppercase.\n\n**Example:** `name.upper()` → `"LUKE"`' },
    { label: 'lower()',     detail: '→ string', doc: 'Converts the string to lowercase.\n\n**Example:** `name.lower()` → `"luke"`' },
    { label: 'trim()',      detail: '→ string', doc: 'Removes leading and trailing whitespace.\n\n**Example:** `"  hello  ".trim()` → `"hello"`' },
    { label: 'contains()',  detail: '(substr) → bool', doc: 'Returns `true` if the string contains the given substring.\n\n**Example:** `name.contains("uke")` → `true`' },
    { label: 'locate()',    detail: '(substr) → number', doc: 'Returns the index of the first occurrence of the substring, or `-1` if not found.\n\n**Example:** `name.locate("ke")` → `2`' },
];

const LIST_METHODS = [
    { label: 'add()',     detail: '(item)',        doc: 'Appends an item to the end of the list.\n\n**Example:** `nums.add(5)`' },
    { label: 'remove()', detail: '(item)',        doc: 'Removes the first occurrence of the item from the list.\n\n**Example:** `nums.remove(3)`' },
    { label: 'pop()',    detail: '→ item',        doc: 'Removes and returns the last item in the list.\n\n**Example:** `last = nums.pop()`' },
    { label: 'has()',    detail: '(item) → bool', doc: 'Returns `true` if the item exists in the list.\n\n**Example:** `nums.has(4)` → `true`' },
];

const MATH_MODULE = [
    { label: 'max()',       detail: '(a, b) → number',          doc: 'Returns the larger of two values.\n\n**Example:** `math.max(3, 7)` → `7`' },
    { label: 'min()',       detail: '(a, b) → number',          doc: 'Returns the smaller of two values.\n\n**Example:** `math.min(3, 7)` → `3`' },
    { label: 'abs()',       detail: '(x) → number',             doc: 'Returns the absolute value of x.\n\n**Example:** `math.abs(-5)` → `5`' },
    { label: 'clamp()',     detail: '(x, low, high) → number',  doc: 'Clamps x so it stays between low and high.\n\n**Example:** `math.clamp(15, 0, 10)` → `10`' },
    { label: 'factorial()', detail: '(n) → number',             doc: 'Returns n! (factorial).\n\n**Example:** `math.factorial(5)` → `120`' },
    { label: 'pow()',       detail: '(base, exp) → number',     doc: 'Raises base to the power of exp.\n\n**Example:** `math.pow(2, 8)` → `256`' },
];

function getImportedModules(document) {
    const modules = {};
    for (let i = 0; i < document.lineCount; i++) {
        const match = document.lineAt(i).text.match(/^\s*add\s+(\w+)/);
        if (match) {
            const name = match[1];
            modules[name] = name === 'math' ? MATH_MODULE : [];
        }
    }
    return modules;
}

function inferType(document, varName) {
    // Scan backwards through the file for the most recent assignment of varName
    for (let i = document.lineCount - 1; i >= 0; i--) {
        const text = document.lineAt(i).text;
        const match = text.match(new RegExp(`^\\s*${varName}\\s*=\\s*(.+)`));
        if (match) {
            const rhs = match[1].trim();
            if (rhs.startsWith('"')) return 'string';
            if (rhs.startsWith('[')) return 'list';
            if (rhs.startsWith('input(')) return 'string';
            if (rhs.startsWith('tostr(')) return 'string';
        }
    }
    return null;
}

function activate(context) {
    const run = vscode.commands.registerCommand('brittainscript.run', () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) return;

        const file = editor.document.fileName;
        const terminal = vscode.window.createTerminal('BrittainScript');
        terminal.show();
        terminal.sendText(`bs "${file}"`);
    });

    const completions = vscode.languages.registerCompletionItemProvider(
        { language: 'brittainscript' },
        {
            provideCompletionItems(document, position) {
                const linePrefix = document.lineAt(position).text.slice(0, position.character);
                const dotMatch = linePrefix.match(/(\w+)\.(\w*)$/);
                if (!dotMatch) return;

                const varName = dotMatch[1];
                const modules = getImportedModules(document);
                let methods;

                if (modules[varName] !== undefined) {
                    methods = modules[varName];
                } else {
                    const type = inferType(document, varName);
                    if (type === 'string') methods = STRING_METHODS;
                    else if (type === 'list') methods = LIST_METHODS;
                    else methods = [...STRING_METHODS, ...LIST_METHODS];
                }

                return methods.map(m => {
                    const item = new vscode.CompletionItem(m.label, vscode.CompletionItemKind.Method);
                    item.detail = m.detail;
                    item.documentation = new vscode.MarkdownString(m.doc);
                    const fnName = m.label.replace('()', '');
                    item.insertText = new vscode.SnippetString(`${fnName}($1)`);
                    return item;
                });
            }
        },
        '.'
    );

    context.subscriptions.push(run, completions);
}

function deactivate() {}

module.exports = { activate, deactivate };
