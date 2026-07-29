# LaTeX source: crossslicer_transfer.tex

Source: `D:\__SFTF_Projects(2026)\Tomo_SFTFSoft_dev\draft\crossslicer_transfer.tex`

% ==========================================================================
% crossslicer_transfer.tex — Cross-slicer transfer validation (PrusaSlicer)
% Suggested insertion: as a subsection at the end of "CuraEngine Validation"
% (or immediately after it), before "Applications and Degenerate Optima".
% Table uses booktabs; if the preamble lacks it, replace \toprule/\midrule/
% \bottomrule with \hline.
% Reproduction entry point: scripts/prusa_transfer_validation.py
% (frozen profile scripts/prusa_profile_g5_tc60.ini; raw JSON
%  outputs/prusa_transfer/prusa_transfer_tc60_K48.json).
% ==========================================================================

\subsection{Cross-Slicer Transfer: PrusaSlicer}
\label{sec:crossslicer}

The Cura validation leaves one question open: is the slicer-gate physics a
property of CuraEngine, or of the printing process?  We therefore repeat the
prediction experiment against a slicer from a different codebase and support
generator: PrusaSlicer~2.9.6 (console), with a frozen profile whose overhang
threshold of $30^\circ$ from the horizontal reproduces the same
$\theta_c=90^\circ-30^\circ=60^\circ$ gate convention.  Nothing is tuned to
the new slicer: $\theta_c$ is again read from the declared profile, both
predictors are fit-free, and the same 48 Fibonacci directions and meshes are
reused.  Support-only mass is measured from the emitted G-code with the same
high-water-mark accounting as the Cura path.

Across all 21~meshes the hard-gate control $S_g^{\mathrm{hard}}$ reaches a
mean per-mesh Spearman of $+0.73$ against real PrusaSlicer support mass
(bootstrap 95\% CI $[+0.62,+0.82]$), and $S_g$ reaches $+0.62$
($[+0.50,+0.73]$); both are positive on 20 of 21 meshes.  The single
exception is the sphere, whose rotationally symmetric support landscape is
nearly constant, so rank correlation against it measures tessellation noise
rather than prediction.  Two further observations delimit what transfers.
First, the inter-slicer agreement itself, $\mathrm{Spearman}$(Cura, Prusa)
over the same directions, averages $+0.70$: the fit-free gate predicts a
slicer it has never seen about as well as the other slicer does, which is the
natural ceiling for this comparison.  On the cube and the hollow box the two
slicers essentially disagree with each other ($+0.05$ and $-0.03$) while the
gate still tracks PrusaSlicer ($+0.83$ and $+0.85$) --- the predictor is
evidently not fit to CuraEngine idiosyncrasies.  Second, the ordering
$S_g^{\mathrm{hard}}>S_g$ found on Cura recurs on PrusaSlicer with the same
magnitude (mean gap $0.11$; Wilcoxon signed-rank $p=1.6\times10^{-4}$ over
the 21 paired per-mesh correlations), including the D9 case where the
soft-overhang and soft-plate terms dilute the ranking most.  The conclusion
of the hard-gate control therefore transfers unchanged: the prediction is
carried by the gate physics on both slicers, and differentiability again
costs a small, consistent amount of rank fidelity.

\begin{table}[H]
\centering
\caption{Cross-slicer transfer to PrusaSlicer~2.9.6 (frozen profile,
$\theta_c=60^\circ$ read from the profile; 48 directions; support-only mass
from G-code).  Per-mesh Spearman of the fit-free predictors against real
PrusaSlicer support mass, and the inter-slicer agreement
$\mathrm{Spearman}$(Cura, Prusa) as the natural ceiling.  The sphere row is a
degenerate control: its near-constant landscape carries no rankable signal.}
\label{tab:crossslicer}
\small
\begin{tabular}{lrrrr}
\toprule
mesh & $S_g^{\mathrm{hard}}$ & $S_g$ & Cura$\sim$Prusa & valid dirs \\
\midrule
cube            & $+0.83$ & $+0.75$ & $+0.05$ & 47/48 \\
sphere          & $-0.04$ & $-0.10$ & $+0.59$ & 48/48 \\
cylinder        & $+0.94$ & $+0.85$ & $+0.96$ & 48/48 \\
cone            & $+0.91$ & $+0.83$ & $+0.95$ & 43/48 \\
torus           & $+0.74$ & $+0.89$ & $+0.83$ & 48/48 \\
u\_bracket      & $+0.83$ & $+0.75$ & $+0.56$ & 47/48 \\
hook            & $+0.90$ & $+0.83$ & $+0.92$ & 48/48 \\
c\_clamp        & $+0.87$ & $+0.77$ & $+0.70$ & 47/48 \\
pipe\_elbow     & $+0.97$ & $+0.95$ & $+0.98$ & 48/48 \\
hollow\_box     & $+0.85$ & $+0.71$ & $-0.03$ & 47/48 \\
Bunny\_69k      & $+0.76$ & $+0.65$ & $+0.80$ & 48/48 \\
manikin         & $+0.68$ & $+0.51$ & $+0.75$ & 48/48 \\
dragon\_100k    & $+0.61$ & $+0.48$ & $+0.63$ & 48/48 \\
happy\_50k      & $+0.51$ & $+0.35$ & $+0.68$ & 48/48 \\
lucy\_50k       & $+0.32$ & $+0.17$ & $+0.45$ & 48/48 \\
nefertiti\_100k & $+0.61$ & $+0.47$ & $+0.67$ & 48/48 \\
liver\_19k      & $+0.88$ & $+0.66$ & $+0.90$ & 48/48 \\
kidney\_12k     & $+0.96$ & $+0.86$ & $+0.94$ & 48/48 \\
D1\_37009       & $+0.79$ & $+0.73$ & $+0.85$ & 48/48 \\
D5\_37095       & $+0.82$ & $+0.71$ & $+0.82$ & 48/48 \\
D9\_37415       & $+0.56$ & $+0.24$ & $+0.74$ & 48/48 \\
\midrule
mean (21)       & $+0.73$ & $+0.62$ & $+0.70$ & \\
mean (w/o sphere) & $+0.77$ & $+0.66$ & $+0.71$ & \\
\bottomrule
\end{tabular}
\end{table}

% Failed slices (9 of 1{,}008: first-layer-empty edge-balanced orientations,
% five of them on the cone) are excluded per mesh; "valid dirs" reports the
% retained directions.

