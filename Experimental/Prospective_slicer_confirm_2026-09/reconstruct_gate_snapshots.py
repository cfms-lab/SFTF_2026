"""Reconstruct the two frozen versions of the GATE protocol and verify them against the lock hashes.

The GATE file was appended twice after freezing (part-1 results + part-2 plan; then part-2 results),
so the current file no longer matches prereg_lock.json / prereg_lock_part2.json. The frozen texts are
recovered by removing the later appendices, hashed, and saved as immutable snapshots under
GATE_snapshots/ when the hashes match the locks.
"""
import hashlib, json, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
GATE = ROOT / "GATE_2026-09-16_prospective_slicer_confirmation.md"
L1 = json.loads((HERE / "prereg_lock.json").read_text(encoding="utf-8"))["files"]["GATE_2026-09-16_prospective_slicer_confirmation.md"]
L2 = json.loads((HERE / "prereg_lock_part2.json").read_text(encoding="utf-8"))["files"]["GATE_2026-09-16_prospective_slicer_confirmation.md"]
raw = GATE.read_bytes()
text = raw.decode("utf-8")
nl = "\r\n" if "\r\n" in text else "\n"

# version B (part-2 lock): everything before the part-2 results block
cut = text.index(nl + "## 2차 결과")
version_b = text[:cut]            # already ends with the newline that closed the part-2 plan
# version A (part-1 lock): before the part-2 plan, with the original change-log placeholder
cut_a = version_b.index(nl + "---" + nl + nl + "# 2차 사전 등록")
version_a = version_b[:cut_a]     # ends with the newline after the change-log line
version_a = re.sub(r"\(없음 — 1차 프로토콜[^\n]*\)", "(없음)", version_a)
print("tail A:", repr(version_a[-40:])); print("tail B:", repr(version_b[-40:]))


def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


out = HERE / "GATE_snapshots"; out.mkdir(exist_ok=True)
results = {}
for name, txt, expected in (("part1", version_a, L1), ("part2", version_b, L2)):
    h = sha(txt); ok = (h == expected)
    results[name] = {"expected": expected, "reconstructed": h, "match": ok}
    if ok:
        (out / f"GATE_frozen_{name}_{expected[:8]}.md").write_text(txt, encoding="utf-8", newline="")
    print(f"{name}: expected {expected[:16]}… reconstructed {h[:16]}… match={ok}")
(out / "VERIFY.md").write_text(
    "# Frozen GATE snapshots\n\n"
    "These files are the byte-exact texts of the protocol at the moment each lock file was written.\n"
    "Verify:\n\n"
    "    sha256sum GATE_frozen_part1_%s.md   # must equal files[GATE…] in ../prereg_lock.json\n"
    "    sha256sum GATE_frozen_part2_%s.md   # must equal files[GATE…] in ../prereg_lock_part2.json\n\n"
    "The current GATE file at the repository root is the same text plus the appended results and the part-2 plan.\n"
    "Lock times are local workstation clocks recorded in the lock files; no external registry was used.\n" % (L1[:8], L2[:8]), encoding="utf-8")
(out / "reconstruction_check.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
