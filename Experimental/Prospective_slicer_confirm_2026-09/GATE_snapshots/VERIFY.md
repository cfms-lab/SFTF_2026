# Frozen GATE snapshots

These files are the byte-exact texts of the protocol at the moment each lock file was written.
Verify:

    sha256sum GATE_frozen_part1_47a30370.md   # must equal files[GATE…] in ../prereg_lock.json
    sha256sum GATE_frozen_part2_6bc4188c.md   # must equal files[GATE…] in ../prereg_lock_part2.json

The current GATE file at the repository root is the same text plus the appended results and the part-2 plan.
Lock times are local workstation clocks recorded in the lock files; no external registry was used.
