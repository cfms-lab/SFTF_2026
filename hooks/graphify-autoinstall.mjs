#!/usr/bin/env node
/**
 * Claude Code SessionStart hook.
 * 새 리포지토리를 받거나 새 프로젝트에서 Claude Code를 시작할 때 graphify를 자동 설치합니다.
 *
 * 동작:
 *  1) graphify CLI가 없으면 전역으로 한 번만 설치(pip install graphifyy && graphify install).
 *  2) 현재 폴더가 코드 프로젝트(.git/package.json/pyproject.toml 등)이고
 *     아직 graphify가 연동되지 않았으면 `graphify claude install` 실행
 *     → 그 프로젝트에 CLAUDE.md 지시문 + PreToolUse 훅을 세팅.
 *
 * 세션 시작을 막지 않도록 항상 exit 0. 로그는 stderr.
 */
import { existsSync, readFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";
import { execFileSync } from "node:child_process";

const GLOBAL_MARKER = join(homedir(), ".claude", ".graphify-global-installed");
const PROJECT_MARKERS = [
  ".git",
  "package.json",
  "pyproject.toml",
  "go.mod",
  "Cargo.toml",
  "pom.xml",
  "build.gradle",
  "requirements.txt",
];

function log(msg) {
  console.error(`[graphify-autoinstall] ${msg}`);
}

function run(cmd, args, opts = {}) {
  return execFileSync(cmd, args, {
    stdio: ["ignore", "pipe", "pipe"],
    windowsHide: true,
    encoding: "utf8",
    ...opts,
  });
}

function hasGraphify() {
  try {
    run("graphify", ["--version"]);
    return true;
  } catch {
    return false;
  }
}

function ensureGlobalInstall() {
  if (hasGraphify() || existsSync(GLOBAL_MARKER)) return hasGraphify();
  log("graphify CLI가 없어 전역 설치를 시도합니다…");
  try {
    run("python", ["-m", "pip", "install", "--user", "graphifyy"]);
  } catch {
    try {
      run("py", ["-m", "pip", "install", "--user", "graphifyy"]); // Windows launcher 대체
    } catch (e) {
      log(`pip 설치 실패: ${e.message}. Python/pip 설치 여부를 확인하세요.`);
      return false;
    }
  }
  try {
    run("graphify", ["install"]);
  } catch (e) {
    log(`graphify install 실패: ${e.message}`);
  }
  try {
    mkdirSync(join(homedir(), ".claude"), { recursive: true });
    writeFileSync(GLOBAL_MARKER, new Date().toISOString());
  } catch {}
  return hasGraphify();
}

function isProject(dir) {
  return PROJECT_MARKERS.some((m) => existsSync(join(dir, m)));
}

function alreadyIntegrated(dir) {
  // graphify claude install 의 산출물(CLAUDE.md / .claude/settings.json)에 graphify 흔적이 있는지 확인
  const checks = [join(dir, "CLAUDE.md"), join(dir, ".claude", "settings.json")];
  for (const f of checks) {
    try {
      if (existsSync(f) && /graphify/i.test(readFileSync(f, "utf8"))) return true;
    } catch {}
  }
  return false;
}

function main() {
  let event = {};
  let raw = "";
  try {
    raw = readFileSync(0, "utf8"); // stdin
    event = JSON.parse(raw);
  } catch {
    /* stdin이 없어도 계속 진행 */
  }

  // 세션을 새로 시작하는 경우에만 동작(resume/clear 제외)
  if (event.source && event.source !== "startup") process.exit(0);

  const cwd = event.cwd || process.cwd();
  if (!isProject(cwd)) {
    log(`프로젝트 폴더가 아니므로 건너뜀: ${cwd}`);
    process.exit(0);
  }

  if (!ensureGlobalInstall()) {
    log("graphify CLI를 사용할 수 없어 종료합니다.");
    process.exit(0);
  }

  if (alreadyIntegrated(cwd)) {
    log("이미 graphify가 연동된 프로젝트입니다. 건너뜀.");
    process.exit(0);
  }

  log(`프로젝트에 graphify 연동: ${cwd}`);
  try {
    run("graphify", ["claude", "install"], { cwd });
    log("완료: CLAUDE.md + PreToolUse 훅이 설치되었습니다. 그래프 생성은 /graphify ./ 로 실행하세요.");
  } catch (e) {
    log(`graphify claude install 실패: ${e.message}`);
  }
  process.exit(0);
}

main();
