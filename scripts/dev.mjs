import { spawn } from 'node:child_process';
const children = [];
function run(command, args) {
  const child = spawn(command, args, { stdio: 'inherit', shell: process.platform === 'win32' });
  children.push(child);
  child.on('exit', code => { if (code && code !== 0) { console.error('Processo encerrado:', command, code); stop(); } });
}
function stop() { for (const child of children) if (!child.killed) child.kill(); }
process.on('SIGINT', () => { stop(); process.exit(0); });
process.on('SIGTERM', () => { stop(); process.exit(0); });
run(process.execPath, ['server/index.mjs']);
run('npm', ['exec', 'vite', '--', '--host', '127.0.0.1']);
