const vscode = require('vscode');
const cp = require('child_process');

/**
 * Detect available Python command by trying multiple options.
 * Returns the first working Python command or throws an error.
 */
function findPythonCommand() {
  const commands = ['python', 'python3', 'py'];
  
  for (const cmd of commands) {
    try {
      cp.execSync(`${cmd} --version`, { stdio: 'ignore' });
      return cmd;
    } catch (err) {
      // Command not available, try next
    }
  }
  
  throw new Error('Python not found. Please ensure Python 3.9+ is installed and available as "python", "python3", or "py" in your PATH.');
}

/**
 * Install mcpydoc package if it is missing. Resolves to void when done.
 */
async function ensureMcpInstall(pythonCmd) {
  try {
    cp.execSync(`${pythonCmd} -m mcpydoc --version`, { stdio: 'ignore' });
  } catch (err) {
    await new Promise((resolve, reject) => {
      const child = cp.spawn(pythonCmd, ['-m', 'pip', 'install', '--upgrade', 'mcpydoc'], {
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
      const pythonCmd = findPythonCommand();
      return [
        new vscode.McpStdioServerDefinition(
          'MCPyDoc',
          pythonCmd,
          ['-m', 'mcpydoc']
        )
      ];
    },
    async resolveMcpServerDefinition(server, token) {
      const pythonCmd = findPythonCommand();
      await ensureMcpInstall(pythonCmd);
      return server;
    }
  };

  const disposable = vscode.lm.registerMcpServerDefinitionProvider('mcpydoc.mcp-servers', provider);
  context.subscriptions.push(disposable);
}

function deactivate() {}

module.exports = { activate, deactivate };
