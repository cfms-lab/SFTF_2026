# LaTeX source: main_en.tex

Source: `D:\__SFTF_Projects(2026)\SFTF_Composite_dev\draft\main_en.tex`

% =====================================================================
%  main_en.tex — English version for an international (SCI) journal.
%  Build:  uv run python scripts/build_pdf.py  draft/main_en.tex   (-> main_en.pdf)
%          uv run python scripts/build_docx.py draft/main_en.tex   (-> main_en.docx)
%  Korean (J. Korean Soc. Textile Eng.) version: main.tex.
% =====================================================================
\documentclass[11pt]{article}

\usepackage{fontspec}              % xelatex
\usepackage{amsmath,amssymb,amsfonts,bm}
\usepackage{graphicx}
\usepackage{svg}
\usepackage{booktabs}
\usepackage{array}
\usepackage{geometry}
\geometry{a4paper, margin=25mm}
\usepackage{placeins}
\usepackage[hidelinks]{hyperref}
\usepackage[numbers]{natbib}

\usepackage{tikz}
\usetikzlibrary{arrows.meta, calc, positioning, decorations.pathreplacing, patterns, shapes.geometric}
\usepackage{pgfplots}
\pgfplotsset{compat=1.18}

\graphicspath{{pics/}{./}}

\newcommand{\Kabs}{\lvert K\rvert}
\newcommand{\Phidr}{\Phi_{\mathrm{drape}}}
\newcommand{\Kstar}{K^{\ast}}

% allow a little last-resort stretch so long tokens never overfull
\setlength{\emergencystretch}{2em}

\title{Porting Support-Flow-Tensor-Field Clustering to Composite Drape-Patch
Partitioning: Manufacturability-Aware Segmentation with a Lightweight Geometric
Drape Field}
\author{InHwan Sul\\
\small Department of Materials Design Engineering, Kumoh National Institute of Technology,\\
\small Gumi 39177, Republic of Korea\\
\small Email: snowman0@kumoh.ac.kr \quad ORCID: 0000-0003-0105-920X}
% NOTE(submission): add co-authors here if the final author list expands
%   (update the author line above and the CRediT block in Author Contributions).
\date{}

\begin{document}
\maketitle

\begin{abstract}
Manufacturing a curved composite part requires draping a flat fabric (prepreg) over
a curved mould. On a doubly curved surface the fabric adapts through \emph{trellis
shear}---the warp/weft grid skewing away from orthogonality---until, beyond a
material \emph{locking angle}, it wrinkles. The manufacturability problem is
therefore to partition a complex surface into \textbf{drape-feasible patches} that
each lay up without wrinkling, with consistent fibre orientation and few seams and
darts. We port the \emph{skeleton} of SFTF-Clustering, an additive-manufacturing
mesh partitioner, to this composite problem. The single replacement is to swap the
per-face support-flow features for a \textbf{per-face drape field} (shear angle
$\gamma$, fibre angle $\theta$, geodesic depth $g$, Gaussian curvature $\Kabs$,
drape regime); the existing partition families, ray-free objective and purity
metric are then reused almost verbatim. The drape field is designed as a drop-in for
the public partitioner's per-face feature interface, so the engine runs unmodified.
We build a fidelity ladder from a first-order curvature proxy
$\gamma\approx\Kabs\,g^2$ to a real pin-jointed-net (fishnet) trellis shear,
multi-seed re-seeding, a discrete manufacturable ply-angle snap $\{0,\pm45,90\}$,
and an automatic patch count, validated on an analytic ladder and on real
anatomical and engineering meshes. We quantitatively compare against standard
surface-partitioning methods (k-means, Variational Shape Approximation, curvature
clustering) and additionally score every partition with two flattening-distortion
metrics (LSCM and ARAP). We validate the lightweight kinematic field against a
high-fidelity Baraff--Witkin implicit cloth solver, reporting honest limitations
(free-hang drape is not forming; element-wise shear prediction is near-zero) and their
physical causes.
\end{abstract}

% =====================================================================
\section{Introduction}
% =====================================================================
Curved composite parts are made by draping flat prepreg/fabric over a curved mould.
The fabric accommodates double curvature through \textbf{trellis shear} of its
warp--weft grid; because the yarns are nearly inextensible, double curvature is
absorbed mainly by this shear. Beyond a material-dependent \textbf{locking angle}
(typically $30\text{--}50^\circ$) the yarns jam and the ply
wrinkles~\citep{prodromou1997}. The core
manufacturability task is therefore to partition a complex surface into
\emph{drape-feasible patches} such that (i) each patch's shear stays below locking,
(ii) fibre orientation is consistent, and (iii) seams and darts (relief cuts) are
minimised.

Our starting point is SFTF-Clustering~\citep{sul_sftfclustering}, a mesh partitioner
for additive manufacturing (AM). Its real asset is not the support-structure
\emph{application} but its \textbf{skeleton}: (a) preserving a per-face
direction-dependent field as clustering features, (b) partitioning so each part
adopts its own favourable direction, and (c) comparing cut versus reorientation
through a ray-free objective. We show this skeleton transfers almost unchanged to
composite drape partitioning: replacing the per-face support flow with a per-face
drape flow reuses the partition families, objective and purity metric.

\paragraph{Related work.} Treating curved surfaces as manufacturable flat
patterns/patches spans three strands. (1) \emph{Drape simulation}: the pin-jointed
net (fishnet) kinematic drape mapping~\citep{vanderweeen1991,wang1999draping}
propagates an inextensible grid geodesically over the surface to estimate shear
cheaply, while physics-based approaches integrate membrane/bending energy as in the
Baraff--Witkin implicit cloth solver~\citep{baraff1998large}; composite-specific
forming simulations further resolve wrinkling from the tensile, in-plane shear and
bending stiffnesses of the reinforcement~\citep{boisse2011wrinkling}. (2) \emph{Flattening}: conformal LSCM
\citep{levy2002lscm}, angle-based ABF++~\citep{sheffer2005abf}, and inextensible
ARAP~\citep{liu2008arap} unfold a curved patch to the plane with minimal distortion
to produce a cutting pattern (distortion grows with departure from developability).
(3) \emph{Mesh segmentation}: coordinate k-means~\citep{lloyd1982}, planar-proxy
Variational Shape Approximation (VSA)~\citep{cohensteiner2004vsa}, the Shape Diameter
Function~\citep{shapira2008sdf}, and curvature-based partitioning split a surface
into regions. Unlike these, our method preserves the \emph{per-face drape flow}
(shear, curvature, geodesic depth) as clustering features and partitions so each
patch adopts its own drape seed while charging seams as a cost---a
manufacturability-driven partition---and we compare against the segmentation methods
above quantitatively in \S\ref{sec:compare}.

\paragraph{Contributions.}
\begin{enumerate}
  \item A \textbf{formal mapping} from support flow to drape, and a \textbf{drop-in
        drape field} that satisfies the public partitioner's per-face feature
        interface.
  \item A fidelity ladder from a curvature proxy to a \textbf{real pin-jointed-net
        trellis shear}, plus \textbf{multi-seed re-seeding and a discrete ply-angle
        snap}.
  \item A \textbf{seam-vs-realign objective} with automatic patch count, validation
        on real meshes, and a \textbf{quantitative comparison} against standard
        partitioning methods.
  \item Validation of the lightweight shear field against a high-fidelity
        Baraff--Witkin solver, a distributed pressure term added for a forming
        boundary condition, and an honest analysis of limitations.
\end{enumerate}

\begin{figure}[ht]
  \centering
  \resizebox{\textwidth}{!}{%
  \begin{tikzpicture}[>=Stealth, node distance=8mm,
      box/.style={draw, rounded corners, align=center, font=\small,
                  inner sep=5pt, minimum height=13mm, text width=27mm},
      newbox/.style={box, fill=orange!12, very thick},
      reuse/.style={box, fill=blue!8}]
    \node[reuse] (mesh) {surface\\mesh};
    \node[newbox, right=of mesh] (field)
      {drape field $\Phi_{\mathrm{drape}}$\\$[\gamma,\theta,g,\lvert K\rvert,\rho]$\\\textbf{(NEW)}};
    \node[reuse, right=of field] (part)
      {partition family\\feature-fusion\\k-medoids / region-grow};
    \node[reuse, right=of part] (obj)
      {seam-vs-realign\\objective $+$ auto $K^{\ast}$};
    \node[reuse, right=of obj] (out) {drape-feasible\\patches};
    \draw[->,thick] (mesh)--(field); \draw[->,thick] (field)--(part);
    \draw[->,thick] (part)--(obj);   \draw[->,thick] (obj)--(out);
    \node[font=\footnotesize\itshape, text=orange!55!black, below=3mm of field]
      {the only new module};
  \end{tikzpicture}}
  \caption{Overall pipeline. The SFTF-Clustering skeleton (blue: partition families,
  ray-free objective, automatic patch count) is reused unchanged; the only new
  module is the per-face \textbf{drape field} (orange), a drop-in for the public
  partitioner's feature interface that drives the engine without modification.}
  \label{fig:pipeline}
\end{figure}

% =====================================================================
\section{Background: SFTF and SFTF-Clustering}
% =====================================================================

\subsection{Prior work: the Support Flow Tensor Field (SFTF)}
\label{sec:sftf-bg}
This subsection summarises the prior work, SFTF~\citep{sul_sftf}, which we reuse as a
partition driver. The goal of SFTF is not to run an expensive validation (a slicer or
a support-volume grid) directly on every build direction, but to first narrow the
search to directions that are likely to need little support. To this end SFTF assumes
a build direction and, from each overhanging face, casts a ray downward to determine
whether that overhang is held by \emph{another face} (face-to-face self-support) or
must be supported all the way down to the \emph{build plate}. As in
Fig.~\ref{fig:sftf-unified}, treating face-to-face and face-to-bed support as a single
``support flow'' lets one compare, direction by direction, the printability that a
plain normal or coordinate distribution cannot reveal: which faces need support, which
faces act as receivers, and how tall the support columns become. On large meshes,
rather than inspecting every face at every direction, SFTF samples representative
source faces (Fig.~\ref{fig:sftf-kray}) to build a cheap direction-score landscape and
only validates precisely around the promising directions. As Fig.~\ref{fig:sftf-landscape}
shows, the good directions for true support volume form a broad low-cost basin rather
than an isolated point, and the best and worst orientations differ markedly in the
actual amount of support. SFTF therefore finds good candidate regions without densely
evaluating the entire direction space. Crucially, the prior SFTF ultimately compresses
this per-face support-flow information into a \emph{direction score} and a
\emph{direction ranking}, discarding the detail of what support role each face played.
The starting point of this work is to \emph{preserve exactly that discarded per-face
flow field}---reinterpreted as composite drape via Table~\ref{tab:mapping}---and use it
for manufacturability-aware partitioning.

\begin{figure}[ht]
\centering
\includegraphics[width=0.9\linewidth]{FTree4x_fig1_unified_flow.pdf}
\caption{Unified-flow view of SFTF: face-to-face and face-to-bed support are
represented in one framework. (Reproduced from the prior work~\citep{sul_sftf}.)}
\label{fig:sftf-unified}
\end{figure}

\begin{figure}[ht]
\centering
\includegraphics[width=\linewidth]{Bunny69k_kray3000_concept_balanced.pdf}
\caption{SFTF source-face sampling and direction-score landscape on \emph{Bunny 69k}:
rays are cast from only a subset of representative faces to estimate per-direction cost
cheaply. (Reproduced from the prior work~\citep{sul_sftf}.)}
\label{fig:sftf-kray}
\end{figure}

\begin{figure}[ht]
\centering
\includegraphics[width=\linewidth]{figure3_bunny_landscape_support.png}
\caption{\emph{Bunny 69k} direction landscape and the TOMO-computed support at the
1st-optimal (yaw $300^\circ$, pitch $40^\circ$) and 1st-worst (yaw $240^\circ$, pitch
$0^\circ$) orientations. Good directions form a broad valley, not a single point.
(Method of the prior work~\citep{sul_sftf}, recomputed with the shared baseline
engine Tomo\_Shell2026.)}
\label{fig:sftf-landscape}
\end{figure}

\subsection{SFTF-Clustering: reusing the per-face field for partitioning}
SFTF-Clustering preserves this per-face field as features and partitions the mesh
with feature-fusion clustering (k-medoids/DBSCAN/agglomerative) and union-find
region growing, evaluating the benefit of cutting with a ray-free objective:
\begin{equation}
  S(\Pi)\;\approx\;S_{\text{whole}}+\Delta S_{\text{cut}}-\Delta S_{\text{reorient}}.
  \label{eq:rayfree}
\end{equation}
Here $\Delta S_{\text{cut}}$ is the cost incurred by a boundary (seam) and
$\Delta S_{\text{reorient}}$ is the gain from each part adopting its own direction.
Its counter-intuitive finding---\emph{support reduction is governed by each part's
reorientation freedom rather than by preserving support columns}---is what we aim to
translate to the composite setting.

% =====================================================================
\section{Method}
% =====================================================================
The overall flow is shown in Fig.~\ref{fig:pipeline}. Only the per-face drape field
is new; the partition families, objective and automatic patch count are reused
verbatim.

\subsection{Problem restatement and feature mapping}
We partition a complex surface into manufacturable patches, each choosing its own
\textbf{drape seed} (reference direction and origin). For face $i$, we solve a
kinematic drape mapping from that seed and record per-face descriptors (an extension
of the classical geometric drape mapping~\citep{vanderweeen1991}). The correspondence
with the support flow is given in Table~\ref{tab:mapping}.

\begin{table}[ht]\centering
\caption{Mapping from per-face support flow (AM) to composite drape flow.}
\label{tab:mapping}
\begin{tabular}{ll}
\toprule
SFTF support flow (AM) & composite drape flow \\
\midrule
overhang $O_i=\max(0,-m_i\!\cdot\! n)$ & shear angle $\gamma_i$ (locking violation) \\
signed tilt $\tau_i=m_i\!\cdot\! n$ & seed alignment $s\!\cdot\! n$ / fibre angle $\theta_i$ \\
build-plate height $\eta_i$ & geodesic depth $g_i$ from the seed \\
support role $\rho$ & drape regime $\rho\!\in\!\{\text{dev},\text{shear},\text{dart}\}$ \\
support height $h_i$ & shear accumulation $\Kabs\,g$ \\
receiver count $r_i$ & curvature concentration $\Kabs$ \\
\bottomrule
\end{tabular}
\end{table}

The feature matrix keeps the same form,
\begin{equation}
  \Phidr=\mathrm{zscore}\!\left([\,\gamma,\ \theta,\ g,\ \Kabs\,g,\ \Kabs\,]\right)\in\mathbb{R}^{N\times5},
\end{equation}
and substitutes directly for the support-flow feature block.

\subsection{The drape field}
The new core module is the \textbf{drape field}. For a fixed surface and seed
direction it produces per-face descriptors and, sharing the field names of the
public partitioner's feature class, acts as a drop-in. The first-order shear proxy is
\begin{equation}
  \gamma_i \;\approx\; \Kabs_i\, g_i^{2},
  \label{eq:proxy}
\end{equation}
dimensionless, zero on developable surfaces and growing with
$\text{(curvature)}\times\text{(distance)}^2$. Gaussian curvature $K$ is computed by
the angle deficit and geodesic distance $g$ by Dijkstra. The drape regime is
classified into $\{$developable, shear, dart$\}$ by local developability $\Kabs L^2$
and the shear threshold $\gamma\ge\gamma_{\text{lock}}$. Under a single global seed
most of a body/organ becomes ``dart'', correctly reflecting that one ply cannot
cover a torso---which is precisely the motivation to partition.

\paragraph{Reading Eq.~\eqref{eq:proxy} intuitively.}
When a flat fabric (or prepreg) is laid on a curved surface, the two originally
orthogonal yarn families (warp and weft) \emph{scissor} apart, so their crossing angle
deviates from $90^\circ$. This deviation is the shear angle $\gamma$, the measure of
wrinkle risk. Why the \emph{square} of distance? By the Gauss--Bonnet theorem, the
total curvature inside a geodesic disk of radius $g$ is $\int K\,dA\approx K\cdot(\pi
g^2)$, proportional to \emph{area} ($\sim g^2$). The fabric must absorb this
accumulated curvature as shear, hence $\gamma\sim\Kabs\,g^2$: shear grows both with how
strongly the surface curves ($\Kabs$) and with geodesic distance from the seed ($g$).

The field then labels each face into three \emph{regimes}.
\textbf{Developable} ($\Kabs\!\approx\!0$): cylinders/cones lay flat without
stretching, no wrinkles.
\textbf{Shear}: the surface is covered with mild scissoring.
\textbf{Dart}: the shear exceeds the material locking angle, so the fabric can twist no
further and a wedge must be \emph{cut out (a dart)} for it to seat.
Fig.~\ref{fig:angledeficit} explains why such a dart arises, via the angle deficit.

\begin{figure}[ht]
  \centering
  \begin{tikzpicture}[font=\footnotesize, scale=0.95]
    % (a) developable: six 60-degree wedges sum to 360 -> closes flat
    \begin{scope}
      \foreach \a in {0,60,...,300}{
        \fill[blue!10, draw=blue!55] (0,0) -- (\a:1.6) -- ({\a+60}:1.6) -- cycle;}
      \fill[black] (0,0) circle (1.2pt);
      \node at (0,-2.15) {(a) developable $K{=}0$};
      \node at (0,-2.7) {$\sum\theta=360^\circ$, no dart};
    \end{scope}
    % (b) positive curvature: five 60-degree wedges sum to 300 -> 60-degree gap = dart
    \begin{scope}[shift={(5.4,0)}]
      \foreach \a in {0,60,...,240}{
        \fill[orange!14, draw=orange!75] (0,0) -- (\a:1.6) -- ({\a+60}:1.6) -- cycle;}
      \fill[black] (0,0) circle (1.2pt);
      \draw[red!75, very thick, dashed] (0,0) -- (300:1.6);
      \draw[red!75, very thick, dashed] (0,0) -- (360:1.6);
      \draw[red!75, -{Stealth}] (330:1.95) arc (330:360:1.95);
      \draw[red!75, -{Stealth}] (330:1.95) arc (330:300:1.95);
      \node[red!75!black] at (330:1.05) {dart};
      \node at (0,-2.15) {(b) positive $K{>}0$};
      \node at (0,-2.7) {$\sum\theta<360^\circ$ = deficit $\delta$};
    \end{scope}
  \end{tikzpicture}
  \caption{Origin of a dart, seen as angle deficit. If the triangle angles around a
  vertex sum to (a) $360^\circ$ the surface flattens perfectly (developable, $K{=}0$);
  if they sum to (b) less than $360^\circ$ (positive Gaussian curvature) a
  wedge-shaped \emph{angle deficit} $\delta$ remains when flattened. This deficit is the
  geometric analogue of a \textbf{dart} (the real fabric dart also depends on shear,
  boundary conditions and curvature sign), and Gaussian curvature is this deficit per
  unit area ($K\!\approx\!\delta/A$). The drape field's $\gamma\approx\Kabs\,g^2$ is the
  amount of this deficit accumulated out to geodesic distance $g$ from the seed.}
  \label{fig:angledeficit}
\end{figure}

\begin{figure}[ht]
  \centering
  \includegraphics[width=0.62\linewidth]{Fig5_drapefield.png}
  \caption{Drape field on a spherical cap. The shear severity
  $\gamma\approx\Kabs\,g^2$ is $\approx0$ at the pole (seed, $g{=}0$) and grows
  outward with geodesic distance $g$. On a developable surface $\Kabs{\approx}0$, so
  $\gamma{\approx}0$ everywhere.}
  \label{fig:drapefield}
\end{figure}

\subsection{Pin-jointed net (fishnet): real trellis shear}
\paragraph{Why the proxy alone is not enough.}
The proxy $\gamma\approx\Kabs\,g^2$ of Eq.~\eqref{eq:proxy} is an \emph{orientation-blind}
lower bound. A real fabric behaves like a net whose two yarn families (warp and weft)
are \emph{pinned} at their crossings: the yarns barely stretch but are free to
\emph{rotate} about each crossing---this is trellis (scissor) shear. Hence, on the same
surface, the actual shear depends on which direction the yarns were laid, a distinction
the proxy cannot make. To measure it accurately one must actually ``lay'' the fabric.

\paragraph{The pin-jointed net model.}
Starting from a square grid, it lays the net one cell at a time along the surface
(projected-straightest geodesic marching $+$ cell closure; exact point-to-triangle
projection on arbitrary triangle meshes), keeping every yarn segment inextensible
($\text{edge\_error}\sim10^{-15}$). At each cell, the amount by which the warp--weft
crossing angle departs from $90^\circ$ is the \emph{measured} trellis shear angle
(Fig.~\ref{fig:trellisschem}); once it exceeds the material locking angle (typically
$30$--$50^\circ$) the cell wrinkles. A single net starts from one seed, so it covers
only one coherent patch and stops at boundaries or high distortion ($\sim22/100$ nodes
laid stably per seed on the manikin); this ``one ply cannot cover everything'' is the
motivation for the multi-seed partitioning of the next subsection.

\begin{figure}[ht]
  \centering
  \begin{tikzpicture}[font=\footnotesize]
    % (a) undeformed orthogonal net
    \foreach \x in {0,1,2,3}{\draw[blue!60,thick] (\x,0)--(\x,3);}
    \foreach \y in {0,1,2,3}{\draw[blue!60,thick] (0,\y)--(3,\y);}
    \foreach \x in {0,1,2,3}{\foreach \y in {0,1,2,3}{\fill[blue!60] (\x,\y) circle (1.3pt);}}
    \draw[->] (0.04,2.0) -- (0.04,2.9) node[left=-1pt]{warp};
    \draw[->] (1.0,0.04) -- (1.9,0.04) node[below=-1pt]{weft};
    \node at (1.5,-0.85) {(a) undeformed: orthogonal $\gamma{=}0$};
    % shear arrow between panels
    \draw[-{Stealth}, very thick, red!70] (3.5,1.5) -- (5.1,1.5)
      node[midway, above]{shear};
    % (b) sheared net (warp tilts; cm shear keeps weft horizontal)
    \begin{scope}[cm={1,0,0.5,1,(5.7cm,0cm)}]
      \foreach \x in {0,1,2,3}{\draw[orange!80,thick] (\x,0)--(\x,3);}
      \foreach \y in {0,1,2,3}{\draw[orange!80,thick] (0,\y)--(3,\y);}
      \foreach \x in {0,1,2,3}{\foreach \y in {0,1,2,3}{\fill[orange!80] (\x,\y) circle (1.3pt);}}
    \end{scope}
    % crossing-angle marker at sheared origin (absolute coords)
    \draw[red!75] (6.3,0) arc (0:63:0.6);
    \node[red!75!black] at (6.95,0.42) {\scriptsize $90^\circ{-}\gamma$};
    \node at (8.0,-0.85) {(b) sheared: $\gamma{>}0$ (scissoring)};
  \end{tikzpicture}
  \caption{Trellis shear of the pin-jointed net. (a) Before deformation the two yarn
  families (warp/weft) are pinned at their crossings and orthogonal ($\gamma{=}0$).
  (b) To cover a surface, the yarn lengths are preserved while the crossings rotate
  \emph{like scissors}, reducing the crossing angle to $90^\circ-\gamma$. This $\gamma$
  is the measured per-cell trellis shear, and beyond the material locking angle the
  cell wrinkles. Because every yarn segment stays inextensible
  (edge\_error~$10^{-15}$), this angle is the \emph{measured} wrinkle risk.}
  \label{fig:trellisschem}
\end{figure}

\subsection{Multi-seed re-seeding and discrete ply angles}
We translate the multi-direction mechanism directly.

\paragraph{The single-seed limitation.}
With only one reference point (seed), Eq.~\eqref{eq:proxy} makes the shear $\gamma$
grow with the square of distance from it. On a large surface, regions far from the seed
are therefore almost all labelled ``dart'' (Fig.~\ref{fig:multiseedschem}a), yielding
nothing but the conclusion ``one ply cannot cover it''.

\paragraph{Multi-seed re-seeding.}
The remedy is to use several reference points. We place $K$ spread-out
seeds\footnote{Seed locations are chosen by farthest-point sampling: the next seed is
the face farthest from all already-chosen seeds, so the seeds spread evenly over the
surface.} and, for each face $i$, compute the per-seed drape cost $c_{ik}$ and keep
only the \emph{cheapest} seed ($\min_k c_{ik}$). Each face is then covered from a seed
\emph{near it}, keeping the geodesic distance $g$ small, and the dart-dominated
single-seed field collapses (Fig.~\ref{fig:multiseedschem}b). This is \emph{re-seeding
freedom}, the composite translation of the prior work's reorientation freedom (``each
part chooses its own best direction'').

\paragraph{Discrete ply angles.}
Real layup cannot lay fibres at an arbitrary angle, only at a few manufacturable ones.
We therefore \emph{snap} the continuous per-patch optimum (computed on the net) to the
menu $\{0,\pm45,90\}^\circ$ that gives the lowest shear.

\begin{figure}[ht]
  \centering
  \begin{tikzpicture}[font=\footnotesize]
    % (a) single seed: gamma grows with distance -> outer band is dart
    \fill[red!22]    (0,0) circle (1.7);
    \fill[yellow!35] (0,0) circle (1.15);
    \fill[green!35]  (0,0) circle (0.55);
    \fill[black] (0,0) circle (1.6pt);
    \node[above right=-2pt] at (0,0) {seed};
    \draw[-{Stealth}] (0,0) -- (35:1.7) node[midway, above, sloped]{$g$};
    \node[red!75!black] at (-1.15,1.15) {\scriptsize dart};
    \node at (0,-2.15) {(a) single seed: $\gamma\approx\Kabs g^2\!\uparrow$};
    % (b) multi-seed: region tiled by nearby seeds -> mostly low shear
    \begin{scope}[shift={(5.6,0)}]
      \fill[green!30] (0,0) circle (1.7);
      \draw[white, very thick] (0,-1.7) -- (0,1.7);
      \draw[white, very thick] (-1.7,0) -- (1.7,0);
      \draw[black!55] (0,0) circle (1.7);
      \foreach \p in {(0.8,0.8),(-0.8,0.8),(0.8,-0.8),(-0.8,-0.8)}{
        \fill[black] \p circle (1.6pt);}
      \node at (0,-2.15) {(b) multi-seed: $\min_k c_{ik}$};
    \end{scope}
  \end{tikzpicture}
  \caption{Principle of single vs.\ multi-seed. (a) With one seed the shear grows with
  the square of distance ($\gamma\approx\Kabs g^2$), so the outer band far from the
  seed becomes all dart (red). (b) With several spread-out seeds, each face picks its
  nearest (cheapest) seed ($\min_k c_{ik}$), keeping geodesic distance small so most of
  the region turns low-shear (green). This re-seeding freedom collapses the
  dart-dominated field.}
  \label{fig:multiseedschem}
\end{figure}

\subsection{Seam-vs-realign objective and automatic patch count}
We reinterpret Eq.~\eqref{eq:rayfree} in drape terms:
\begin{equation}
  \text{cost}(\Pi)=\sum_{\ell}\min_{\text{seed}}\sum_{i\in P_\ell}A_i\,\text{shear}_i(\text{seed})
  \;+\;w_{\text{seam}}\,\mathrm{seamlen}(\Pi),
\end{equation}
where the first term is the (area-weighted) shear each patch reduces by realigning to
its own seed, and the second is the fibre-continuity cut (seam length). The automatic
patch count sweeps $K$ and selects $\Kstar$ at the knee of the normalised cost curve
with a complexity penalty $\alpha K/K_{\max}$.

\subsection{Engine integration and benchmark}
Only the drape-field generation is new; an adapter drives the public
\texttt{partition\_mesh} without modification. The benchmark compares coordinate
k-medoids, axis slabs, curvature, and the drape-aware partition on a difficulty
ladder (developable $\sim$ doubly curved $\sim$ real meshes) using manufacturing
metrics (locking-exceedance area, dart fraction, drape purity, seam).

\paragraph{Implementation environment.}
All experiments ran on a Windows~11 workstation with an AMD Ryzen~9 9950X3D CPU
(16~cores/32~threads) and 125~GB RAM. The drape field, the partitioner and the
manufacturing metrics are single-machine CPU code in Python~3.12 (NumPy, SciPy,
Trimesh, scikit-learn), with optional Open3D for screened-Poisson remeshing and an
in-house Baraff--Witkin implicit cloth solver (\texttt{cfmsDrape}, a native DLL) for
the high-fidelity validation of \S\ref{sec:baraff}. All reported run times are
wall-clock on this machine.

% =====================================================================
\section{Results}
% =====================================================================
\subsection{Re-seeding freedom collapses the dart-dominated field}
In plain terms, the ``dart fraction'' in Table~\ref{tab:r2} is the \emph{fraction of
faces that one ply cannot lay and that therefore need a wedge cut out} ($0$ means the
whole region can be laid as one sheet; near $1$ almost everything must be cut). With a
single seed (the point where the fabric is first anchored), $98\%$ of the manikin's
faces are darts; letting each patch use its own seed (multi-seed, the principle of
Fig.~\ref{fig:multiseedschem}) drops this to $42\%$ (with $\approx260$ per-patch
seeds; a mere $8$ seeds only reach $88\%$, showing that a body-shaped shell needs
\emph{sufficiently small} patches).

As shown in Table~\ref{tab:r2}, letting each patch adopt its own seed sharply reduces
the dart fraction (manikin $0.98\to0.42$, analytic sphere $0.36\to0.00$). The
remaining darts are \emph{intrinsic} high-curvature regions (fingers, folds) that no
seed can lay flat---the composite translation of the reorientation-freedom finding.

\begin{table}[ht]\centering
\caption{Single- vs multi-seed. The proxy $\gamma\approx\Kabs g^2$ is a dimensionless
first-order severity; for regime labelling a face is flagged a ``dart'' when $\gamma$
exceeds a \emph{proxy threshold calibrated to the locking angle} (not a direct
angle comparison). The min-shear columns are therefore in raw proxy units (scale-dependent);
the calibrated trellis angle in degrees comes from the fishnet/Baraff validation
(Fig.~\ref{fig:trellis}).}
\label{tab:r2}
\begin{tabular}{lccc}
\toprule
mesh & single-seed dart & multi-seed dart & mean min-shear (single$\to$multi) \\
\midrule
sphere cap (analytic) & 0.36 & \textbf{0.00} ($k{=}8$) & $0.63\to0.18$ \\
manikin (13.7k F) & 0.98 & \textbf{0.42} ($\approx260$ per-patch seeds) & $13150\to6.9$ \\
liver (19.4k F) & 0.86 & \textbf{0.45} ($k{=}16$) & $92\to3.2$ \\
\bottomrule
\end{tabular}
\end{table}

\begin{figure}[ht]
  \centering
  \includegraphics[width=0.72\linewidth]{Fig2_reseeding.png}
  \caption{Re-seeding freedom. Letting each patch adopt its own seed sharply reduces
  the dart fraction (manikin $0.98\!\to\!0.42$, sphere $0.36\!\to\!0.00$); the
  remaining darts are intrinsic high-curvature regions.}
  \label{fig:reseeding}
\end{figure}

The discrete ply-angle menu picks an aligned angle ($0^\circ/90^\circ$, $\sim0^\circ$
shear) on a developable cylinder, and $45^\circ$ on a sphere ($6.6\times$ lower than
the worst orientation).

\subsection{Seam-vs-realign automatic patch count}
As in Table~\ref{tab:r3}, developable moulds give $\Kstar{=}1$ (cutting never pays),
whereas doubly curved moulds set the patch count at the cost knee. On the real manikin
the proxy returns $\Kstar{=}1$ (intrinsic curvature), but scoring with the real
per-patch net halves the per-patch cost and flips it to $\Kstar{=}5$. Coupling the
$\{0,\pm45,90\}$ angle optimisation restores developable $\Kstar{=}1$ (cylinder
$2\to1$), halves the sphere shear ($5.9^\circ\to2.8^\circ$), and lets the manikin use
fewer patches ($5\to2$) with a realistic angle mix.

\begin{table}[ht]\centering
\caption{Automatic patch count. Proxy cost vs real net cost.}
\label{tab:r3}
\begin{tabular}{lccc}
\toprule
mould & curvature & proxy $\Kstar$ & net $\Kstar$ \\
\midrule
plane / cylinder & developable & 1 & 1 \\
sphere cap & doubly curved & 6 & 4 \\
saddle & doubly curved & 6 & --- \\
manikin (13.7k F) & intrinsic high curvature & 1 & \textbf{5} \\
\bottomrule
\end{tabular}
\end{table}

\begin{figure}[ht]
  \centering
  \includegraphics[width=0.74\linewidth]{Fig3_autocount.png}
  \caption{Seam-vs-realign cost vs patch count $K$ (normalised to a common scale).
  The developable cylinder is flat near $0$ with $\Kstar{=}1$ (no benefit to cutting);
  the doubly curved sphere and saddle offset the cut cost and pick $\Kstar{=}6$ at the
  knee.}
  \label{fig:autocount}
\end{figure}

\subsection{Real meshes and engine integration}
The drape field is computed in $0.34$\,s (manikin, 13.7k F) and $0.22$\,s (liver,
19.4k F) and flows directly into the public partitioner. The $\Kabs$ coherence in
Table~\ref{tab:r4} (within-patch curvature std / global std; lower is more
curvature-coherent) decreases with patch count at a fixed method (k-medoids
$0.81\to0.61$ from $k{=}6$ to $12$), indicating the partition groups similar-curvature
surface rather than being merely spatial. The drape-region-grow rows reach purity
$1.000$, but at $608$/$291$ patches; that purity is an over-segmentation effect (many
tiny, trivially homogeneous patches), not a matched-budget comparison with the
$k{=}6$/$12$ k-medoids, so we do not read it as evidence of superiority.

\begin{table}[ht]\centering
\caption{Real-mesh partitioning. Seed $=+z$, locking $45^\circ$. Purity is the
fraction of each patch in a single drape regime.}
\label{tab:r4}
\begin{tabular}{llccc}
\toprule
mesh & method & patches & drape purity & $\Kabs$ coherence $\downarrow$ \\
\midrule
manikin & kmedoids $k{=}6$ & 6 & 0.977 & 0.81 \\
manikin & kmedoids $k{=}12$ & 12 & 0.977 & 0.61 \\
manikin & drape-region grow & 608 & 1.000 & 0.49 \\
liver & kmedoids $k{=}6$ & 6 & 0.861 & 0.87 \\
liver & drape-region grow & 291 & 1.000 & 0.49 \\
\bottomrule
\end{tabular}
\end{table}

\subsection{Application cases: real anatomical and engineering meshes}
We apply \emph{our drape field} with feature-fusion k-medoids to organs (liver,
kidney) and a bust (Nefertiti); see Figs.~\ref{fig:app_organs}--\ref{fig:app_nefertiti}
(patch colour $=$ drape-coherent patch). Drape purity is $0.85$ (kidney), $0.86$
(liver), $0.95$ (Nefertiti); patch boundaries follow curvature/drape regime.

\paragraph{Post-processing for manufacturable patches.}
Feature-space clustering labels each face \emph{independently}, and the imported mesh
itself may contain pieces whose vertices coincide in space but not in index (triangle
soup)---so the raw result is hard to cut and lay up. We apply a four-stage
post-process.
\textbf{(1) Mesh conditioning.} Weld near-coincident vertices to reconnect split seams,
drop duplicate/degenerate faces, keep only sizeable connected components, and make the
winding consistent.
\textbf{(2) Remeshing (engineering shells only).} Soup-heavy shells are remeshed into
clean drape shells/components (the seam staircase disappears); edge subdivision instead
\emph{cracks} a non-watertight mesh (it took the car from $277$ to $903$ components),
so resampling is required. We implement two methods (compared in
Fig.~\ref{fig:app_remesh}). \emph{(i) Voxel remeshing} voxelizes the surface, fills the
interior and re-extracts the outer surface by marching cubes, giving a single watertight
shell but rounding sharp edges to the voxel resolution. \emph{(ii) Screened-Poisson
reconstruction}~\citep{kazhdan2013poisson} samples oriented points and solves the
Poisson equation to a smooth isosurface, which \emph{preserves features} (the car's door
lines, the hull contour). We use (ii) by default (when open3d is available) and fall
back to (i) otherwise.
\textbf{(3) Boundary regularization.} The precursor SFTF-Clustering's
\emph{dihedral-weighted graph-cut} (an MRF solved by ICM, iterated conditional modes)
relabels each face to minimise a \emph{data cost} (feature-space distance to its patch
centroid) plus a \emph{cut cost} ($\lambda$-weighted, large on flat areas and small
along concave creases), so seams become short and align to the concave curves where a
real dart/seam would sit; a majority-vote pass then straightens any residual
triangle-scale staircase.
\textbf{(4) Small-region absorption.} Same-label components below a face-count
threshold are absorbed into the neighbour they share the most boundary with, removing
speckle ($\lambda{=}3$, as in the precursor).
This cuts Nefertiti's seam-edge fraction from $0.047$ to $0.009$ and its disconnected
fragments from $1508$ to $6$ (Fig.~\ref{fig:app_smooth}); for the soup-heavy engineering
shells the cached Poisson-remesh pipeline gives drape purity $0.915$ (airliner, with
both engine components preserved) and $0.949$ (car), while the open yacht hull is lower
at $0.632$; their seam-edge fractions are $0.009$--$0.012$
(Figs.~\ref{fig:app_condition},~\ref{fig:app_remesh}). All application figures below use
this post-process.

\begin{figure}[ht]\centering
  \includegraphics[width=0.40\linewidth]{App_nefertiti_raw.png}\hfill
  \includegraphics[width=0.40\linewidth]{App_nefertiti.png}
  \caption{\emph{Boundary regularization}, before (left) vs.\ after (right), same mesh.
  Left: raw feature-fusion labels---jagged boundaries and scattered specks (triangle
  soup). Right: after dihedral-weighted MRF smoothing $+$ seam straightening $+$
  small-region absorption---smooth, curvature-aligned seams with the speckle removed
  (seam-edge fraction $0.047\!\to\!0.009$, fragments $1508\!\to\!6$).}
  \label{fig:app_smooth}
\end{figure}

\begin{figure}[ht]\centering
  \includegraphics[width=0.31\linewidth]{App_obj_car_supra_soup.png}\hfill
  \includegraphics[width=0.31\linewidth]{App_obj_car_supra_conditioned.png}\hfill
  \includegraphics[width=0.31\linewidth]{App_obj_car_supra.png}
  \caption{\emph{Three-stage} repair of an engineering shell (car body, top view).
  Left: raw import---faces whose coordinates match but whose indices are split leave the
  surface in $277$ disconnected pieces with staircased boundaries and slivers. Middle:
  after vertex welding, duplicate-face removal and large-component keeping ($8$
  components)---connected, but a triangle-scale staircase remains. Right: after
  screened-Poisson remeshing---a single smooth shell with curved seams that preserves
  features such as the door lines.}
  \label{fig:app_condition}
\end{figure}

\begin{figure}[ht]\centering
  \includegraphics[width=0.40\linewidth]{App_obj_car_supra_voxel.png}\hfill
  \includegraphics[width=0.40\linewidth]{App_obj_car_supra.png}
  \caption{Remesh-method comparison (car body). Left: \emph{voxel remeshing}---a single
  watertight shell, but sharp edges round off (an outer envelope; drape purity $0.70$).
  Right: \emph{screened-Poisson}~\citep{kazhdan2013poisson}---preserves features (door
  lines, body contour), giving a smoother result and higher drape purity ($0.95$).}
  \label{fig:app_remesh}
\end{figure}

\begin{figure}[ht]\centering
  \includegraphics[width=0.47\linewidth]{App_kidney.png}\hfill
  \includegraphics[width=0.47\linewidth]{App_liver.png}
  \caption{Drape-field partition ($k{=}6$) of the kidney (12.4k F; left) and liver
  (19.4k F; right). Drape purity $0.85$ / $0.86$; patches follow curvature regions.}
  \label{fig:app_organs}
\end{figure}

\begin{figure}[ht]\centering
  \includegraphics[width=0.46\linewidth]{App_nefertiti.png}
  \caption{Drape-field partition of the Nefertiti bust (99.9k F; $k{=}8$, drape purity
  $0.95$). Patches follow the curvature regions of crown, face, neck and chest.}
  \label{fig:app_nefertiti}
\end{figure}

We further apply the same partition to doubly curved free-form shells (seashells)
from the public Thingi10K dataset~\citep{zhou2016thingi10k}
(Fig.~\ref{fig:app_shells}). Seashells are canonical non-developable surfaces and are
themselves natural laminated composites (nacre). All three score drape purity
$0.96\text{--}0.98$.

\begin{figure}[ht]\centering
  \includegraphics[width=0.31\linewidth]{App_thingi_turritella_shell_44704.png}\hfill
  \includegraphics[width=0.31\linewidth]{App_thingi_oxystele_shell_46774.png}\hfill
  \includegraphics[width=0.31\linewidth]{App_thingi_shell01_41909.png}
  \caption{Drape-field partition ($k{=}6$) of doubly curved free-form shells
  (seashells) from Thingi10K: Turritella (left), Oxystele (centre), Shell~01 (right).
  Drape purity $0.96$/$0.98$/$0.98$.}
  \label{fig:app_shells}
\end{figure}

Finally we apply it to \textbf{engineering composite shells}---an aircraft fuselage, a
car body and a yacht hull (Fig.~\ref{fig:app_eng})---from
Objaverse~\citep{deitke2023objaverse} (CC-BY); the Boeing 787 is an iconic
carbon-composite airliner. Doubly curved shells such as fuselages, wings and hulls are
direct application targets, whereas bicycles and golf clubs (tube/rod structures) are
not shell-drape targets and are excluded. These Objaverse shells are non-manifold with
disconnected pieces in the imported mesh, so they are partitioned after the
\emph{screened-Poisson remeshing} above, which yields smooth, feature-preserving
shell components with curved seams and improves drape purity for the airliner/car cases
($0.915$/$0.949$). Poisson trims its extrapolated surface at a density quantile, so watertightness
can break where the data is sparse (use the voxel remesh if a strictly watertight shell
is required), with no effect on patch/seam planning. For railing-heavy open assemblies
such as the yacht, Poisson closes the surface into a smooth outer hull but loses the fine
deck structures, so the drape target is then the hull shell only (purity $0.632$).

\begin{figure}[ht]\centering
  \includegraphics[width=0.37\linewidth]{App_obj_airplane_b787.png}\hfill
  \includegraphics[width=0.30\linewidth]{App_obj_car_supra.png}\hfill
  \includegraphics[width=0.30\linewidth]{App_obj_yacht.png}
  \caption{Drape-field partition ($k{=}6$) of engineering composite shells: Boeing 787
  airliner (left), Toyota Supra body (centre), yacht hull (right). Objaverse (CC-BY).}
  \label{fig:app_eng}
\end{figure}

\subsection{Quantitative comparison of methods}
\label{sec:compare}
We apply the segmentation methods from the Related Work---coordinate
k-means~\citep{lloyd1982}, longest-axis slabs (axis-BSP), curvature clustering, and
Variational Shape Approximation (VSA)~\citep{cohensteiner2004vsa}---and our
drape-aware partition to the nine meshes of
Figs.~\ref{fig:app_organs}--\ref{fig:app_eng} ($k{=}6$, locking $45^\circ$) and
compare with manufacturing metrics. The aggregate (Table~\ref{tab:cmp-agg}) reports
lock\_area, dart, purity and seam averaged over all nine meshes; the
\textbf{flattening-distortion} metrics, which are unreliable on the non-manifold
engineering imports, are reported separately on the \textbf{six non-engineering meshes}
(Table~\ref{tab:cmp-flat}), and the per-mesh lock\_area table (Table~\ref{tab:cmp-lock})
likewise uses the six, since on the three engineering meshes lock\_area is
partition-insensitive (set by intrinsic curvature). The two flattening metrics measure
how easily each patch unfolds to a flat cutting pattern (zero on a developable patch):
LSCM~\citep{levy2002lscm} (conformal) and ARAP~\citep{liu2008arap} (inextensible
stretch, closer to the yarn inextensibility of the trellis).

\begin{table}[ht]\centering
\caption{Method comparison, mean over the nine meshes (partition-sensitive metrics
only). All metrics are lower-is-better except purity. Flattening distortion (LSCM/ARAP)
is reported separately on the six non-engineering meshes in Table~\ref{tab:cmp-flat}.}
\label{tab:cmp-agg}
\begin{tabular}{lcccc}
\toprule
method & lock\_area $\downarrow$ & dart $\downarrow$ & purity $\uparrow$ & seam $\downarrow$ \\
\midrule
k-means (coordinate; mfg-blind) & \textbf{0.469} & \textbf{0.643} & 0.770 & \textbf{1271} \\
axis-BSP & 0.531 & 0.692 & 0.780 & 1700 \\
curvature & 0.596 & 0.738 & \textbf{0.825} & 5253 \\
VSA~\citep{cohensteiner2004vsa} & 0.553 & 0.712 & 0.793 & 4810 \\
\textbf{drape-aware (ours)} & \underline{0.490} & \underline{0.675} & 0.776 & 2428 \\
\bottomrule
\end{tabular}
\end{table}

\begin{table}[ht]\centering
\caption{Per-mesh wrinkle risk lock\_area (area fraction with shear above locking;
lower is better). Among the surface-modelling methods (curvature$\cdot$VSA$\cdot$axis),
ours is consistently the lowest and approaches the spatial-compactness ceiling
(k-means). Engineering meshes are omitted as lock\_area is partition-insensitive there.}
\label{tab:cmp-lock}
\begin{tabular}{lccccc}
\toprule
mesh & k-means & axis-BSP & curvature & VSA & ours \\
\midrule
kidney & \textbf{0.273} & 0.474 & 0.651 & 0.478 & \underline{0.360} \\
liver & \textbf{0.337} & 0.532 & 0.690 & 0.528 & \underline{0.401} \\
Nefertiti & \textbf{0.716} & 0.767 & 0.851 & 0.797 & \underline{0.738} \\
shell-01 & \textbf{0.761} & 0.889 & 0.948 & 0.948 & \underline{0.799} \\
turritella & 0.916 & 0.902 & 0.952 & 0.957 & \textbf{0.899} \\
oxystele & 0.913 & 0.907 & 0.958 & 0.958 & \textbf{0.905} \\
\bottomrule
\end{tabular}
\end{table}

\begin{table}[ht]\centering
\caption{Per-mesh ARAP inextensible flattening stretch on the six non-engineering
meshes (lower is easier to flatten; zero if developable). Curvature clustering is worst
on every one of these meshes and ours beats it consistently, but normal-proxy VSA and
compact k-means flatten well too, so ours is competitive rather than dominant on
flattenability.}
\label{tab:cmp-flat}
\begin{tabular}{lccccc}
\toprule
mesh & k-means & axis-BSP & curvature & VSA & ours \\
\midrule
kidney & 0.078 & 0.150 & 0.554 & \textbf{0.036} & 0.150 \\
liver & 0.255 & 0.135 & 0.613 & \textbf{0.075} & 0.240 \\
Nefertiti & \textbf{0.209} & 0.235 & 0.643 & 0.216 & 0.292 \\
shell-01 & 0.161 & 0.126 & 0.728 & \textbf{0.120} & 0.146 \\
turritella & 0.187 & 0.269 & 0.655 & 0.244 & \textbf{0.201} \\
oxystele & \textbf{0.100} & 0.227 & 0.728 & 0.422 & \underline{0.163} \\
\bottomrule
\end{tabular}
\end{table}

\paragraph{Honest reading.} Three points emerge. (1) \emph{Spatial compactness}
(k-means) is a strong baseline on the raw costs (lock\_area, dart, seam) but is a
\emph{manufacturing-blind} partition that sees neither curvature nor shear. (2) Among
the \emph{surface-modelling} segmentation methods (curvature, VSA, axis-BSP),
\textbf{ours has the lowest lock\_area} (Table~\ref{tab:cmp-lock}: within the top two on
every one of the six non-engineering meshes, and first overall on turritella and
oxystele) and, in aggregate, also the lowest dart among them
(Table~\ref{tab:cmp-agg}), because it fuses spatial compactness with drape features.
(3) Curvature and VSA cluster only by curvature/normal and reach high purity (almost
tautologically, since the regime derives from curvature) but over-fragment, giving
$2\text{--}4\times$ larger seams. On flattenability (ARAP inextensible stretch;
Table~\ref{tab:cmp-flat}) \textbf{curvature clustering is worst on every one of the six
meshes} and ours beats it consistently, but normal-proxy VSA and
compact k-means flatten as well or better (planar/compact patches unfold easily), so
ours does not \emph{dominate} flattenability. The decisive advantage of our method is
\textbf{re-seeding-aware wrinkle risk} (lock\_area, dart), where it leads the
surface-aware methods. Its value, then, is not beating compactness on raw cost but
achieving near-compactness wrinkle risk \emph{while} using manufacturing-aware
features that enable re-seeding, discrete ply angles, dart flagging and regime
coherence---which k-means cannot provide.

\subsection{Flattening cross-check and double-dome benchmark}
The preceding flattening scores use our in-house ARAP/LSCM implementation, so we first
separate implementation correctness from fabric physics. On open developable patches
with closed-form isometric unrolls, the analytic cross-check gives RMS/characteristic
length residuals of \(6.73\times10^{-5}\) on a cylinder and \(5.83\times10^{-5}\) on a
cone for ARAP, with edge-length-ratio standard deviation reported as \(0.0000\) at the
displayed precision (Table~\ref{tab:extra-validation}). Thus the solver reproduces
exact developable unrolls. The optional libigl path is reserved for third-party
cross-checks on non-developable meshes; in the present environment it is skipped unless
libigl is installed.

We then use a parametric double-dome benchmark as a woven-composite forming sanity check
(Fig.~\ref{fig:double-dome-validation}). On a \(9434\)-face double-dome, the kinematic
fishnet remains inextensible (edge error \(0.0000\) at the displayed precision) and
predicts a diagonal-section peak shear of \(39.1^\circ\), below the \(45^\circ\) locking
angle for this geometry. In contrast, ARAP flattening reports only \(4.8^\circ\) peak
shear. This reinforces the same interpretation as the method comparison: ARAP is useful
for developable exactness and pattern distortion, whereas shear and wrinkle risk should
be read from the fishnet model or a mechanics solver. The benchmark script includes an
experimental-overlay hook, but no external measurements are fabricated here.

\begin{table}[ht]\centering
\caption{Additional flattening and forming validation checks.}
\label{tab:extra-validation}
\begin{tabular}{lll}
\toprule
check & geometry & observed result \\
\midrule
analytic unroll & cylinder, cone &
ARAP RMS/char \(6.73\times10^{-5}\), \(5.83\times10^{-5}\) \\
double dome & 9434 faces &
fishnet peak \(39.1^\circ\), ARAP peak \(4.8^\circ\), edge error \(0.0000\) \\
\bottomrule
\end{tabular}
\end{table}

\begin{figure}[ht]\centering
  \includegraphics[width=\linewidth]{Val_double_dome_report.png}
  \caption{Double-dome forming benchmark. The fishnet model preserves edge length and
  exposes the expected diagonal shear concentration, while ARAP flattening substantially
  under-reports forming shear. The dashed line marks the \(45^\circ\) locking angle used
  for this check.}
  \label{fig:double-dome-validation}
\end{figure}
\FloatBarrier

\subsection{Validation against a high-fidelity Baraff solver}
\label{sec:baraff}
We validate the lightweight kinematic shear field against a Baraff--Witkin
\citep{baraff1998large} implicit cloth solver. The metric recovering shear from the
deformation gradient is analytically verified (pure stretch$\to0$, $20^\circ$
affine$\to20^\circ$, cylinder$\to0$, sphere$\to$grows). The result is an
\textbf{honest negative}: \emph{free-hang gravity drape is not the right boundary
condition for forming}. On a convex dome the sheet avoids shear by draping
developably (mean $\sim2^\circ$, Spearman $\approx0$); in a concave bowl it piles up
with only weak, unstable correlation (Table~\ref{tab:r7}).

\begin{table}[ht]\centering
\caption{Kinematic shear vs Baraff shear, cap-angle sweep, fixed material.}
\label{tab:r7}
\begin{tabular}{lccc}
\toprule
mould & Baraff shear (mean) & proxy Spearman & net Spearman \\
\midrule
dome (convex, free-hang) & $1.8$--$2.6^\circ$ & $-0.03\ldots0.03$ & $-0.01\ldots0.04$ \\
bowl (concave, gravity) & $35$--$44^\circ$ & $-0.03\ldots0.41$ & $0.00\ldots0.27$ \\
\bottomrule
\end{tabular}
\end{table}

To obtain a proper forming condition we added a \textbf{distributed pressure term} to
the solver's implicit RHS (analogous to gravity) and drove a vacuum/diaphragm forming
load. A radial pressure with an apex pin and a woven material (stiff stretch, compliant
shear) gives \textbf{clean conformance} (residual $\sim0.8$\,cm, mean shear
$18.6^\circ$, p90 $35.8^\circ$). Even so, the Baraff forming shear shows
\textbf{essentially no} correlation with the kinematic field (Spearman $0.03$ proxy /
$0.05$ fishnet), for two reasons:
(i) sphere trellis shear carries a \textbf{four-fold angular pattern} (lower on the
warp/weft axes, higher on the $\pm45^\circ$ diagonals; a mild $\sim\!3^\circ$
endpoint contrast over a wrinkle floor of $\sim\!17^\circ$), which the radially
symmetric $\gamma=\Kabs g^2$ cannot see; and (ii) the formed region is dominated by
buckling.
Thus forming does not rescue an element-wise quantitative validation; the field's value
is regime coherence and the re-seeding mechanism, not raw shear prediction.

\begin{figure}[ht]
  \centering
  \includegraphics[width=0.66\linewidth]{Fig6_trellis.png}
  \caption{The honest core of the forming validation. Even on a cleanly conformed
  sphere, the Baraff shear carries a \textbf{mild four-fold trellis signal}---lowest
  on the warp/weft axes ($|\sin2\varphi|{\approx}0$, $16.6^\circ$) and highest on the
  $\pm45^\circ$ diagonals ($|\sin2\varphi|{\approx}1$, $19.7^\circ$), non-monotonic
  across the middle bins because wrinkling floors the whole cap near $17^\circ$. The
  radially symmetric proxy $\gamma=\Kabs g^2$ cannot see this angular structure, so
  the element-wise correlation is essentially zero.}
  \label{fig:trellis}
\end{figure}

% =====================================================================
\section{Discussion and honest limitations}
% =====================================================================
\begin{itemize}
  \item \textbf{Nature of the approximation.} Kinematic drape is a deterministic
        geometric approximation that ignores fabric mechanics and forming forces;
        adequate for first-order screening but not absolute wrinkle magnitude.
  \item \textbf{Material dependence.} The locking angle is material-dependent, so
        results are reported together with the threshold.
  \item \textbf{Seed sensitivity.} The seed/origin choice affects the result; we
        control it with multiple candidates and iteration and report sensitivity.
  \item \textbf{Single-ply scope.} The present scope is a single ply; multi-layer
        stacking sequence and angle schedules are future work.
  \item \textbf{Validation boundary condition.} Free-hang cloth drape is not the right
        reference for forming. A distributed pressure term opens the forming boundary
        condition, but strong element-wise shear agreement is not obtained, being
        intrinsically precluded by the four-fold trellis structure and buckling.
\end{itemize}

% =====================================================================
\section{Conclusion}
% =====================================================================
About $80\%$ of the SFTF-Clustering skeleton (partition families, feature fusion,
region growing, ray-free objective, purity, automatic patch count) is reused
unchanged; the only new module is a single kinematic drape-field generator. The
per-face drape field is a drop-in for the public partitioner; multi-seed re-seeding
collapses the dart-dominated field (manikin $0.98\to0.42$); and the seam-vs-realign
automatic count correctly returns $\Kstar{=}1$ for developable moulds and multiple
patches for doubly curved ones. The comparison against standard methods shows our
partition leads the surface-aware methods on wrinkle risk, and the Baraff validation
shows---honestly---that the value of this lightweight field lies in role-coherent
patches and the re-seeding mechanism rather than in raw shear prediction. Future work
includes an angle/trellis-aware shear field, multi-layer layup, and using the
pressure-driven forming harness to generate forming ground truth.

% =====================================================================
% BACK MATTER (added 2026-07-06; mirrors the SFTF trilogy declarations)
% =====================================================================
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
analysis, Investigation, Data curation, Writing -- original draft, Writing --
review \& editing, Visualization, Funding acquisition.
% NOTE(submission): expand the CRediT roles above if co-authors are added.

\section*{Statements and Declarations}

\paragraph{Ethical considerations.} Not applicable (no human participants, human data,
human tissue, or animals).

\paragraph{Consent to participate.} Not applicable.

\paragraph{Consent for publication.} Not applicable.

\paragraph{Declaration of conflicting interest.}
The author declared no potential conflicts of interest with respect to the research,
authorship, and/or publication of this article.

\paragraph{Funding statement.}
This work was supported by the National Research Foundation of Korea (NRF) grant
funded by the Korean government (MSIT) (NRF-2022R1A2C1010072).

\paragraph{Data availability.}
% NOTE(submission): create this repository and make it PUBLIC before submission.
%   If composite drape partitioning is covered by a patent filing, respect the
%   grace-period timing (trilogy checklist Section E) before making it public.
The drape-field code, the nine-mesh partition caches, and the benchmark and
evaluation scripts supporting the findings of this study are openly available at
\url{https://github.com/cfms-lab/SFTFComposite_2026}. The third-party meshes used in
this study should be obtained from their original sources under their respective
licenses (Thingi10K; Objaverse, CC-BY; and other public repositories cited in the
text).

% =====================================================================
\appendix
\section{2D fabric cutting patterns (for practitioners)}
\label{app:patterns}
% =====================================================================
This appendix unfolds each application-case drape partition into an
\emph{inspection-ready 2D pattern draft}. It is a first-cut layout, not a production
cutting file: a manufacturable pattern would still add seam allowances, ply-orientation
(grain) specifications, manufacturable minimum widths, explicit dart treatment and full
nesting constraints. In every figure the \textbf{left} cell is the same 3D drape partition
as in the main text and the \textbf{right} cell is its corresponding 2D pattern. Each patch is flattened with ARAP (stretch-minimising)\footnote{If
ARAP flattening fails for a patch we fall back to LSCM (conformal); very large patches
are decimated before flattening. ARAP penalises general edge-length stretch, but it does
not explicitly enforce separate warp/weft inextensibility with shear-only trellis
kinematics.} The pieces are then nested on a fixed-width fabric roll
using convex-hull cutting lines as the collision polygons, with no rotation so
that the fibre grain direction is preserved. Unless otherwise noted, the dimensionless
mesh layouts are normalized to a 100 cm carbon-fabric roll width. Black arrows mark the
fabric length direction, i.e. the long marker axis used as the grain/warp direction. Each piece is filled with the same colour
as its 3D patch, and the dashed rectangle is the occupied marker area on the roll. The
finer grey dashed curve around each piece is the pattern convex hull, used here as a
simplified cutting/marking line for easier scissor or cutter paths. Folds/overlaps visible
inside a flattened piece signal that the patch is non-developable (needs a dart);
zero-area or below-minimum cuttable fragments are omitted.

\clearpage
\begin{figure}[p]\centering
\setlength{\tabcolsep}{2pt}
\renewcommand{\arraystretch}{0.92}
\scriptsize
\begin{tabular}{cc}
\begin{minipage}{0.486\linewidth}\centering
  \includegraphics[width=0.47\linewidth,height=0.17\textheight,keepaspectratio]{App_kidney.png}\hfill
  \includegraphics[width=0.47\linewidth,height=0.17\textheight,keepaspectratio]{App_kidney_pattern.png}\\[-1pt]
  Kidney ($\approx$11\,cm)
\end{minipage} &
\begin{minipage}{0.486\linewidth}\centering
  \includegraphics[width=0.47\linewidth,height=0.17\textheight,keepaspectratio]{App_liver.png}\hfill
  \includegraphics[width=0.47\linewidth,height=0.17\textheight,keepaspectratio]{App_liver_pattern.png}\\[-1pt]
  Liver ($\approx$21\,cm)
\end{minipage} \\[4pt]
\begin{minipage}{0.486\linewidth}\centering
  \includegraphics[width=0.47\linewidth,height=0.17\textheight,keepaspectratio]{App_nefertiti.png}\hfill
  \includegraphics[width=0.47\linewidth,height=0.17\textheight,keepaspectratio]{App_nefertiti_pattern.png}\\[-1pt]
  Nefertiti ($\approx$49\,cm)
\end{minipage} &
\begin{minipage}{0.486\linewidth}\centering
  \includegraphics[width=0.47\linewidth,height=0.17\textheight,keepaspectratio]{App_thingi_turritella_shell_44704.png}\hfill
  \includegraphics[width=0.47\linewidth,height=0.17\textheight,keepaspectratio]{App_thingi_turritella_shell_44704_pattern.png}\\[-1pt]
  Turritella ($\approx$15\,cm)
\end{minipage} \\[4pt]
\begin{minipage}{0.486\linewidth}\centering
  \includegraphics[width=0.47\linewidth,height=0.17\textheight,keepaspectratio]{App_thingi_oxystele_shell_46774.png}\hfill
  \includegraphics[width=0.47\linewidth,height=0.17\textheight,keepaspectratio]{App_thingi_oxystele_shell_46774_pattern.png}\\[-1pt]
  Oxystele ($\approx$4\,cm)
\end{minipage} &
\begin{minipage}{0.486\linewidth}\centering
  \includegraphics[width=0.47\linewidth,height=0.17\textheight,keepaspectratio]{App_thingi_shell01_41909.png}\hfill
  \includegraphics[width=0.47\linewidth,height=0.17\textheight,keepaspectratio]{App_thingi_shell01_41909_pattern.png}\\[-1pt]
  Shell~01 ($\approx$10\,cm)
\end{minipage} \\[4pt]
\begin{minipage}{0.486\linewidth}\centering
  \includegraphics[width=0.47\linewidth,height=0.17\textheight,keepaspectratio]{App_obj_car_supra.png}\hfill
  \includegraphics[width=0.47\linewidth,height=0.17\textheight,keepaspectratio]{App_obj_car_supra_pattern.png}\\[-1pt]
  Car body ($\approx$4.4\,m, not to scale)
\end{minipage} &
\begin{minipage}{0.486\linewidth}\centering
  \includegraphics[width=0.47\linewidth,height=0.17\textheight,keepaspectratio]{App_obj_yacht.png}\hfill
  \includegraphics[width=0.47\linewidth,height=0.17\textheight,keepaspectratio]{App_obj_yacht_pattern.png}\\[-1pt]
  Yacht hull ($\approx$12\,m, not to scale)
\end{minipage}
\end{tabular}
  \caption{Application-case pattern gallery. In each cell, the left image is the 3D drape
  partition and the right image is the corresponding 2D fabric pattern. The researched
  average physical size is noted under each cell as a scale reference, but the layouts
  are display-normalised per case so that the pattern shapes remain readable in the
  small panels. Each layout is nested on an assumed 100 cm fabric roll, with pieces
  concentrated against the left edge in the usual marker-making direction that reduces
  unused roll length. This gallery is therefore for comparing pattern shape and piece
  arrangement, not for comparing absolute size across different objects. The merged
  layout combines the former organ, Nefertiti, seashell, car-body, and yacht-hull
  appendix figures into a single A4-page figure.}
  \label{app:fig-organs}
  \label{app:fig-nefertiti}
  \label{app:fig-shells}
  \label{app:fig-eng}
\end{figure}

\clearpage
\begin{figure}[p]\centering
\setlength{\tabcolsep}{0pt}
\begin{tabular}{@{}c@{\hspace{0.025\linewidth}}c@{\hspace{0.025\linewidth}}c@{}}
  \includegraphics[width=0.20\linewidth,height=0.18\textheight,keepaspectratio]{App_obj_airplane_b787_nosym.png} &
  \includegraphics[width=0.20\linewidth,height=0.18\textheight,keepaspectratio]{App_obj_airplane_b787_shear.png} &
  \includegraphics[width=0.36\linewidth,height=0.18\textheight,keepaspectratio]{App_obj_airplane_b787_pattern_nosym.png}
\end{tabular}\\[-2pt]
  {\small (a) Partition and flattening without symmetry (100 cm roll width)}\\[4pt]
\begin{tabular}{@{}c@{\hspace{0.025\linewidth}}c@{\hspace{0.025\linewidth}}c@{}}
  \includegraphics[width=0.20\linewidth,height=0.18\textheight,keepaspectratio]{App_obj_airplane_b787.png} &
  \includegraphics[width=0.20\linewidth,height=0.18\textheight,keepaspectratio]{App_obj_airplane_b787_shear.png} &
  \includegraphics[width=0.36\linewidth,height=0.18\textheight,keepaspectratio]{App_obj_airplane_b787_pattern_roll100.png}
\end{tabular}\\[-2pt]
  {\small (b) Symmetric partition + 100 cm fabric-roll width}\\[4pt]
\begin{tabular}{@{}c@{\hspace{0.025\linewidth}}c@{\hspace{0.025\linewidth}}c@{}}
  \includegraphics[width=0.20\linewidth,height=0.18\textheight,keepaspectratio]{App_obj_airplane_b787.png} &
  \includegraphics[width=0.20\linewidth,height=0.18\textheight,keepaspectratio]{App_obj_airplane_b787_shear.png} &
  \includegraphics[width=0.36\linewidth,height=0.18\textheight,keepaspectratio]{App_obj_airplane_b787_pattern_roll50.png}
\end{tabular}\\[-2pt]
  {\small (c) Symmetric partition + 50 cm fabric-roll width constraint}
  \caption{Boeing 787 drape partition and 2D pattern-layout variants. In each row, the
  left image is the 3D drape partition, the middle image is the same surface coloured
  by the relative shear-severity field, and the right image is the corresponding 2D
  pattern layout. Row (a) is the baseline \textbf{without symmetry}: the left and right
  patches split differently, so the flattened pattern is asymmetric. Rows (b) and (c)
  apply \textbf{left--right symmetry inside the partition algorithm itself} (the coloured
  patches in the left column split symmetrically about the fuselage mid-plane), so the
  flattened 2D pattern inherits that symmetry naturally. Black arrows mark the fabric
  length direction, i.e. the long marker axis used as the grain/warp direction, and fine grey dashed curves mark convex-hull cutting lines. Rows
  (a) and (b) use the 100 cm roll width to directly contrast the absence versus presence
  of symmetry; row (c) uses a narrower 50 cm roll-width constraint.}
  \label{app:fig-airplane-pattern-variants}
\end{figure}

\clearpage

% ---- References -----------------------------------------------------
\bibliographystyle{plainnat}
\bibliography{references}

\end{document}

