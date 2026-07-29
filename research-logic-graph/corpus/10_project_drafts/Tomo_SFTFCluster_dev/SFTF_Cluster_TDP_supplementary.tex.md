# LaTeX source: SFTF_Cluster_TDP_supplementary.tex

Source: `D:\__SFTF_Projects(2026)\Tomo_SFTFCluster_dev\draft\SFTF_Cluster_TDP_supplementary.tex`

% =====================================================================
%  SFTF-Cluster -- Supplementary Material for 3D Printing and Additive
%  Manufacturing (TDP), SAGE.
%  Companion to SFTF_Cluster_TDP_draft.tex.
%  All figures, tables, equations, and sections are S-numbered.
% =====================================================================
% !TEX program = pdflatex
\documentclass[12pt]{article}

\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{amsmath,amssymb,bm}
\usepackage{graphicx}
\graphicspath{{pics/}}
\usepackage[labelfont=bf,labelsep=space]{caption}
\usepackage{booktabs}
\usepackage{float}
\usepackage[margin=25mm]{geometry}
\usepackage{xcolor}
\usepackage[hidelinks]{hyperref}
\usepackage{url}

% S-numbering for all cross-referenced objects
\renewcommand{\thefigure}{S\arabic{figure}}
\renewcommand{\thetable}{S\arabic{table}}
\renewcommand{\theequation}{S\arabic{equation}}
\renewcommand{\thesection}{S\arabic{section}}

\title{Supplementary Material for\\\emph{Output-Aware Mesh Partitioning Based on a
Support Flow Tensor Field}}
\author{InHwan Sul}
\date{}

\begin{document}
\maketitle

\noindent This supplementary file collects the explanatory figures, detailed
quantitative tables, and the internal-estimate/CuraEngine cost analysis that are
referenced from but omitted in the shortened main manuscript. Figures, tables, and
equations are numbered with an ``S'' prefix. Numeric values match those in the main
text and are grouped here only to respect the article length limits.

% =====================================================================
\section*{Supplementary Figures}
% =====================================================================

\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{Bunny69k_kray3000_concept_balanced.png}
\caption{\textbf{Deterministic surface sampling and the v2 direction-score landscape
on the Bunny mesh.} SFTF v2 reuses the same $8{,}192$ normalized-area samples for all
$2{,}048$ candidate directions, normalizes ray heights by the bounding-box diagonal,
and evaluates the dimensionless symmetric-Rayleigh-plus-bed score. The resulting
landscape separates low-score basins from high-score orientations without
direction-dependent resampling. The main manuscript uses the selected basin direction
and the resulting per-face support-flow records.}
\label{fig:supp-kray}
\end{figure}

\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{figure3_bunny_landscape_support.png}
\caption{\textbf{Bunny internal-screen landscape and support structures at
representative orientations.} This independent TOMO2026 sweep compares its lowest and
highest screening orientations; it is not the dimensionless SFTF v2 score of
Fig.~\ref{fig:supp-kray} and is not used as the final slicer result. The large support
contrast motivates retaining a cheap screening stage while validating headline
comparisons with CuraEngine.}
\label{fig:supp-landscape}
\end{figure}

\begin{figure}[H]
\centering
\includegraphics[width=0.82\textwidth]{lambda_sweep_manikin.png}
\caption{\textbf{Boundary-smoothing parameter sweep for the manikin
\texttt{support\_flow} partition.} Pure support-flow methods initially produce
face-level boundaries that follow support roles and support pairs; such boundaries are
physically meaningful but can be jagged. This sweep varies the graph-cut smoothing
strength $\lambda$ and measures boundary behaviour and support-class purity. Boundary
length and roughness fall rapidly from $\lambda=0$ to about $\lambda=2$ and then
saturate, while support-class purity stays nearly stable. The value $\lambda=3$ is
therefore selected as a practical compromise beyond the roughness-saturation point
that still preserves interpretable support-role structure.}
\label{fig:supp-lambda}
\end{figure}

\begin{figure}[H]
\centering
\includegraphics[width=0.86\textwidth]{support_liver_equal_scale.png}
\caption{\textbf{Liver partitions and supports at equal scale.} Because the liver is
compact, most methods find nearly support-free part orientations, so support mass is
weakly discriminative and support-class purity is the more sensitive metric. SFTF
support-flow methods separate the self-supporting body from the downward-facing
overhang regions, reaching purity up to $0.96$ (Table~\ref{tab:supp-app-purity}).}
\label{fig:supp-liver}
\end{figure}

\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{cura_vs_tomo_contour.png}
\caption{\textbf{Whole-mesh orientation agreement between the internal solid estimator
and open CuraEngine.} On the regenerated Bunny grid the internal (TOMO2026) estimator
agrees strongly with CuraEngine at the whole-mesh orientation level (total-mass
Spearman $0.939$; TOMO--Cura $\rho=0.927$). This justifies using the fast estimator
for broad screening while the per-part support comparisons in the main text still use
CuraEngine directly.}
\label{fig:supp-cura-tomo}
\end{figure}

\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{g5test_sftCluster_kmedoids_grouped.png}
\caption{\textbf{Four-group (A--D) qualitative overview of feature-fusion $k$-medoids
partitions.} Primitive, mechanical, graphics/application, and scanned-anatomical meshes
are shown with their v2-conditioned feature-fusion partitions. The application group
includes graphics scans, organs, and a human form, illustrating the same pipeline
across substantially different topology and scale.}
\label{fig:supp-g5}
\end{figure}

\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{g5test_sftCluster_representative_methods_abg.png}
\caption{\textbf{Representative side-by-side comparison of partitioning methods.} For
a representative mesh from each group, the coordinate/geometry baselines and the
SFTF-based methods are shown with the same colour convention, complementing the
quantitative twelve-shape benchmark of the main text (Table~4).}
\label{fig:supp-abg}
\end{figure}

\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{partcount_confound_s8.png}
\caption{\textbf{Part count explains much of the apparent support advantage.} Both
panels use the twelve-shape CuraEngine benchmark of Table~4 in the main
text, with no re-slicing. \textbf{(a)} Added-variable plot: for every method and shape,
$\log_{10}$ of the summed Cura-optimal support and $\log_{10}$ of the part count are
centred by their per-shape means, so all twelve shapes overlay on common axes with each
shape's absolute support scale removed. The pooled within-shape slope ($-0.25$) confirms
that more parts generally lower support---the reorientation-freedom mechanism---but points
below the line use \emph{less} support than their part count alone predicts.
\textbf{(b)} Mean residual from a support model that controls for both shape and part
count: coordinate $k$-means has the most negative residual ($0.74\times$ the support
predicted by part count), followed by feature-fusion $k$-medoids ($0.77\times$), whereas
the pure support-flow and Gao partitions use more support than their part counts would
suggest. \emph{Caveat}: this observational analysis is superseded by
the direct matched-part-count control of Note~\ref{sec:supp-matchedk}, which shows the
within-shape slope fitted here is underestimated---no method in this pool combines a
high part budget with coordinate compactness---and that at an equalised part budget the
coordinate baseline in fact uses less support. The panel is retained to document the
part-count--support relation itself, not a feature advantage beyond it.}
\label{fig:supp-partcount}
\end{figure}

\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{split_benefit_scatter_s9.png}
\caption{\textbf{When does partitioning itself pay off?} Split benefit is
$\log_{10}$ of the no-split CuraEngine support divided by the best splitting
method's support on the same shape (positive: the best decomposition reduces
support; negative: every decomposition adds support). \textbf{(a)} Benefit against
the best \emph{single-direction} support-free coverage, a ray-free quantity
computable before any partitioning. The relation is one-sided, a ceiling rather
than a trend: high coverage bounds what any decomposition can save, and the only
shape whose best single direction already covers $99\%$ of its area (anat-D1) is
also the only shape where every compared method's split hurts at its default part
budget (the matched-budget control of Note~\ref{sec:supp-matchedk} shows a
sufficiently fine split can still win there), while low coverage permits but does
not guarantee a large gain (happy). \textbf{(b)} The intuitive alternative
descriptor---PCA elongation $e_1/e_2$---shows no relation (Spearman
$\rho=-0.01$); ``already elongated'' is not by itself a usable criterion. Both
panels are observational post-hoc summaries of the twelve benchmark shapes, not a
fitted decision rule.}
\label{fig:supp-splitbenefit}
\end{figure}

\begin{figure}[H]
\centering
\includegraphics[width=0.74\textwidth]{ablation_arms_s10.png}
\caption{\textbf{What the feature-ablation arms look like}
(Supplementary Note~S4 and Table~S13). Columns are the three ablation arms of the
same $k$-medoids run (identical algorithm, requested cluster count $K=6$, seed, and
post-processing; only the input matrix changes); annotations give connected parts
and summed per-part CuraEngine-optimal support. \emph{Coordinates only} yields few,
blocky, spatially compact parts whose cuts ignore support behaviour.
\emph{Fusion} (the main-text configuration) keeps parts spatially coherent while
bending cuts along support roles (manikin $0.84$~g, \emph{Nefertiti} $7.59$~g).
\emph{SFTF features only} follows support roles across the whole surface and is lower
on most shapes (liver $4.29$~g, \emph{Nefertiti} $1.72$~g), but it commonly produces
more connected parts (anat-D3: $43$ versus $26$ for fusion). The panels therefore show
a support--fragmentation trade-off, not an isolated benefit from either feature block.}
\label{fig:supp-ablation-arms}
\end{figure}

% =====================================================================
\section*{Supplementary Tables}
% =====================================================================

\begin{table}[H]
\centering
\caption{Partitioning results on the Bunny ($69{,}662$ faces).}
\label{tab:supp-bunny}
\begin{tabular}{lrrr}
\toprule
Method & Time (s) & Parts & Noise faces\\
\midrule
\texttt{support\_flow} (support basin) & 1.84 & 5  & 0\\
\texttt{flow\_region} (region growing) & 1.50 & 14 & 0\\
$k$-medoids (coord+SFTF)               & 1.11 & 28 & 0\\
DBSCAN (coord+SFTF)                    & 9.11 & 4  & 202\\
\texttt{build\_direction} (multi-dir argmax) & 4.55 & 14 & 0\\
\bottomrule
\end{tabular}
\end{table}

\begin{table}[H]
\centering
\caption{Support-class purity by partitioning method on the manikin ($13{,}672$
faces; higher is better). Baseline methods follow the coordinate/geometry branch of
Fig.~2 in the main text. Pure-SFTF methods use the default boundary smoothing
$\lambda=3$.}
\label{tab:supp-manikin-purity}
\begin{tabular}{llrr}
\toprule
Family & Method & Parts & Purity\\
\midrule
\input{generated_v2/sftf_v2_manikin_purity_rows.tex}
\end{tabular}
\end{table}

\begin{table}[H]
\centering
\caption{Detailed support-class purity on the three application shapes (higher is
better).}
\label{tab:supp-app-purity}
\begin{tabular}{llrr}
\toprule
Shape (faces) & Method & Parts & Purity\\
\midrule
\input{generated_v2/sftf_v2_application_purity_rows.tex}
\end{tabular}
\end{table}

\begin{table}[H]
\centering
\caption{Current CPU-TOMO screening support on the three application shapes (g,
lower is better; each part stood at its own SFTF v2 diagnostic direction,
$\theta_c=45^\circ$). Only methods re-run with the synchronized DLL are included.}
\label{tab:supp-app-support}
\resizebox{\textwidth}{!}{%
\begin{tabular}{llrr}
\toprule
Shape & Method & Parts & Support mass (g)\\
\midrule
\input{generated_v2/sftf_v2_internal_tomo_support_rows.tex}
\end{tabular}}
\end{table}

\begin{table}[H]
\centering
\caption{Open-CuraEngine orientation diagnostic on the SFTF v2-conditioned partitions,
in grams. ``SFTF v2 diagnostic'' orients each part to the lowest-score v2 basin;
``Cura-optimal'' orients each part to its own CuraEngine-best direction over a uniform
$48$-direction menu. Across the listed methods, using the diagnostic direction costs
$1.9$--$19.7\times$ more support than the slicer search; for feature-fusion
$k$-medoids the factor is $5.0$--$16.3\times$.}
\label{tab:supp-cura-diag}
\resizebox{\textwidth}{!}{%
\begin{tabular}{llrr}
\toprule
Shape & Method & SFTF v2 diagnostic (g) & Cura-optimal (g)\\
\midrule
\input{generated_v2/sftf_v2_cura_diagnostic_rows.tex}
\end{tabular}}
\end{table}

\begin{table}[H]
\centering
\caption{Comparison with the multi-directional support-minimising decomposition of
Gao et al.\ (2019), using a faithful reproduction of its core procedure. Each part is
stood at its own optimal direction, and Gao runs at its natural part count.}
\label{tab:supp-gao}
\resizebox{\textwidth}{!}{%
\begin{tabular}{llrrr}
\toprule
Shape & Method & Parts & Purity & $S$ (g)\\
\midrule
\input{generated_v2/sftf_v2_internal_gao_rows.tex}
\end{tabular}}
\end{table}

\begin{table}[H]
\centering
\caption{SFTF v1-to-v2 integration audit on the twelve benchmark shapes. V1 is the
previous tuned-h25/uniform router; v2 uses $8{,}192$ deterministic normalized-area
surface samples, $2{,}048$ Fibonacci directions, and $12^\circ$ basin separation.
Angle is the directed angular difference between the v1 and v2 conditioning
directions. The final column counts changed connected partitions among the five
SFTF-dependent methods. No CuraEngine or TOMO result enters this label-only audit:
59 of 60 partitions changed, so the slicer checkpoints were regenerated.}
\label{tab:supp-breadth-support}
\resizebox{\textwidth}{!}{%
\begin{tabular}{llrrr}
\toprule
Shape & V1 route & v2 score & angle ($^\circ$) & changed / 5\\
\midrule
torus            & uniform    & 0.1137 & 88.54  & 5\\
hook             & uniform    & 0.0961 & 147.41 & 5\\
anat-D9          & uniform    & 0.0891 & 54.41  & 4\\
anat-D3          & uniform    & 0.1115 & 60.39  & 5\\
anat-D1          & uniform    & 0.0089 & 9.16   & 5\\
liver            & uniform    & 0.1083 & 17.04  & 5\\
\emph{Nefertiti} & uniform    & 0.1142 & 18.80  & 5\\
manikin          & tuned-h25  & 0.0808 & 171.90 & 5\\
dragon           & tuned-h25  & 0.1140 & 3.52   & 5\\
happy            & tuned-h25  & 0.1324 & 98.61  & 5\\
lucy             & tuned-h25  & 0.0697 & 2.37   & 5\\
kidney           & tuned-h25  & 0.0616 & 168.31 & 5\\
\bottomrule
\end{tabular}}
\end{table}

\begin{table}[H]
\centering
\caption{Support-class purity (SFTF classes, higher is better) for the twelve-shape
benchmark partitions of Table~4 in the main text. Bold marks the best value in each
row.}
\label{tab:supp-breadth-purity}
\resizebox{\textwidth}{!}{%
\begin{tabular}{lrrrrrrrr}
\toprule
Shape & $k$-means & Planar & Gao & basin & region & medoids & multi-dir & auto\\
\midrule
\input{generated_v2/sftf_v2_purity_rows.tex}
\end{tabular}}
\end{table}

\begin{table}[H]
\centering
\caption{Anti-circularity check: mean support-class purity over the twelve benchmark
shapes when face classes are defined by SFTF (as in the main text) versus derived from
actual CuraEngine support geometry (whole mesh sliced at the SFTF reference direction;
a face is \textsc{needs} if a support column ends directly below it, \textsc{supporter}
if a column stands on it). SFTF \textsc{needs} captures every Cura support-contact face
(recall $1.0$ on all twelve shapes) at precision $0.06$--$0.40$; the two purity
definitions are not interchangeable: over the eight partitioners, per-shape Spearman
$\rho$ ranges from $-0.58$ to $0.77$, with median $0.42$ among the eleven defined
shapes (anat-D1 is undefined because one purity vector is constant).}
\label{tab:supp-slicer-purity}
\begin{tabular}{lrr}
\toprule
Method & Purity (SFTF classes) & Purity (Cura-derived classes)\\
\midrule
\input{generated_v2/sftf_v2_slicer_purity_rows.tex}
\end{tabular}
\end{table}

\begin{table}[H]
\centering
\caption{Per-orientation evaluation time on the Bunny ($69{,}662$ faces, $12$
orientations, serial).}
\label{tab:supp-speed}
\begin{tabular}{lrrr}
\toprule
Engine & mean (s) & median (s) & relative cost\\
\midrule
Internal estimator & $0.102$ & $0.098$ & ---\\
CuraEngine (legacy, full slice)       & $11.33$  & $10.69$  & $\sim$$110\times$ slower\\
\quad of which CuraEngine subprocess  & $11.30$  & ---     & (STL prep $0.03$\,s)\\
\bottomrule
\end{tabular}
\end{table}

\begin{table}[H]
\centering
\caption{Bootstrap uncertainty of the twelve-shape mean ranks in Table~4 of the main
text. Shapes are resampled with replacement ($20{,}000$ replicates, seed $0$);
tie-adjusted ranks are recomputed per replicate. The intervals quantify the
small-sample caveat stated in the main text: feature-fusion $k$-medoids holds the best
mean rank or a tie in $81.7\%$ of replicates, while its interval overlaps that of coordinate
$k$-means, consistent with the non-significant pairwise Wilcoxon test ($p=0.733$).}
\label{tab:supp-bootstrap}
\begin{tabular}{lrr}
\toprule
Method & Mean rank & Bootstrap $95\%$ CI\\
\midrule
\input{generated_v2/sftf_v2_bootstrap_rows.tex}
\end{tabular}
\end{table}

% =====================================================================
\section{Supplementary Note: internal screening estimate and CuraEngine cost}
\label{sec:supp-speed}
% =====================================================================

This note documents the fast internal estimate used for broad sweeps and ray-free
objective checks, and the reason CuraEngine is used only for the headline comparisons.
The reference slicer in the paper is CuraEngine; the internal estimate is used only
where repeated per-orientation or per-partition slicing would be too expensive.

On the Stanford Bunny ($69{,}662$ faces), we timed the per-orientation evaluation of
CuraEngine and the internal solid-support estimator over the same set of build-up
direction vectors (after one warm-up call each, 12 orientations). CuraEngine legacy
15.04 slices the rotated, bed-dropped STL with support everywhere and
$\theta_c=45^\circ$. The internal estimator costs $\sim$$0.10$\,s per orientation
versus $\sim$$11.3$\,s for CuraEngine, a $\sim$$110\times$ difference dominated
entirely by the CuraEngine slicing subprocess (Table~\ref{tab:supp-speed}). This gap
is decisive for repeated evaluation (serial extrapolation): a single $256$-direction
menu costs the estimator $26$\,s versus CuraEngine $2900$\,s ($0.8$\,h); the
slicer-in-the-loop manikin search costs the estimator $169$\,s versus CuraEngine
$18{,}802$\,s ($5.2$\,h); and a dense eight-shape sweep ($8$ shapes $\times$ $5$
methods $\times$ $\sim$$10$ parts $\times$ $256$ directions) costs the estimator
$10{,}401$\,s versus CuraEngine $1{,}159{,}846$\,s ($322.2$\,h). The large screening
tables, which require thousands to tens of thousands of evaluations, are therefore
practical only with the fast estimate, while the headline support comparison uses
CuraEngine directly. \emph{Note:} CuraEngine parallelises across orientations (e.g.\
$14$ cores $\to$ $\sim$$0.51$\,s/slice), but the intrinsic per-orientation cost
remains much higher, so the conclusion holds.

Crucially, the internal estimate is a \emph{screening} tool, not a slicer surrogate.
On two scanned-anatomical shapes the screening ranking inverts relative to CuraEngine:
anat-D9 and anat-D1 in Table~\ref{tab:supp-breadth-support} favour different methods
than the slicer-level benchmark (Table~4 of the main text). This is exactly why every
headline support comparison in the paper is computed with CuraEngine rather than the
fast estimate. Historically, the internal estimator was also compared with
printer-side and slicer-side measurements from an earlier 3DWOX/DP-103 workflow; with
the shared solid engine, the regenerated Bunny grid shows strong whole-mesh
orientation agreement (total-mass Spearman $0.939$, support-mass Spearman $0.936$ over
$144$ matched orientations; TOMO--Cura $\rho=0.927$, $R=0.939$;
Fig.~\ref{fig:supp-cura-tomo}), which makes the estimator useful as a fast
orientation-screening signal while CuraEngine remains the citable reference slicer.

% =====================================================================
\section{Supplementary Note: extended feature-fusion formulae}
\label{sec:supp-formulae}
% =====================================================================

When the optional multi-direction preference block is included, the clustering matrix
is
\begin{equation}
X_{\mathrm{cluster}}
= \big[\, w_s\,\operatorname{zscore}(C)\ \big|\ w_f\,X_F^{\mathrm{part}}\ \big|\
  w_d\,W\,\big]
\in\mathbb{R}^{N\times(8+K)},
\label{eq:supp-cluster-matrix-full}
\end{equation}
where $C\in\mathbb{R}^{N\times3}$ is the face-centre matrix,
$X_F^{\mathrm{part}}\in\mathbb{R}^{N\times5}$ is
$\operatorname{zscore}([O,\tau,\eta,h,\nu^{\mathrm{in}}])$, $W=[w_{ik}]\in\mathbb{R}^{N\times K}$
contains the soft direction-preference weights, and $w_s,w_f,w_d$ are scalar weights.
Without $W$, Eq.~\eqref{eq:supp-cluster-matrix-full} reduces to the $N\times8$ matrix
used for the fixed-direction clustering experiments in the main text. The support
saving attributed to allowing each part to choose its own orientation is
\begin{equation}
\Delta J_{\mathrm{reorient}}(\Pi)
=\sum_\ell\left[C_\ell(n^\ast)-\min_d C_\ell(d)\right],
\label{eq:supp-reorient}
\end{equation}
where $n^\ast$ is the whole-mesh reference build direction. During greedy merging for
automatic part-count selection, the incremental support penalty of merging two
candidate parts $a$ and $b$ is evaluated in $O(K_{\mathrm{dir}})$ as
\begin{equation}
\Delta\widehat J_{\mathrm{merge}}
=\min_k\left(C_{a,k}+C_{b,k}\right)-\min_k C_{a,k}-\min_k C_{b,k}\ge0,
\label{eq:supp-merge-cost}
\end{equation}
and this additivity is what makes the ray-free objective practical for repeated
part-count searches.

% =====================================================================
\section{Supplementary Note: verification of the Gao-2019 re\-im\-ple\-men\-ta\-tion}
\label{sec:supp-gao-verify}
% =====================================================================

The multi-directional decomposition of Gao et al.\ (2019) is compared in the main text
through a reimplementation of its core procedure, because the original code was not
available. The reimplementation maps one-to-one onto the published pipeline: (i) a
global near-support-free build-direction set is selected by area-weighted greedy
set-cover over $128$ Fibonacci plus six axis candidate directions, where a face is
support-free along $d$ when $n\cdot d\ge-\cos\theta_c$; (ii) faces are assigned to the
selected direction that best self-supports them, with ICM smoothing enforcing the
spatial coherence of the original global optimisation; and (iii) same-direction
connected components form parts, evaluated at their natural part count (no external
part budget is imposed on Gao).

Because every step is deterministic, the partitions can be regenerated exactly: the
regenerated part counts match the benchmark checkpoints on all twelve shapes. More
importantly, the reimplementation is verified against the \emph{original method's own
success criterion}. Gao et al.\ optimise near-support-free \emph{coverage}---the area
fraction printable without support when each part is built along its assigned
direction---not slicer support mass. Table~\ref{tab:supp-gao-coverage} shows that the
reimplementation attains this design goal on every benchmark shape: mean coverage
rises from $0.943$ (best single direction) to $0.993$ (multi-directional parts), with
coverage of at least $0.95$ on all twelve shapes and $0.99$ or higher on nine. The
reimplementation therefore does what the original method is designed to do. Its
comparatively high support mass in Table~4 of the main text is a property of the
evaluation axis, not of an under-tuned reproduction: a near-total \emph{area} coverage
can still leave a large support \emph{mass}, because the residual steep area, although
small, may sit high above the plate and generate tall support columns.
\emph{Nefertiti} is the sharpest example---coverage $0.999$ yet $30.70$~g of
CuraEngine support---and the selected direction sets are small (two directions per
shape), so Gao parts forgo the per-part reorientation freedom that the slicer-level
protocol rewards. The comparison conditions favour Gao where a choice existed: it runs
at its natural part count, while the clustering methods are charged for every
connected component they produce.

\begin{table}[H]
\centering
\caption{Verification of the Gao-2019 reimplementation on its own objective:
near-support-free coverage (area fraction with $n\cdot d\ge-\cos\theta_c$,
$\theta_c=45^\circ$). ``Single dir'' is the best coverage achievable with one build
direction; ``Gao multi-dir'' scores each face at its part's assigned direction from
the reimplementation. $K$ is the number of directions selected by the greedy
set-cover; part counts equal the benchmark checkpoints on all twelve shapes. Cura-opt
support (from Table~4 of the main text) is shown for contrast: high coverage does not
imply low slicer support mass.}
\label{tab:supp-gao-coverage}
\begin{tabular}{lrrrrr}
\toprule
Shape & $K$ & Parts & Single dir & Gao multi-dir & Cura-opt (g)\\
\midrule
torus            & 2 & 3   & 0.906 & 1.000 & 0.12\\
hook             & 2 & 2   & 0.938 & 0.990 & 0.11\\
anat-D9          & 2 & 220 & 0.935 & 0.966 & 16.65\\
anat-D3          & 2 & 16  & 0.963 & 0.988 & 0.74\\
anat-D1          & 2 & 4   & 0.991 & 0.996 & 13.65\\
liver            & 2 & 5   & 0.969 & 0.996 & 10.51\\
\emph{Nefertiti} & 2 & 2   & 0.950 & 0.999 & 30.70\\
manikin          & 2 & 11  & 0.947 & 1.000 & 6.59\\
dragon           & 2 & 12  & 0.916 & 0.994 & 48.94\\
happy            & 2 & 13  & 0.890 & 0.994 & 16.67\\
lucy             & 2 & 10  & 0.953 & 0.999 & 12.73\\
kidney           & 2 & 4   & 0.964 & 1.000 & 1.49\\
\midrule
mean             &   &     & 0.943 & \textbf{0.993} & \\
\bottomrule
\end{tabular}
\end{table}

% =====================================================================
\section{Supplementary Note: feature ablation for the fusion clustering}
\label{sec:supp-ablation}
% =====================================================================

To isolate what the SFTF feature block contributes to feature-fusion $k$-medoids,
the clustering input matrix of Eq.~(9) in the main text was ablated while holding
everything else fixed: the same $k$-medoids algorithm, the same requested cluster
count ($K=6$), the same seed, the same connectivity post-process, and the same
48-direction CuraEngine protocol as Table~4. Only the two block weights change:
\emph{coordinates only} ($w_s=1, w_f=0$), \emph{fusion} ($w_s=1, w_f=1.5$; the
configuration reported in the main text), and \emph{SFTF features only}
($w_s=0, w_f=1.5$). The fusion arm regenerates the Table~4 $k$-medoids results
exactly on all twelve shapes, which validates the harness.

Table~\ref{tab:supp-ablation} shows the outcome, and
Fig.~\ref{fig:supp-ablation-arms} shows the three arms' partitions on four
representative shapes. Mean ranks are $2.25$ for coordinates only, $2.33$ for fusion,
and $1.42$ for SFTF features only. Fusion beats coordinates only on $6/12$ shapes and
the paired contrast is not significant (Wilcoxon $p=0.6221$); features only beats
fusion on $10/12$ shapes ($p=0.0161$). However, the
connectivity post-process yields different final part counts across arms, so the
table does not identify a fixed-budget feature effect. The coordinate block is
retained as a compactness prior: without it, clusters can follow support roles across
the whole surface and often fragment into more connected parts (anat-D3: $43$ vs.\
$26$). Under v2, that compactness does not improve CuraEngine support on average;
instead it trades a smaller part budget for higher support on several large shapes.

\begin{table}[H]
\centering
\caption{Feature ablation of the fusion clustering matrix (Eq.~9 of the main text):
summed per-part CuraEngine-optimal support (g, lower is better) with connected
parts in parentheses. Algorithm ($k$-medoids), requested cluster count, seed,
connectivity post-process, and the 48-direction slicer protocol are identical
across arms; only the input matrix changes. The fusion column reproduces the
$k$-medoids column of Table~4 exactly (harness self-check, twelve of twelve
shapes).}
\label{tab:supp-ablation}
\begin{tabular}{lrrr}
\toprule
Shape & Coordinates only & Fusion (main text) & SFTF features only\\
\midrule
\input{generated_v2/sftf_v2_ablation_rows.tex}
\end{tabular}
\end{table}

% =====================================================================
\section{Supplementary Note: matched part count and seed variance}
\label{sec:supp-matchedk}
% =====================================================================

Feature-fusion $k$-medoids produces more connected parts than the other Table-4
methods at the shared requested cluster count, and support falls as parts gain
independent build orientations. The decisive control is therefore to give the
simplest baseline the same part budget: for each shape, the requested cluster
count of coordinate $k$-means is raised (binary search on the requested $K$;
$k$-means seed and $n_{\mathrm{init}}$ identical to Table~4) until its
\emph{final} connected-part count matches the $k$-medoids part count within
the closest attainable count (within two parts), and the matched partition is
re-evaluated under the identical
48-direction CuraEngine protocol.

Table~\ref{tab:supp-matchedk} shows the outcome, which reverses the
fixed-budget ranking: the matched coordinate baseline uses less support on
all twelve shapes (Wilcoxon $p=0.0005$), often by a wide margin (dragon
$3.30$ vs.\ $26.38$~g), and on most shapes it also undercuts the per-shape best
of all nine Table-4 methods. Even anat-D1, the one shape where every Table-4
decomposition adds support over the no-split floor, is improved from $4.68$ to
$1.66$~g by a sufficiently fine coordinate split. The part budget, not the
feature set, is thus the first-order control on slicer-level support; the
SFTF-feature contribution suggested by the ablation of
Note~\ref{sec:supp-ablation} is not isolated from final part count. This also explains why
the observational regression of Fig.~\ref{fig:supp-partcount} pointed the other
way: its within-shape part-count slope was fitted on a method pool in which no
partitioner combined a high part budget with coordinate compactness, so the
slope was underestimated and the residual analysis under-controlled.

\begin{table}[H]
\centering
\caption{Matched-part-count control: coordinate $k$-means with its requested
cluster count raised until the final connected-part count is as close as attainable
to feature-fusion $k$-medoids (within two parts), evaluated with the identical
48-direction CuraEngine
protocol as Table~4 of the main text (g, lower is better). The matched baseline
wins on all twelve shapes (Wilcoxon $p=0.0005$).}
\label{tab:supp-matchedk}
\resizebox{\textwidth}{!}{%
\begin{tabular}{lrrrrr}
\toprule
Shape & Requested $K$ & Parts & $k$-medoids parts & Matched $k$-means (g) & $k$-medoids (g)\\
\midrule
\input{generated_v2/sftf_v2_matched_rows.tex}
\end{tabular}}
\end{table}

A second control probes seed sensitivity. The Table-4 benchmark runs each
stochastic method once at seed~$0$; re-running the fusion $k$-medoids
configuration at seeds $1$--$4$ on three representative shapes
(Table~\ref{tab:supp-seedvar}) shows a substantial spread---on the liver the
Cura-optimal support ranges from $3.12$ to $8.71$~g across five seeds; on
\emph{Nefertiti} it ranges from $3.23$ to $7.59$~g, and on the manikin from
$0.65$ to $3.82$~g. Part of
this spread is what the multi-start selector of the main text is designed to
absorb, but the benchmark itself does not exploit it, so the single-seed
Table-4 values should be read with this variance in mind.

\begin{table}[H]
\centering
\caption{Seed variance of feature-fusion $k$-medoids on three representative
shapes: Cura-optimal support (g) for seeds $0$--$4$ under the Table-4 protocol
(seed $0$ is the Table-4 checkpoint). The final column gives the best
non-$k$-medoids method on that shape in Table~4, for scale.}
\label{tab:supp-seedvar}
\begin{tabular}{lrrrrrrr}
\toprule
Shape & Seed 0 & Seed 1 & Seed 2 & Seed 3 & Seed 4 & Mean$\pm$SD & Best other\\
\midrule
\input{generated_v2/sftf_v2_seed_rows.tex}
\end{tabular}
\end{table}

\end{document}

