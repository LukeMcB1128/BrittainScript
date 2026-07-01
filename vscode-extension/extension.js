const vscode = require('vscode');

function activate(context) {
    const run = vscode.commands.registerCommand('brittainscript.run', () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) return;

        const file = editor.document.fileName;
        const terminal = vscode.window.createTerminal('BrittainScript');
        terminal.show();
        terminal.sendText(`bs "${file}"`);
    });

    context.subscriptions.push(run);
}

function deactivate() {}

module.exports = { activate, deactivate };
