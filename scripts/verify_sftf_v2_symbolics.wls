(* ::Package:: *)

(*
  Independent symbolic checks for the dimensionless SFTF v2 equations.

  Run on this Windows workstation with:
    "C:\\Program Files\\Wolfram Research\\Wolfram\\14.3\\math.exe" \
      -script scripts/verify_sftf_v2_symbolics.wls

  The script exits nonzero if any identity fails.  It is intentionally small:
  Mathematica is an algebra oracle, not an alternative implementation of the
  experimental pipeline.
*)

ClearAll["Global`*"];

n = {nx, ny, nz};
ms = {msx, msy, msz};
mr = {mrx, mry, mrz};
skew = {{0, a, b}, {-a, 0, c}, {-b, -c, 0}};

sym[m_] := (m + Transpose[m])/2;

assumptions = {
  Element[{nx, ny, nz, msx, msy, msz, mrx, mry, mrz, a, b, c}, Reals],
  Element[{o, r, h, hb, d, lambda, scale}, Reals],
  d > 0, h >= 0, hb >= 0, lambda >= 0, scale > 0,
  n.n == 1,
  n.ms == -o,
  ms.n == -o,
  n.mr == r,
  mr.n == r
};

pairTensor = o/(1 + lambda h/d) Outer[Times, ms, mr];
pairRayleigh = FullSimplify[-n.sym[pairTensor].n, assumptions];
pairExpected = o^2 r/(1 + lambda h/d);

bedVirtualTensor = (1 + lambda hb/d) Outer[Times, ms, n];
bedRayleigh = FullSimplify[-n.sym[bedVirtualTensor].n, assumptions];
bedExpected = o (1 + lambda hb/d);

skewRayleigh = FullSimplify[n.skew.n, assumptions];

pairScaled = FullSimplify[
  pairExpected /. {h -> scale h, d -> scale d},
  assumptions
];
bedScaled = FullSimplify[
  bedExpected /. {hb -> scale hb, d -> scale d},
  assumptions
];

checks = <|
  "antisymmetric_rayleigh_zero" -> FullSimplify[skewRayleigh == 0, assumptions],
  "pair_contraction" -> FullSimplify[pairRayleigh == pairExpected, assumptions],
  "virtual_bed_identity" -> FullSimplify[bedRayleigh == bedExpected, assumptions],
  "pair_uniform_scale_invariance" -> FullSimplify[pairScaled == pairExpected, assumptions],
  "bed_uniform_scale_invariance" -> FullSimplify[bedScaled == bedExpected, assumptions]
|>;

Print[ExportString[checks, "RawJSON", "Compact" -> False]];

If[And @@ Values[checks], Exit[0], Exit[1]];
