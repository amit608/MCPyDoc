const vscode = require('vscode');
const cp = require('child_process');

/**
 * Check if a command is available on the system.
 */
function isCommandAvailable(command) {
  try {
    cp.execSync(`${command} --version`, { stdio: 'ignore' });
    return true;
  } catch (err) {
    return false;
  }
}

/**
 * Detect available Python command by trying multiple options.
 * Returns the first working Python command or null if none found.
 */
function findPythonCommand() {
  const commands = ['python', 'python3', 'py'];
  
  for (const cmd of commands) {
    if (isCommandAvailable(cmd)) {
      return cmd;
    }
  }
  
  return null;
}

/**
 * Detect available package managers.
 * Returns an object with boolean flags for each manager.
 */
function detectPackageManager() {
  return {
    pipx: isCommandAvailable('pipx'),
    uvx: isCommandAvailable('uvx'),
    uv: isCommandAvailable('uv'),
    pip: findPythonCommand() !== null
  };
}

/**
 * Try to run mcpydoc with pipx run (isolated execution).
 * Returns true if successful, false otherwise.
 */
function tryPipxRun() {
  try {
    cp.execSync('pipx run --help', { stdio: 'ignore' });
    // Check if mcpydoc can be run with pipx
    cp.execSync('pipx run mcpydoc --version', { stdio: 'ignore' });
    return true;
  } catch (err) {
    return false;
  }
}

/**
 * Try to run mcpydoc with uvx (isolated execution).
 * Returns true if successful, false otherwise.
 */
function tryUvxRun() {
  try {
    cp.execSync('uvx --version', { stdio: 'ignore' });
    // Check if mcpydoc can be run with uvx
    cp.execSync('uvx mcpydoc --version', { stdio: 'ignore' });
    return true;
  } catch (err) {
    return false;
  }
}

/**
 * Check if mcpydoc is installed in Python environment.
 */
function isPythonMcpydocInstalled(pythonCmd) {
  try {
    cp.execSync(`${pythonCmd} -m mcpydoc --version`, { stdio: 'ignore' });
    return true;
  } catch (err) {
    return false;
  }
}

/**
 * Install mcpydoc using the best available package manager.
 * Priority: pipx > uv > pip
 */
async function installWithBestManager(managers) {
  // Try pipx install first (best isolation)
  if (managers.pipx) {
    try {
      await new Promise((resolve, reject) => {
        const child = cp.spawn('pipx', ['install', 'mcpydoc'], {
          stdio: 'inherit'
        });
        child.on('exit', code => {
          if (code === 0) {
            resolve();
          } else {
            reject(new Error('pipx install failed'));
          }
        });
        child.on('error', reject);
      });
      return { method: 'pipx', command: 'pipx', args: ['run', 'mcpydoc'] };
    } catch (err) {
      // Fall through to next option
    }
  }

  // Try uv install
  if (managers.uv) {
    try {
      await new Promise((resolve, reject) => {
        const child = cp.spawn('uv', ['tool', 'install', 'mcpydoc'], {
          stdio: 'inherit'
        });
        child.on('exit', code => {
          if (code === 0) {
            resolve();
          } else {
            reject(new Error('uv install failed'));
          }
        });
        child.on('error', reject);
      });
      return { method: 'uvx', command: 'uvx', args: ['mcpydoc'] };
    } catch (err) {
      // Fall through to next option
    }
  }

  // Fall back to pip install
  if (managers.pip) {
    const pythonCmd = findPythonCommand();
    await new Promise((resolve, reject) => {
      const child = cp.spawn(pythonCmd, ['-m', 'pip', 'install', '--upgrade', 'mcpydoc'], {
        stdio: 'inherit'
      });
      child.on('exit', code => {
        if (code === 0) {
          resolve();
        } else {
          reject(new Error('pip install failed'));
        }
      });
      child.on('error', reject);
    });
    return { method: 'pip', command: pythonCmd, args: ['-m', 'mcpydoc'] };
  }

  throw new Error('No package manager available to install mcpydoc. Please install Python 3.9+ with pip, or install pipx/uv.');
}

/**
 * Determine the best way to run mcpydoc and ensure it's available.
 * Returns an object with command and args for the server definition.
 */
async function resolveServerCommand() {
  // Strategy 1: Try pipx run (isolated, no install needed if in pipx cache)
  if (isCommandAvailable('pipx')) {
    if (tryPipxRun()) {
      return { command: 'pipx', args: ['run', 'mcpydoc'] };
    }
  }

  // Strategy 2: Try uvx (isolated, no install needed)
  if (isCommandAvailable('uvx')) {
    if (tryUvxRun()) {
      return { command: 'uvx', args: ['mcpydoc'] };
    }
  }

  // Strategy 3: Check if mcpydoc is installed in Python environment
  const pythonCmd = findPythonCommand();
  if (pythonCmd && isPythonMcpydocInstalled(pythonCmd)) {
    return { command: pythonCmd, args: ['-m', 'mcpydoc'] };
  }

  // Strategy 4: Install mcpydoc with best available manager
  const managers = detectPackageManager();
  const result = await installWithBestManager(managers);
  return { command: result.command, args: result.args };
}

function activate(context) {
  const provider = {
    async provideMcpServerDefinitions(token) {
      // Return a basic definition; actual resolution happens in resolveMcpServerDefinition
      const pythonCmd = findPythonCommand() || 'python';
      return [
        new vscode.McpStdioServerDefinition({
          label: 'MCPyDoc',
          command: pythonCmd,
          args: ['-m', 'mcpydoc']
        })
      ];
    },
    
    async resolveMcpServerDefinition(server, token) {
      try {
        // Resolve the best command to run mcpydoc
        const { command, args } = await resolveServerCommand();
        
        // Return updated server definition with the resolved command
        return new vscode.McpStdioServerDefinition({
          label: 'MCPyDoc',
          command: command,
          args: args
        });
      } catch (err) {
        vscode.window.showErrorMessage(`Failed to set up MCPyDoc: ${err.message}`);
        throw err;
      }
    }
  };

  const disposable = vscode.lm.registerMcpServerDefinitionProvider('mcpydoc.mcp-servers', provider);
  context.subscriptions.push(disposable);
}

function deactivate() {}

module.exports = { activate, deactivate };
