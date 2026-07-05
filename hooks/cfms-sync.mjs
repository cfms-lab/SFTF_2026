#!/usr/bin/env node
/**
 * Claude Code SessionStart hook.
 * cfms 공유 git 채널(cfmsShared2026_dev)을 pull 하고, 이 프로젝트의 인박스를 세션 컨텍스트로 표시한다.
 *
 * 대상 판별: 프로젝트 루트에 `.cfms-sync.json` 이 있을 때만 동작한다(없으면 무해하게 종료).
 *   { "role": "cad" | "drape", "sharedPath": "../cfmsShared2026_dev" }
 *
 * 동작: 공유 저장소 git pull --ff-only → contract 버전 + 내 인박스(to_<role>.md) 출력.
 * 쓰기/푸시는 하지 않는다(요청 작성은 CLAUDE.md 규칙에 따라 Claude가 수행).
 * 세션 시작을 막지 않도록 항상 exit 0.
 */
import { existsSync, readFileSync } from "node:fs";
import { join, isAbsolute, resolve } from "node:path";
import { execFileSync } from "node:child_process";

function log(m) {
  console.error(`[cfms-sync] ${m}`);
}
function out(m) {
  process.stdout.write(m + "\n"); // SessionStart stdout → 세션 컨텍스트로 주입
}
function git(args, cwd) {
  return execFileSync("git", args, {
    cwd,
    stdio: ["ignore", "pipe", "pipe"],
    encoding: "utf8",
    windowsHide: true,
  });
}

function main() {
  let ev = {};
  try {
    ev = JSON.parse(readFileSync(0, "utf8"));
  } catch {
    /* stdin 없어도 진행 */
  }
  if (ev.source && ev.source !== "startup") process.exit(0);

  const cwd = ev.cwd || process.cwd();
  const cfgPath = join(cwd, ".cfms-sync.json");
  if (!existsSync(cfgPath)) process.exit(0); // 이 프로젝트는 대상 아님

  let cfg;
  try {
    cfg = JSON.parse(readFileSync(cfgPath, "utf8"));
  } catch (e) {
    log(`.cfms-sync.json 파싱 실패: ${e.message}`);
    process.exit(0);
  }

  const role = cfg.role === "drape" ? "drape" : "cad";
  const other = role === "cad" ? "drape" : "cad";
  let shared = cfg.sharedPath || "../cfmsShared2026_dev";
  shared = isAbsolute(shared) ? shared : resolve(cwd, shared);

  if (!existsSync(shared)) {
    log(`공유 저장소 없음: ${shared} — 먼저 clone 하세요.`);
    process.exit(0);
  }

  // pull (best effort)
  try {
    git(["pull", "--ff-only"], shared);
    log(`pull 완료: ${shared}`);
  } catch (e) {
    log(`git pull 실패(무시): ${String(e.message).split("\n")[0]}`);
  }

  // contract 버전 + 인박스 표시
  const verFile = join(shared, "contract", "VERSION");
  const ver = existsSync(verFile) ? readFileSync(verFile, "utf8").trim() : "(unknown)";
  const inbox = join(shared, "messages", `to_${role}.md`);

  out(`\n===== cfms 공유 채널 (role=${role}) =====`);
  out(`Contract version: ${ver}`);
  if (existsSync(inbox)) {
    const body = readFileSync(inbox, "utf8");
    const openCount = (body.match(/\*\*Status:\*\*\s*OPEN/gi) || []).length;
    out(`Inbox messages/to_${role}.md — OPEN ${openCount}건:`);
    out(body.length > 4000 ? "...\n" + body.slice(-4000) : body);
  } else {
    out(`인박스 파일이 아직 없습니다: messages/to_${role}.md`);
  }
  out(`상대에게 요청: ${join(shared, "messages", `to_${other}.md`)} 에 append 후 commit & push`);
  out(`========================================\n`);
  process.exit(0);
}

main();
