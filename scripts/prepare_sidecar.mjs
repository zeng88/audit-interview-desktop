import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const scriptPath = join(__dirname, "prepare_sidecar.py");

function canRun(command) {
  const result = spawnSync(command, ["--version"], { stdio: "ignore" });
  return !result.error && result.status === 0;
}

// macOS/Linux 通常是 python3，Windows setup-python 通常是 python。
const pythonCommand = canRun("python3") ? "python3" : canRun("python") ? "python" : null;

if (!pythonCommand) {
  console.error("未找到 Python，请先安装 Python 3.12 或确认 GitHub Actions 已执行 setup-python。");
  process.exit(1);
}

const result = spawnSync(pythonCommand, [scriptPath], {
  stdio: "inherit",
  env: process.env,
});

if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}

process.exit(result.status ?? 1);
