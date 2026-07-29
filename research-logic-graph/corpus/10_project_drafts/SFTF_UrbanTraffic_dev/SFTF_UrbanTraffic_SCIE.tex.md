# LaTeX source: SFTF_UrbanTraffic_SCIE.tex

Source: `D:\__SFTF_Projects(2026)\SFTF_UrbanTraffic_dev\draft\SFTF_UrbanTraffic_SCIE.tex`

% SIMPAT-oriented review manuscript. Author metadata and repository DOI pending.
\documentclass[11pt]{article}
\usepackage[a4paper,margin=25mm]{geometry}
\usepackage{amsmath,amssymb,booktabs,graphicx}
\usepackage{float}
\usepackage[round]{natbib}
\usepackage[colorlinks=true,allcolors=blue]{hyperref}
\setlength{\emergencystretch}{2em}

\title{Validation and Falsification of a Flow-Coherent Directed-Field Model\
for Reversible-Lane Initialization}
\author{Anonymous for review}
\date{}

\begin{document}
\maketitle

\begin{abstract}
Reversible-lane simulation couples discrete directional-capacity decisions with
uncertain time-dependent demand and downstream assignment. We formulate and
evaluate a Directed Support-Flow Tensor Field (D-SFTF) as a lane-conserving
initializer and proxy-plan model, not as a replacement for traffic assignment.
The JAX implementation combines normalized directional imbalance with temporal,
hysteretic, and forecast-coherent signed spatial regularization. A tiered
verification and validation protocol uses exact dynamic programming, paired
synthetic experiments, a public network, and an observed-count falsification
audit. Across 450 identical downstream-solver runs, all initializers reached
effectively identical final objectives, while D-SFTF was usually slower than the
local initializer; general solver acceleration is therefore rejected. Direct
proxy plans improved across controlled grid and irregular-network families. On
the Sioux Falls topology with synthetic temporalization, flow-coherent D-SFTF
reduced mean proxy gap from 17.30\% to 11.84\%, whereas topology-only smoothing
failed. A separate OSM/AADT audit exposed demand-vintage and calibration
limitations; conserved OD disaggregation improved held-out coverage but not
Pearson correlation. The evidence supports D-SFTF as a reproducible conditional
candidate model under noisy demand and demonstrates why negative solver and
external-data checks are necessary before operational claims.
\end{abstract}

\noindent\textbf{Keywords:} simulation validation; reversible lanes;
traffic modelling; tensor field; reproducibility; falsification

\section{Introduction}
Network-wide lane reversal is a mixed discrete--continuous problem because lane
directions change capacity while travelers change routes. Existing work embeds
lane decisions in mixed-integer, equilibrium, system-optimal, cell-transmission,
or joint routing formulations \citep{conceicao2020rlndp,levin2016ctm,wollenstein2022lane}.
These formulations target the final plan. We ask a narrower computational
question: can a structured directional field provide a useful candidate plan or
initial condition before those expensive validators are run?

Our contributions are: (i) a bounded, lane-conserving directed-field model with
flow-coherent signed coupling and a differentiable JAX implementation; (ii)
verification against exact discrete optimization and explicit constraint tests;
(iii) a falsification-oriented evaluation showing when a strong solver erases
initialization and when topology-only smoothing fails; and (iv) a PC-reproducible
validation hierarchy spanning synthetic graphs, a public benchmark, and an
external observed-count audit.

\section{Related Work}
\subsection{Reversible-lane and network design}
Joint routing and lane-reversal optimization is already well established
\citep{wollenstein2022lane,conceicao2020rlndp,di2020coupling}. Mixed-integer
Frank--Wolfe methods likewise address traffic network design directly
\citep{sharma2024mifw}. D-SFTF is therefore positioned below these solvers as an
initializer/proxy, not as a competing optimality framework.

\subsection{Spatiotemporal graph and traffic-assignment surrogates}
Graph structure learning captures spatial and temporal dependence in traffic
forecasting \citep{zhang2020stgraph}, while physics-informed heterogeneous GNNs
can approximate traffic assignment \citep{liu2024heterogeneous}. Asymmetric
traffic-assignment costs have also been treated explicitly
\citep{marechal2024asymmetric}. Our novelty is not generic graph regularization,
asymmetry, or learned assignment; it is forecast-coherent directed regularization
for a constrained initialization layer, together with explicit negative results.

\section{Directed-Field Initializer}
\subsection{Normalized directional field}
For forward and reverse forecast demand $q^+_{et}$ and $q^-_{et}$, define
\begin{equation}
d_{et}=\frac{q^+_{et}-q^-_{et}}{q^+_{et}+q^-_{et}+\epsilon}.
\end{equation}
The bounded field $x\in[-1,1]^{E\times T}$ minimizes data fidelity plus signed
spatial, temporal, and hysteretic quadratic terms:
\begin{align}
\mathcal{L}(x)={}&\sum_{e,t}w_{et}(x_{et}-d_{et})^2
+\lambda_s\sum_{(e,g),t}|c_{eg}|\left(x_{et}-\operatorname{sgn}(c_{eg})x_{gt}\right)^2 \nonumber\\
&+\lambda_t\sum_{e,t>1}(x_{et}-x_{e,t-1})^2
+\lambda_h\sum_{e,t}(x_{et}-x^{\mathrm{prev}}_{et})^2.\label{eq:field}
\end{align}
The sign of $c_{eg}$ transports canonical corridor orientation through a shared
node. On the public-network variant, its magnitude is gated by the positive
cosine similarity between orientation-aligned forecast profiles. Thus adjacent
but flow-incoherent corridors are not smoothed merely because they share a node.
Projected-gradient iterations use JAX derivatives and enforce the box constraint.

\subsection{Lane conservation and claim boundary}
Integer projection preserves the total lanes per corridor and a minimum lane
count $m$ in both directions:
\begin{equation}
k^+_{et}=m+\operatorname{round}\!\left[(K_e-2m)(1+x_{et})/2\right],\qquad
k^-_{et}=K_e-k^+_{et}.
\end{equation}
Setting all regularizers to zero recovers the local demand-proportional baseline.
The resulting plan is always evaluated by a downstream proxy optimizer or
user-equilibrium assignment.

\section{Verification and Validation Design}
\subsection{Hypotheses and baselines}
We tested four falsifiable hypotheses: D-SFTF reduces downstream iterations; its
regularization improves robustness to forecast noise; signed spatial coupling
adds value beyond temporal filtering; and the effect transfers to a public road
network. Baselines were fixed, random, local proportional, temporal-only,
topology-only signed/unsigned, exact separable dynamic programming (DP), and BPR
user-equilibrium assignment. All initialization methods used forecast demand;
realized demand was reserved for evaluation.

\subsection{Evidence tiers}
Tier 1 used $3\times3$, $4\times4$, and $5\times5$ grids with 30 paired seeds per
size. Tier 2 used irregular Euclidean graphs with 12, 20, and 30 nodes and 30
paired seeds per size. Both used six periods, asymmetric commuter/reversal demand,
25\% multiplicative forecast noise, and a corridor-separable exact DP reference.
Tier 3 used the public Sioux Falls TNTP topology and OD matrix, but its six-period
profile and forecast noise remained synthetic. Tier 4 mapped 2025 City counts to
a frozen OSM arterial graph and served only as an external falsification audit.

\subsection{Statistical analysis}
Seed-level comparisons were paired. We report wins, the mean and median paired
gap difference, a deterministic 10,000-resample bootstrap 95\% interval for the
mean, paired Cohen's $d_z$, and a two-sided Wilcoxon signed-rank test. Wilcoxon
$p$-values were Holm-adjusted within the grid, irregular, and public-network
evidence families. Positive gap differences favor D-SFTF.

\section{Results}
\subsection{Rejected convergence-acceleration hypothesis}
Across balanced, commuter, incident, reversal, and forecast-noise scenarios, the
tested projected downstream solver converged to final gaps within 0.0--0.6\% of
the exact proxy optimum regardless of initialization. Across 30 paired seeds per
scenario, D-SFTF required more iterations than local initialization to enter a
1\% objective-descent band in balanced, commuter, reversal, and forecast-noise
cases. The mean local-minus-D-SFTF differences were $-130.9$, $-21.2$, $-61.8$,
and $-57.0$ iterations, respectively; their bootstrap 95\% intervals excluded
zero. The incident difference was $+12.0$ iterations but was not significant
after within-scenario Holm correction ($p=0.116$). All 450 runs preserved lane
constraints, and the largest within-instance spread in final relaxed objective
was $3.81\times10^{-6}$. We therefore reject general acceleration under this
solver. This negative result defines the scope of the remaining direct-plan
experiments.

\subsection{Noise and topology ablations}
Table~\ref{tab:grid} shows that the full field outperformed local proportional
allocation in all 90 grid instances and increasingly separated from the
temporal-only ablation as network size grew.

\begin{table}[t]
\centering\small
\caption{Median gap to exact separable DP on synthetic grids. Differences are
percentage points; switches saved are relative to local allocation.}
\label{tab:grid}
\begin{tabular}{lrrrrr}
\toprule
Grid & Local & Temporal & D-SFTF & Local$-$D-SFTF & Switches saved\\
\midrule
$3\times3$ & 15.38\% & 8.96\% & 7.30\% & 8.08 & 15.2\\
$4\times4$ & 15.28\% & 8.46\% & 6.92\% & 8.35 & 32.6\\
$5\times5$ & 26.38\% & 13.84\% & 9.68\% & 16.70 & 70.9\\
\bottomrule
\end{tabular}
\end{table}

\begin{figure}[t]
\centering
\includegraphics[width=.78\linewidth]{pics/urb_grid_scaling.png}
\caption{Scaling of direct proxy-plan gaps on controlled grids (30 paired seeds
per size). Bars/points are generated from the frozen result JSON.}
\label{fig:grid}
\end{figure}

Irregular networks remove regular-grid and Manhattan-routing assumptions.
Signed D-SFTF beat local and temporal-only allocation in all 90 paired instances
(Table~\ref{tab:irregular}). Its advantage over unsigned coupling was smaller:
0.38--0.45 percentage points on average, with paired win rates of 56.7\%, 80.0\%,
and 70.0\% for 12, 20, and 30 nodes. Thus most improvement came from spatial
regularization, while orientation transport supplied a secondary correction.

\begin{table}[t]
\centering\small
\caption{Median gap to exact separable DP on irregular synthetic networks.}
\label{tab:irregular}
\begin{tabular}{lrrrrr}
\toprule
Nodes & Local & Temporal & Unsigned & Signed D-SFTF & Local$-$signed\\
\midrule
12 & 18.10\% & 11.80\% & 3.69\% & 3.24\% & 14.87\\
20 & 19.82\% & 11.62\% & 3.92\% & 3.51\% & 16.31\\
30 & 20.97\% & 11.68\% & 4.04\% & 3.67\% & 17.30\\
\bottomrule
\end{tabular}
\end{table}

\begin{figure}[t]
\centering
\includegraphics[width=.78\linewidth]{pics/urb_irregular_scaling.png}
\caption{Irregular-network ablation across 30 paired seeds per size.}
\label{fig:irregular}
\end{figure}

\subsection{Public-network transfer}
Pure geometric smoothing failed on Sioux Falls: unsigned and signed variants had
mean gaps of 53.38\% and 81.46\%, compared with 17.30\% for local allocation.
Flow-coherent gating reversed that failure (Table~\ref{tab:sioux}). It beat local
in 28 of 30 paired seeds and temporal-only in 23 of 30; the mean improvement over
local was 5.46 percentage points (bootstrap 95\% interval 2.22--9.67).

\begin{table}[t]
\centering\small
\caption{Public Sioux Falls benchmark with synthetic temporalization (30 seeds).}
\label{tab:sioux}
\begin{tabular}{lrrr}
\toprule
Method & Mean gap & Median gap & Mean switches\\
\midrule
Local proportional & 17.30\% & 12.24\% & 91.8\\
Temporal only & 16.94\% & 10.39\% & 67.8\\
Geometric unsigned & 53.38\% & 56.38\% & 45.3\\
Geometric signed & 81.46\% & 100.45\% & 41.7\\
Flow-coherent D-SFTF & 11.84\% & 8.06\% & 69.6\\
\bottomrule
\end{tabular}
\end{table}

\begin{figure}[t]
\centering
\includegraphics[width=.78\linewidth]{pics/urb_sioux_falls.png}
\caption{Public-network comparison. Topology-only smoothing is a falsified
baseline rather than a hidden negative result.}
\label{fig:sioux}
\end{figure}

\subsection{External observed-count falsification}
The original TNTP loading did not reproduce current spatial AADT ranking
(Pearson $r\approx0$). Replacing the simplified graph with a current OSM arterial
network raised Pearson correlation to 0.360, but median absolute percentage error
remained 87.97\% and only 395 of 560 eligible stations received positive modeled
flow. This falsifies a calibrated-current-city interpretation of the public OD.

As a separate demand audit, four geometry-only anchors were assigned to each
zone and origin/destination weights were learned with JAX on four folds while
preserving every original zonal OD total. All five held-out assignments reached
relative gap below 0.5\%. Compared with converged uniform anchors, learned
weights increased positive-flow coverage from 410 to 444 stations, Spearman
correlation from 0.363 to 0.396, reduced median percentage error from 89.53\% to
87.38\%, and reduced mean absolute log error from 3.332 to 2.857. Pearson
correlation remained 0.332. These results support demand preprocessing, not
D-SFTF efficacy.

\section{Discussion}
The evidence supports conditional initializer utility rather than a new final
traffic-control method. A strong downstream optimizer removes value because all
tested structured starts already lie in a small basin around the relaxed optimum.
Direct projection exposes differences that the solver otherwise erases. Spatial
regularization is useful only when the coupling reflects transported forecast
flow: junction adjacency alone can connect unrelated OD streams and catastrophically
oversmooth their directional fields. The public-network failure and correction
are therefore as important as the positive synthetic results.

The external audit provides a second boundary. Better road geometry and
training-only OD disaggregation improve coverage and ranking, but substantial
magnitude error persists. This separates demand-model inadequacy from the central
initializer question and prevents circular calibration against the test counts.

\section{Limitations}
The study lacks directional hourly ground truth, signal control, queue spillback,
transition safety, endogenous incidents, microscopic simulation, and field
deployment. Exact DP is exact only for the defined separable proxy. The public
temporal profile is synthetic, OSM capacities use road-class defaults when tags
are missing, and static bidirectional AADT cannot validate time-dependent lane
direction decisions. The reported paired comparisons cover the implemented
generators and should not be generalized to arbitrary traffic distributions.

\section{Conclusion}
Flow-coherent D-SFTF provides a fast, lane-conserving candidate plan under the
tested noisy demand regimes, and its spatial component transfers across grid,
irregular, and public topologies when coupling is conditioned on forecast-flow
coherence. It does not accelerate the tested strong solver, topology-only
smoothing fails, and the external AADT audit does not establish real-world
operational benefit. The appropriate role is therefore a conditional initializer
or proxy-plan generator upstream of assignment and safety-aware optimization.

\appendix
\section{Paired Statistical Summary}
\input{generated/paired_primary_table.tex}
The full machine-readable appendix additionally includes temporal-only and
unsigned/geometric ablations and rank-biserial effects. It is generated directly
from frozen seed-level JSON by \texttt{scripts/build\_paired\_statistics.py}.

\section*{Data and Code Availability}
The repository contains fixed random seeds, environment metadata, tests, frozen
TNTP and OSM snapshots, source checksums, and scripts that regenerate every
reported JSON and figure. City traffic counts are distributed under their stated
open-data license. An anonymized repository URL will be inserted at submission.

\section*{Glossary}
\noindent\textbf{D-SFTF:} Directed Support-Flow Tensor Field.\quad
\textbf{AADT:} Annual average daily traffic.\quad
\textbf{OD:} Origin--destination demand matrix.\quad
\textbf{Proxy plan:} A feasible candidate evaluated before trusted assignment
or optimization; it is not asserted to be the operational solution.

\bibliographystyle{plainnat}
\bibliography{references}
\end{document}

