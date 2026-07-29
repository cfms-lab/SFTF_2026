# LaTeX source: SFTF_Cluster_TDP_draft.tex

Source: `D:\__SFTF_Projects(2026)\Tomo_SFTFCluster_dev\draft\SFTF_Cluster_TDP_draft.tex`

% =====================================================================
%  SFTF-Cluster -- main manuscript for 3D Printing and Additive
%  Manufacturing (TDP), SAGE.  Article type: Original Article.
%    limits: 4000 words body | abstract <300w | <=8 figures | <=5 tables | <=100 refs
%  Restructured from the PiAM/EN draft (SFTF_Clustering_EN.tex) into TDP IMRaD:
%    Introduction / Materials and Methods / Results / Discussion / Conclusions.
%  Table budget: 4 tables kept here; the rest moved to the Supplement (S1-S10).
%    See SFTF_Cluster_TDP_supplementary.tex.
%  Review type: single-anonymized -> author identity NOT hidden (self-citation & repo link OK).
%  Reference style: Sage Vancouver (numeric).
% =====================================================================
% !TEX program = pdflatex
\documentclass[12pt]{article}

\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{amsmath,amssymb,amsthm,bm}
\usepackage{graphicx}
\graphicspath{{pics/}}
\usepackage[labelfont=bf,labelsep=space]{caption}
\captionsetup[figure]{name=Fig.}
\usepackage{booktabs}
\usepackage{float}
\usepackage{algorithm}
\usepackage{algpseudocode}
\usepackage[numbers,sort&compress]{natbib}
\usepackage{setspace}
\usepackage[margin=25mm]{geometry}
\usepackage{xcolor}
\usepackage[hidelinks]{hyperref}
\usepackage{fancyhdr}
\setlength{\headheight}{13.6pt}

\doublespacing            % TDP: double-spaced manuscript

% running head (<= 50 chars incl. spaces)
\pagestyle{fancy}\fancyhf{}
\fancyhead[R]{\small Output-Aware Mesh Partitioning via SFTF}
\fancyfoot[C]{\thepage}
\renewcommand{\headrulewidth}{0.4pt}

\title{Output-Aware Mesh Partitioning Based on a Support Flow Tensor Field}
\author{InHwan Sul\\
\small Department of Materials Design Engineering, Kumoh National Institute of Technology,\\
\small Gumi 39177, Republic of Korea\\
\small Email: snowman0@kumoh.ac.kr \quad ORCID: 0000-0003-0105-920X}
\date{}

\begin{document}
\maketitle

% ============================ ABSTRACT ( <300 words ) =================
\begin{abstract}
\noindent
Mesh partitioning is widely used to fabricate large or complex additively
manufactured parts, yet conventional partitioners mainly group geometric
coordinates and often ignore whether each part is printable with little support.
This paper proposes an output-aware mesh partitioning method that reuses the
per-face support-flow information produced by a Support Flow Tensor Field (SFTF).
Instead of using SFTF only to rank build directions, the method exposes each
face's overhang strength, support receiver type, support height, and support role
as clustering features. These features drive two partitioning families: pure
support-flow partitioning based on support pairs and roles, and feature-fusion
clustering that augments standard clustering with SFTF features. All headline
comparisons are evaluated directly with the open-source CuraEngine: every
connected part of every partition is re-oriented by a 48-direction slicer search,
amounting to roughly $1.4\times10^5$ slices over a twelve-shape benchmark. Under
this slicer-level ground truth no partitioner is universally best; feature-fusion
$k$-medoids attains the best mean rank after same-label disconnected components are
treated as independent parts, but a matched-part-count control---coordinate
$k$-means with its cluster count raised to the same final part budget---overturns
that advantage, identifying the part budget, not the feature set, as the
first-order determinant of slicer-level support. SFTF-based partitioning also produces
the most coherent support-role partitions: pure support-flow region growing is
highest under the SFTF-defined classes, while feature-fusion $k$-medoids is highest
when the classes are re-derived from actual CuraEngine support contacts. The
results indicate that support reduction is governed less by preserving existing
support columns than by giving each part freedom to adopt a favourable build
direction. The proposed method is therefore best characterised not as a universal
support minimiser but as an output-aware partitioner that produces interpretable,
role-consistent parts with competitive support once the slicer selects each part's
orientation.
\end{abstract}

\noindent\textbf{Keywords:} additive manufacturing; mesh partitioning; support
structure; build orientation; support flow tensor field; clustering

% ============================ 1. INTRODUCTION ========================
\section{Introduction}

Partitioning a large or complex mesh into printable pieces is a practical strategy
in additive manufacturing (AM). It is especially relevant for free-form shapes that
conform to or imitate the human body, such as mannequin forms, wearable devices,
custom protective equipment, orthoses, anatomical models, and other large curved
shells~\cite{oh2018}. In these applications, a partition is useful only if the
resulting pieces can be printed, assembled, and finished with limited support marks.
A partition boundary should therefore reflect not only geometric proximity, but also
the support behaviour induced by the selected build direction.

Many mesh-partitioning pipelines still cluster vertices or face centres with
algorithms such as DBSCAN~\cite{dbscan}, $k$-means, $k$-medoids~\cite{kmedoids},
agglomerative clustering, or spectral clustering. Classical mesh segmentation also
provides strong geometric criteria, including hierarchical decomposition with
cuts~\cite{katz2003}, shape-diameter functions~\cite{shapira2008}, curvature-tensor
analysis~\cite{lavoue2005}, and approximate convex decomposition~\cite{mamou2009}.
AM-specific decomposition methods add build-volume, assembly, or support-related
objectives; examples include Chopper~\cite{luo2012chopper}, support-free skeletal
partitioning~\cite{wei2018}, and multi-directional support-area
minimisation~\cite{gao2019}. These methods are important baselines, but they do not
directly expose the per-face support-flow quantities of a build-orientation analysis
as clustering features. A compact taxonomy of these baselines and the proposed
SFTF-based route is shown in Fig.~\ref{fig:taxonomy}.

The Support Flow Tensor Field (SFTF) was introduced as a fast build-direction
candidate generator~\cite{sftf}. Its current v2 formulation evaluates one fixed,
deterministic sample drawn under normalized surface-area measure for every direction,
normalizes ray heights by the bounding-box diagonal $D$, and removes the legacy
source-area--receiver-area product. The pair-flow tensor contributes only through its
symmetric Rayleigh contraction,
$R(n)=\max[0,-n^{\mathsf T}\operatorname{sym}(F_{\rm pair})n]$; rays without a face
receiver contribute the dimensionless bed score $B(n)$, giving
$J_{\mathrm{score}}(n)=R(n)+B(n)$.
The score is therefore invariant to uniform mesh scaling, while the antisymmetric
tensor component is retained only as an uncertainty diagnostic. This paper asks a
different question: once SFTF has computed per-face support-flow physics, can those
data be reused to partition the mesh itself?

The answer is yes. This work preserves the per-face support-flow field that is
normally compressed into a global direction score, and uses it as the basis of an
output-aware partitioner. The contributions are: (i) an adaptive per-face feature
matrix built from SFTF support-flow data at the mesh's selected build direction;
(ii) two partitioning families, pure support-flow partitioning and SFTF
feature-fusion clustering; (iii) a dimensionless SFTF v2 basin selector and
random-seed multi-start selector that reduce dependence on one conditioning direction;
(iv) a
ray-free support objective that estimates the support effect of cutting and
reorienting parts; and (v) slicer-level validation of every reported partition
against CuraEngine across twelve shapes, including a reimplementation of prior
multi-directional decomposition and a slicer-derived re-validation of the purity
metric. The emphasis is intentionally narrow: SFTF itself is treated as prior work,
while the present contribution is to recast its discarded per-face flow information
as a mesh-partitioning signal. The scope is likewise narrow: the output of this paper
is the partition itself, evaluated by slicer-level support and role coherence;
connector geometry, joint strength, and assembly sequencing are orthogonal
post-processing concerns already addressed by Chopper-style
systems~\cite{luo2012chopper} and are not optimised here.

\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{fig_method_taxonomy.pdf}
\caption{Taxonomy of coordinate, geometry, and SFTF-based partitioning methods. The
left branch lists conventional baselines (coordinate-only $k$-means, planar BSP,
graph-cut/MRF, spectral/normalized-cut) that do not encode support behaviour. The
right branch is the proposed SFTF-based route: prior SFTF computation supplies
per-face support-flow features, which are reused as feature-fusion clustering and as
pure support-flow partitioning, with a multi-direction extension assigning parts to
different favourable build directions.}
\label{fig:taxonomy}
\end{figure}

% ============================ 2. MATERIALS AND METHODS ===============
\section{Materials and Methods}

\subsection{Per-face support-flow features}

Let face $i$ have centre $c_i$, outward unit normal $m_i$, and area $A_i$, and let
$D=\lVert b_{\max}-b_{\min}\rVert_2$ be the mesh bounding-box diagonal. For a build
direction $n$, define the build-plate height
\begin{equation}
z_{\mathrm{plate}}(n)=\min_{v\in V} v\cdot n ,
\end{equation}
and the basic per-face quantities
\begin{align}
O_i(n) &= \max(0,-m_i\cdot n),\\
\tau_i(n) &= m_i\cdot n,\\
\eta_i(n) &= \frac{c_i\cdot n - z_{\mathrm{plate}}(n)}{D}.
\end{align}
Here $O_i$ measures overhang strength, $\tau_i$ preserves signed orientation, and
$\eta_i$ is the dimensionless height above the build plate.

A partition is conditioned by the dimensionless SFTF v2 score.  We denote this
selector field by $\Psi_K^{\mathrm{score}}(n)$. Following the frozen
v2 candidate protocol, one deterministic set of $8{,}192$ normalized-area surface
samples is reused for $2{,}048$ Fibonacci-sphere directions. Directions are sorted by
$J_{\mathrm{score}}(n)=R(n)+B(n)$, and angular non-maximum suppression retains basins separated by at
least $12^\circ$. A single-start run uses the lowest-score basin, while multi-start
extraction repeats over the first $K_o$ separated basins $\{n_q\}_{q=1}^{K_o}$.
The pre-v2 routed policy remains available only as an explicit reproduction option,
and the v1-to-v2 impact is reported separately. For each overhang face under a conditioning
direction $n$, a ray is cast along $-n$ using the same receiver tests as SFTF: the
receiver cannot be the source face, must lie below it, and must sufficiently face
the build direction~\cite{sftf}. For the experimental meshes in this paper, rays are
cast from all overhang faces rather than from the source-face subsample used by SFTF
scoring. Thus the partitioner does not reuse the score samples as a face field: it
constructs a separate all-face field $\Psi_F^{\mathrm{part}}(n)$ over all $N$ faces.
The following face-level support descriptors are then recorded: support role
$\rho_i\in\{\mathrm{none},\mathrm{face},\mathrm{bed}\}$, indicating no support need,
face-to-face self-support, or build-plate support; dimensionless support height
$\hat h_i=(c_i-c_{t_i})\cdot n/D$ for a valid receiver $t_i$ and zero otherwise; receiver
index $t_i$ (or $-1$); and receiver in-degree $\nu_i^{\mathrm{in}}$, the number of
incoming support rays.
The standard feature matrix is
\begin{equation}
X_F^{\mathrm{part}}
=\operatorname{zscore}\!\left([O,\tau,\eta,\hat h,\nu^{\mathrm{in}}]\right)\in\mathbb{R}^{N\times5},
\label{eq:phi}
\end{equation}
with constant columns set to zero. The two height channels are already dimensionless;
standardisation balances them against orientation and receiver-count channels. The two
support-flow cases that SFTF distinguishes---face-to-face self-support and
build-plate support through a virtual ground node---are illustrated in
Fig.~\ref{fig:unified-flow}.

\begin{figure}[H]
\centering
\includegraphics[width=0.86\textwidth]{FTree4x_fig1_unified_flow_supp-1.png}
\caption{Unified support-flow representation reused by the partitioner. A downward
overhang face may be supported by another face below it (face-to-face flow) or fail
to find a receiver and require support down to the build plate (a virtual
ground-node flow). SFTF accumulates these events into a direction score; the present
method instead retains them per face as support roles, receivers, receiver counts,
and support heights, which become the output-aware partitioning features.}
\label{fig:unified-flow}
\end{figure}

\subsection{Partitioning families}

\paragraph{Pure support-flow partitioning.}
The first family uses only support-flow relationships. In \texttt{support\_flow},
each face is assigned a four-way class
\begin{equation}
\kappa_i\in\{\mathrm{bed},\mathrm{needs},\mathrm{supporter},\mathrm{free}\}.
\end{equation}
A face near the build plate is labelled \textsc{bed}; an overhang face is
\textsc{needs}; a face receiving at least one ray is \textsc{supporter}; all others
are \textsc{free}. A union--find pass then merges (i) each support pair $(i,t_i)$ and
(ii) adjacent faces with the same $\kappa_i$. The resulting components are support
basins: an overhang and the local surface supporting it are kept in the same part.
In \texttt{flow\_region}, support pairs are not forced to merge; instead, adjacent
faces $i,j$ merge when
\begin{equation}
\rho_i=\rho_j
\quad\mathrm{and}\quad
m_i\cdot m_j\ge \cos\theta_{\mathrm{sim}},
\end{equation}
with $\theta_{\mathrm{sim}}=35^\circ$ by default. This variant favours geometrically
coherent regions with consistent support role. In both variants, very small
components are absorbed into their most adjacent neighbour, and a dihedral-weighted
graph-cut smoothing step may be applied to reduce jagged seams; the default
$\lambda=3$ was selected from a sweep on the manikin model (Supplementary Fig.~S3).

\paragraph{Feature-fusion clustering.}
The second family injects SFTF features into standard clustering. Let
$C\in\mathbb{R}^{N\times3}$ be the face-centre matrix. The main clustering matrix is
\begin{equation}
X_{\mathrm{cluster}}=\left[w_s\,\operatorname{zscore}(C)\mid
w_f\,X_F^{\mathrm{part}}\right]
\in\mathbb{R}^{N\times8}.
\label{eq:cluster-matrix}
\end{equation}
DBSCAN, $k$-means, agglomerative clustering, and an extended $k$-medoids
implementation are applied to $X_{\mathrm{cluster}}$. For large meshes, the $k$-medoids implementation
avoids an $O(N^2)$ distance matrix: each iteration assigns faces to the nearest
medoid in $O(NK)$ and updates each medoid to the member closest to the cluster mean
under Manhattan distance. After any partitioner returns face labels, the
implementation splits each non-negative label by face-adjacency connectivity, so
same-colour but physically disconnected shells are treated as separate parts, each
receiving its own orientation and support evaluation. The requested cluster count is
therefore an initial grouping parameter; the reported part count is the number of
connected printable components after this post-process. For a multi-direction
extension, the separated v2 conditioning directions $\{n_k\}$ define $c_{ik}=\max(0,-m_i\cdot
n_k)$, a hard preferred direction $b_i=\arg\min_k c_{ik}$, and soft weights
$w_{ik}=\exp(-\beta c_{ik})/\sum_{k'}\exp(-\beta c_{ik'})$ with $\beta=8$; the labels
$b_i$ drive support-region growing (\texttt{build\_direction}), while the soft block
$W=[w_{ik}]$ may be appended to Eq.~\eqref{eq:cluster-matrix}.

\subsection{Ray-free partition objective}

To score and later optimise a partition $\Pi=\{\mathcal{P}_\ell\}$ we use a ray-free
support model. The actual support of a partition can be viewed as
\begin{equation}
\widehat J_{\mathrm{part}}(\Pi)\approx \widehat J_{\mathrm{whole}}
 +\Delta J_{\mathrm{cut}}(\Pi)
 -\Delta J_{\mathrm{reorient}}(\Pi),
\label{eq:support-decomp}
\end{equation}
where $\Delta J_{\mathrm{cut}}$ is the proxy induced by separating an overhang from its
receiver, and $\Delta J_{\mathrm{reorient}}$ is the proxy reduction when each part
stands in its own best orientation. For an overhang face $i$ with receiver $t_i$,
define a cheap cut weight $w_i=A_iO_i\eta_i$; the cut cost is
\begin{equation}
\Delta J_{\mathrm{cut}}(\Pi)
=\sum_{i:\rho_i=\mathrm{face},\ \ell(i)\ne\ell(t_i)} w_i ,
\label{eq:dscut}
\end{equation}
and normalising by $\sum_i w_i$ gives the fraction of support columns severed. The
reorientation term relies on additivity. A face-level support proxy for direction $d$
is
\begin{equation}
\begin{aligned}
\gamma_i(d;t_d)&=\mathbf{1}\{\max(0,-m_i\cdot d)>t_d\},\\
s_i(d)&=A_i\,\gamma_i(d;t_d)\max(0,-m_i\cdot d),
\end{aligned}
\label{eq:sik}
\end{equation}
optionally multiplied by a height term when column volume is emphasised. The gate is
used only for the partition support proxy so that it matches the slicer
critical-angle convention; it does not change the original SFTF candidate-generation
coefficient $O_i(n)=\max(0,-m_i\cdot n)$. The dimensionless threshold is
$t_d=\sin\theta_v$ for a vertical/slicer angle $\theta_v$, or
$t_d=\cos\theta_c$ for a cosine-coded angle $\theta_c$; the protocol records the
angle semantics together with $t_d$. A part's support proxy is
$C_\ell(d)=\sum_{i\in\mathcal{P}_\ell}s_i(d)$, and its best direction minimises
$C_\ell$ over a discrete direction set, giving the ray-free predicted support
\begin{equation}
\hat S_{\mathrm{fp}}(\Pi)=
\sum_\ell \min_d \sum_{i\in\mathcal{P}_\ell}s_i(d).
\label{eq:shat}
\end{equation}
Because this footprint proxy cannot see self-support, we also evaluate a
height-field correction $\hat S_{\mathrm{hf}}$: after selecting each part's direction
using $\hat S_{\mathrm{fp}}$, each overhang column descends only to the nearest higher
surface in the same projected cell rather than necessarily to the build plate. This
remains ray-free and is the default score for automatic part-count selection. When
multi-start selection is enabled, candidate partitions are generated for each
conditioning direction $n_q$ in the v2 $K_o$-basin menu and, for stochastic
clustering, each random seed $s$, and the selected partition is
$\Pi^\star=\arg\min_{\Pi(q,s)} \hat S_{\mathrm{hf}}(\Pi(q,s))$. This is a small,
physics-guided multi-start search rather than an exhaustive Chopper-style
exploration; the implementation defaults to $K_o=5$ and seeds $\{0,\dots,4\}$. The
complete workflow is summarised in Algorithm~\ref{alg:workflow}.

\begin{algorithm}[H]
\caption{Output-aware mesh partitioning workflow.}
\label{alg:workflow}
\begin{algorithmic}[1]
\State Rank the dimensionless SFTF v2 pool and retain separated basins $\{n_q\}_{q=1}^{K_o}$.
\For{each conditioning direction $n_q$}
  \State Compute the all-face field $(O,\tau,\eta,\rho,\hat h,t,\nu^{\mathrm{in}})$ and $X_F^{\mathrm{part}}(n_q)$.
  \For{each random seed $s$ used by the selected clustering method}
    \If{method is \texttt{support\_flow}}
      \State classify faces by $\kappa_i$ and merge support pairs plus equal-class adjacent faces.
    \ElsIf{method is \texttt{flow\_region} or multi-direction growing}
      \State merge adjacent faces with equal role/regime and similar normals.
    \Else
      \State build $X_{\mathrm{cluster}}=[w_s z(C)\mid w_fX_F^{\mathrm{part}}(n_q)]$ and cluster with seed $s$.
    \EndIf
    \State absorb small components, optionally smooth boundaries, relabel disconnected same-label components as separate parts, and score with $\hat S_{\mathrm{fp}}$ or $\hat S_{\mathrm{hf}}$.
  \EndFor
\EndFor
\State output the lowest-score candidate partition.
\end{algorithmic}
\end{algorithm}

\subsection{Data and implementation}
\label{sec:data}

The method was evaluated on the Stanford Bunny ($69{,}662$ faces) for
feature-extraction and face-coverage tests, and on three application meshes for
output-aware partitioning: a liver mesh from BodyParts3D ($19{,}416$
faces)~\cite{bodyparts3d}, the \emph{Nefertiti} bust ($99{,}938$ faces), and a
full-body manikin ($13{,}672$ faces). A broader benchmark extends these to twelve
shapes spanning primitive, mechanical, scanned-anatomical, graphics-scan, organ, and
human-form classes, adding a torus, a hook, three scanned-anatomical Thingi10k shapes,
the Stanford dragon ($99{,}999$ faces), the Happy Buddha ($49{,}944$ faces), Lucy
($49{,}999$ faces), and a kidney mesh from BodyParts3D ($12{,}394$ faces). One scanned
shape (anat-D9) is a fragmented scan of 241 disconnected components; it is retained
deliberately as a data-quality stress case. The SFTF front-end used before
partitioning---source-face sampling and the direction-score landscape---is
illustrated in Supplementary Figs.~S1 and~S2.

The reference slicer is the open-source CuraEngine. For the direct slicer evaluation,
each partitioned part is oriented by a CuraEngine search over a uniform 48-direction
menu, with a coarse-to-local slicer-in-the-loop optimiser used as the practical
implementation: the optimiser starts from the SFTF-proposed partition and warm-start
direction, then lets CuraEngine choose the final build orientation for each part. All
direct slicer results use support everywhere and the FDM critical overhang angle
$\theta_c=45^\circ$. The paper also reports a fast internal screening estimate for
candidate generation and ray-free objective checks; this estimate is used only to
rank candidate partitions during development and to explain the reorientation
mechanism. Every reported support comparison, including the twelve-shape benchmark, is
evaluated directly with CuraEngine (Sections~\ref{sec:cura} and~\ref{sec:broad}). This
separation matters: on two scanned-anatomical shapes the screening estimate inverts
the method ranking relative to CuraEngine (Supplementary Note~S1), so screening numbers
are never used to support a headline claim. The internal estimate is about $110\times$
faster per orientation than a full CuraEngine slice (Supplementary Table~S10) yet agrees
with it at the whole-mesh orientation level (Supplementary Fig.~S5), which is why it is
retained for broad screening only. All experiments ran on Microsoft Windows
11 (64-bit) with an AMD Ryzen 9 9950X3D processor (16 cores, 32 threads), 125 GB memory,
and an NVIDIA GeForce RTX 5080 GPU (16 GB). The Python 3.12 environment used NumPy,
SciPy, Trimesh, scikit-learn, and the local \texttt{tomo-sftf} package; CuraEngine
legacy 15.04 was called as the reference slicer. The partitioning implementation and
the benchmark and evaluation scripts are openly available at
\url{https://github.com/cfms-lab/SFTFCluster_2026}.

\subsection{Evaluation metrics}
\label{sec:metrics}

Support-class purity measures whether each part has a consistent support role. For
support classes $\kappa_i\in\{\mathrm{bed},\mathrm{needs},\mathrm{supporter},
\mathrm{free}\}$ and partition $\{\mathcal{P}_\ell\}$,
\begin{equation}
\mathrm{Purity}=\frac{1}{N}
\sum_\ell \max_\kappa |\{i\in\mathcal{P}_\ell:\kappa_i=\kappa\}|.
\end{equation}
Higher purity means each part is closer to a single support behaviour, such as an
overhang-dominant or a self-supporting part. Because the classes $\kappa_i$ are
produced by SFTF itself, purity alone could be criticised as self-referential. Two
safeguards address this. First, the classes are validated externally: each whole mesh
is sliced by CuraEngine at the same reference direction, the support extrusion paths
are parsed from the G-code, and each face is re-classified from the slicer output
alone. Across the twelve shapes, every face that receives an actual CuraEngine support
contact is labelled \textsc{needs} by SFTF (recall $1.0$ on all twelve shapes);
precision is $0.07$--$0.51$ only because the sparse line-pattern support physically
touches a subset of the overhang faces it protects. Second, all purity comparisons are
recomputed against these slicer-derived classes (Supplementary Table~S9); the
per-shape method ranking is not uniformly aligned between the two definitions: over
the eight partitioners, Spearman $\rho$ ranges from $-0.58$ to $0.77$, with median
$0.42$ among the eleven defined shapes,
so slicer-derived purity is treated as a robustness check rather than a duplicate of
the SFTF-class metric. The two definitions therefore play distinct roles and are never
interchanged: SFTF-class purity is an \emph{internal} metric of whether the intended
role-coherent decomposition was achieved, Cura-derived purity is an \emph{external}
metric of agreement with actual slicer support contacts, and neither is used to rank
support performance---that ranking comes only from the CuraEngine support masses.

% ============================ 3. RESULTS =============================
\section{Results}

\subsection{Partitioning behaviour}

On the Bunny, all non-DBSCAN methods partitioned every face. SFTF v2 conditioning and
feature extraction took $3.20$ s; the selected build direction was
\[
n^\ast\approx(-0.883,-0.277,0.379).
\]
The pure support-flow methods produced five and
fourteen connected parts in $1.84$ s and $1.50$ s, respectively; feature-fusion
$k$-medoids produced 28 connected parts in $1.11$ s after same-label disconnected
components were split; DBSCAN was slower ($9.11$ s) and left 202 noise faces, confirming its
sensitivity to density parameters (Supplementary Table~S1). The application meshes
show the main qualitative behaviour. On the liver, most methods find nearly
support-free part orientations, so support mass becomes less discriminative and purity
is the more sensitive metric (Supplementary Fig.~S4). On \emph{Nefertiti}, coordinate
clustering cuts the model mainly by spatial proximity, while SFTF methods separate
self-supporting crown/back-head regions from face and under-chin overhang regions
(Fig.~\ref{fig:support-nefertiti}). On the manikin, which mixes many support roles
across a human-form surface (Fig.~\ref{fig:support-manikin}), coordinate and geometric
baselines have purity near $0.5$, while SFTF-based methods form parts with
substantially more coherent support roles; a per-method purity breakdown on the
manikin is given in Supplementary Table~S2.

\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{support_manikin_review_paired.png}
\caption{Manikin partition examples. Each panel shows the parent partition and the
separated parts placed in their screening orientations with estimated support in red.
SFTF-feature-fused clustering gives compact low-support candidates, while pure
support-flow methods provide interpretable support-role partitions.}
\label{fig:support-manikin}
\end{figure}

\begin{figure}[H]
\centering
\includegraphics[width=0.86\textwidth]{support_nefertiti_equal_scale.png}
\caption{\emph{Nefertiti} partitions and supports at equal scale. Coordinate-only
clustering cuts the bust by spatial proximity, whereas SFTF-based methods separate
the self-supporting crown and back of the head from the overhanging face and
under-chin regions.}
\label{fig:support-nefertiti}
\end{figure}

Table~\ref{tab:application} reports the current internal-TOMO screening results. They
show why this stage cannot replace the final slicer: the internal estimate saturates
at zero for three liver partitions and selects multi-direction splitting on
\emph{Nefertiti}, whereas the CuraEngine evaluation in Table~\ref{tab:siloop} selects
coordinate $k$-means for liver, multi-direction splitting for \emph{Nefertiti}, and
$k$-medoids for manikin. The screen is therefore used to explore
candidate partitions and support mechanisms, not to make the headline comparison.

\begin{table}[H]
\centering
\caption{Application-shape internal screening results under the SFTF v2 conditioning
policy. Purity is SFTF support-class purity (higher is better). Support is the current
CPU TOMO estimate for separated parts placed in their v2 diagnostic
orientations (g, lower is better); it is not the final CuraEngine result.}
\label{tab:application}
\begin{tabular}{llrrr}
\toprule
Shape & Method & Parts & Purity & Support mass (g)\\
\midrule
\input{generated_v2/sftf_v2_internal_tomo_rows.tex}
\end{tabular}
\end{table}

\subsection{Ray-free screening objective}

Table~\ref{tab:validate} evaluates the ray-free objective on raw manikin partitions,
without boundary smoothing. On this shape the footprint proxy has only moderate rank
agreement with the internal screen (Spearman $\rho=0.50$), whereas the height-field
correction reproduces its five-method order ($\rho=1.00$). Across the three application
shapes, however, agreement is shape-dependent; on the liver both proxy columns
degenerate to zero and their rank correlation is undefined (Supplementary Table~S10).
The proxy is therefore useful for proposing candidates,
not as a calibrated support-mass surrogate. The practical mechanism remains
reorientation freedom: a partition is useful when its pieces can stand in orientations
the whole shape cannot adopt.

\begin{table}[H]
\centering
\caption{Ray-free predicted support vs.\ fast screening support $S$ on raw manikin
partitions. The predicted quantities are arbitrary proxy units; $S$ is in
grams-equivalent screening units. Methods are sorted by $S$.}
\label{tab:validate}
\begin{tabular}{lrrrrr}
\toprule
Method & cut & reorient & $\hat S_{\mathrm{fp}}$ & $\hat S_{\mathrm{hf}}$ & $S$ (g)\\
\midrule
\input{generated_v2/sftf_v2_proxy_rows.tex}
\end{tabular}
\end{table}

\subsection{CuraEngine support validation}
\label{sec:cura}

The screening estimate is not used as the final slicer result. For the main support
comparison, we re-evaluated the same raw partitions with CuraEngine and allowed each
part to choose its own slicer-optimal build direction from a uniform 48-direction
menu. A practical coarse-to-local slicer-in-the-loop implementation budgets about 20
slices per part, but all values reported here use the full 48-direction menu.
Table~\ref{tab:siloop} shows the
three application shapes under this fair slicer-level protocol. Different methods are
lowest on the three shapes: coordinate $k$-means on the liver, multi-direction splitting
on \emph{Nefertiti}, and feature-fusion $k$-medoids on the manikin. A diagnostic
comparing the SFTF
screening orientation with the CuraEngine-optimal orientation (Supplementary
Table~S5) shows that orienting each part at the v2 diagnostic direction costs
$1.9$--$19.7\times$
more support than letting the slicer choose, which is why the final orientation must
be selected by the slicer.

\begin{table}[H]
\centering
\caption{Per-part CuraEngine-optimal support (g) on the application shapes: each part
is oriented to its CuraEngine-optimal build direction by a 48-direction search
(CuraEngine legacy 15.04, $\theta_c=45^\circ$). Per-shape minimum in bold; the mean
rank is over these three shapes only (see Table~\ref{tab:broad} for the twelve-shape
benchmark).}
\label{tab:siloop}
\begin{tabular}{lrrrrr}
\toprule
Shape & $k$-medoids & $k$-means & \texttt{flow\_region} & \texttt{support\_flow} & \texttt{build\_direction}\\
\midrule
\input{generated_v2/sftf_v2_application_cura_rows.tex}
\end{tabular}
\end{table}

\subsection{Comparison with prior multi-directional decomposition}

The closest competitor is the multi-directional support-minimising decomposition of
Gao et al.~\cite{gao2019}. Because the original code was not used, we implemented the
core idea faithfully: area-weighted greedy set-cover selects build directions that
make faces support-free, ICM assigns face labels with spatial coherence, and connected
components form parts (Gao is evaluated at its natural part count). The
reimplementation is verified against the original method's own objective: it reaches
near-support-free \emph{coverage} of $0.99$ on average across the twelve benchmark
shapes (at least $0.95$ on every shape; Supplementary Note~S3), so its higher slicer
support mass below reflects the evaluation axis---support \emph{mass} under per-part
reorientation---rather than a weak reproduction. On the regenerated manikin screen
Gao is lowest ($0.021$~g) and feature-fusion $k$-medoids is close ($0.038$~g). Under
the slicer-level protocol, $k$-medoids is lower on the manikin ($0.84$ vs.\ $6.59$~g)
and \emph{Nefertiti} ($7.59$ vs.\ $30.70$~g), while on the liver both trail coordinate
$k$-means ($4.72$~g; Table~\ref{tab:broad}). Support-class purity provides a distinct
comparison: on the liver, Gao's partition has purity $0.60$ while SFTF support-flow
partitions reach $0.94$--$0.96$ (Supplementary Table~S6). Thus SFTF supplies
role-consistent decompositions, but its support advantage is shape- and
part-budget-dependent.

\subsection{Broad slicer-level benchmark and automatic part-count selection}
\label{sec:broad}

The ray-free score can also select the part count. Adjacent regions are greedily
merged from a feature-fusion over-segmentation, and for each part count $K$ the method
evaluates
\begin{equation}
K^\ast=\arg\min_K
\frac{\mathrm{score}(K)}{\max_K\mathrm{score}}
\;+\;
\alpha\frac{K}{K_{\max}},
\label{eq:auto}
\end{equation}
using $\hat S_{\mathrm{hf}}$ by default and $\alpha=0.2$. On the regenerated manikin
screening benchmark this selects nine connected parts. The broad benchmark applies the
eight partitioners to all twelve shapes and re-evaluates every resulting connected part
with CuraEngine under the same 48-direction protocol as Section~\ref{sec:cura}---in
total $3{,}152$ connected parts and $142{,}100$ slices.
Table~\ref{tab:broad} reports the summed per-part CuraEngine-optimal support; a
qualitative four-group (A--D) overview and a representative side-by-side method comparison are
shown in Supplementary Figs.~S6 and~S7, and the twelve-shape v1-to-v2 impact audit is
listed in Supplementary Table~S7.

\begin{table}[H]
\centering
\caption{Broad slicer-level benchmark: summed per-part CuraEngine-optimal support (g,
lower is better) with every connected part oriented by the same 48-direction search
(CuraEngine legacy 15.04, $\theta_c=45^\circ$). The \emph{no split} column applies no
clustering: each natural connected component is oriented at its own CuraEngine-optimal
direction. Bold marks the best value in each row; the final row gives tie-adjusted
mean ranks. Support-class purity for the same partitions is in Supplementary Table~S8.}
\label{tab:broad}
\resizebox{\textwidth}{!}{%
\begin{tabular}{lrrrrrrrrr}
\toprule
Shape (faces) & no split & $k$-means & Planar & Gao & basin & region & medoids & multi-dir & auto\\
\midrule
\input{generated_v2/sftf_v2_broad_rows.tex}
\end{tabular}}
\end{table}

Three findings follow. First, no partitioner is best on every shape, but the methods
differ significantly (Friedman $\chi^2(8)=31.44$, $p=1.17\times10^{-4}$). After
disconnected same-label shells are split and oriented independently, feature-fusion
$k$-medoids has the best mean rank ($2.58$; bootstrap $95\%$ CI $1.75$--$3.50$ over
shape resamples, best or tied in $81.7\%$ of replicates, Supplementary Table~S11). Its
pairwise advantage over coordinate $k$-means is not significant on twelve shapes
(two-sided Wilcoxon $p=0.733$); the differences from Planar BSP ($p=0.092$) and
\texttt{flow\_region} ($p=0.052$) are also uncertain. The no-split baseline (mean rank
$5.54$) is itself best on anat-D1, where every default-budget decomposition adds
support. That split-averse case is also the only shape whose best single direction
already renders $99\%$ of its area support-free (Supplementary Fig.~S9).

Because $k$-medoids produces more parts, its low support could reflect the extra
reorientation freedom purchased by fragmentation. A direct control confirms that
this is the dominant effect. Raising coordinate $k$-means to the same final connected
part count (the closest attainable count, within two parts) reverses the comparison:
the matched baseline is lower on all twelve shapes (mean $1.81$ vs.\ $6.07$~g;
Wilcoxon $p=0.0005$), including dragon ($3.30$ vs.\ $26.38$~g) and anat-D1
($1.66$ vs.\ the no-split $4.68$~g;
Supplementary Note~S5). An ablation that holds the requested $K$, algorithm, and seed
fixed yields mean ranks of $2.25$ (coordinates only), $2.33$ (fusion), and $1.42$
(features only). Fusion does not improve on coordinates ($p=0.622$), while features
only is lower than fusion ($p=0.016$); connectivity nevertheless creates different
final part counts across arms (Supplementary Note~S4). It is therefore
suggestive rather than a fixed-budget causal estimate; the observational residual
analysis likewise under-controls the part budget (Supplementary Fig.~S8).

Second, under the connected-volume protocol $k$-medoids is lowest on four of twelve
shapes. Coordinate $k$-means is best on liver and dragon, Planar BSP on torus and
anat-D9, no split on anat-D1, multi-direction splitting on anat-D3 and
\emph{Nefertiti}, and \texttt{flow\_region} on Lucy. The safe claim is that feature
fusion has the best average rank within the compared default budgets, not that it is
universally or budget-matched optimal. Third, purity is method-dependent:
\texttt{support\_flow} and \texttt{flow\_region} have the highest mean SFTF-class
purities ($0.770$ and $0.753$ vs.\ $0.558$ for coordinate $k$-means; Supplementary
Table~S8), whereas feature-fusion $k$-medoids is highest when classes are re-derived
from CuraEngine support contacts ($0.853$; Supplementary Table~S9).
The automatic part-count selector remains a screening-stage convenience: its mean
rank is mid-field because the ray-free proxy is too coarse to choose $K$ against a
slicer ground truth without sparse slicer checks along the merge path.

% ============================ 4. DISCUSSION ==========================
\section{Discussion}

The results reposition SFTF-based partitioning. Its value is not that a single method
minimises support everywhere, but that reusing the discarded per-face support-flow
field yields interpretable, role-consistent parts whose support is competitive once
the slicer chooses each part's orientation. The support decomposition of
Eq.~\eqref{eq:support-decomp} explains why: on the tested shapes the reorientation
term dominates the cut term, so preserving support columns is less important than
giving each part the freedom to stand well. The matched-part-count control makes the
same point at the benchmark level: granted the same final part budget, a coordinate
baseline matches or beats feature fusion in raw support, so the distinctive value of
the SFTF features lies in role-coherent, interpretable cuts rather than support
minimisation. This is consistent with the CuraEngine
diagnostic, in which orienting parts at the v2 diagnostic direction is
$1.9$--$19.7\times$ worse than the common 48-direction slicer search. The final
orientation must therefore be selected by the slicer rather than the v2 score.

Several limitations follow directly. The ray-free score is a ranking proxy, not an
absolute slicer support-mass model: the footprint score ignores self-support, and the
height-field correction still depends on grid resolution. The twelve-shape
re-validation makes the limit concrete---on two scanned-anatomical shapes the screening
estimate inverts the method ranking relative to CuraEngine (Supplementary Note~S1), and
the proxy-driven automatic part-count selection stays behind feature-fusion $k$-medoids
in Table~\ref{tab:broad}. The multi-start selector reduces sensitivity to a single SFTF
direction or clustering seed but still returns the best member of a finite candidate
set and is not a proof of global optimality; moreover, the benchmark itself runs each
stochastic method once at a fixed seed, and re-running fusion $k$-medoids at five
seeds shows a substantial spread (liver $3.12$--$8.71$~g, \emph{Nefertiti}
$3.23$--$7.59$~g, and manikin $0.65$--$3.82$~g; Supplementary Table~S15)
that the multi-start selector is designed to absorb but the benchmark does not
exploit. The method currently handles joining only
through boundary smoothing; it does not optimise connector geometry, joint strength,
cut-plane area, or assembly order, unlike decomposition systems designed around
assembly~\cite{luo2012chopper}. Finally, the experiments cover twelve shapes up to
about $10^5$ faces, the Gao comparison uses a faithful reimplementation rather than the
authors' original code, and support-free skeletal partitioning~\cite{wei2018} remains
to be compared. The main open direction is to integrate CuraEngine evaluation into the
partition objective itself, beyond only the final orientation search, so that partition
and orientation are optimised jointly against the slicer.

% ============================ 5. CONCLUSIONS =========================
\section{Conclusions}

This paper presented an output-aware mesh partitioning method that reuses per-face
support-flow information from SFTF. By exposing support roles, support receivers, and
support heights as features, the method turns a build-orientation candidate generator
into a partitioning driver, and a ray-free support objective explains the main
mechanism: reducing support depends less on preserving original support columns than on
giving each part freedom to choose its own favourable orientation. A twelve-shape
CuraEngine re-validation, in which every connected part of every partition is oriented
by the same 48-direction slicer search, delimits the claim honestly: no partitioner is
universally best, and although feature-fusion $k$-medoids has the best mean rank once
disconnected same-label shells are treated as independent printable volumes, a
matched-part-count control overturns that advantage---coordinate $k$-means given the
same final part budget uses less support on all twelve shapes. The mean-rank
leadership of feature fusion within the compared pool thus reflects, above all, the
reorientation freedom purchased by its finer fragmentation, and the part budget is
the first-order lever on slicer-level support. What SFTF
methods deliver uniformly is interpretability---pure support-flow region growing gives
the highest SFTF-class purity, and feature-fusion $k$-medoids gives the highest
Cura-derived purity. SFTF-based partitioning is therefore best used as an
interpretable, role-consistent decomposition tool for free-form AM shapes, with the
slicer, not the proxy, making the final orientation and part-count decisions.

% ============================ BACK MATTER ============================
\section*{Acknowledgments}

\paragraph{Use of AI-assisted tools.}
AI coding assistants, including OpenAI Codex and Anthropic Claude Code, were used to
assist with portions of the research-code implementation, figure-generation scripts,
and manuscript-support automation. All generated code, experimental results, and
manuscript changes were reviewed and validated by the author, who takes full
responsibility for the correctness of the methodology, data, results, and conclusions.
No generative AI was used to generate research data, figures presented as novel
research images, or references.

\section*{Author Contributions}
\textbf{InHwan Sul:} Conceptualization, Methodology, Software, Validation, Formal
analysis, Investigation, Data curation, Writing -- original draft, Writing -- review
\& editing, Visualization, Funding acquisition.

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
The partitioning code, the twelve-shape CuraEngine benchmark and evaluation scripts, and
the summary result records supporting the reported results are openly available at
\url{https://github.com/cfms-lab/SFTFCluster_2026}. The third-party
meshes used in this study are available from their original sources (BodyParts3D,
Thingi10K, and the Stanford 3D Scanning Repository) under their respective licences;
generated partitions and per-part support-evaluation records can be provided by the
corresponding author on reasonable request.

% References -- Sage Vancouver (numeric, citation order).
\begin{thebibliography}{99}
\bibitem{oh2018} Oh Y, Zhou C, Behdad S. Part decomposition and assembly-based (re)design for additive manufacturing: a review. Addit Manuf 2018;22:230-242.
\bibitem{dbscan} Ester M, Kriegel HP, Sander J, et al. A density-based algorithm for discovering clusters in large spatial databases with noise. In: Proc 2nd Int Conf Knowledge Discovery and Data Mining (KDD-96); 1996. p. 226-231.
\bibitem{kmedoids} Kaufman L, Rousseeuw PJ. Finding groups in data: an introduction to cluster analysis. New York: Wiley; 1990.
\bibitem{katz2003} Katz S, Tal A. Hierarchical mesh decomposition using fuzzy clustering and cuts. ACM Trans Graph 2003;22(3):954-961.
\bibitem{shapira2008} Shapira L, Shamir A, Cohen-Or D. Consistent mesh partitioning and skeletonisation using the shape diameter function. Vis Comput 2008;24(4):249-259.
\bibitem{lavoue2005} Lavou\'e G, Dupont F, Baskurt A. A new CAD mesh segmentation method, based on curvature tensor analysis. Comput Aided Des 2005;37(10):975-987.
\bibitem{mamou2009} Mamou K, Ghorbel F. A simple and efficient approach for 3D mesh approximate convex decomposition. In: Proc 16th IEEE Int Conf Image Processing (ICIP); 2009. p. 3501-3504.
\bibitem{luo2012chopper} Luo L, Baran I, Rusinkiewicz S, et al. Chopper: partitioning models into 3D-printable parts. ACM Trans Graph 2012;31(6):129:1-129:9.
\bibitem{wei2018} Wei X, Qiu S, Zhu L, et al. Toward support-free 3D printing: a skeletal approach for partitioning models. IEEE Trans Vis Comput Graph 2018;24(10):2799-2812.
\bibitem{gao2019} Gao Y, Wu L, Yan DM, et al. Near support-free multi-directional 3D printing via global-optimal decomposition. Graph Models 2019;104:101097.
\bibitem{sftf} Sul I. Support flow tensor field for fast build-orientation candidate generation in support-requiring additive manufacturing. 3D Print Addit Manuf. 2026. Submitted (code: \url{https://github.com/cfms-lab/SFTF_2026}).
\bibitem{bodyparts3d} Mitsuhashi N, Fujieda K, Tamura T, et al. BodyParts3D: 3D structure database for anatomical concepts. Nucleic Acids Res 2009;37(Database issue):D782-D785.
\end{thebibliography}

\end{document}

