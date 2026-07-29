# LaTeX source: SFTF_ThermalChip_PoC_en.tex

Source: `D:\__SFTF_Projects(2026)\SFTF_ThermalChip_dev\draft\SFTF_ThermalChip_PoC_en.tex`

% !TEX program = pdflatex
% English submission draft. Korean reference version: SFTF_ThermalChip_PoC.tex
% Numbers/figures: uv run python scripts/build_paper_data.py (draft/paper_data.json,
% pics/thermal_*_en.{png,svg}). Build: pdflatex x2.
\documentclass[11pt]{article}

\usepackage[a4paper,margin=25mm]{geometry}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{amsmath,amssymb,amsthm}
\usepackage{booktabs}
\usepackage{array}
\usepackage{graphicx}
\usepackage{caption}
\captionsetup{font=small,labelfont=bf}
\usepackage{enumitem}
\usepackage{xcolor}
\usepackage[colorlinks=true,linkcolor=blue!55!black,citecolor=teal!60!black,
            urlcolor=blue!55!black]{hyperref}

\usepackage{tikz}
\usetikzlibrary{arrows.meta,positioning,calc,fit,backgrounds,shapes.geometric}
\tikzset{
  node distance=8mm,
  >={Stealth[length=2.4mm]},
  box/.style={draw,rounded corners=2pt,align=center,inner sep=4pt,
              font=\small,fill=blue!4},
  hl/.style={draw,rounded corners=2pt,align=center,inner sep=4pt,
              font=\small,fill=orange!12},
  flowarr/.style={->,thick,blue!55!black},
  trunk/.style={->,very thick,orange!75!black},
}

\newcommand{\term}[1]{\textbf{#1}}
\newcommand{\R}{\ensuremath{R}}
\newcommand{\PP}{\ensuremath{P}}
\newcommand{\Bsum}{\ensuremath{B_{\mathrm{sum}}}}
\newcommand{\Bpeak}{\ensuremath{B_{\mathrm{peak}}}}
\newcommand{\J}{\ensuremath{J}}
\newcommand{\Tpeak}{\ensuremath{T_{\mathrm{peak}}}}
\newcommand{\Tmean}{\ensuremath{T_{\mathrm{mean}}}}

\title{\textbf{Thermal-Via Placement Screening with a Support-Flow
Tensor Field:\\ When Does a Peak-Temperature Proxy Pay?}\\[2mm]
\large Transplanting an additive-manufacturing candidate generator to chip
heat dissipation: a proof of concept}
\author{InHwan Sul\\
\small Department of Materials Design Engineering,
Kumoh National Institute of Technology,\\
\small Gumi 39177, Republic of Korea\\
\small Email: snowman0@kumoh.ac.kr \quad ORCID: 0000-0003-0105-920X}
\date{2026-07 (draft v0.3)}

\begin{document}
\maketitle

\begin{abstract}
\noindent
The Support Flow Tensor Field (SFTF), a build-orientation candidate generator
for additive manufacturing (AM), summarises the structure ``load flows down a
few routes, and cost is dominated by load $\times$ distance'' in one
closed-form tensor pass. This proof of concept transplants that skeleton to
chip heat dissipation via the substitutions \emph{overhang load $=$ cell power
density $P_i$}, \emph{receiver $=$ neighbour on the lowest-thermal-resistance
path}, and \emph{build plate (ground node) $=$ heatsink/thermal via}
($T=T_{\mathrm{amb}}$): the support-flow tree becomes a heat-flux network and
support-volume minimisation becomes temperature-rise minimisation. On top of
the isomorphism with its sibling PoC (static IR-drop pad placement), we ask
the one question this domain adds: the first-order reliability metric of chip
heat is the \emph{peak} temperature, not a sum --- so does a peak objective
need a peak-aware proxy? The answer, quantified against steady conduction
sign-off on synthetic dies, is \emph{only when the question is posed
correctly}. In pools that mix via counts, peak and mean temperature are
strongly coupled ($\rho\!\approx\!0.94$), the sum proxy \Bsum\ already ranks
peak-$T$ ($\rho=0.945$), and the peak-aware proxy \Bpeak\ wins only 11/40
seeds. Fixing the via \emph{budget} and optimising placement only --- the
practical ``where'' question --- decouples peak from mean
($\rho\!\approx\!0.78$) and \Bpeak\ wins in $73{-}83\%$ of seeds at budgets
9/16/25. The operational value is settled by shortlist regret: verifying only
the proxy's top $k{=}3$ layouts leaves a mean excess peak-$T$ of $1.4\%$
(random shortlists: $17.8\%$), a $20\times$ reduction in sign-off calls.
Robustness is established in four directions: the conclusion survives (i) a
compact-model sign-off with finite via resistances ($70\%$ win rate), (ii) a
\emph{real} processor power map (HotSpot Alpha EV6, gcc trace), where the
proxy's top-1 layout coincides with the true optimum ($k{=}1$ regret $0.0\%$
vs.\ random $47.2\%$) and the regime boundary is shown to depend on the power
map; (iii) a \emph{transient} sign-off driven by the full 100-interval gcc
trace; and (iv) a \emph{3D-stack} sign-off on the HotSpot EV6\_3D testcase
(two cache dies $+$ core die), where the cheap 2D proxy applied to the
thickness-aggregated map still ranks via placements. A per-zone additive
decomposition --- the thermal analogue of SFTF-Clustering's tensor additivity
--- identifies the bottleneck thermal domain without any extra solve (zone
rank $\rho=0.79$; hottest-zone hit $67\%$ vs.\ $12.5\%$ chance).
\end{abstract}

\noindent\term{Keywords:} thermal-aware design; thermal via placement; design
space screening; candidate generation; tensor field; peak temperature;
HotSpot benchmark

% ============================================================================
\section{Introduction: does a peak objective need a peak proxy?}
% ============================================================================

Chip heat-dissipation design --- \emph{how many} thermal vias/TSVs to attach
to the heatsink path, and \emph{where} --- relies on a screening stage
because precise thermal analysis (FEM/CFD, compact thermal models) is
expensive per candidate. In a sibling proof of concept we showed that the
skeleton of the Support Flow Tensor Field (SFTF), an additive-manufacturing
build-orientation candidate generator, transplants directly to PDN IR-drop
pad placement; since steady heat conduction and static IR drop are
mathematically isomorphic (\S\ref{sec:mapping}), those results carry over to
the thermal domain by a change of units.

The contribution of this PoC is therefore not a re-confirmation of the
isomorphism but the one thing the thermal domain \emph{adds}. In the PDN and
sewer transplants the cost was a \emph{sum} (total IR drop, total
excavation); the first-order reliability metric of chip heat is the
\emph{peak} temperature \Tpeak. A single hotspot decides reliability, so
alongside the sum-based ground-node term \Bsum\ we introduce a
\term{peak-aware proxy} \Bpeak\ that accumulates thermal resistance $\times$
cumulative heat down the flow tree (\S\ref{sec:mapping-peak}).

The validation turned out to be more subtle than expected, and we consider
that subtlety the paper's central result (\S\ref{sec:exp}):

\begin{itemize}[leftmargin=1.6em,itemsep=1pt]
\item \term{Negative.} When layouts with \emph{different} via counts compete
  in one pool --- the setting screening benchmarks commonly adopt --- total
  sink access drives peak and mean together ($\rho\approx0.94$), so \Bsum\
  already ranks peak-$T$ well and \Bpeak\ does not win (11/40 seeds). Three
  physics-based alternatives (local $P\varphi$, Jacobi-smoothed diffusion, a
  2D log Green's function) also all lose to \Bsum.
\item \term{Positive.} When the via \emph{budget is fixed} and only the
  placement is optimised --- the practical ``where'' question --- peak and
  mean decouple ($\rho\approx0.78$) and \Bpeak\ wins in $73{-}83\%$ of seeds
  at budgets 9/16/25.
\item \term{Operational value.} In shortlist operation (verify only the
  proxy's top $k$), $k{=}3$ leaves an excess peak-$T$ of $1.4\%$ (\Bsum\
  $1.8\%$, random $17.8\%$): a cheap proxy plus a tiny verification budget
  reaches a near-optimal placement.
\end{itemize}

In short, peak-awareness pays when choosing \emph{where}, not \emph{how
many}. This delineation is both a successful domain adaptation (of the
objective's form) and an honest report that transplants do not succeed
automatically.

% ============================================================================
\section{Background}
% ============================================================================

\subsection{SFTF in one paragraph: a flow tensor and three terms}\label{sec:bg-sftf}

SFTF treats the overhang load $O_i$ of each mesh face as a load that ``flows
down'' to a receiver face or to the build plate, and aggregates the routes in
closed form. The score combines three terms: a directional-tensor Rayleigh
term \R, a face-pair proximity term \PP, and the \term{ground-node term} $B$
that aggregates the load draining to the build plate with a distance weight.
As the sibling PoCs showed, what survives in fixed-geometry, fixed-sink
domains is chiefly the $B$ family --- in the PDN domain the directional
Rayleigh term degenerates to zero structurally --- so the protagonists of
this paper are \Bsum\ and \Bpeak.

\subsection{Steady conduction and the PDN isomorphism}\label{sec:bg-iso}

Steady heat conduction and static IR drop are the same elliptic equation:
\begin{equation}
\nabla\!\cdot\!(k\,\nabla T) = -P_{\mathrm{diss}},\qquad
\nabla\!\cdot\!(\sigma\,\nabla V) = -I_{\mathrm{inject}},
\label{eq:iso}
\end{equation}
with the sink boundary $T=T_{\mathrm{amb}}$ corresponding to pads $V=0$, and
the correspondence $V\!\leftrightarrow\!T$, current $\leftrightarrow$ heat
flux, $\sigma\!\leftrightarrow\!k$, pad $\leftrightarrow$ heatsink/via. The
sibling PoC's resistive-network solver $Gv=i$ becomes the thermal solver
$Kt=P$ by a change of units. Fourier's law $q=-k\nabla T$ shares the
``potential $\to$ sink'' structure of gravity $-\nabla\Phi$, so the match
with AM support flow is if anything cleaner than for the electrical case.

% ============================================================================
\section{Mapping: SFTF $\to$ ThermalChip}\label{sec:mapping}
% ============================================================================

\begin{table}[h]\centering\small
\caption{Symbol correspondence. The last two rows are what distinguishes this
PoC from its PDN sibling.}
\label{tab:mapping}
\begin{tabular}{lll}
\toprule
SFTF (additive manufacturing) & ThermalChip PoC & symbol \\
\midrule
build direction $n\in S^2$ & nearly uniform $-z$ w/ backside sink & $n$ \\
face $i$ / overhang $O_i(n)$ & grid cell / power density & $P_i\ge0$ \\
receiver search (ray cast) & steepest-descent neighbour of $\varphi$ & $\mathrm{rec}(i)$ \\
support height $h_{ij}$ & thermal-resistance distance & $r_{ij}$ \\
build plate (ground node) & heatsink / thermal via ($T=T_{\mathrm{amb}}$) & \Bsum \\
partition $+$ reorientation & thermal domains $+$ multi-sink & \\
\midrule
cost $=$ total support (sum) & cost $=$ \term{peak temperature (max)} & \Bpeak \\
--- & placement at a fixed via budget (\S\ref{sec:exp-budget}) & \\
\bottomrule
\end{tabular}
\end{table}

\subsection{The sink-distance potential $\varphi$ as elevation}

Given a sink set $S$, define each cell's potential as the distance transform
$\varphi_i=\mathrm{dist}(i,S)$. It plays the role AM elevation played: heat
``flows downhill'' in $\varphi$.

\subsection{Receivers and the flow tree}

Taking each cell's receiver as its steepest-descent neighbour of $\varphi$
makes $\mathrm{rec}:i\mapsto j$ a forest rooted at the sinks, and defines the
cumulative heat $\mathrm{accum}_i$ (own dissipation $+$ upstream inflow)
passing through cell $i$ --- exactly the data structure of the SFTF support
flow tree.

\subsection{The sum proxy \Bsum\ and the peak proxy \Bpeak}\label{sec:mapping-peak}

The literal transplant of the ground-node term is the power-times-distance
sum
\begin{equation}
\Bsum \;=\; \sum_i P_i\,\bigl(1+\alpha\,\varphi_i\bigr),
\label{eq:bsum}
\end{equation}
a first-order law of the mean temperature rise and precisely the term that
reproduced sign-off rankings in the sibling PoC. The thermal-specific
addition accumulates resistance $\times$ cumulative heat down the flow tree:
\begin{equation}
t^{\mathrm{proxy}}_i \;=\; t^{\mathrm{proxy}}_{\mathrm{rec}(i)}
   \;+\; \alpha\,\mathrm{accum}_i\, r_i,
\qquad
\Bpeak \;=\; \max_i\, t^{\mathrm{proxy}}_i,
\label{eq:bpeak}
\end{equation}
so cells far from sinks with heavy upstream dissipation score high ---
targeting the \emph{location} of the hotspot. The full score keeps the family
form $\J = w_R\R + w_P\PP + w_B\Bsum$; the comparisons below focus on \Bsum\
vs.\ \Bpeak.

\begin{figure}[h]\centering
\begin{tikzpicture}[node distance=6mm]
  \node[box] (am) {AM: overhang load $O_i$\\ $\downarrow$ flows down\\ build plate};
  \node[box,right=18mm of am] (th) {chip: power $P_i$\\ $\downarrow$ steepest $\varphi$ descent\\ sink $T=T_{\mathrm{amb}}$};
  \node[hl,right=18mm of th] (proxy) {\Bsum: sum (Eq.~\ref{eq:bsum})\\[1mm] \Bpeak: max (Eq.~\ref{eq:bpeak})};
  \draw[trunk] (am) -- node[above,font=\scriptsize]{substitute} (th);
  \draw[flowarr] (th) -- node[above,font=\scriptsize]{closed form} (proxy);
\end{tikzpicture}
\caption{The transplant skeleton: support-flow tree $=$ heat-flux network,
ground node $=$ sink. The domain-specific addition is a max (\Bpeak) rather
than a sum (\Bsum) objective.}
\label{fig:concept}
\end{figure}

\subsection{Thermal domains = the SFTF-Clustering transplant}

SFTF-Clustering's cut-induced (cost of a separate sink group) vs.\
reorientation (each zone served by its own nearest sinks) structure carries
over, and tensor additivity $F(\mathrm{part})=\sum F_{\mathrm{part}}$ prices
partitions without re-solving. In the thermal transplant both additive
estimators (Eqs.~\ref{eq:bsum}--\ref{eq:bpeak}) are per-cell sums, so
restricting the sum to a Voronoi zone yields that zone's cost --- with no
extra analysis. \S\ref{sec:exp-zones} validates this per-zone decomposition
quantitatively.

% ============================================================================
\section{Implementation}\label{sec:impl}
% ============================================================================

The implementation is a fork of the sibling repository
(\texttt{SFTF\_PDNElectric\_dev}), numpy/scipy only (no learning, no GPU).
Modules under \texttt{python/src/thermal/}: \texttt{chip.py} (synthetic dies,
sink placement, $\varphi$ distance transform), \texttt{heat\_field.py} (flow
tree, \Bsum, \Bpeak, flow tensor), \texttt{verify.py} (four sign-off levels;
rank correlation, hit@$k$, shortlist regret), \texttt{zones.py} (thermal
domains, per-zone additive decomposition), \texttt{realchip.py} (HotSpot
\texttt{.flp}/\texttt{.ptrace}/\texttt{.lcf} loaders with area-weighted
rasterisation), \texttt{cli.py} (demos). There are 34 acceptance tests; every
number in this paper regenerates from one command
(Appendix~\ref{sec:repro}).

Sign-off comes in four levels. The \term{stand-in}
(\texttt{thermal\_solve}) removes sink cells as Dirichlet ($T=0$) nodes and
solves $Kt=P$ directly. The \term{compact model} (\texttt{signoff\_thermal})
replaces that idealisation with HotSpot-style finite verticals: every cell
leaks weakly to ambient through the package ($g_{\mathrm{bg}}$) and via
cells get a strong but \emph{finite} vertical conductance $g_{\mathrm{via}}$,
i.e.\ $(K_{\mathrm{lat}}+\mathrm{diag}\,g)\,t=P$; the limit
$g_{\mathrm{via}}\!\to\!\infty$ recovers the stand-in (regression-tested).
The \term{transient} solver (\texttt{transient\_solve}) integrates
$C\,\dot T = -(K_{\mathrm{lat}}+\mathrm{diag}\,g)T + P(t)$ over a power
trace with one implicit (backward-Euler) step per interval, factorising the
constant system matrix once; its metric is the time-max peak. The
\term{3D-stack} solver (\texttt{signoff\_thermal\_3d}) stacks per-layer
lateral Laplacians coupled by per-cell vertical conductances through TIM/TSV
layers, with the package leakage and via conductances on the sink-near
layer; with one layer it reduces exactly to the compact model
(regression-tested). Swapping in a full HotSpot/FEM call remains the
extension point for real-unit calibration.

% ============================================================================
\section{Experiments}\label{sec:exp}
% ============================================================================

\subsection{Setup}\label{sec:exp-setup}

Synthetic dies are $48\times48$ grids of a low power baseline $+$ four
high-power hotspots $+$ noise (\texttt{synthetic\_chip}, reproducible per
seed). Candidate pools come in two kinds: \term{varying-count} pools (7
regular $k\times k$ grids and offsets $+$ 40 irregular random layouts,
differing in via count) and \term{fixed-budget} pools (via count fixed at
budget $b$; only the placement varies; 40--60 random layouts). For each
layout we compute the proxies (\Bsum, \Bpeak) and the solved (\Tpeak,
\Tmean), summarised by Spearman rank correlation $\rho$, per-seed win rates,
and shortlist regret. Fig.~\ref{fig:fields} shows the seed-0 die.

\begin{figure}[h]\centering
\includegraphics[width=\linewidth]{pics/thermal_die_fields_en.png}
\caption{Seed-0 synthetic die ($48^2$) and a budget-16 layout (the \Bpeak\
top-1 pick; $\times$ marks). Left: power density $P$. Middle: sink-distance
potential $\varphi$. Right: solved steady-conduction temperature field.}
\label{fig:fields}
\end{figure}

\subsection{Negative result: with mixed via counts, the sum proxy suffices}\label{sec:exp-neg}

In the varying-count pool \Bsum\ reproduces the \Tmean\ ranking at
$\rho=+0.969$ and \emph{even the \Tpeak\ ranking} at $\rho=+0.945$ (seed 0,
47 layouts); \Bpeak, designed for peaks, trails at $\rho=+0.918$. Across 40
seeds \Bpeak\ wins 11/40 with mean $\Delta\rho=-0.015$. The cause is the pool
structure: when layouts differ in sink count, total sink access drives peak
and mean together ($\rho\approx0.936$), so a mean-tracking proxy
automatically tracks peaks. Three physics-based alternatives (local
$P\varphi$, Jacobi-smoothed diffusion, an image-method 2D log Green's
function) also all lost to \Bsum. Unlike SFTF's \emph{discrete} support
trees, heat \emph{diffuses} --- the sum-vs-max distinction does not transfer
unchanged. This is the transplant's first honest boundary.

\subsection{Positive result: at a fixed budget, peak-awareness wins}\label{sec:exp-budget}

Real design flows usually fix the via budget first (cost/area) and then ask
\emph{where}. Fixing the count holds total access roughly constant, peak and
mean decouple ($\rho\approx0.78$), and \Bpeak\ prevails
(Table~\ref{tab:budget}, Fig.~\ref{fig:budget}): win rates $73.3\%$/$83.3\%$/
$76.7\%$ at budgets 9/16/25, mean $\rho_{\mathrm{peak}}\approx0.85 >
\rho_{\mathrm{sum}}\approx0.80$. The win rate is somewhat budget-sensitive
(budget 12: $63.3\%$, with the $\rho$ advantage intact), but the sign is
consistent. An under-provisioned budget ($b{=}4$) fails even when fixed ---
access itself dominates --- the second honest boundary.

\begin{table}[h]\centering\small
\caption{Fixed-budget placement-only pools (30 seeds $\times$ 40 layouts).
Win $=$ fraction of seeds with $\rho(\Bpeak,\Tpeak)>\rho(\Bsum,\Tpeak)$.}
\label{tab:budget}
\begin{tabular}{rcccc}
\toprule
budget $b$ & \Bpeak\ win & mean $\rho(\Bpeak,\Tpeak)$ & mean
$\rho(\Bsum,\Tpeak)$ & $\rho(\Tpeak,\Tmean)$ \\
\midrule
 4 & $10.0\%$ & $0.828$ & $\mathbf{0.898}$ & $0.868$ \\
 9 & $\mathbf{73.3\%}$ & $\mathbf{0.853}$ & $0.828$ & $0.781$ \\
12 & $\mathbf{63.3\%}$ & $\mathbf{0.845}$ & $0.801$ & $0.775$ \\
16 & $\mathbf{83.3\%}$ & $\mathbf{0.858}$ & $0.803$ & $0.794$ \\
25 & $\mathbf{76.7\%}$ & $\mathbf{0.857}$ & $0.788$ & $0.788$ \\
\bottomrule
\end{tabular}
\end{table}

\begin{figure}[h]\centering
\includegraphics[width=0.78\linewidth]{pics/thermal_budget_en.png}
\caption{\Bpeak\ win rate (bars) and mean rank correlations (lines) per via
budget. Peak-awareness prevails at every non-starved budget ($b\ge9$).}
\label{fig:budget}
\end{figure}

\begin{figure}[h]\centering
\includegraphics[width=0.78\linewidth]{pics/thermal_scatter_en.png}
\caption{Proxy vs.\ solved scatter for the budget-16 seed-0 pool. \Bpeak\
(left) is the more monotone predictor of \Tpeak.}
\label{fig:scatter}
\end{figure}

\subsection{Shortlist regret: the real metric of a candidate generator}\label{sec:exp-regret}

Exact top-1 agreement (hit@1) is low at $19/60\,(32\%)$, but only because the
best layouts are near-ties (not a proxy defect): the true \Tpeak\ of
\Bpeak's top pick exceeds the optimum by $4.1\%$ on average
(best$\to$worst normalised). The intended operation is ``shortlist top-$k$
by proxy, sign off only those $k$'', so the right metric is shortlist
regret. Table~\ref{tab:regret} and Fig.~\ref{fig:regret} give 60 seeds
$\times$ 60 layouts at budget 16: at $k{=}3$, \Bpeak's regret is $1.4\%$ ---
a $20\times$ reduction in sign-off calls versus exhaustive verification while
landing essentially at the optimum. \Bpeak\ beats \Bsum\ precisely at the
tight budgets $k\in\{1,3\}$ ($4.1\%$ vs $4.6\%$; $1.4\%$ vs $1.8\%$) and the
two converge for $k\ge5$: the benefit of peak-awareness concentrates where
verification is scarcest.

\begin{table}[h]\centering\small
\caption{Shortlist regret (60 seeds $\times$ 60 layouts, budget 16); lower is
better.}
\label{tab:regret}
\begin{tabular}{rccc}
\toprule
$k$ & \Bpeak & \Bsum & random \\
\midrule
 1 & $\mathbf{4.1\%}$ & $4.6\%$ & $36.3\%$ \\
 3 & $\mathbf{1.4\%}$ & $1.8\%$ & $17.8\%$ \\
 5 & $0.9\%$ & $\mathbf{0.8\%}$ & $11.4\%$ \\
10 & $0.2\%$ & $0.2\%$ & $6.8\%$ \\
\bottomrule
\end{tabular}
\end{table}

\begin{figure}[h]\centering
\includegraphics[width=0.62\linewidth]{pics/thermal_regret_en.png}
\caption{Verification budget $k$ vs.\ shortlist regret. At $k{=}3$ the proxy
shortlist converges to a $12\times$ lower excess peak-$T$ than random.}
\label{fig:regret}
\end{figure}

\subsection{Cost: the gain is in call counts, not per-evaluation speed}\label{sec:exp-timing}

We report honestly: on small 2D grids a direct sparse solve is itself cheap,
so the proxy's per-evaluation advantage is only $2{-}3\times$
(Table~\ref{tab:timing}) --- unlike the sibling PDN PoC's $42{-}122\times$,
because the verifiers differ. But a candidate generator's value proposition
is the reduction in the \emph{number} of sign-off calls: the shortlist
operation of \S\ref{sec:exp-regret} ($k{=}3$ out of a pool of 60) cut
sign-off calls $20\times$, and that saving scales with the true cost of
sign-off (FEM/CFD, transient). The proxy is linear in grid size while the
direct solve is superlinear, so the per-evaluation gap also widens with size
($3.1\times$ at $192^2$).

\begin{table}[h]\centering\small
\caption{Per-layout evaluation cost (budget 16, mean of 20, single core).}
\label{tab:timing}
\begin{tabular}{rccc}
\toprule
die & proxy ($B$ terms) & solve $Kt=P$ & ratio \\
\midrule
$48^2$  & $1.6$ ms & $3.9$ ms & $2.4\times$ \\
$96^2$  & $6.8$ ms & $15.2$ ms & $2.2\times$ \\
$192^2$ & $29.8$ ms & $91.0$ ms & $3.1\times$ \\
\bottomrule
\end{tabular}
\end{table}

\subsection{Robustness 1: the conclusion survives a compact-model sign-off}\label{sec:exp-signoff}

Replacing the idealised Dirichlet verifier by the finite-resistance compact
model (\S\ref{sec:impl}) and repeating the fixed-budget experiment (budget
16, 30 seeds $\times$ 40 layouts): \Bpeak\ wins $70.0\%$ of seeds,
$\rho_{\mathrm{peak}}=0.793>\rho_{\mathrm{sum}}=0.762$, and shortlist regret
is $8.2\%$ vs $11.3\%$ at $k{=}1$ and $2.4\%$ vs $3.9\%$ at $k{=}3$
(reversing to $1.5\%$ vs $0.9\%$ at $k{=}5$ --- the small-$k$ concentration
pattern again). Absolute correlations drop (the verifier got harder), but
the \emph{sign and the operating conclusion are unchanged}.

\subsection{Robustness 2: a real processor power map (HotSpot Alpha EV6)}\label{sec:exp-realchip}

We rasterised (area-weighted, $64^2$) the Alpha EV6 floorplan
($16\,\mathrm{mm}\times16\,\mathrm{mm}$, 19 units) with the time-averaged
gcc power trace from the standard HotSpot benchmark~\cite{hotspot}
(Fig.~\ref{fig:ev6}); total trace power ${\approx}99.6\,\mathrm{W}$,
concentrated in the FP cluster and integer core --- a typical real-chip map.

\begin{table}[h]\centering\small
\caption{EV6/gcc real-chip map, fixed-budget placement-only pools (30 pools
$\times$ 40 layouts, stand-in verifier). Regret at budget 16.}
\label{tab:ev6}
\begin{tabular}{rccc}
\toprule
budget $b$ & \Bpeak\ win & mean $\rho(\Bpeak,\Tpeak)$ & mean $\rho(\Bsum,\Tpeak)$ \\
\midrule
 9 & $\mathbf{100.0\%}$ & $\mathbf{0.913}$ & $0.855$ \\
16 & $66.7\%$ & $0.888$ & $0.889$ \\
25 & $16.7\%$ & $0.862$ & $\mathbf{0.872}$ \\
\midrule
\multicolumn{4}{l}{regret ($b{=}16$): $k{=}1$: \Bpeak\ $\mathbf{0.0\%}$ /
\Bsum\ $0.7\%$ / random $47.2\%$;\quad $k{\ge}3$: both proxies $0.0\%$} \\
\bottomrule
\end{tabular}
\end{table}

Two findings. First, \term{the candidate-generator value is stronger on the
real chip}: at budget 16 the \Bpeak\ top-1 pick coincided with the true
optimal placement in all 30 pools ($k{=}1$ regret $0.0\%$; random $47.2\%$)
--- real maps have few, large hotspots that the proxy cannot miss. Second,
\term{the regime boundary depends on the power map}: unlike the synthetic
dies (where \Bpeak\ won for all $b\in[9,25]$), on EV6 it wins $100\%$ at
$b{=}9$ (vias scarce relative to hotspots) but loses to \Bsum\ at $b{=}25$
(ample budget). Peak-awareness pays when vias are \emph{scarce relative to
the hotspots}; with budget to spare, either proxy finds a good layout ---
consistent with \S\ref{sec:exp-neg}, and a third honest boundary.

\begin{figure}[h]\centering
\includegraphics[width=0.86\linewidth]{pics/thermal_ev6_fields_en.png}
\caption{HotSpot Alpha EV6 with the time-averaged gcc trace: power density
(left) and the compact-model temperature field of the \Bpeak\ top-1
16-via layout (right; $\times$ marks the vias).}
\label{fig:ev6}
\end{figure}

\subsection{Robustness 3: transient sign-off on the full gcc trace}\label{sec:exp-transient}

What if the truth is not steady state but the \emph{time-max} peak over the
actual gcc drive trace (100 intervals)? We re-validated the EV6 die
($64^2$, budget 16, 15 pools $\times$ 30 layouts) with the backward-Euler
transient solver (\S\ref{sec:impl}). This regime is qualitatively
different: over a 100-interval burst the heat does not fully ``see'' the via
layout, so the spread of time-max peaks across layouts compresses from
$278\%$ (steady) to $21\%$, and the correlation with the steady truth drops
to $0.59$ (every layout peaks at the final frame --- a ramp regime).
Against this harder truth the rank advantage is modest
($\rho_{\mathrm{peak}}=0.783>\rho_{\mathrm{sum}}=0.764$; win rate $60\%$),
but \term{the shortlist gap is dramatic}: \Bsum\ fails even at $k{=}5$
(regret $45.9\%$) while \Bpeak\ converges to $1.4\%$ ($k{=}3$: $30.5\%$
vs $68.0\%$). The time-max peak of a short burst is dominated by
\emph{local} hotspot heating, which the location-targeting \Bpeak\ captures
and the global sum \Bsum\ does not --- under transient truth, peak-awareness
stops being optional. Top-1 confidence is low, however ($k{=}1$ regret
$70\%$; near-tie noise in the compressed-span regime), so we recommend
$k\ge5$ shortlists for transient operation.

\subsection{Robustness 4: a 3D stack (HotSpot EV6\_3D)}\label{sec:exp-3d}

We validated 3D stacking on the HotSpot example4 EV6\_3D testcase --- two
cache dies plus a core die (TIM/TSV layers in between, total power
${\approx}36\,\mathrm{W}$). Vias (budget 16) sit on the sink-near core
layer; the proxies are applied unchanged to the \emph{thickness-aggregated}
2D map; the truth is the all-layer peak of the three-layer coupled compact
model (\texttt{signoff\_thermal\_3d}; 20 pools $\times$ 30 layouts).
Results: \Bpeak\ wins \term{100\%} of pools,
$\rho_{\mathrm{peak}}=0.826 \gg \rho_{\mathrm{sum}}=0.693$, and shortlists
reach regret $0.0\%$ at $k{=}3$ for both proxies ($k{=}1$: \Bsum\ $8.7\%$
vs \Bpeak\ $15.7\%$ --- a toss-up at the very top). The hottest cell lies on
the sink-far cache layer in all 600 cases --- physically consistent. In
short, the cheap 2D proxy still ranks the 3D truth even with inter-layer
coupling, and \Bpeak's rank advantage \emph{grows}
($\Delta\rho=0.13$): aggregation blurs the mean's layer allocation but the
peak path survives.

\subsection{Thermal domains (D3): per-zone sums find the bottleneck}\label{sec:exp-zones}

We validated the thermal analogue of tensor additivity. Placing 8 random
vias, partitioning into Voronoi thermal domains, and predicting each zone's
risk \emph{with no extra analysis} (the zone-restricted partial sums of
Eq.~\ref{eq:bpeak}), against the compact-model per-zone peak-$T$ (30 seeds):
zone-rank Spearman $0.790$ on average, and \term{hottest (bottleneck) zone
hit rate $67\%$} ($5.3\times$ the $12.5\%$ chance for 8 zones). A designer
can answer ``which domain to reinforce first'' without a solve. The
counter-intuitive SFTF-Clustering transplant --- many distributed vias beat
one large sink --- was also confirmed by the solver: a $3\times3$ distributed
layout lowers the compact-model peak-$T$ by $29\%$ versus one central sink,
and the additive proxy predicts the sign of that gain analysis-free.

% ============================================================================
\section{Related work and positioning}\label{sec:related}
% ============================================================================

The chip-thermal literature falls into four strands: (1) numerical thermal
sign-off (FEM/FDM, compact thermal models such as
HotSpot~\cite{hotspot}); (2) thermal-aware floorplanning/placement (SA,
analytical, force-directed placement of blocks, TSVs, microchannels, thermal
domains)~\cite{floorplan3d,atplace25d}; (3) thermal-via/TSV planning; and
(4) ML thermal surrogates (CNN, operator-learning, transformer temperature
predictors)~\cite{mlcad2022,surrogate2025,operator2025}. This PoC differs
in:

\begin{itemize}[leftmargin=1.6em,itemsep=1pt]
\item \term{(D1) A learning-free candidate generator.} ML surrogates (strand
  4) need retraining per technology/design. The SFTF transplant ranks
  sink/via placements and thermal-domain splits in closed form with zero
  training data, passing only a shortlist to the precise solver.
\item \term{(D2) A closed-form ground-node term.} \Bsum\ is a tensor reading
  of the first-order temperature-rise law, giving the ``power $\times$
  sink-distance'' heuristic a derivable basis.
\item \term{(D3) Tensor additivity.} Thermal-domain costs price without
  re-solving --- the per-zone decomposition finds the bottleneck zone with
  $67\%$ accuracy (\S\ref{sec:exp-zones}).
\item \term{(D5) A peak-aware proxy --- with an explicit scope.} Adapting the
  objective's \emph{form} (max, not sum) is this paper's specific
  contribution; \S\ref{sec:exp} bounds its validity to fixed-budget
  placement ranking with vias scarce relative to hotspots. Making that scope
  explicit is itself a methodological caution for screening benchmarks that
  compare across sink counts.
\end{itemize}

% ============================================================================
\section{Limitations and future work}\label{sec:limits}
% ============================================================================

\begin{itemize}[leftmargin=1.6em,itemsep=1pt]
\item \term{Compact models in PoC units.} All four sign-off levels are
  scipy stand-ins in PoC units, not calibrated silicon. The transient
  capacitance and vertical conductances are plausibility-scaled;
  real-unit calibration belongs to the HotSpot/FEM swap-in at the
  \texttt{signoff\_thermal()} hook family. Convection (microchannels) and
  electrothermal coupling remain out of scope.
\item \term{Benchmark breadth.} Real-chip validation covers HotSpot
  EV6 (gcc trace, 2D) and EV6\_3D (stacked caches $+$ core). Having shown
  the regime boundary is map-dependent (\S\ref{sec:exp-realchip}), a sweep
  over more floorplans and workload traces is the natural next step.
\item \term{Partition scope.} The per-zone decomposition validates
  \emph{bottleneck identification} for a fixed placement. Ranking whole
  partition candidates (the cut/reorientation trade-off) is future work.
\item \term{Differentiability.} Thermal costs are smooth, so a
  soft-attention relaxation enabling gradient descent on via positions (in
  the family's differentiable-SFTF line) is a natural extension.
\end{itemize}

% ============================================================================
\section{Conclusion}
% ============================================================================

AM support flow and chip heat dissipation share the skeleton ``load drains
to a few sinks; cost is load $\times$ distance''. On top of the PDN-mediated
transplant, this PoC asked the thermal-specific question --- does a peak
objective need a peak-aware proxy? --- and quantified a \emph{conditional}
answer: with mixed via counts \Bsum\ suffices (\Bpeak\ 11/40), while at a
fixed budget \Bpeak\ wins ($73{-}83\%$). The operational metric, shortlist
regret, settles the value proposition: verifying the top 3 of 60 layouts
leaves $1.4\%$ excess peak-$T$ (random: $17.8\%$) --- near-optimal placement
at $20\times$ fewer sign-off calls. Robustness was established in four
directions (finite-resistance compact model; the real EV6/gcc power map,
where top-1 regret is $0.0\%$ and the regime boundary is map-dependent; a
100-interval transient sign-off; a three-die 3D stack), and the per-zone
additive decomposition locates bottleneck domains analysis-free ($67\%$
hit). What transplants (ground node, flow tree, regret operation,
additivity), what is conditional (the peak-awareness regime), and what
remains (real-unit calibration, partition ranking, differentiability) are
all fixed numerically --- that is the contribution of this proof of concept.

% ============================================================================
\section*{Declarations}
% ============================================================================
\noindent\term{Funding.} To be completed at submission.\\[1mm]
\term{Conflicts of interest.} The author declares no conflict of
interest.\\[1mm]
\term{Data availability.} The real-chip inputs are the public HotSpot
benchmark files (\texttt{examples/example1} and \texttt{example4} of
\url{https://github.com/uvahotspot/HotSpot}); copies ship with the code
under \texttt{data/}. Every number and figure in this paper regenerates
deterministically from one script (Appendix~\ref{sec:repro}).\\[1mm]
\term{Code availability.} The full numpy/scipy implementation, 34 acceptance
tests, and the reproduction script will be released with the paper.

% ============================================================================
\begin{thebibliography}{9}\small
\bibitem{floorplan3d}
Anonymous, ``Thermal-aware floorplanner for 3D IC, including TSVs, liquid
microchannels and thermal domains,'' arXiv:2402.14627, 2024.
\url{https://arxiv.org/abs/2402.14627}
\bibitem{atplace25d}
Q.~Wang et al., ``ATPlace2.5D: Analytical thermal-aware chiplet placement
framework for large-scale 2.5D-IC,'' \emph{Proc. ICCAD}, 2024.
\bibitem{mlcad2022}
R.~Ranade et al., ``A thermal machine learning solver for chip simulation,''
\emph{Proc. MLCAD}, 2022.
\bibitem{surrogate2025}
Anonymous, ``Fast thermal-aware chiplet placement assisted by surrogate,''
arXiv:2504.03808, 2025.
\bibitem{operator2025}
Anonymous, ``From self-attention to operator learning: 3D-IC thermal
simulation,'' arXiv:2510.15968, 2025.
\bibitem{hotspot}
K.~Skadron, M.~R. Stan, W.~Huang, S.~Velusamy, K.~Sankaranarayanan, and
D.~Tarjan, ``Temperature-aware microarchitecture,'' \emph{Proc. ISCA}, 2003;
HotSpot benchmark suite, \url{https://github.com/uvahotspot/HotSpot}.
\end{thebibliography}

\appendix
% ============================================================================
\section{Reproduction}\label{sec:repro}
% ============================================================================
From the repository root:
\begin{quote}\ttfamily\small
uv sync\\
uv run pytest python/src/thermal -q\hfill\rmfamily(34 acceptance tests)\\
\ttfamily uv run python -m thermal.cli demo --budget 16\hfill\rmfamily(fixed-budget demo)\\
\ttfamily uv run python scripts/build\_paper\_data.py\hfill\rmfamily(all numbers and figures)
\end{quote}
The last command regenerates \texttt{draft/paper\_data.json} (every quoted
number) and \texttt{draft/pics/thermal\_*.png,svg} (every data figure, in
Korean and English label sets). All random seeds are fixed; only the timing
table is machine-dependent. The real-chip inputs are copies of the official
HotSpot benchmark~\cite{hotspot} under \texttt{data/hotspot\_ev6\{,\_3d\}/}.

\end{document}

