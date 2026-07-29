# LaTeX source: main_en.tex

Source: `D:\__SFTF_Projects(2026)\Tomo_SFTFSoft_dev\draft\main_en.tex`

% =====================================================================
%  main_en.tex -- concise English manuscript for PiAM-style submission
%  Build: uv run python scripts/build_pdf.py draft/main_en.tex
% =====================================================================
\documentclass[11pt,a4paper]{article}

\usepackage{fontspec}
\setmainfont{Times New Roman}

\usepackage{amsmath,amssymb,amsfonts,bm}
\usepackage{amsthm}
\newtheorem{assumption}{Assumption}
\newtheorem{proposition}{Proposition}

\usepackage{graphicx}
\usepackage[labelfont=bf,labelsep=space]{caption}
\captionsetup[figure]{name=Fig.}
\captionsetup[table]{name=Table}
\usepackage{float}
\usepackage{booktabs}
\usepackage{geometry}
\geometry{margin=25mm}
\usepackage[numbers]{natbib}
\usepackage[hidelinks]{hyperref}

\graphicspath{{pics/}{./}}

\newcommand{\nvec}{\bm{n}}
\newcommand{\mvec}{\bm{m}}
\newcommand{\cvec}{\bm{c}}
\newcommand{\relu}{\operatorname{relu}}
\newcommand{\softplus}{\operatorname{softplus}}
\newcommand{\sigmoid}{\operatorname{sigmoid}}

\title{Differentiable Support Flow Tensor Field as a Loss Term:\\
\large Formulation and CuraEngine Validation}
\author{InHwan Sul\\
\small Department of Materials Design Engineering, Kumoh National Institute of Technology,\\
\small Gumi 39177, Republic of Korea\\
\small Email: snowman0@kumoh.ac.kr \quad ORCID: 0000-0003-0105-920X}
\date{}

\begin{document}
\maketitle

\begin{abstract}
The Support Flow Tensor Field (SFTF) estimates support demand for a build direction by
casting rays from overhang faces to their supporting receiver faces or to the build
plate.  This discrete routing makes the original objective useful for sampling-based
orientation search but unsuitable as a gradient loss.  We replace the hard ray cast
with a soft attention over candidate receiver faces plus a build-plate slot, obtaining
a loss $L_{\mathrm{SFTF}}(V,\nvec)$ differentiable in both the build direction $\nvec$
and vertex coordinates $V$.  The relaxation converges to the weighted original SFTF
cost in the sharp-temperature limit, and its analytic gradient matches central finite
differences to relative error $3\times10^{-10}$.  The role of $L_{\mathrm{SFTF}}$ is
fidelity rather than prediction: it reproduces the prior SFTF objective differentiably,
while physical prediction is carried by \emph{gated} physics terms built with the same
relaxation machinery.  First, the slicer-gated support-height term $S_g$, activated at
the production slicer's own $60^\circ$ critical angle, reaches mean per-mesh Spearman
correlation $+0.80$ with the real support-only mass of legacy CuraEngine 15.04 (the
engine statically linked in 3DWOX Desktop; Sindoh DP103 PLA profile) on the headline
18-mesh subset of the g5test five-group benchmark, over 48 build directions ---
primitives, brackets, Thingi10k mechanical parts, and large organic scans up to 100k
faces --- positive on \emph{all} 18 (95\% CI $[+.74,+.84]$), substantially ahead of the
TomoNV voxel estimator ($+0.46$) and ungated SFTF variants ($+0.26$--$+0.39$).  A
hard-gate control isolates the source of this accuracy: replacing every smooth
ingredient of $S_g$ by its sharp limit --- a plain gated overhang-area$\times$height
sum with no tensor, no attention, and no relaxation --- tracks Cura slightly better
still ($+0.87$), while adding the tensor loss to the gated term lowers the correlation
to $+0.58$; prediction is carried by the slicer-gate physics alone, and the value of
the relaxation is confined to supplying gradients.
Second,
the same smooth gate carries vertex gradients $\partial L/\partial V$: with a single
untuned recipe, self-support shape optimization on 9 meshes removes $96$--$100\%$ of
the real Cura support mass on all 6 meshes that require support at $\nvec{=}+z$ (total
$14.2\to0.23$ g) --- a regime unreachable by sampling-based search in a design space
with tens of thousands of vertex degrees of freedom.  This second result, unlike the
first, is slicer-specific and we report it as such: re-slicing the identical geometry
with PrusaSlicer removes only $2.7\%$, because a facet-angle objective is free to meet
the build plate at a point, which zeroes the overhang but leaves a taller wedge of air
for the slicer to fill --- and two of the optimized meshes have no printable first
layer at all.  Sharpening the gate toward a step
function collapses this optimization (up to $25\times$ worse), showing that the smooth
gate is the source of usable gradients; a straight-through gate --- hard indicator
forward, sigmoid backward --- retains the soft gate's optimization performance
($98.0\%$ vs $98.4\%$ Cura support removal) while eliminating the gate's share of the
prediction bias.  The multi-mesh objective itself contains no
tensor term; adding the tensor changes nothing, and the tensor alone fails --- the
SFTF tensor drives neither headline.  The support-height term also strongly improves
cross-mesh generalization against TomoNV, rotationally degenerate optima are reported
as sets (point, circle, sphere), and a label-free amortized-inference proof of concept
(a graph neural network trained only on the differentiable loss) reaches mean
held-out-mesh support-mass percentile $0.28$ against the TomoNV reference (random
$0.41$, per-mesh oracle $0.13$) --- but shows no advantage on the decisive real-Cura
metric even in a GPU rerun including 50k--100k-face meshes, and is therefore reported
as a proof of concept only, not as a contribution.
\end{abstract}

\noindent\textbf{Keywords:} additive manufacturing; build orientation; support
structure; differentiable optimization; CuraEngine; support flow tensor field.

\section{Introduction}

Build orientation strongly affects support material, surface quality, print time, and
post-processing effort in additive manufacturing.  Existing orientation methods often
evaluate many sampled directions and select a low-support candidate after geometric,
voxel, or slicer analysis.  The original SFTF follows this pattern: for a direction
$\nvec$, each overhang face casts a ray opposite to $\nvec$ and is assigned either to a
receiver face or to the build plate; tensor and support-volume scores are then computed
from this directed support relation~\citep{sftf_engine}.  The method is interpretable
and fast as a candidate generator, but the receiver assignment is a hard visibility
decision.  As a result, the objective cannot directly drive gradient descent over
orientation, mesh vertices, or neural-network parameters.

This paper converts SFTF into a differentiable loss and asks a practical validation
question: does the resulting smooth objective predict the support material generated by
a real production slicer?  Earlier experiments used TomoNV as a solid voxel reference,
but TomoNV is still an estimator rather than the manufacturing toolchain that deposits
filament.  We therefore make the slicer comparison decisive: the final validation uses
legacy CuraEngine 15.04 with the Sindoh DP103 PLA profile, matching the 3DWOX toolpath
pipeline used in prior hand-checked experiments.

\subsection{Related Work}

\paragraph{Self-supporting shape and topology optimization.}
One way to reduce support is to design geometry that is self-supporting in the first
place.  Density- and boundary-based topology optimization imposes overhang-angle or
undercut constraints so that optimized parts print without sacrificial material
\citep{guo2017self,zhao2017self,kumar2022overhang,qian2017undercut}, and dedicated
additive-manufacturing filters embed the layer-by-layer printability rule directly into
the optimization loop \citep{langelaar2016selfsupp,langelaar2017filter}.  These methods
optimize a volumetric density field, usually at a fixed build direction.  Our loss
instead operates on a surface mesh and exposes gradients with respect to both the build
direction $\nvec$ and the vertices $V$ within a single objective (our shape-optimization
use is a proof of concept), and it is validated against real slicer support mass rather
than an overhang-angle proxy.

\paragraph{Build-orientation search and support-structure generation.}
Build orientation is a classical lever on support material, surface quality, and cost,
and has been optimized by discrete search over support volume, surface accessibility, or
perceptual saliency \citep{ezair2015orientation,zhang2015perceptual,mirzendehdel2021build},
with recent reviews cataloguing the objectives and search strategies involved
\citep{diangelo2020review}.  A complementary line reduces support at a fixed orientation
by generating economical scaffoldings rather than reorienting the part
\citep{vanek2014clever,dumas2014scaffold,jiang2018review}.  The original SFTF
\citep{sftf_engine} belongs to the orientation-search family: it scores a direction by a
per-face ray cast to receiver faces or the plate.  All of these evaluate many sampled
directions and pick a low-support candidate; the objective is not differentiable and
cannot itself drive gradient descent over orientation or geometry.

\paragraph{Differentiable and neural additive manufacturing.}
Learning-based work co-optimizes build direction, part segmentation, and topology with
neural networks \citep{chen2023concurrent} or learns differentiable curved-layer slicing
fields for multi-axis printing \citep{neuralslicer2024}, while mesh-native networks
supply a representation for such predictors \citep{hanocka2019meshcnn}.  These design
\emph{new} differentiable surrogates; we instead differentiate an existing,
physically-motivated SFTF cost with minimal change, so the same loss can also act as a
label-free physics term for mesh predictors.

\paragraph{Soft relaxation of discrete operators.}
Relaxing a hard, non-differentiable operator into a soft probabilistic one to recover
gradients is the central idea of differentiable rendering: soft rasterizers replace hard
rasterization and $z$-buffer visibility with a probabilistic aggregation over faces
\citep{softras2019,kato2018neural}, hardware-oriented and edge-sampling formulations
extend this to production pipelines and discontinuity handling
\citep{laine2020modular,loubet2019reparam}, and surveys map the design space
\citep{kato2020survey}.  Our soft receiver assignment applies the same principle to the
hard ray cast of SFTF (a receiver $\arg\min$ plus binary below/plate tests); to our
knowledge this is the first such relaxation applied directly to an additive-manufacturing
support-flow objective.

\subsection{Contribution}

We make four contributions.  First, a \textbf{slicer-gated differentiable support
objective}: the support-height term $S_g$, gated at the production slicer's own
$60^\circ$ threshold, predicts real Cura support-only mass at mean per-mesh Spearman
$+0.80$ (positive on all 18 headline meshes of the g5test benchmark, from primitives to
100k-face organic scans), well ahead of the TomoNV voxel estimator ($+0.46$).  A
hard-gate control ($S_g^{\mathrm{hard}}$, the sharp limit of $S_g$: no tensor, no
attention, no relaxation) predicts slightly better still ($+0.87$), and adding
$L_{\mathrm{SFTF}}$ to $S_g$ hurts ($+0.58$) --- so the predictive value lies in the
slicer-gate physics, and the relaxation is what makes that physics optimizable.
We state the division of roles explicitly: $L_{\mathrm{SFTF}}$ is an SFTF-faithful
differentiable surrogate of the prior objective, not a support-mass predictor; physical
prediction belongs to the gated physics terms ($S$, $S_g$).  Second, the
\textbf{soft-attention relaxation framework}: we identify the hard ray-cast receiver
assignment as the only operation preventing differentiation under fixed mesh topology
and general-position assumptions, replace it with a soft attention over receiver faces
plus a bed slot, and prove convergence to the weighted hard objective in the sharp
limit; the sigmoid gate of $S_g$ is an instance of the same relaxation principle.
Third, \textbf{multi-mesh quantification of vertex-gradient shape optimization}: a
single untuned recipe removes $96$--$100\%$ of real Cura support mass on all 6
support-requiring meshes (of 9), and a gate-sharpness ablation shows the optimization
collapses in the hard-gate limit --- the smooth gate is what makes the gradients
usable; a straight-through gate (hard indicator forward, sigmoid backward) retains
the soft gate's optimization performance while removing the gate's share of the
prediction bias.  A tensor contrast confirms the removal owes nothing to the tensor: the
objective contains no tensor term, adding $L_{\mathrm{SFTF}}$ changes nothing, and the
tensor alone fails on the sphere.  Fourth, degenerate rotational optima are reported as sets (point, circle,
sphere) rather than arbitrary single directions, with proof-of-concept orientation
search.  (A label-free amortized-inference GNN experiment is deliberately \emph{not}
listed among the contributions: trained only on the loss, without direction labels, it
transfers on the TomoNV metric --- mean held-out-mesh support-mass percentile $0.28$
against $0.41$ for random and $0.13$ for a per-mesh gradient-descent oracle --- but
shows no advantage on the decisive real-Cura metric even when the leave-one-out set
includes 50k--100k-face meshes, and is reported only as a proof of concept.)  The intended use
is not to replace a final
slicer check, but to move much of the orientation and design search into a
differentiable inner loop before the expensive manufacturing-faithful evaluation is
invoked.

\section{Method}

\subsection{From Hard Routing to Soft Flow}\label{sec:softflow}

Let face $i$ have centroid $\cvec_i$, unit normal $\mvec_i$, and area $A_i$.  For build
direction $\nvec$, the hard SFTF cost uses the overhang factor
\begin{equation}
  O_i(\nvec)=\max(0,-\mvec_i\cdot\nvec)
\end{equation}
and routes face $i$ to a single receiver $t_i$ found by a ray cast, or to the build
plate.  The weighted hard objective can be written as
\begin{equation}
  J_w(\nvec)=w_R R(\nvec)+w_P P(\nvec)+w_B B(\nvec),
\end{equation}
where $R$ is the Rayleigh support-flow term, $P$ is face-to-face support volume, and
$B$ is the build-plate penalty.  Normals, centroids, areas, and heights are smooth
functions of $V$ away from degenerate triangles; the discontinuity is the choice of
$t_i$.

For each source face $i$ we therefore define a finite candidate receiver set
$\mathcal C(i)$ and assign unnormalized compatibility
\begin{equation}
  a_{ij}=
  \sigmoid\!\left(\frac{h_{ij}}{\tau_b D}\right)
  \exp\!\left(-\frac{d_{ij}^2}{2(\sigma_\ell D)^2}\right)
  \sigmoid\!\left(\frac{\mvec_j\cdot\nvec-\tau_r}{\epsilon_r}\right)
  \exp\!\left(-\frac{\beta_n}{D}\relu(h_{ij})\right),
\end{equation}
where $D$ is the mesh scale, $h_{ij}=(\cvec_i-\cvec_j)\cdot\nvec$ is vertical
separation, and $d_{ij}$ is lateral distance to the build ray.  A bed slot with weight
$a_0$ handles direct plate support:
\begin{equation}
  \pi_{ij}=\frac{a_{ij}}{\sum_{k\in\mathcal C(i)}a_{ik}+a_0},
  \qquad
  \pi_i^{\mathrm{bed}}=\frac{a_0}{\sum_{k\in\mathcal C(i)}a_{ik}+a_0}.
\end{equation}
The differentiable loss is the soft counterpart of $J_w$:
\begin{equation}
  L_{\mathrm{SFTF}}(V,\nvec)=w_R\tilde R_{\mathrm{face}}+
  w_P\tilde P+w_B\tilde B .
  \label{eq:loss}
\end{equation}
Here $\tilde P$ and $\tilde B$ replace the hard receiver/bed decision by the
probabilities $\pi_{ij}$ and $\pi_i^{\mathrm{bed}}$, while
$\tilde R_{\mathrm{face}}$ contracts the soft support-flow tensor with $\nvec$ and uses
a softplus in place of the final positive part.  As the temperature parameters sharpen,
$\pi_{ij}$ concentrates on the affinity-maximizing candidate; whenever this maximizer
coincides with the hard receiver $t_i$ --- a geometric condition that holds on the
meshes used here but can fail in adversarial configurations
(Section~\ref{sec:centroid-limit}) --- $L_{\mathrm{SFTF}}\rightarrow J_w$.  Only three operations differ from the
original hard SFTF: the overhang factor $\max(0,\cdot)$ and the Rayleigh positive part
become $\softplus_\beta$, and the discrete receiver $\arg\min$ (with its below-source and
bed-versus-face tests) becomes the soft attention $\pi_{ij}$; every other quantity ---
areas, normals, height weighting, and the tensor algebra --- is shared verbatim with the
original, so, under the receiver-agreement condition of
Section~\ref{sec:centroid-limit}, the differentiable version adds gradients without
changing the support relation it converges to.
In implementation, the candidate set is built geometrically and evaluated in chunks, so
the method avoids materializing the full face-to-face matrix on high-resolution meshes.
The relaxation does not remove all modeling choices: the candidate radius, bed prior,
and temperature schedule control how quickly the soft assignment becomes a hard support
relation.  We keep these parameters fixed in the reported experiments and validate the
resulting objective externally with CuraEngine rather than tuning them per mesh.

\begin{figure}[H]
\centering
\includegraphics[width=0.82\linewidth]{diff_sftf_relaxation.png}
\caption{Differentiable relaxation of SFTF.  The soft receiver assignment converges to
the hard SFTF objective as the attention sharpens whenever the sharpened attention
selects the ray-cast receiver (Section~\ref{sec:centroid-limit}), while retaining
gradients with respect to both build direction and vertex coordinates.}
\label{fig:relaxation}
\end{figure}

\subsection{Support-Height Term and Slicer Gate}

The tensor loss preserves the structure of SFTF, but physical support mass depends
strongly on overhang height.  We add
\begin{equation}
  S(V,\nvec)=\sum_i \tilde O_i A_i \eta_i,\qquad
  \eta_i=\cvec_i\cdot\nvec-z_{\mathrm{plate}}(\nvec),
  \label{eq:supvol}
\end{equation}
where $\tilde O_i$ is a soft overhang factor and $z_{\mathrm{plate}}$ is a soft minimum
of vertex heights.  Against TomoNV, this term improves leave-one-mesh-out (LOMO)
generalization from about $+0.17$ for the original soft loss to $+0.61$ for
$L_{\mathrm{SFTF}}+\lambda_S S$.

For a production slicer, however, not every negative normal contributes support: the
slicer first applies its critical-angle rule.  The Cura/DP103 profile uses a
$60^\circ$ support angle, measured consistently with the TomoNV DLL and Cura's
\texttt{support\_angle}.  We therefore define
\begin{equation}
  S_g(V,\nvec)=\sum_i
  \sigmoid\!\left(\frac{-\mvec_i\cdot\nvec-\sin60^\circ}{\epsilon_g}\right)
  A_i\eta_i ,
  \label{eq:slicer-gate}
\end{equation}
so only true slicer overhangs receive support-height weight.  The final orientation
objective used for slicer-faithful validation is
$L_{\mathrm{SFTF}}+\lambda_g S_g$.

\paragraph{Gate functional forms and the straight-through (STE) variant.}
The critical-angle gate in Eq.~\eqref{eq:slicer-gate} is a sigmoid by default, but the
implementation keeps the functional form exchangeable
(\texttt{SFTFConfig.gate\_mode}): the sigmoid; a $C^1$ smoothstep that is exactly
$0/1$ outside a band $[t\pm d]$ around the threshold $t=\sin\theta_c$; and a
\textbf{straight-through estimator} (STE)~\citep{bengio2013ste}.  The STE gate is the
one-liner
$g_{\mathrm{ste}}=g_{\mathrm{soft}}+\mathrm{stopgrad}(g_{\mathrm{hard}}-g_{\mathrm{soft}})$:
the forward pass (values) uses the hard indicator $g_{\mathrm{hard}}=\mathbf 1[x>t]$,
$x=-\mvec\cdot\nvec$, and only the backward pass routes the sigmoid's gradient through
--- the standard device for training binary (quantized) neural networks.  We state its
character explicitly: the STE backward pass is a \emph{surrogate gradient}, not the
true derivative of the forward function --- the indicator's derivative is zero almost
everywhere, so STE deliberately supplies a biased gradient to keep optimization
moving.  Consequently, the finite-difference-versus-analytic gradient agreement
reported in the results applies only to the smooth (sigmoid or smoothstep) gate
configurations; it does not hold for the STE configuration and is not meant to ---
the STE gate is validated by its optimization outcome instead (the gate-prescription
paragraph of the results section).  Two further compact-support variants are provided.
A $C^2$ \emph{smootherstep} (the quintic $6u^5-15u^4+10u^3$, $u\!=\!\mathrm{clamp}((x-(t-d))/2d,0,1)$,
whose first \emph{and} second derivatives vanish at both band edges) is the
smooth-forward counterpart of the $C^1$ smoothstep; and a \emph{compact-backward} STE
(\texttt{ste\_smooth}) keeps the hard forward but replaces the sigmoid surrogate with the
smootherstep derivative, so the surrogate gradient is nonzero only inside the band
$[t\pm d]$.  As shown in the gate-prescription paragraph, this compact surrogate is
better \emph{aligned} with the hard descent direction when a direction already lies in
the band, but is exactly zero outside it and can therefore stall from a cold start; the
plain sigmoid-backward STE remains the robust default.

\subsection{Optimization Uses}

The same loss supports three optimization modes.  With $V$ fixed, gradients on
$\nvec$ drive build-orientation search on the sphere.  With $\nvec$ fixed, gradients on
$V$ reshape a model toward self-supporting geometry.  When embedded in a learning
pipeline, the loss provides a label-free physics term for predicted orientations or
generated shapes.

\section{Evaluation Protocol and Datasets}

\subsection{Datasets and Implementation}

The core numerical checks use synthetic meshes for controlled gradient and convergence
tests.  TomoNV-stage comparisons use watertight benchmark shapes as an intermediate
voxel estimator~\citep{msst,tomonv}.  Mesh identities follow the same g5test five-group
benchmark (A basic shapes, B simple functional parts, C organic scans, D Thingi10k
set~1, E Thingi10k set~2 large meshes) as the base SFTF study~\citep{sftf_engine} and
its companion SFTFCluster; Table~\ref{tab:coverage-g5} (Appendix~\ref{app:coverage})
lists which subset each experiment uses.  The decisive slicer validation uses a headline 18 meshes
--- a core set of 8 (cylinder, cone, torus, U-bracket, hook, c-clamp, pipe-elbow,
Stanford Bunny) plus 10 more: large organic scans (manikin, dragon 100k faces, Happy
Buddha 50k, Lucy 50k, Nefertiti 100k, liver 19k, kidney 12k) and three Thingi10k
mechanical parts --- reported alongside three A/B shapes (cube, sphere, hollow box)
whose landscapes are degenerate for rank validation (21 meshes total in
Table~\ref{tab:cura}).  The E group ($5{\times}10^{5}$--$10^{6}$ faces) exceeds the
all-pairs $O(F^2)$ receiver set and enters only through the fixed decimation of
Appendix~\ref{app:mesh-mg}.  Each mesh is evaluated over the same 48 Fibonacci build
directions.  Meshes are rotated so
the candidate build direction maps to $+z$, then sliced headlessly by legacy
CuraEngine 15.04 under the Sindoh DP103 PLA profile: line support, $60^\circ$ overhang
threshold, 20\% support density, 15\% line infill, and no raft.

Support-only material is extracted from generated G-code by summing extrusion inside
regions whose \texttt{;TYPE:} comment contains SUPPORT.  Extrusion is measured by a
high-water mark on absolute $E$ coordinates, which prevents retraction re-prime moves
from being double-counted.  Filament length is converted to volume and grams using PLA
density $1.21$ g/cm$^3$.  This engine reproduces the earlier 3DWOX/DP103 hand-measured
Bunny grid at Spearman approximately $0.99$, so the comparison is to the real
production toolchain rather than to an unrelated slicer.

\subsection{Comparison Targets}

We compare TomoNV, $L_{\mathrm{SFTF}}$, $L_{\mathrm{SFTF}}+S$, and the slicer-gated
term $S_g$.  The main metric is per-mesh Spearman rank correlation between each
predictor and real Cura support mass over 48 orientations; the reported mean and 95\%
confidence interval are computed over meshes by bootstrap resampling.  For end-to-end
orientation search, each objective is optimized and the selected direction is scored by
its percentile in the real Cura support-mass distribution, where 0 is the best
orientation among the 48 sampled directions.
We emphasize rank rather than absolute grams because the differentiable terms are
surrogates with arbitrary scale, whereas build-orientation selection depends on ordering
candidate directions.  The percentile check complements correlation: a method can rank
the full landscape imperfectly but still steer the optimizer into a low-support basin,
or conversely correlate well while missing the best orientation.

\section{Results and Discussion}

\subsection{Differentiability and Intermediate TomoNV Check}

The soft loss behaves as intended.  On a synthetic shape, analytic gradients match
central finite differences to relative error $3\times10^{-10}$, and gradient descent
on $\nvec$ converges to the basin selected by brute-force spherical sampling.  The
sharp-temperature sweep in Fig.~\ref{fig:relaxation} shows convergence toward the hard
SFTF objective while preserving usable gradients before the limiting discontinuity.
This finite-difference agreement is a statement about the smooth (sigmoid or
smoothstep) gate configurations; the STE gate uses a surrogate gradient that is by
design not the derivative of its forward pass, so it is excluded from this check and
validated by its optimization outcome instead (Method, gate functional forms).

TomoNV is useful as an intermediate physical estimator, but not as the final arbiter.
The original soft tensor loss correlates only loosely with TomoNV support mass; adding
the support-height term $S$ raises LOMO correlation from $+0.17$ to $+0.61$, matching
or exceeding the fitted ridge, gradient-boosted, and MLP baselines used in the internal ablation.
This confirms that support height is the missing physical signal.  It also explains
why the slicer-gated variant is necessary: real slicers do not score every smooth
overhang continuously; they first apply a threshold.

\subsection{CuraEngine Validation}

Table~\ref{tab:cura} is the central result.  The gated term $S_g$, using the slicer's
own $60^\circ$ threshold, reaches a mean Spearman correlation of $+0.80$ with real
Cura support-only mass on the headline 18-mesh set, positive on every one of them,
with a bootstrap 95\% CI of $[+.74,+.84]$.  TomoNV reaches only $+0.46$, and
the ungated differentiable SFTF variants reach $+0.26$--$+0.39$.  The extension ---
large organic scans (manikin, dragon 100k, Happy Buddha, Lucy, \textbf{Nefertiti,
liver, kidney}) and three Thingi10k mechanical parts --- is itself all positive, and
the three organic scans added here (Nefertiti $+0.90$, liver $+0.82$, kidney $+0.80$)
strengthen rather than dilute the headline, showing the result is not confined to
primitives.  Figure~\ref{fig:g5landscape} is the \emph{qualitative} companion to this
quantitative ranking, spread over the whole benchmark: placing the three methods'
(yaw,\,pitch) support-cost landscapes side by side for each mesh makes it visible at a
glance that the hard-SFTF and differentiable-SFTFsoft landscapes almost coincide (the
consistency claim), whereas the physical predictor TomoNV often points to a different
basin.

\begin{figure}[p]
  \centering
  \includegraphics[width=\textwidth]{g5test_methods_landscape_grouped.png}
  \caption{\emph{Qualitative} comparison of the three build-orientation predictors
  across the entire g5test five-group benchmark (38 meshes).  Each mesh row is, from
  the left, \textbf{[input shape $\mid$ TomoNV physical support mass $\mid$ hard SFTF
  cost $J$ $\mid$ differentiable SFTFsoft loss $L$]}.  The three right panels are the
  support cost each method assigns, drawn as a landscape over the
  (yaw,\,pitch)$\in[0,360)^2$ grid in RdBu\_r (redder = costlier).  Because the three
  methods carry different units --- TomoNV in grams, the SFTF-family scores
  dimensionless --- \emph{each panel is self-scaled} (per-panel min--max); the figure
  therefore compares the \emph{shape} of each landscape (which orientations are judged
  good vs.\ bad), not absolute values.  The $\times\,1$--$5$ mark each method's
  \emph{top-five} predicted orientations, chosen to sit in \emph{distinct} basins by
  toroidal non-minimum suppression on the periodic (yaw,\,pitch) grid --- pick the
  global minimum, suppress a neighbourhood of radius ${\approx}$grid$/6$ (distances wrap
  around the $360^\circ$ boundary on both axes), repeat --- and numbered by rank, with
  $\times\,1$ the global minimum (rank 1); simply taking the five lowest cells would
  cluster them around the single global minimum instead of yielding five genuinely
  separate candidate orientations.  What the Spearman columns of
  Table~\ref{tab:cura} state numerically --- the strong agreement between hard $J$ and
  soft $L$, and the variable fidelity of the physical TomoNV --- is also legible in the
  terrain.  For rotationally degenerate shapes (A2 sphere) or large scans whose normals
  spread over all angles (part of Group E), the landscape is nearly flat, so
  self-scaling amplifies tiny variations into noise-like texture (cf.\ the ill-posed
  discussion in the text); those rows showing weak terrain contrast is expected.  This
  figure is a qualitative aid to the prediction accuracy; the quantitative conclusions
  are carried by Table~\ref{tab:cura}.}
  \label{fig:g5landscape}
\end{figure}

Three shapes added to complete the g5test A/B groups --- cube, sphere,
and hollow box --- are reported in the table but excluded from the headline because
rank validation is \emph{ill-posed} on them: the sphere's Cura landscape is flat
($0.6$--$0.7$ g across all orientations, within slicer quantization), so $S_g$
($-0.14$) and TomoNV ($-0.00$) alike are at noise; the cube is a 12-face
near-degenerate solid; and the hollow box's support is driven by an internal cavity
that surface-normal predictors (TomoNV included, $+0.17$) cannot see.  We report them
honestly without any gate or weight re-tuning (a project-wide rule); the full 21-mesh
mean is $S_g$ $+0.67$, with the degenerate cases treated in the symmetry study and
the shape-optimization limitations.  The TomoNV column was recomputed with a build of the
support-volume engine that fixes an integer-overflow defect; before the fix the TomoNV
correlation on the large organic scans (Bunny, manikin, dragon, Happy Buddha, Lucy) was
underestimated and the column mean read $+0.27$ (now $+0.38$).  The $S_g$ column, the
ungated variants, and the real-Cura reference are geometry- or slicer-derived and are
unaffected.

Three control columns in Table~\ref{tab:cura} isolate what drives this accuracy ---
in particular, whether the SFTF tensor or the relaxation machinery contributes to
prediction at all.  Adding the tensor loss to the gated term
($L_{\mathrm{SFTF}}{+}S_g$, equal-weight rank-space sum) \emph{lowers} the headline
mean correlation from $+0.80$ to $+0.58$ (Wilcoxon signed-rank $p=2\times10^{-5}$ over
the 18 paired per-mesh correlations): the tensor term does not sharpen the ranking of
real support mass, it dilutes the gated signal.  The hard-gate control
$S_g^{\mathrm{hard}}$ replaces every smooth ingredient of $S_g$ by its sharp limit ---
the softplus overhang and sigmoid gate by the exact indicator
$-\mvec_i\cdot\nvec>\sin60^\circ$, the soft-min plate height by the exact minimum ---
so it uses neither the tensor, nor receiver attention, nor any relaxation, and amounts
to a few lines of plain array arithmetic.  It predicts Cura slightly \emph{better}
than $S_g$ ($+0.87$ vs $+0.80$; paired per-mesh difference $-0.07$, Wilcoxon
$p=0.003$).  The prediction headline is therefore carried entirely by the slicer-gate
physics --- gated overhang area times height-to-plate --- and not by
differentiability, which costs about $0.07$ in mean rank fidelity.  Neither $S_g$ nor $S_g^{\mathrm{hard}}$ contains a fitted parameter
($\theta_c$ is read from the target profile), so this comparison involves no training
and needs no held-out split.  What the relaxation buys is not accuracy but
\emph{gradients}: $S_g^{\mathrm{hard}}$ is a step-gated sum that cannot drive the
orientation and shape optimization that follows, and the gate-sharpness ablation below
shows the optimization collapsing exactly in that hard limit.  The role of the smooth
machinery --- and of $L_{\mathrm{SFTF}}$ itself --- is optimization and fidelity to
the prior SFTF objective, not prediction.

\textbf{Decomposing the gap, and the $S_g^{\mathrm{ste}}$ column.}  The $0.07$ gap in
favor of the hard gate can be decomposed by ingredient.  Isolating the gate axis
first, two mechanisms emerge.  (i) \emph{Blur}: at sharpness $24$ the sigmoid's
$10$--$90\%$ transition width in cos-space ($-\mvec\cdot\nvec$) is ${\approx}0.18$,
which at $\theta_c{=}60^\circ$ (where $d\sin\theta/d\theta=\cos60^\circ=0.5$)
corresponds to an ambiguity band of about $21^\circ$ of angle.  Mechanical parts
consist of a few large planar patches that frequently straddle the threshold
wholesale, so these partial scores decide the ranking; organic scans spread their
normals over all angles and average the error out.  (ii) \emph{Leakage}: the sigmoid
is nowhere exactly zero, so the many directions whose true support is exactly $0$ g
($15$--$22$ of 48 on near-self-supporting shapes) receive spurious partial scores
that randomize their tied ranks.  Sweeping only the gate $g$ on the
$S_g^{\mathrm{hard}}$ skeleton $\sum_i g(-\mvec_i\cdot\nvec)\,A_i\,\eta_i$ (same
cached Cura landscapes) confirms this: the organic scans are flat
at $+0.88$--$+0.89$ under every gate, whereas the four $L_{\mathrm{SFTF}}$ failure
cases (cylinder, cone, D5, D9) read sigmoid $+0.82$ versus hard $+0.93$, and a $C^1$
smoothstep gate that is exactly $0/1$ outside $\pm0.02$--$0.05$ removes both
mechanisms, recovering the failure subset to hard-level accuracy
($+0.90$--$+0.93$) while retaining a $3$--$8^\circ$ gradient band.  The gate is not
the whole gap, however.  The $S_g^{\mathrm{ste}}$ column of Table~\ref{tab:cura}
swaps \emph{only the gate} of the full $S_g$ for the straight-through gate defined in
the Method section (hard indicator forward, sigmoid backward) --- a gate-only-hard
variant --- and lands at headline mean $+0.78$: statistically indistinguishable from
$S_g$ ($+0.80$; paired per-mesh difference $-0.02$, Wilcoxon $p=0.09$) and still below
$S_g^{\mathrm{hard}}$ ($+0.87$; paired difference $-0.09$, $p=8\times10^{-6}$).
Since $S_g^{\mathrm{ste}}$ and $S_g^{\mathrm{hard}}$ share the same forward gate
(both exact indicators), this $-0.09$ is carried entirely by the \emph{non-gate}
relaxations of $S_g$ --- the softplus overhang-magnitude weight and the soft-min
plate height.  A further control fixes the blame: the skeleton with hard gate,
\emph{exact} overhang magnitude, and exact plate height,
$\sum_i \mathbf 1[\cdot]\,\max(0,-\mvec_i\cdot\nvec)\,A_i\,\eta_i$, scores $+0.87$,
identical to $S_g^{\mathrm{hard}}$ --- the magnitude factor itself is harmless; what
costs accuracy is its \emph{relaxation} (the softplus's residual bias and the
direction-dependent offset that the soft-min adds to $\eta$).  The prescription
therefore splits by role: for \emph{evaluation and ranking} no relaxation is needed
at all --- use $S_g^{\mathrm{hard}}$; for the gate \emph{inside a differentiable
objective}, STE removes the gate-axis bias at no optimization cost (the
gate-prescription paragraph below).

\begin{table}[H]
\centering
\caption{Per-mesh Spearman rank correlation with real Cura support-only mass
(legacy CuraEngine 15.04 / Sindoh DP103 PLA; g5test five-group benchmark, 48
directions.  Top: 8 core primitives/brackets; middle: 10 large organic scans and
Thingi10k mechanical parts --- these 18 are the headline set; bottom block: 3
degenerate/internal-cavity shapes).
The three rightmost columns are controls:
$L_{\mathrm{SFTF}}{+}S_g$ adds the tensor loss to the gated term (equal-weight
rank-space sum) and \emph{lowers} the mean to $+0.58$; $S_g^{\mathrm{ste}}$ swaps
\emph{only the gate} of the full $S_g$ for a straight-through gate (hard indicator
forward, sigmoid backward) and stays at $S_g$'s level ($+0.78$); and the hard-gate
control $S_g^{\mathrm{hard}}$ --- every smooth ingredient of $S_g$ replaced by its
sharp limit; no tensor, no attention, no relaxation --- is slightly \emph{higher}
($+0.87$).  The difference between $S_g^{\mathrm{ste}}$ and $S_g^{\mathrm{hard}}$
($-0.09$) is the share of the non-gate relaxations (softplus overhang magnitude,
soft-min plate height).  Mesh identities follow the g5test five-group benchmark of
the base SFTF study; the top 18 (core primitives/brackets, organic scans, three
Thingi10k parts) form the headline set where rank validation is well-posed, and the
bottom block of three (cube, sphere, hollow box) is shown for transparency but is
excluded from the headline: their Cura landscapes are degenerate --- the sphere's is
\emph{flat} ($0.6$--$0.7$ g regardless of orientation, by rotational symmetry), so
\emph{every} predictor including TomoNV is at noise, and the internal cavity of the
hollow box is invisible to surface-normal predictors.  The two mean rows are the
headline 18 and the full 21.}
\label{tab:cura}
\small
\begin{tabular}{lrrrrrrrr}
\toprule
mesh & Cura mass [g] & TomoNV & $L_{\mathrm{SFTF}}$ &
$L_{\mathrm{SFTF}}{+}S$ & $L_{\mathrm{SFTF}}{+}S_g$ & $S_g$ & $S_g^{\mathrm{ste}}$ & $S_g^{\mathrm{hard}}$ \\
\midrule
cylinder    & $0.0$--$10.2$ & $-0.20$ & $-0.63$ & $-0.59$ & $+0.44$ & $+0.87$ & $+0.92$ & $+0.98$ \\
cone        & $0.0$--$10.1$ & $-0.42$ & $+0.03$ & $-0.18$ & $+0.51$ & $+0.86$ & $+0.96$ & $+0.98$ \\
torus       & $2.6$--$6.5$  & $+0.86$ & $+0.37$ & $+0.74$ & $+0.79$ & $+0.86$ & $+0.76$ & $+0.82$ \\
U-bracket   & $0.0$--$55.7$ & $-0.45$ & $+0.32$ & $+0.31$ & $+0.52$ & $+0.66$ & $+0.48$ & $+0.48$ \\
hook        & $0.1$--$7.1$  & $+0.78$ & $+0.31$ & $+0.58$ & $+0.66$ & $+0.84$ & $+0.83$ & $+0.91$ \\
c-clamp     & $0.0$--$29.5$ & $-0.40$ & $+0.23$ & $+0.13$ & $+0.52$ & $+0.77$ & $+0.76$ & $+0.76$ \\
pipe-elbow  & $0.0$--$13.8$ & $+0.95$ & $+0.22$ & $+0.53$ & $+0.61$ & $+0.97$ & $+0.98$ & $+0.99$ \\
Bunny       & $2.0$--$14.8$ & $+0.89$ & $+0.14$ & $+0.50$ & $+0.50$ & $+0.85$ & $+0.84$ & $+0.94$ \\
\midrule
manikin     & $1.2$--$6.2$  & $+0.82$ & $+0.54$ & $+0.67$ & $+0.70$ & $+0.82$ & $+0.82$ & $+0.91$ \\
dragon 100k & $4.3$--$19.2$ & $+0.75$ & $+0.56$ & $+0.64$ & $+0.65$ & $+0.60$ & $+0.58$ & $+0.64$ \\
Happy Buddha 50k & $3.8$--$18.7$ & $+0.64$ & $+0.53$ & $+0.69$ & $+0.64$ & $+0.67$ & $+0.55$ & $+0.73$ \\
Lucy 50k    & $2.3$--$16.9$ & $+0.87$ & $+0.56$ & $+0.76$ & $+0.72$ & $+0.90$ & $+0.87$ & $+0.96$ \\
Nefertiti 100k & $1.4$--$12.4$ & $+0.86$ & $-0.02$ & $+0.35$ & $+0.56$ & $+0.90$ & $+0.86$ & $+0.98$ \\
liver 19k   & $0.4$--$16.0$ & $+0.90$ & $+0.27$ & $+0.47$ & $+0.58$ & $+0.82$ & $+0.78$ & $+0.97$ \\
kidney 12k  & $0.2$--$5.7$  & $+0.91$ & $+0.58$ & $+0.65$ & $+0.71$ & $+0.80$ & $+0.79$ & $+0.95$ \\
Thingi-D1 (37009) & $0.1$--$11.7$ & $+0.01$ & $+0.67$ & $+0.73$ & $+0.72$ & $+0.77$ & $+0.75$ & $+0.86$ \\
Thingi-D5 (37095) & $0.0$--$27.2$ & $-0.35$ & $+0.01$ & $+0.00$ & $+0.26$ & $+0.84$ & $+0.94$ & $+0.94$ \\
Thingi-D9 (37415) & $4.3$--$14.6$ & $+0.87$ & $+0.06$ & $+0.13$ & $+0.29$ & $+0.53$ & $+0.51$ & $+0.80$ \\
\midrule
\textbf{mean (18, headline)} & & $+0.46$ & $+0.26$ & $+0.39$ & $+0.58$ & $\mathbf{+0.80}$ & $+0.78$ & $+0.87$ \\
95\% CI & & $[+.20,+.70]$ & $[+.12,+.39]$ & $[+.22,+.55]$ & $[+.51,+.64]$ &
$[\mathbf{+.74,+.84}]$ & $[+.71,+.84]$ & $[+.80,+.92]$ \\
\midrule
\multicolumn{9}{l}{\footnotesize\emph{degenerate / internal-cavity shapes (rank ill-posed; excluded from headline --- see symmetry study and limitations)}}\\
cube        & $0.0$--$52.3$ & $+0.22$ & $+0.48$ & $+0.48$ & $+0.32$ & $-0.11$ & $-0.15$ & $-0.15$ \\
sphere (flat) & $0.6$--$0.7$ & $-0.00$ & $-0.14$ & $-0.14$ & $-0.14$ & $-0.14$ & $-0.13$ & $+0.04$ \\
hollow box  & $0.0$--$50.0$ & $+0.17$ & $+0.09$ & $+0.11$ & $+0.09$ & $+0.02$ & $-0.00$ & $-0.00$ \\
\midrule
mean (21, full) & & $+0.41$ & $+0.25$ & $+0.36$ & $+0.51$ & $+0.67$ & $+0.65$ & $+0.74$ \\
95\% CI & & $[+.18,+.63]$ & $[+.11,+.37]$ & $[+.20,+.50]$ & $[+.40,+.60]$ &
$[+.52,+.80]$ & $[+.50,+.78]$ & $[+.58,+.87]$ \\
\bottomrule
\end{tabular}
\end{table}

\begin{figure}[H]
\centering
\includegraphics[width=0.49\linewidth]{demo_sftf_vs_slicer.png}\hfill
\includegraphics[width=0.49\linewidth]{demo_sftf_slicer_opt.png}
\caption{Validation against legacy CuraEngine 15.04 / DP103 PLA.  Left: correlation
with real support-only mass.  Right: percentile of the selected orientation in real
Cura support mass, where lower is better.}
\label{fig:slicer}
\end{figure}

The result is driven by the gate, not by weight fitting alone.  Near-self-supporting
shapes such as the cylinder, cone, U-bracket, and c-clamp contain many orientations
with approximately zero support.  Ungated smooth terms rank these weakly and can even
anti-correlate with the slicer.  Gating at the slicer's threshold raises Cura agreement
by about $+0.45$--$+0.74$ on those cases while lowering agreement with TomoNV, which is
expected: the gated term is matching Cura's rule, whereas the ungated term remains
closer to the voxel estimator.  End-to-end optimization follows the same pattern:
$L_{\mathrm{SFTF}}+S_g$ gives mean Cura support-mass percentile $0.232$ on the 8-mesh
core set, improving on
plain $L_{\mathrm{SFTF}}$ ($0.242$) and ungated $L_{\mathrm{SFTF}}+S$ ($0.240$).

The gate angle $\theta_c$ is not a fitted constant but a parameter \emph{read from}
the target slicer profile: DP103 sets it to $60^\circ$, and porting to another profile
means re-gating at that profile's own overhang threshold rather than retuning the loss.
This convention of adopting the target profile's angle is shared across the author's
SFTF manuscript series; the companion SFTFCluster study targets a generic FDM profile
and accordingly gates at $45^\circ$.
To show that the agreement is not brittle to this value, we re-gate $S_g$ at
$\theta_c\in\{45,50,55,60\}^\circ$ while holding the Cura reference fixed at the DP103
$60^\circ$ profile (Fig.~\ref{fig:thetac}).  The mean per-mesh Spearman is $+0.79$ at
both $55^\circ$ and $60^\circ$, $+0.77$ at $50^\circ$, and still $+0.71$ at $45^\circ$
--- a $15^\circ$ mismatch --- in every case far above TomoNV ($+0.38$) and the ungated
variants ($+0.26$--$+0.40$).  The mild degradation is concentrated in near-self-supporting
primitives whose ranking signal lives right at the threshold (cylinder
$+0.87\to+0.21$, c-clamp $+0.77\to+0.49$ as $\theta_c$ moves from $60^\circ$ to
$45^\circ$), whereas the organic scans are essentially flat or even improve slightly
(Lucy $+0.90\to+0.94$, Bunny $+0.85\to+0.89$).  Adopting a new slicer profile therefore
requires only reading its overhang angle, and the predictor tolerates moderate
misspecification of that angle.

\begin{figure}[H]
\centering
\includegraphics[width=0.66\linewidth]{demo_sftf_thetac_sensitivity.png}
\caption{Gate-angle sensitivity of $S_g$ (15 meshes, 48 directions; the real Cura
reference stays fixed at the DP103 $60^\circ$ profile).  Gray lines are per-mesh
Spearman correlations, the green line is the mean with a bootstrap 95\% CI band, and
the dotted line marks the DP103 threshold.  Mean agreement is essentially unchanged for
a $\pm5^\circ$ change of $\theta_c$ and remains well above the TomoNV and ungated
baselines even at a $15^\circ$ mismatch.}
\label{fig:thetac}
\end{figure}

Beyond re-gating, we also check that the predictor transfers to a \emph{different
generation} of slicer.  We re-slice four meshes (torus, hook, pipe-elbow, Thingi D9)
over the \emph{same} 48 Fibonacci directions with the current \textbf{UltiMaker
CuraEngine 5.13} (default $0.4$ mm PLA, lines support, $60^\circ$ overhang) and measure
support mass.  $S_g$ predicts this modern slicer's per-direction support ranking at mean
Spearman $+0.68$ (torus, hook, pipe-elbow $+0.77$--$+0.84$; the mechanical part D9 is
weaker at $+0.33$, for the same reason it is on the legacy engine), and --- most
importantly --- the legacy (15.04) and modern (5.13) engines rank the directions almost
identically, at mean Spearman $+0.90$.  The DP103 / 15.04 validation is therefore not an
artifact of one legacy engine but physics that holds across slicer generations; adopting
a new profile or engine only requires re-gating at its overhang angle, empirically
supporting the portability argument above.

Since orientation search itself is only two-dimensional, one may ask whether gradients
pay for themselves \emph{within} this problem, or only in the high-dimensional regimes
discussed below.  We tested this directly with an equal-budget protocol: for a total
budget of $B$ objective evaluations ($B\in\{8,16,48\}$; a gradient step is charged as
one evaluation even though its backward pass roughly doubles the true cost, which
favors the gradient arm), pure Fibonacci sampling with $B$ evaluations is compared
against $B/2$ samples followed by $B/2$ Adam steps warm-started at the best sample.
Both arms rank directions with the same $L_{\mathrm{SFTF}}+S_g$ objective, and the
final direction chosen by each arm is sliced with the real Cura engine
(Fig.~\ref{fig:equalbudget}).  On mean percentile the two strategies are effectively
tied, with per-mesh wins on both sides ($0.41/0.33$, $0.32/0.39$, $0.31/0.32$ for
sampling/hybrid at $B{=}8/16/48$): the two-dimensional orientation landscape is indeed
sampling-friendly, as claimed.  In actual grams, however, the hybrid matches or beats
sampling at every budget and halves the mean excess support mass over the
48-direction oracle at $B{=}48$ ($3.16\to1.40$ g).  The gain comes from
near-degenerate shapes (cylinder, U-bracket, c-clamp) whose zero-support basins are
narrow enough that a fixed sample grid straddles them; the final $10$--$15^\circ$ of
local refinement walks into the basin.  Conversely, on meshes where the surrogate
minimum is offset from Cura's (cone, hook), refinement can drift slightly away.
Orientation search alone therefore does not \emph{require} gradients --- but at equal
budget they are not wasted either, and the decisive value of differentiability remains
in the vertex-space regime of Table~\ref{tab:shapeopt-multi}, which sampling cannot
reach.

\begin{figure}[H]
\centering
\includegraphics[width=0.88\linewidth]{demo_equal_budget.png}
\caption{Equal-budget orientation search (8 core meshes, objective
$L_{\mathrm{SFTF}}+S_g$).  For the same number of objective evaluations $B$, pure
Fibonacci sampling is compared with $B/2$ samples plus $B/2$ warm-started gradient
steps; the direction selected by each arm is sliced with legacy CuraEngine 15.04 /
DP103.  Left: mean percentile in the 48-direction real support-mass landscape
(0 = best) --- an effective tie.  Right: mean excess support mass over the
48-direction oracle --- the gradient arm matches or beats sampling at every budget and
halves the excess at $B{=}48$.}
\label{fig:equalbudget}
\end{figure}

Mesh resolution is therefore a fidelity variable, not only a speed knob.  The
support-volume term integrates per-face overhang and height, so decimation smooths away
part of the signal being summed.  On Bunny, raising the SFTF proxy from 6k to 50k faces
raises the support-volume correlation with Cura from $+0.58$ to $+0.83$
(Appendix~\ref{app:mesh-mg}).  This shows that the SFTF loss is not a
mesh-independent scalar; it depends on the overhang/height distribution preserved by
the surface discretization.  A decimated mesh should therefore be used to narrow
candidates in a coarse-to-fine search, not to replace the final physical evaluation.
In a Bunny 15k--30k--69k case study, a 15k top-4 $\to$ 30k top-2 $\to$ 69k top-2
schedule preserved the full-mesh best sampled direction and reduced a 24-direction
sweep by about $6.0\times$, while the 15k optimum alone was $43.7^\circ$ away from
the full optimum.

\input{crossslicer_transfer}

\subsection{Applications and Degenerate Optima}

Vertex gradients make the loss useful beyond orientation search.  In the shape
optimization experiment, a support-demanding model is deformed under
$\partial L_{\mathrm{SFTF}}/\partial V$ toward a lower-support geometry, and TomoNV/Cura
checks show the intended reduction in support material.  This is not proposed as a
complete structural optimizer; rather, it demonstrates that a support objective
previously usable only by sampling can now act as a local differentiable design signal.

\begin{figure}[H]
\centering
\includegraphics[width=0.88\linewidth]{demo_sftf_shapeopt_tomocpu_support.png}
\caption{Support-aware shape optimization driven by vertex gradients of the
differentiable SFTF loss.}
\label{fig:shapeopt}
\end{figure}

To show that this is not a one-off demo, we apply the \emph{same} recipe (scalable
$O(F)$ objective + surface-area preservation, $\theta_c{=}60^\circ$, 400 steps, no
per-mesh tuning) to 9 meshes and slice the geometry before and after deformation with
the \textbf{real production slicer} (legacy CuraEngine 15.04 / DP103) at
$\nvec{=}+z$ (Table~\ref{tab:shapeopt-multi}).  On \textbf{all 6 meshes} that require
support at $z$-up, real Cura support-only mass is removed by $96$--$100\%$ (total
$14.2\to0.23$ g).  A vertex design space with thousands to tens of thousands of degrees
of freedom is out of reach for sampling-based search, so this result is attainable only
through differentiability.  One low-resolution exception is reported honestly: on the
28-face U-bracket the TomoNV estimate increases ($0.24\to0.39$ g), a voxel-estimator
artifact at very coarse resolution --- the real Cura support is zero before and after.
The removal figures in this table are specific to CuraEngine and do not survive a
change of slicer; Section~\ref{sec:shapeopt-transfer-limit} re-slices the same
geometry with PrusaSlicer and delimits what the vertex gradients have and have not
achieved.

\begin{table}[H]
\centering
\caption{Multi-mesh quantification of vertex-gradient self-support shape optimization
($\nvec{=}+z$, $\theta_c{=}60^\circ$, scalable $O(F)$ objective + surface-area
preservation, 400 steps --- \emph{no per-mesh tuning}).  Overhang area is measured on
the unit-diagonal mesh; TomoNV is the voxel estimate; Cura is the \textbf{real
support-only mass} from legacy CuraEngine 15.04 / DP103.  Rows are split into the 6
meshes that need support at $z$-up (top; $96$--$100\%$ removal) and 3 no-support
controls (bottom; zero real support before and after).  The two rightmost columns are
tensor-contribution controls (final Cura mass after re-optimization): adding the
tensor loss to the objective (+tensor) changes nothing material, while the tensor
alone fails on the sphere ($0.88\to\mathbf{0.99}$ g) and degrades the torus and
Bunny.}
\label{tab:shapeopt-multi}
\small
\begin{tabular}{lrrrrrr}
\toprule
mesh & faces & overhang@$60^\circ$ & TomoNV [g] & Cura [g] &
\multicolumn{2}{c}{Cura after [g]} \\
 & & & & (objective) & +tensor & tensor only \\
\midrule
icosphere   & $1{,}280$  & $0.073\to0.000$ & $1.82\to0.04$ & $0.66\to\mathbf{0.00}$ & $0.00$ & $0.01$ \\
sphere      & $2{,}976$  & $0.062\to0.001$ & $1.80\to0.30$ & $0.88\to\mathbf{0.00}$ & $0.00$ & $\mathbf{0.99}$ \\
torus       & $2{,}304$  & $0.149\to0.000$ & $2.49\to0.62$ & $0.26\to\mathbf{0.00}$ & $0.00$ & $0.03$ \\
hook        & $1{,}560$  & $0.032\to0.000$ & $2.03\to0.46$ & $3.57\to\mathbf{0.00}$ & $0.00$ & $0.00$ \\
pipe-elbow  & $2{,}400$  & $0.113\to0.000$ & $6.27\to1.43$ & $6.39\to\mathbf{0.14}$ & $0.11$ & $0.16$ \\
Bunny       & $69{,}662$ & $0.106\to0.000$ & $3.21\to1.66$ & $2.47\to\mathbf{0.09}$ & $0.03$ & $0.26$ \\
\midrule
cone (no-support control)      & $96$ & $0.220\to0.000$ & $0.30\to0.13$ & $0.00\to0.00$ & $0.00$ & $0.00$ \\
U-bracket (no-support control) & $28$ & $0.228\to0.000$ & $0.24\to0.39$ & $0.00\to0.00$ & $0.00$ & $0.00$ \\
c-clamp (no-support control)   & $28$ & $0.350\to0.000$ & $0.24\to0.24$ & $0.00\to0.00$ & $0.00$ & $0.00$ \\
\bottomrule
\end{tabular}
\end{table}

The recipe behind Table~\ref{tab:shapeopt-multi} is itself a statement about the
tensor: the scalable $O(F)$ objective is the gated overhang-area$\times$height sum ---
the shape-side counterpart of $S_g$ --- and contains no tensor term.  The two control
columns quantify what the tensor would add.  Re-optimizing all 9 meshes with the
tensor loss $L_{\mathrm{SFTF}}$ added at equal weight changes nothing material: every
support-requiring mesh stays in the $96$--$100\%$ removal band (total residual $0.23$
vs $0.14$ g).  Re-optimizing with the tensor loss alone is not sufficient: the sphere
fails outright ($0.88\to0.99$ g), and the torus and Bunny fall to $88$--$90\%$ removal
(total residual $1.45$ g).  Together with the prediction controls of
Table~\ref{tab:cura}, this completes the role assignment with data: the SFTF tensor
drives neither the prediction headline nor the shape-optimization headline --- both
are carried by the gated support-height physics --- and its role is the
differentiable, SFTF-faithful reproduction of the prior objective.  (The tensor-only
run still shares the smooth overhang gate, so its partial success is consistent with
the ablation below: what supplies usable vertex gradients is the gate's smoothness,
not the tensor structure.)

A gate-sharpness ablation addresses the natural objection that ``the term that works
($S_g$) hardly needs differentiability.''  Sweeping the sigmoid gate sharpness
$k=8\to24\to96\to384\to6144$ (toward the step-function limit) and repeating the same
shape optimization, the soft settings ($k{=}8$--$24$) remove the overhang completely
and converge stably to the lowest TomoNV mass (sphere: $0.04$ g), whereas from
$k{\ge}96$ residual overhang persists and the outcome destabilizes, ending up to
$25\times$ worse on the sphere ($0.90$ g; the torus shows the same trend).  A hard gate
kills the gradient signal away from the threshold, turning the vertex signal into
noise.  The value of $S_g$ is therefore not the overhang-times-drop-height expression
itself but its \emph{smooth} gate --- exactly the relaxation machinery of this paper.

\paragraph{Gate prescription: a straight-through gate serves both prediction and
optimization.}  The ablation above, combined with the hard-gate advantage in
Table~\ref{tab:cura}, leaves a practical dilemma: \emph{prediction} (rank fidelity)
favors a sharp gate, while \emph{optimization} (gradients) requires a soft one.  The
prescription that resolves the optimization side is the \textbf{straight-through
estimator} (STE) gate defined in the Method section --- hard indicator forward, the
sigmoid's surrogate gradient backward~\citep{bengio2013ste}.  Re-running the 9-mesh
batch protocol of Table~\ref{tab:shapeopt-multi} with only the gate swapped, the total
real-Cura residual on the 6 support-requiring meshes is $0.23$ g for the paper's
sigmoid $k{=}24$ recipe ($98.4\%$ removal) versus $0.28$ g for STE ($98.0\%$) ---
effectively equivalent --- whereas the pure hard gate collapses to $7.26$ g ($49\%$
removal) and even degrades two of the no-support controls.  Static compact-support
smoothstep gates ($\pm0.02$--$0.05$) land in between ($0.59$--$0.68$ g,
$95$--$96\%$).  On the prediction side the STE forward pass removes the gate-axis
bias (blur and leakage), and on the $A_i\eta_i$ skeleton it scores the same as the
hard gate; plugged into the \emph{full} $S_g$ predictor, however, the remaining
relaxations (softplus overhang magnitude, soft-min plate height) still carry the rest
of the gap, so $S_g^{\mathrm{ste}}$ reaches $+0.78$, not $S_g^{\mathrm{hard}}$'s
$+0.87$ (Table~\ref{tab:cura} and the gap-decomposition discussion above).  In short:
for evaluation and ranking use the fully hard $S_g^{\mathrm{hard}}$ (no relaxation is
needed there at all); for the gate inside a differentiable objective, use STE --- it
removes the gate-axis prediction bias at no optimization cost.

The STE backward pass admits a further choice, and it is a genuine trade-off rather than
a strict improvement.  Because the STE forward is the hard indicator, the ranking is
identical whatever surrogate is used; the surrogate only shapes the optimization.
Replacing the sigmoid surrogate with a compact $C^2$ smootherstep derivative
(\texttt{ste\_smooth}) raises the per-step alignment between the surrogate gradient and a
hard finite-difference reference on the mechanical parts (mean cosine $0.52$ vs.\ $0.35$
for the sigmoid backward, over cylinder/cone/U-bracket/pipe-elbow and a Thingi10k part),
but the compact surrogate is exactly zero outside the band $[t\pm d]$ and stalls from
directions that start far from the critical angle: under a tight single-start,
$20$-step budget it reaches a \emph{worse} orientation than the sigmoid-backward STE
(normalized hard-support $0.272$ vs.\ $0.247$), while a generous multi-start budget
erases the difference (all gate variants reach the global optimum).  The compact backward
is therefore a double-edged refinement --- sharper where it is active, blind where it is
not --- so the \emph{sigmoid-backward} STE is the robust default for cold-start
orientation search; the compact variant is worthwhile only near the solution, or under a
broad-to-compact anneal of the band width $d$ (start wide, sharpen as the design settles).

\paragraph{Limitations of the shape-optimization demonstration.}
We state explicitly that the shape optimization in this paper is a \emph{geometry-only}
proof of concept.  The objective sees only support-related geometric quantities ---
overhang strength, drop height, and surface-area preservation.  It contains no
structural response (stress or stiffness), no minimum printable wall thickness, no
assembly tolerances, and no other manufacturability or functional constraints, all of
which restrict shape in real part design.  The results in
Table~\ref{tab:shapeopt-multi} are therefore evidence that vertex gradients can move a
shape toward genuinely lower real-slicer support, not finished part designs.  The
natural next step is to combine the loss with structural constraints, in the spirit of
density-based topology optimization with self-support constraints
\citep{langelaar2016selfsupp,guo2017self,qian2017undercut} --- that is, to use the
present loss as an \emph{additional term} inside an established topology-optimization
loop.

\paragraph{Neural network (proof of concept): label-free amortized inference.}
Learning build orientation directly with neural networks has been explored before, but
typically with a purpose-built differentiable surrogate or labeled
supervision~\citep{chen2023concurrent}.  Our aim here is not a strong learning claim,
but to show at small scale that label-free \emph{amortized} inference is possible using
only the differentiability of our loss.  A message-passing graph neural network takes
the mesh face graph (nodes $=$ faces, edges $=$ face adjacency) and outputs a
nonnegative per-face weight $a_i\ge0$; the build direction is predicted as the weighted
sum of face anti-normals, $\nvec=\mathrm{norm}(\sum_i a_i(-\mvec_i))$ --- a construction
that behaves naturally under rotation and prevents constant collapse.  The training
signal is \emph{only} $L_{\mathrm{SFTF}}$ evaluated at the predicted direction (no
ground-truth direction labels); gradients flow through $\nvec$ into the network
weights.  Evaluated with per-mesh leave-one-out over 9 meshes (a \emph{single forward}
prediction on each held-out mesh), the TomoNV-estimated support-mass percentile
averages $0.28$, well ahead of random ($0.41$) and midway toward the per-mesh
gradient-descent oracle ($0.13$) (Fig.~\ref{fig:gnn}).  The network beats random on 6
of 9 meshes and fails on some (cylinder, cone, pipe-elbow): amortized inference is
possible, but with this small dataset and simple model it does not replace per-mesh
optimization.  Rotation-equivariant architectures and larger training sets are future
work.  In the interest of honesty, repeating the experiment against \emph{real Cura}
support-mass percentile, with the loss trained as the gated combination
($L_{\mathrm{SFTF}}+S_g$), shows no advantage on the small set (GNN $0.60$ vs random
$0.40$).  We tested whether this failure was merely a consequence of its mostly
near-self-supporting primitives: a fused GPU implementation enabled a 15-mesh
leave-one-out rerun including five 50k--100k-face support-bearing organic scans.  Across
five independent seeds, with the random comparator stabilized by 1,000 directions
per mesh and seed, the GNN reaches $0.538$ without augmentation versus $0.469$ for random
($29/75$ mesh--seed wins), and degrades to $0.642$ with random SO(3) augmentation
($14/75$ wins).  The mesh-cluster bootstrap intervals for the mean GNN-minus-random
difference are $+0.069$ $[-0.030,+0.172]$ without augmentation (Wilcoxon on the 15
mesh-level mean differences, $p=0.277$) and $+0.173$ $[+0.101,+0.249]$ with augmentation
($p=6.1\times10^{-4}$).  Excluding large meshes is therefore not a sufficient explanation
for the original failure, and the apparent single-seed improvement from augmentation
does not replicate.  Each fold still trains on only 14 meshes and no equivariant model
is compared directly, however, so this neither rules out data scale in general nor
identifies non-equivariance as the cause.  The result instead prioritizes controlled
tests of equivariance error and model inductive bias.  We therefore retain the
TomoNV-based proof of concept, and accordingly do not list amortized inference among
this paper's contributions.

\begin{figure}[H]
\centering
\includegraphics[width=\linewidth]{demo_sftf_gnn.png}
\caption{Label-free self-supervised GNN build-direction prediction (per-mesh
leave-one-out, 9 meshes).  Left: TomoNV-estimated support-mass percentile of the
predicted direction for each held-out mesh (lower is better).  Right: means.  A single
forward pass of the GNN ($0.28$) substantially beats random ($0.41$) and approaches
the per-mesh gradient-descent oracle ($0.13$), trained without labels using only
$L_{\mathrm{SFTF}}$.}
\label{fig:gnn}
\end{figure}

The orientation landscape also reveals when a single reported optimum is misleading.
For a sphere, every build direction is equivalent; for an axisymmetric cylinder or
torus, an entire circle of directions may tie at the same tilt.  A flatness test and a
polar-collapse axis test therefore report an optimum set--point, circle, or sphere--
rather than an arbitrary direction returned by gradient descent.

\begin{figure}[H]
\centering
\includegraphics[width=0.66\linewidth]{demo_sftf_symmetry.png}
\caption{Rotationally degenerate optima.  The loss landscape identifies whether the
minimum is an isolated point, a circle of equivalent directions, or an almost flat
sphere of equivalent build directions.}
\label{fig:symmetry}
\end{figure}

\subsection{Limitation: the Shape-Optimization Result Is Slicer-Specific}
\label{sec:shapeopt-transfer-limit}

Table~\ref{tab:shapeopt-multi} measures support removal with a single slicer.
Section~\ref{sec:crossslicer} has just argued that the gate physics is a property of
the process rather than of CuraEngine, on the strength of the \emph{prediction}
transferring to a slicer the predictor was never shown; the obvious test is whether the
\emph{optimized geometry} also prints support-free on that same slicer.  We re-sliced the identical
before/after meshes with PrusaSlicer~2.9.6 (console) under a frozen profile whose
overhang threshold of $30^\circ$ from the horizontal reproduces the same
$\theta_c{=}60^\circ$ convention, with nothing tuned to the new slicer.  It does not
transfer, and the reason is instructive enough to state in full
(Table~\ref{tab:shapeopt-prusa}).

Two results are worth separating.  The first is a confirmation: PrusaSlicer
independently reproduces the \emph{control} designation, charging exactly $0.00$ g on
the cone, U-bracket, and c-clamp before optimization.  Those three rows are genuinely
parts that need no support at $z$-up, on both slicers, and the U-bracket anomaly in
Table~\ref{tab:shapeopt-multi} is confirmed to be a TomoNV voxel artifact rather than a
real cost.  The second is a failure.  On the six support-requiring meshes, two of the
optimized shapes (icosphere, torus) cannot be sliced at all: PrusaSlicer aborts with an
empty first layer.  On the four that do slice, the total support falls from $37.9$ to
$36.9$ g --- a $2.7\%$ reduction, against the $98.4\%$ that CuraEngine reports for the
same deformations.  The Bunny does not merely fail to improve; its real support rises
by $59\%$ ($14.3\to22.7$ g) even though its airborne overhang area falls by $96\%$
($1523\to66$ mm\textsuperscript{2}).  The two optimized no-support controls likewise
acquire a support bill under PrusaSlicer ($0.00\to1.29$ and $0.00\to2.21$ g) where
CuraEngine still reports zero.

The mechanism is a mismatch between what the objective charges for and what a slicer
charges for, and the empty first layer is the clearest symptom.  Our objective is a
\emph{facet-angle} criterion: a facet costs nothing once its slope clears
$\theta_c$, no matter what lies beneath it.  The cheapest way to satisfy that criterion
on a blunt shape is to sharpen the underside until it meets the plate at a point --- the
classic teardrop of Figure~\ref{fig:shapeopt} is exactly this move, and it is why the
icosphere reaches zero overhang.  A mathematical point, however, is not a first layer.
Reading the emitted G-code makes the same point quantitatively: every support extrusion
PrusaSlicer generates for the torus sits at the bottom of the part ($z=0.20$--$1.20$ mm
before optimization, $0.20$--$4.40$ mm after).  PrusaSlicer is not propping up
overhanging facets; it is filling the wedge of air under a part that barely touches the
plate, and sharpening the underside makes that wedge \emph{taller}.  The objective
rewards precisely the deformation that raises the real cost.

This is intrinsic to the facet formulation rather than an artifact of our height
weight.  The weight $(1+\eta/D)$ charges a facet resting on the plate its full area
even though the plate already carries it, so dropping the floor to $\eta/D$ is the
natural repair; it does not help.  Under the repaired weight the torus underside ends
with no down-facing facet within $35^\circ$ of horizontal --- every one of them clears
the $30^\circ$ threshold with margin --- and its support still rises, $2.895\to2.969$ g.
On the four meshes that slice under both weights the repair is worse, not better
(U-bracket $1.29\to3.35$, c-clamp $2.21\to2.76$, pipe-elbow $7.16\to8.75$, Bunny
$22.75\to26.68$ g).  Zero facet overhang and zero support are simply different
conditions, and only the former is what our gradient can see.

We therefore scope the claim.  What Table~\ref{tab:shapeopt-multi} establishes is that
vertex gradients can remove essentially all of the support that CuraEngine 15.04/DP103
asks for, in a design space of tens of thousands of degrees of freedom that sampling
cannot reach; those numbers are measurements and they stand.  What it does not
establish --- and what we withdraw --- is that the resulting geometry is
self-supporting for a slicer in general, or manufacturable as emitted.  The prediction
headline is unaffected: $S_g$ and $S_g^{\mathrm{hard}}$ involve no shape optimization,
and their ranking transfers to PrusaSlicer unchanged (Section~\ref{sec:crossslicer}).
The two results sit on opposite sides of the same boundary --- reading $\theta_c$ off a
profile transfers, exploiting a facet criterion does not.  The repair is to make the objective charge
for the air beneath the part rather than for facet angle alone, and to constrain the
bed contact to a printable footprint instead of letting it collapse to a point; both
are outside the scope of this paper.

\begin{table}[H]
\centering
\caption{Cross-slicer re-slice of the \emph{same} before/after meshes as
Table~\ref{tab:shapeopt-multi} (PrusaSlicer~2.9.6, frozen profile, threshold
$30^\circ$ from horizontal $\Rightarrow\theta_c{=}60^\circ$, $\nvec{=}+z$,
support-only mass from G-code).  Both slicer columns are measured on the identical STL pairs: the CuraEngine column is a direct re-slice of the same files, with per-file SHA-256 provenance in \texttt{outputs/prusa\_transfer/shapeopt\_cura\_reslice\_tc60.json}.  ``---'' marks an optimized mesh PrusaSlicer refuses:
the deformation drives the underside to a downward apex, leaving the first layer empty.
PrusaSlicer independently confirms the three no-support controls at $0.00$ g before
optimization; on the four support-requiring meshes that slice, it removes $2.7\%$
($37.9\to36.9$ g) where CuraEngine reports $98.4\%$.}
\label{tab:shapeopt-prusa}
\small
\begin{tabular}{lrrr}
\toprule
mesh & Cura [g] before$\to$after & Prusa [g] before$\to$after & Prusa change \\
\midrule
icosphere   & $0.66\to0.00$ & $3.45\to$ ---     & unsliceable \\
sphere      & $0.88\to0.00$ & $3.74\to1.60$     & $-57\%$ \\
torus       & $0.26\to0.00$ & $2.89\to$ ---     & unsliceable \\
hook        & $3.57\to0.00$ & $8.01\to5.38$     & $-33\%$ \\
pipe-elbow  & $6.39\to0.14$ & $11.85\to7.16$    & $-40\%$ \\
Bunny       & $2.47\to0.09$ & $14.32\to22.75$   & $\mathbf{+59\%}$ \\
\midrule
\multicolumn{4}{l}{\footnotesize\emph{no-support controls (Prusa confirms $0.00$ g before, on both slicers)}}\\
cone        & $0.00\to0.00$ & $0.00\to$ ---     & unsliceable \\
U-bracket   & $0.00\to0.00$ & $0.00\to1.29$     & acquires support \\
c-clamp     & $0.00\to0.00$ & $0.00\to2.21$     & acquires support \\
\bottomrule
\end{tabular}
\end{table}

\input{limitation_centroid_attention}

\section{Conclusion}

This study turns the ray-cast SFTF support objective into a differentiable loss by
replacing hard receiver selection with soft attention over candidate receiver faces and
a build-plate slot.  The loss recovers the weighted original objective in the sharp
limit whenever the sharpened attention agrees with the ray-cast receiver --- the gate,
overhang, and plate relaxations converge unconditionally, and
Section~\ref{sec:centroid-limit} delimits the receiver condition --- and provides
accurate gradients with respect to both build direction and mesh vertices.  A support-height term improves agreement with TomoNV, but the decisive
physical validation comes from the production slicer: when gated by the Cura/DP103
$60^\circ$ overhang threshold, $S_g$ predicts real Cura support-only mass with mean
per-mesh Spearman $+0.80$ across the g5test headline 18-mesh set --- positive on every
mesh, from primitives to 100k-face organic scans --- and improves end-to-end
orientation selection.  A hard-gate control shows the prediction itself owes nothing to
differentiability --- the sharp limit of $S_g$ ranks Cura slightly better ($+0.87$) ---
and a tensor
contrast shows the multi-mesh shape result likewise owes nothing to the tensor term
--- so the contribution
of the relaxation is precisely that it makes this slicer-gate physics optimizable:
the smooth gate carries the gradients that hard slicer calls cannot provide.  The
resulting tension between prediction (sharpness) and optimization (smoothness) is
addressed at the level of gate design: a straight-through gate~\citep{bengio2013ste}
--- hard indicator forward, sigmoid backward --- retains the soft recipe's
optimization performance (Cura removal $98.0\%$ vs $98.4\%$) while removing the
gate's share of the prediction bias; the residual gap to the fully hard control is
carried by the remaining relaxations (softplus overhang magnitude, soft-min plate
height), so pure evaluation and ranking are best served by the fully hard
$S_g^{\mathrm{hard}}$.  The method
therefore reframes SFTF from a sampling-only candidate generator into a differentiable
loss for build orientation, shape optimization, and learning-based additive
manufacturing workflows.

The two headlines carry different warranties, and we close by stating them
separately.  The prediction result is slicer-transferable
(Section~\ref{sec:crossslicer}): it is fit-free, $\theta_c$
is read from the declared profile, and the ranking holds on a slicer the predictor has
never seen.  The shape-optimization result is not
(Section~\ref{sec:shapeopt-transfer-limit}); it removes the support CuraEngine asks
for, but the optimizer is free to satisfy a facet-angle criterion by collapsing the
bed contact to a point, and PrusaSlicer charges for the air that this leaves
underneath --- or refuses the mesh outright.  Vertex gradients demonstrably move a
mesh to an optimum of the objective we wrote down; that objective is not yet a
faithful model of what a slicer bills.  Closing that gap --- charging for the air
beneath the part rather than for facet angle alone, and constraining the footprint to
remain printable --- is the first item of future work, alongside broader slicer
profiles, print-time and surface-quality objectives, and rotation-equivariant
predictors that exploit the detected point/circle/sphere structure of degenerate
orientation landscapes.

\appendix
\section{Experiment $\times$ Mesh-Group Coverage (g5test five groups)}\label{app:coverage}
The table below lists which subset of the g5test five-group benchmark (mesh identities
identical to the base SFTF study and SFTFCluster) each experiment uses.  The CuraEngine
validation slices all of groups A/B/C; its headline mean is taken over the 18 meshes on
which rank validation is well-posed, with three degenerate / internal-cavity shapes
reported in a separate block for transparency.
\input{coverage_table_g5}

\section{Mesh Resolution and Coarse-to-Fine Evaluation}\label{app:mesh-mg}

The mesh-resolution recommendation in the main text rests on two observations.  First,
decimation reduces the directional discriminative power of the support-volume term when
it is compared with real slicer support mass.  Second, coarse meshes can still be useful
as candidate filters, provided that the final score is re-evaluated on the fine mesh.

\begin{table}[H]
\centering
\caption{Bunny 69k SFTF support-volume resolution sweep.  Values are correlations
with legacy CuraEngine 15.04 / DP103 PLA support-only mass.  The configuration uses
$SFTFConfig(w_{\mathrm{supvol}}{=}1,\mathrm{gate\_supvol}{=}\mathrm{True},
\mathrm{supvol\_to\_bed}{=}\mathrm{True})$, the $60^\circ$ slicer threshold, unit
diagonal normalization, and a coarse yaw/pitch grid.}
\label{tab:mesh-resolution-sweep}
\small
\begin{tabular}{lrr}
\toprule
input faces & Spearman & Pearson \\
\midrule
$6{,}000$  & $0.263$ & $0.563$ \\
$15{,}000$ & $0.460$ & $0.649$ \\
$30{,}000$ & $0.590$ & $0.719$ \\
$40{,}000$ & $0.631$ & $0.745$ \\
\bottomrule
\end{tabular}
\end{table}

The drop is not a comparison-harness artifact.  Running the voxel predictor
TOMO through the same Cura grid and yaw/pitch convention gives Spearman $0.62$ and
Pearson $0.80$, far above the $0.26$ of the decimated proxy.  The rotation convention
and measurement pipeline therefore do not destroy the agreement; the loss comes from
surface overhang/height information removed by decimation.

\begin{table}[H]
\centering
\caption{Bunny 15k--30k--69k coarse-to-fine case study.  The experiment uses quadric
decimation, $K{=}24$ Fibonacci directions, float32, $k{=}64$ receiver candidates, and
the default $L_{\mathrm{SFTF}}$ loss.  Times are wall-clock measurements on the current
experimental PC.  ``Full-best rank'' is the rank, on that level, of the direction that
is best on the full 69k mesh.}
\label{tab:bunny-mg-levels}
\small
\begin{tabular}{lrrrrrr}
\toprule
level & faces & s/dir & mean ratio & $\rho$ vs full & best-angle error & full-best rank \\
\midrule
15k  & $15{,}000$ & $0.583$ & $0.727$ & $0.890$ & $43.7^\circ$ & $4$ \\
30k  & $30{,}000$ & $2.230$ & $0.844$ & $0.957$ & $0.0^\circ$  & $1$ \\
full & $69{,}662$ & $11.480$ & $1.000$ & $1.000$ & $0.0^\circ$  & $1$ \\
\bottomrule
\end{tabular}
\end{table}

The case study shows both the benefit and the limit of coarse-to-fine evaluation.  The
15k landscape correlates well with the full landscape, but its standalone optimum is
$43.7^\circ$ away from the full optimum.  If 15k is used only to keep the top 4
directions, 30k to keep the top 2, and the full mesh only to score those two finalists,
the same best sampled direction is recovered while the estimated sweep cost drops from
$275.5$\,s to $45.9$\,s, a $6.0\times$ speedup.  Thus the coarse mesh is a candidate
filter, not a replacement for the fine physical score.

\subsection{Runtime Performance}\label{app:runtime}

Runtime measurements are included to show the practical mesh size reachable by the
current reference implementation.  The test machine is an AMD Ryzen 9 9950X3D
(16 cores / 32 threads) with 128\,GB physical memory, PyTorch 2.12.1 CPU build
(\texttt{torch.get\_num\_threads()=16}, no CUDA), on Windows.  All timings use the
unit-diagonal Bunny mesh, $k{=}64$ receiver candidates, the default
$L_{\mathrm{SFTF}}$ configuration, and one representative build direction.

\begin{table}[H]
\centering
\caption{Single-direction runtime by dtype.  ``$n$-grad'' denotes one
forward+backward pass with respect to the build direction only; vertex gradients are
not requested in this table.}
\label{tab:runtime-dtype}
\small
\begin{tabular}{lrrrr}
\toprule
faces & no-grad f32 & no-grad f64 & $n$-grad f32 & $n$-grad f64 \\
\midrule
15k & $0.523$\,s & $0.762$\,s & $0.658$\,s & $0.804$\,s \\
30k & $1.872$\,s & $2.943$\,s & $2.322$\,s & $3.119$\,s \\
$69{,}662$ & $9.738$\,s & $15.176$\,s & $12.123$\,s & $16.079$\,s \\
\bottomrule
\end{tabular}
\end{table}

\begin{table}[H]
\centering
\caption{Float32 runtime and process RSS by autograd mode.  RSS includes memory retained
by the PyTorch allocator after the measurement, so it should be read as an approximate
working-set upper bound rather than an exact peak allocation.}
\label{tab:runtime-autograd}
\small
\begin{tabular}{llrr}
\toprule
level & mode & time [s] & RSS after [GiB] \\
\midrule
15k & no-grad & $0.594$ & $0.96$ \\
15k & $n$-grad & $0.589$ & $0.96$ \\
15k & $V$-grad & $0.636$ & $0.96$ \\
30k & no-grad & $2.244$ & $1.72$ \\
30k & $n$-grad & $2.250$ & $1.76$ \\
30k & $V$-grad & $2.279$ & $1.75$ \\
full & no-grad & $11.520$ & $4.50$ \\
full & $n$-grad & $11.459$ & $4.69$ \\
full & $V$-grad & $11.576$ & $4.89$ \\
\bottomrule
\end{tabular}
\end{table}

Thus, on this PC, Bunny-scale 65k--70k meshes can be evaluated directly at the fine
level, including gradients with respect to either the build direction or vertices.  The
main bottleneck is time in receiver-candidate selection rather than memory.  The initial
\texttt{soft\_receiver\_assignment} recomputed chunked below-candidate search for each
direction even when $k$-NN candidates were used; the current implementation also
supports a static KD-tree pool cache, from which each direction selects its nearest-below
top-$k$ candidates.  On Bunny 69k with $K{=}6$ directions, the original directional
$k{=}64$ search took $68.9$\,s, while a static pool with
$K_{\mathrm{pool}}{=}256$ took $1.4$\,s to build plus $1.0$\,s to evaluate, with
Spearman $1.00$ and mean ratio $1.003$ relative to the directional result.  The
$K{=}24$ full sweep dropped from $275.5$\,s to $5.5$\,s.  After this cache, full
evaluation is cheap enough that coarse-to-fine gives only $1$--$1.5\times$ additional
speedup on small sweeps, but it remains useful for hundreds of directions or repeated
optimization loops because it reduces the number of fine-mesh evaluations.

\subsection{Comparison with Existing Support-Cost Methods}\label{app:runtime-compare}

The two tables above report only the internal cost of our method across dtypes and
autograd modes; they do not show where the method sits relative to existing
support-cost estimators.  Table~\ref{tab:runtime-methods} compares, on the same PC and
under the same conditions as Table~\ref{tab:runtime-dtype} (only TOMO\_gpu uses the CUDA
path of its DLL), the wall-clock time each method needs to compute the support cost for a
single build direction on the same Bunny mesh ($69{,}662$ faces, $120$\,mm diagonal,
$\nvec{=}+z$).  The comparators are a real production slicer (legacy CuraEngine 15.04);
the CPU and GPU implementations of a voxel-based estimator that discretizes the object
onto a regular 3D grid to approximate support mass (TOMO\_cpu / TOMO\_gpu, i.e.\ the
TomoNV~\citep{tomonv} family); a C++ implementation of the prior SFTF that builds the
support-flow tensor field by non-differentiable hard ray casting; and the present method
(SFTFSoft).  The first four are all non-differentiable and usable only for discrete
direction sampling, whereas our method generalizes the same support-flow tensor field
into a differentiable form through soft attention.

\begin{table}[H]
\centering
\caption{Single-direction support-cost runtime by method (Bunny 69k, $120$\,mm diagonal,
$\nvec{=}+z$).  Our times use the static candidate-pool cache path, which builds the pool
once (about $1.46$\,s) and reuses it, so they are smaller than
Table~\ref{tab:runtime-dtype} (full $9.7$\,s), which re-searches candidates per
direction.}
\label{tab:runtime-methods}
\small
\begin{tabular}{llrc}
\toprule
method & output / character & time/dir [s] & differentiable \\
\midrule
CuraEngine 15.04 (real slice) & real support mass & $5.245$ & no \\
TOMO\_cpu (voxel estimate) & support-mass estimate & $0.058$ & no \\
TOMO\_gpu (voxel estimate, CUDA) & support-mass estimate & $0.201$ & no \\
SFTF original (hard ray cast, C++) & support-flow score & $0.0005$ & no \\
\textbf{ours SFTFSoft} (no-grad) & differentiable loss & $0.198$ & \textbf{yes} \\
\textbf{ours SFTFSoft} ($n$-grad) & loss $+$ direction gradient & $0.272$ & \textbf{yes} \\
\bottomrule
\end{tabular}
\end{table}

At roughly $0.2$\,s per direction, our method is about $26\times$ faster than the real
production slicer (about $5.2$\,s) and on par with the voxel estimator (TOMO).  The
original SFTF (C++) and TOMO are as fast as or faster than our method but are all
non-differentiable, hence limited to discrete direction sampling; our method, even when
it also returns the direction gradient, costs only about $0.27$\,s per direction while
being the only one that provides gradients with respect to both the build direction and
the vertex coordinates (for a single direction, kernel-launch overhead can make TOMO\_gpu
slower than TOMO\_cpu).  Thus our method combines a large speed advantage over the real
slicer with differentiability, making it suitable for the inner loop of gradient-based
build-direction and shape optimization.

\section*{Statements and Declarations}

\subsection*{Funding}
Funding information is provided separately in the submission system and title-page file
to preserve double-anonymous review.

\subsection*{Competing interests}
The author declares no competing interests.

\subsection*{Data availability}
The source code, the cached 21-mesh $\times$ 48-direction Cura validation records, and
the analysis scripts supporting the findings of this study are openly available at
\url{https://github.com/cfms-lab/SFTFCluster_2026}, under the \texttt{sftfsoft/}
subfolder (the repository is shared with the companion SFTFCluster paper; every asset
of this study lives under that subfolder).  In particular, the slicer-correlation
results are reproducible from the cached slicer records alone, without re-running any
slicer, via \texttt{sftfsoft/scripts/validate\_vs\_slicer.py}; the gate-sensitivity,
Cura~5.13 transfer, and multi-mesh shape-optimization analyses are reproduced by
\texttt{sftfsoft/scripts/sweep\_thetac\_gate.py},
\texttt{sftfsoft/scripts/transfer\_cura5.py}, and
\texttt{sftfsoft/scripts/shapeopt\_multimesh.py}, respectively.  The PrusaSlicer
transfer of Section~\ref{sec:crossslicer} is reproduced by
\texttt{sftfsoft/scripts/prusa\_transfer\_validation.py} and the before/after re-slice
of Section~\ref{sec:shapeopt-transfer-limit} by
\texttt{sftfsoft/scripts/shapeopt\_bedweight\_ab.py}; the nine before/after mesh pairs
behind that table are distributed with the package.  Re-running the slicers themselves
requires pointing environment variables at the external tools
(see \texttt{sftfsoft/scripts/README\_prusa\_transfer.md}).  Third-party mesh models
should be obtained from their original sources subject to their respective licenses.

\subsection*{Code availability}
The code and scripts supporting the reported results are openly available in the same
repository, \url{https://github.com/cfms-lab/SFTFCluster_2026} (\texttt{sftfsoft/}
subfolder).  An anonymized review archive can be provided during peer review if
required.

\subsection*{Use of artificial intelligence tools}
AI coding assistants, including OpenAI Codex and Anthropic Claude Code, were used to
assist with portions of research-code implementation, figure-generation scripts, and
manuscript-support automation.  All generated code, experimental results, and
manuscript changes were reviewed and validated by the author.

\subsection*{Ethics approval and consent to participate}
Not applicable.

\subsection*{Consent for publication}
Not applicable.

\section*{Acknowledgments}

\paragraph{Use of AI-assisted tools.}
AI coding assistants, including OpenAI Codex and Anthropic Claude Code, were used to
assist with portions of the research-code implementation, figure-generation scripts,
and manuscript-support automation. All generated code, experimental results, and
manuscript changes were reviewed and validated by the author, who takes full
responsibility for the correctness of the methodology, data, results, and conclusions.
No generative AI was used to generate research data, figures presented as novel research
images, or references.

\section*{Author Contributions}
\textbf{InHwan Sul:} Conceptualization, Methodology, Software, Validation, Formal
analysis, Investigation, Data curation, Writing -- original draft, Writing -- review \&
editing, Visualization, Funding acquisition.

\section*{Statements and Declarations}

\paragraph{Ethical considerations.} Not applicable (no human participants, human data,
human tissue, or animals).

\paragraph{Consent to participate.} Not applicable.

\paragraph{Consent for publication.} Not applicable.

\paragraph{Declaration of conflicting interest.}
The author(s) declared no potential conflicts of interest with respect to the research,
authorship, and/or publication of this article.

\paragraph{Funding statement.}
This work was supported by the National Research Foundation of Korea (NRF) grant funded
by the Korean government (MSIT) (NRF-2022R1A2C1010072).

\paragraph{Data availability.}
The source code, the cached 21-mesh $\times$ 48-direction Cura validation records, and
the analysis scripts supporting the findings of this study are openly available at
\url{https://github.com/cfms-lab/SFTFCluster_2026}, under the \texttt{sftfsoft/}
subfolder (the repository is shared with the companion SFTFCluster paper; every asset
of this study lives under that subfolder). In particular, the slicer-correlation
results (Table~\ref{tab:cura}) are reproducible from the cached slicer records alone,
without re-running any slicer, via \texttt{sftfsoft/scripts/validate\_vs\_slicer.py};
the gate-sensitivity, Cura~5.13 transfer, and multi-mesh shape-optimization analyses are
reproduced by \texttt{sftfsoft/scripts/sweep\_thetac\_gate.py},
\texttt{sftfsoft/scripts/transfer\_cura5.py}, and
\texttt{sftfsoft/scripts/shapeopt\_multimesh.py}, respectively. The PrusaSlicer transfer
of Section~\ref{sec:crossslicer} and the before/after re-slice of
Section~\ref{sec:shapeopt-transfer-limit} are reproduced by
\texttt{sftfsoft/scripts/prusa\_transfer\_validation.py} and
\texttt{sftfsoft/scripts/shapeopt\_bedweight\_ab.py}; re-running the slicers themselves
requires pointing environment variables at the external tools (see
\texttt{sftfsoft/scripts/README\_prusa\_transfer.md}). An independent JAX/XLA
reimplementation of the differentiable loss and the cross-framework parity scripts are
provided alongside the reference implementation. Third-party mesh models should
be obtained from their original sources under their respective licenses.

\bibliographystyle{plainnat}
\bibliography{references}

\end{document}

