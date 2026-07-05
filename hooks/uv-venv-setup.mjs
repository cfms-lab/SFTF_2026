#!/usr/bin/env node
/**
 * Claude Code SessionStart hook.
 * Python 프로젝트에서 세션을 시작하면 uv로 Python 3.12를 준비하고 .venv를 생성합니다.
 *
 * 동작:
 *  1) 현재 폴더가 Python 프로젝트(pyproject.toml/requirements.txt/*.py 등)인지 확인. 아니면 건너뜀.
 *  2) uv가 없으면 pip로 설치 시도(폴백). 그래도 없으면 안내 후 종료.
 *  3) `uv python install 3.12` (이미 있으면 무시됨).
 *  4) .venv 가 없으면 `uv venv --python 3.12` 로 생성. 이미 있으면 건너뜀.
 *
 * 세션 시작을 막지 않도록 항상 exit 0. 로그는 stderr.
 */
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { execFileSync } from "node:child_process";

const PY_VERSION = "3.12";
const PY_MARKERS = [
  "pyproject.toml",
  "requirements.txt",
  "setup.py",
  "setup.cfg",
  ".python-version",
  "Pipfile",
];

function log(m) {
  console.error(`[uv-venv-setup] ${m}`);
}

function run(cmd, args, opts = {}) {
  return execFileSync(cmd, args, {
    stdio: ["ignore", "pipe", "pipe"],
    windowsHide: true,
    encoding: "utf8",
    ...opts,
  });
}

function has(cmd, args) {
  try {
    run(cmd, args);
    return true;
  } catch {
    return false;
  }
}

function isPythonProject(dir) {
  if (PY_MARKERS.some((m) => existsSync(join(dir, m)))) return true;
  try {
    return readdirSync(dir).some((f) => f.endsWith(".py"));
  } catch {
    return false;
  }
}

function ensureUv() {
  if (has("uv", ["--version"])) return true;
  log("uv가 없어 설치를 시도합니다 (pip install --user uv)…");
  try {
    run("python", ["-m", "pip", "install", "--user", "uv"]);
  } catch {
    try {
      run("py", ["-m", "pip", "install", "--user", "uv"]);
    } catch (e) {
      log(`uv 설치 실패: ${e.message}. https://docs.astral.sh/uv/ 참고`);
      return false;
    }
  }
  return has("uv", ["--version"]);
}

function main() {
  let event = {};
  try {
    event = JSON.parse(readFileSync(0, "utf8"));
  } catch {
    /* stdin 없어도 진행 */
  }

  if (event.source && event.source !== "startup") process.exit(0);

  const cwd = event.cwd || process.cwd();
  if (!isPythonProject(cwd)) {
    log(`Python 프로젝트가 아니므로 건너뜀: ${cwd}`);
    process.exit(0);
  }

  if (!ensureUv()) {
    log("uv를 사용할 수 없어 종료합니다.");
    process.exit(0);
  }

  // Python 3.12 준비
  try {
    run("uv", ["python", "install", PY_VERSION]);
    log(`uv python ${PY_VERSION} 준비 완료`);
  } catch (e) {
    log(`Python ${PY_VERSION} 설치 실패: ${e.message}`);
  }

  // .venv 생성
  if (existsSync(join(cwd, ".venv"))) {
    log(".venv 이미 존재 — 건너뜀");
    process.exit(0);
  }
  try {
    run("uv", ["venv", "--python", PY_VERSION], { cwd });
    log(`.venv 생성 완료 (Python ${PY_VERSION}) @ ${cwd}`);
  } catch (e) {
    log(`.venv 생성 실패: ${e.message}`);
  }
  process.exit(0);
}

main();
