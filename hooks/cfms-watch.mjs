#!/usr/bin/env node
/**
 * cfms-watch — cfms 공유 채널 자동 반응 워처(데몬, 훅 아님).
 *
 * 동작: 공유 저장소를 intervalSec 마다 git fetch/merge 하여, 내 인박스(to_<role>.md)에
 *       "새로운 OPEN 항목"이 생기면 헤드리스 `claude -p` 를 실행해 자동 처리한다.
 *
 * 실행: node cfms-watch.mjs <projectDir>     (projectDir 생략 시 현재 폴더)
 *       projectDir 에는 .cfms-sync.json (role/sharedPath) 가 있어야 한다.
 *       옵션은 같은 폴더의 .cfms-watch.json 으로 설정.
 *
 * 가드레일:
 *   - 내 인박스(to_<me>.md)만 감시 → 상대만 쓰는 파일이라 내 push로 자기 트리거 안 됨.
 *   - 각 메시지(헤더 해시)는 단 1회만 트리거(.cfms-watch.state.json).
 *   - cooldownSec 간격 + maxPerHour 상한 + 단일 실행(동시 실행 금지).
 *   - 최초 실행 시 기존 메시지는 기준선으로 무시(processBacklog=true면 처리).
 */
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { join, isAbsolute, resolve } from "node:path";
import { execFileSync, spawn } from "node:child_process";
import { createHash } from "node:crypto";

const projectDir = resolve(process.argv[2] || process.cwd());
const syncPath = join(projectDir, ".cfms-sync.json");
if (!existsSync(syncPath)) {
  console.error(`[cfms-watch] .cfms-sync.json 없음: ${projectDir}`);
  process.exit(1);
}
const sync = JSON.parse(readFileSync(syncPath, "utf8"));
const role = sync.role === "drape" ? "drape" : "cad";
const other = role === "cad" ? "drape" : "cad";
let shared = sync.sharedPath || "../cfmsShared2026_dev";
shared = isAbsolute(shared) ? shared : resolve(projectDir, shared);

const wcfgPath = join(projectDir, ".cfms-watch.json");
const w = existsSync(wcfgPath) ? JSON.parse(readFileSync(wcfgPath, "utf8")) : {};
const intervalSec = w.intervalSec ?? 10;
const cooldownSec = w.cooldownSec ?? 30;
const maxPerHour = w.maxPerHour ?? 12;
const auto = w.auto !== false;
const processBacklog = w.processBacklog === true;
const claudeCmd = w.claudeCmd || "claude";
const claudeArgs = w.claudeArgs || ["-p"]; // 권한 자동수락 필요 시 ["-p","--permission-mode","acceptEdits"] 등

const statePath = join(projectDir, ".cfms-watch.state.json");
const fresh = !existsSync(statePath);
let st = fresh ? { processed: [], runs: [] } : JSON.parse(readFileSync(statePath, "utf8"));
const processed = new Set(st.processed);
let running = false;
let lastRun = 0;

function log(m) { console.error(`[cfms-watch ${role}] ${new Date().toISOString()} ${m}`); }
function save() { writeFileSync(statePath, JSON.stringify({ processed: [...processed], runs: st.runs }, null, 0)); }

function gitSync() {
  try {
    execFileSync("git", ["fetch", "--quiet"], { cwd: shared, windowsHide: true });
    execFileSync("git", ["merge", "--ff-only", "--quiet"], { cwd: shared, windowsHide: true });
  } catch (e) { log(`git fetch/merge 실패(무시): ${String(e.message).split("\n")[0]}`); }
}

function inboxEntries() {
  const f = join(shared, "messages", `to_${role}.md`);
  if (!existsSync(f)) return [];
  const body = readFileSync(f, "utf8");
  return body
    .split(/(?=^##\s)/m)
    .filter((s) => s.trim().startsWith("##"))
    .map((p) => {
      const header = (p.split("\n")[0] || "").trim();
      const status = /\*\*Status:\*\*\s*OPEN/i.test(p) ? "OPEN" : "DONE";
      const id = createHash("sha1").update(header).digest("hex").slice(0, 12);
      return { id, header, status };
    });
}

function rateOk() {
  const now = Date.now();
  st.runs = (st.runs || []).filter((t) => now - t < 3600 * 1000);
  if (st.runs.length >= maxPerHour) { log(`시간당 실행 한도(${maxPerHour}) 도달 — 대기`); return false; }
  if (now - lastRun < cooldownSec * 1000) return false;
  return true;
}

function trigger(newOpen) {
  running = true;
  lastRun = Date.now();
  st.runs = st.runs || [];
  st.runs.push(lastRun);
  const subjects = newOpen.map((e) => e.header.replace(/^##\s*/, "")).join(" / ");
  const prompt =
    `cfms 공유 채널에 새 요청이 도착했다(내 역할: ${role}). ` +
    `${shared} 를 git pull 한 뒤, messages/to_${role}.md 에서 Status가 OPEN 인 항목을 처리하라. ` +
    `완료한 항목은 Status를 DONE 으로 바꾸고, 상대에게 회신/요청이 필요하면 messages/to_${other}.md 에 ` +
    `항목을 추가한 뒤 공유 저장소를 commit & push 하라. ` +
    `단, contract/ 를 바꾸는 큰 변경은 직접 수행하지 말고 to_${other}.md 에 제안만 남겨라. 새 요청: ${subjects}`;
  log(`자동 반응 실행 → ${subjects}`);
  const child = spawn(claudeCmd, claudeArgs, { cwd: projectDir, windowsHide: true, shell: true, stdio: ["pipe", "ignore", "ignore"] });
  child.on("error", (err) => { running = false; log(`claude 실행 실패: ${err.message}`); });
  child.on("exit", (code) => { running = false; log(`claude 종료(code=${code})`); save(); });
  try { child.stdin.write(prompt); child.stdin.end(); } catch {}
}

function tick() {
  if (running) return;
  gitSync();
  const entries = inboxEntries();
  const newOpen = entries.filter((e) => e.status === "OPEN" && !processed.has(e.id));
  if (newOpen.length === 0) return;
  log(`새 OPEN ${newOpen.length}건 감지`);
  if (!auto) { newOpen.forEach((e) => processed.add(e.id)); save(); log("auto=false: 알림만(자동 실행 안 함)"); return; }
  if (!rateOk()) return; // 처리표시 안 함 → 다음 틱에 재시도
  newOpen.forEach((e) => processed.add(e.id));
  save();
  trigger(newOpen);
}

log(`시작 — shared=${shared}, interval=${intervalSec}s, auto=${auto}, cooldown=${cooldownSec}s, maxPerHour=${maxPerHour}`);
gitSync();
if (fresh && !processBacklog) {
  inboxEntries().forEach((e) => processed.add(e.id));
  save();
  log("기준선 설정 — 기존 메시지는 무시하고, 이후 도착하는 새 메시지에만 반응합니다.");
}
tick();
setInterval(tick, intervalSec * 1000);
