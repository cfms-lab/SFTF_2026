"use strict";

const fs = require("fs");
const vm = require("vm");

if (process.argv.length < 3) {
  throw new Error("Usage: node verify_inline_js.js <graph.html> [...]");
}

for (const htmlPath of process.argv.slice(2)) {
  const html = fs.readFileSync(htmlPath, "utf8");
  const blocks = [...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)]
    .map((match) => match[1])
    .filter((script) => script.trim());
  blocks.forEach((script, index) => {
    new vm.Script(script, { filename: `${htmlPath}#inline-${index}` });
  });
  console.log(`${htmlPath}: ${blocks.length} inline scripts syntax OK`);
}
