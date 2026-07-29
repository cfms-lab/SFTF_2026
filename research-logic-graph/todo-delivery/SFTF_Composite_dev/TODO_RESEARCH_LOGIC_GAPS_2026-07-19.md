# TODO: research logic gap #2 — rebuild the proxy-to-trusted-reference ladder

Date: 2026-07-19  
Source: cross-project Graphify research-logic audit

## Current logical boundary

R7 is an important honest negative result: neither the kinematic `|K| g^2` proxy nor the fishnet
field validates strongly against the audited Baraff forming shear, while free-hang is itself the
wrong reference condition. The next step is not another parameter sweep that tries to recover a
positive correlation. The paper must choose a narrower proxy claim or construct a reference that
matches the intended composite-forming process.

## Tasks

- [ ] Freeze the negative R7 result as evidence. Tag the engine commit, boundary conditions,
  material/trellis axes, mould geometry, caps, mesh resolution, and seeds used to obtain it.
- [ ] Choose and document one claim branch before new experiments:
  - **Branch A:** retain the field only as a geometric partition initializer/feature;
  - **Branch B:** introduce a forming-aware field and validate it against a trusted forming solve.
- [ ] For Branch B, define the reference before fitting: mould contact, blank holders or tension,
  anisotropic material axes, friction, and a per-element shear/locking quantity comparable to the
  proposed proxy.
- [ ] Use held-out moulds/material axes and report element-, patch-, and final partition-level
  metrics. Include seam length, maximum/p95 shear, locking violations, and solver cost.
- [ ] Add simple baselines (`|K|`, geodesic/normal features, fishnet-only, random/spatial
  partitions) so any benefit is attributable to the new field rather than clustering capacity.
- [ ] Define an escalation policy: candidates near locking or with proxy/reference disagreement
  must be evaluated by the trusted forming solver.
- [ ] Update both Korean and English drafts so the old free-hang validation plan is not described
  as successful quantitative validation.

## Done when

- The manuscript has the explicit chain `cheap feature/proxy -> trusted forming solve -> held-out
  verification -> bounded claim`.
- R7 remains reproducible and visible even if the follow-up result is negative.
- The method is called an initializer/feature unless held-out trusted-solver evidence supports a
  stronger and precisely scoped claim.
