const vscode = require('vscode');
const cp = require('child_process');

/**
 * Install mcpydoc package if it is missing. Resolves to void when done.
 */
async function ensureMcpInstall() {
  try {
    cp.execSync('python -m mcpydoc --version', { stdio: 'ignore' });
  } catch (err) {
    await new Promise((resolve, reject) => {
      const child = cp.spawn('python', ['-m', 'pip', 'install', '--upgrade', 'mcpydoc'], {
        stdio: 'inherit'
      });
      child.on('exit', code => {
        if (code === 0) {
          resolve();
        } else {
          reject(new Error('Failed to install mcpydoc')); 
        }
      });
      child.on('error', reject);
    });
  }
}

function activate(context) {
  const provider = {
    async provideMcpServerDefinitions(token) {
      return [
        new vscode.McpStdioServerDefinition(
          'MCPyDoc',
          'python',
          ['-m', 'mcpydoc']
        )
      ];
    },
    async resolveMcpServerDefinition(server, token) {
      await ensureMcpInstall();
      return server;
    }
  };

  const disposable = vscode.lm.registerMcpServerDefinitionProvider('mcpydoc.mcp-servers', provider);
  context.subscriptions.push(disposable);
}

function deactivate() {}

module.exports = { activate, deactivate };