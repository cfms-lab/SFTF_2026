#!/usr/bin/env node
/**
 * Claude Code PostToolUse hook.
 * .tex 파일이 Write/Edit/MultiEdit 될 때마다 pandoc으로 같은 폴더에 .docx를 생성합니다.
 * 변환 실패가 Claude Code의 작업을 막지 않도록 항상 exit 0 으로 종료합니다(로그는 stderr).
 */
import { existsSync } from "node:fs";
import { execFile } from "node:child_process";

let raw = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (c) => (raw += c));
process.stdin.on("end", () => {
  let event;
  try {
    event = JSON.parse(raw);
  } catch {
    process.exit(0); // 입력 파싱 실패 시 조용히 종료
  }

  const filePath = event?.tool_input?.file_path;
  if (!filePath || !filePath.toLowerCase().endsWith(".tex")) {
    process.exit(0); // .tex 가 아니면 아무것도 하지 않음
  }
  if (!existsSync(filePath)) {
    process.exit(0); // 파일이 아직 없으면 종료
  }

  const docxPath = filePath.replace(/\.tex$/i, ".docx");
  console.error(`[texdoc-gen] ${filePath} -> ${docxPath}`);

  // execFile: 셸을 거치지 않아 Windows 따옴표/이스케이프 문제를 피합니다.
  execFile(
    "pandoc",
    [filePath, "-o", docxPath],
    { windowsHide: true },
    (err, _stdout, stderr) => {
      if (err) {
        console.error(`[texdoc-gen] pandoc 변환 실패: ${stderr || err.message}`);
      } else {
        console.error(`[texdoc-gen] 완료: ${docxPath}`);
      }
      process.exit(0); // 실패해도 워크플로를 막지 않음
    }
  );
});
