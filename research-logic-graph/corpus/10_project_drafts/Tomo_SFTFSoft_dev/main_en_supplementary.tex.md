# LaTeX source: main_en_supplementary.tex

Source: `D:\__SFTF_Projects(2026)\Tomo_SFTFSoft_dev\draft\main_en_supplementary.tex`

% =====================================================================
%  main_en_supplementary.tex -- supplementary material for main_en.tex
%  Build: uv run python scripts/build_pdf.py draft/main_en_supplementary.tex
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
\usepackage{array}
\usepackage{algorithm}
\usepackage{algpseudocode}
\usepackage{geometry}
\geometry{margin=25mm}
\usepackage[hidelinks]{hyperref}

\usepackage{tikz}
\usetikzlibrary{arrows.meta, calc, positioning, decorations.pathreplacing,
  decorations.pathmorphing, patterns, shapes.geometric}
\usepackage{pgfplots}
\pgfplotsset{compat=1.18}

\graphicspath{{pics/}{./}}

\renewcommand{\thefigure}{S\arabic{figure}}
\renewcommand{\thetable}{S\arabic{table}}
\renewcommand{\theequation}{S\arabic{equation}}

\newcommand{\nvec}{\bm{n}}
\newcommand{\mvec}{\bm{m}}
\newcommand{\cvec}{\bm{c}}
\newcommand{\relu}{\operatorname{relu}}
\newcommand{\softplus}{\operatorname{softplus}}
\newcommand{\sigmoid}{\operatorname{sigmoid}}

\title{Supplementary Material:\\
Differentiable Support Flow Tensor Field as a Loss Term}
\author{}
\date{}

\begin{document}
\maketitle

\section{Hard SFTF and the Wave Relaxation}

The concise manuscript keeps only the minimal notation needed to state the
differentiable loss.  This supplement records the fuller hard-SFTF construction and
the figures that motivated the relaxation.  Let face $i$ have centroid $\cvec_i$, unit
normal $\mvec_i$, and area $A_i$.  For build direction $\nvec\in S^2$, define the build
plate height, overhang factor, and source height as
\begin{align}
z_{\mathrm{plate}}(\nvec) &= \min_{\bm v\in V}\ \bm v\cdot\nvec, &
O_i(\nvec) &= \max\!\big(0,\,-\mvec_i\cdot\nvec\big), &
\eta_i(\nvec) &= \cvec_i\cdot\nvec-z_{\mathrm{plate}}(\nvec).
\label{seq:base}
\end{align}
Here $O_i$ is zero for self-supporting faces and grows as the face normal tilts
opposite to the build direction.  In hard SFTF, an overhang face casts a ray in
direction $-\nvec$.  If a valid receiver $t_i$ exists, the closest valid receiver is
selected; otherwise the face is assigned to the build plate.  A valid receiver must be
below the source, laterally hit by the ray, nonidentical to the source face, and
sufficiently upward facing with respect to $\nvec$.

\begin{figure}[H]
\centering
\includegraphics[width=\linewidth]{stft_wave_analogy1.png}
\caption{Particle-versus-wave analogy for the SFTF relaxation.  In the particle
picture, a ray has a sharp boundary and assigns each source face to one receiver.  In
the wave picture, diffraction near geometric discontinuities spreads the influence
over several receiver candidates.  The differentiable SFTF loss uses this analogy only
as a modeling guide: the hard receiver is replaced by a soft attention distribution
whose width is controlled by temperature parameters.  As the effective wavelength
shrinks, the soft assignment approaches the original hard ray cast.}
\label{sfig:wavelength}
\end{figure}

With $D$ denoting the mesh bounding-box diagonal and
$\operatorname{sym}(\bm F)=\tfrac12(\bm F+\bm F^\top)$, the hard face-to-face,
build-plate, and tensor terms are
\begin{align}
P(\nvec) &= \sum_{i:\,\mathrm{face}}\! O_i A_i A_{t_i},
\label{seq:hard-p}\\
B(\nvec) &= \sum_{i:\,\mathrm{bed}}\! O_i A_i\big(1+\alpha\eta_i\big),
\qquad \alpha=\frac{1}{D},
\label{seq:hard-b}\\
\bm F(\nvec) &= \sum_{i:\,\mathrm{face}}
\frac{O_i A_i A_{t_i}}{1+\alpha h_{it_i}}\,
\mvec_i\otimes\mvec_{t_i}, \qquad
R(\nvec)=\max\!\big(0,-\nvec^\top\operatorname{sym}(\bm F)\nvec\big).
\label{seq:hard-f}
\end{align}
The original SFTF objective and the weighted version used for the differentiable
relaxation are
\begin{align}
J_{\mathrm{SFTF}}(\nvec)
  &= \tilde R_{\mathrm{aug}}(\nvec)+P(\nvec)
   = R(\nvec)+B(\nvec)+P(\nvec), \qquad
     \nvec^\ast=\arg\min_{\nvec\in S^2}J_{\mathrm{SFTF}}(\nvec),
\label{seq:hard-j}\\
J_w(\nvec)&=w_R R(\nvec)+w_P P(\nvec)+w_B B(\nvec).
\label{seq:hard-jw}
\end{align}
The nondifferentiable operation is not the tensor algebra itself, but the discrete
receiver switch $t_i$ and the bed-versus-face decision attached to the ray cast.

\section{Soft Receiver Assignment and Full Loss}

For a source face $i$, let $\mathcal C(i)$ be the finite receiver candidate set.  For
each candidate $j$, define
\[
h_{ij}=(\cvec_i-\cvec_j)\cdot\nvec,\qquad
d_{ij}^2=\|\cvec_j-\cvec_i\|^2-\big((\cvec_j-\cvec_i)\cdot\nvec\big)^2 .
\]
The unnormalized receiver compatibility is
\begin{equation}
a_{ij}=
\underbrace{\sigmoid\!\left(\frac{h_{ij}}{\tau_b D}\right)}_{\text{below-source gate}}\,
\underbrace{\exp\!\left(-\frac{d_{ij}^2}{2(\sigma_\ell D)^2}\right)}_{\text{lateral ray proximity}}\,
\underbrace{\sigmoid\!\left(\frac{\mvec_j\cdot\nvec-\tau_r}{\epsilon_r}\right)}_{\text{receiver normal gate}}\,
\underbrace{\exp\!\left(-\frac{\beta_n}{D}\relu(h_{ij})\right)}_{\text{nearest-receiver preference}},
\qquad a_{ii}=0.
\label{seq:aij}
\end{equation}
A constant bed slot $a_0$ converts these scores to probabilities:
\begin{equation}
\pi_{ij}=\frac{a_{ij}}{\sum_{k\in\mathcal C(i)}a_{ik}+a_0},\qquad
\pi_i^{\mathrm{bed}}=\frac{a_0}{\sum_{k\in\mathcal C(i)}a_{ik}+a_0},\qquad
\sum_j\pi_{ij}+\pi_i^{\mathrm{bed}}=1.
\label{seq:pi}
\end{equation}

\begin{figure}[H]
\centering
\input{pics/ftree4x_unified_tikz.tex}
\resizebox{\linewidth}{!}{%
\begin{tikzpicture}[line join=round,line cap=round]
  \begin{scope}
    \node[panelLabel] at (-2.35,6.95) {(a) particle hard raycasting};
    \ftreeSun{-2.5}{6.35}
    \draw[sunray] (-2.32,6.20) -- (-0.95,4.32);
    \draw[sunray] (-2.18,6.48) -- (0.20,6.35);
    \draw[sunray] (-2.42,6.04) -- (-1.25,5.32);
    \ftreeUPlate
    \ftreeUMesh
    \filldraw[recface] \ftreeURec;
    \filldraw[srcface] \ftreeUSrcFace;
    \draw[hardray] (-0.872,3.936) -- (-0.872,3.066) node[midway,right=14pt,yshift=-7pt,font=\scriptsize]{$-\nvec$};
    \draw[normSrc] (-0.872,4.026) -- (-0.872,3.366) node[right=1pt,font=\scriptsize]{$\mvec_i$};
    \draw[normRec] (-0.872,2.826) -- (-0.872,3.486) node[left=1pt,font=\scriptsize]{$\mvec_j$};
    \fill[srcDot] (-0.872,4.026) circle (1.25pt);
    \fill[recDot] (-0.872,2.826) circle (1.25pt);
    \node[ohred!80!black,font=\scriptsize] at (-1.32,3.97) {$i$};
    \node[rcblue!82!black,font=\scriptsize] at (-1.95,2.74) {$j$};
    \draw[measure] (0.5,4.026) -- (0.5,2.826) node[midway,right=2pt,font=\scriptsize]{$h_{ij}$};
    \node[termLabel] at (1.45,5.95) {$\mvec_i\!\otimes\!\mvec_j$};
    \draw[axisn] (-3.42,3.687) -- (-3.42,5.487) node[above,inner sep=1pt,font=\scriptsize]{$\nvec$};
  \end{scope}
  \begin{scope}[xshift=8.4cm]
    \node[panelLabel] at (-2.35,6.95) {(b) wave soft routing};
    \ftreeSun{-2.5}{6.35}
    \draw[sunwave] (-2.32,6.20) -- (-0.95,4.32);
    \draw[sunwave] (-2.18,6.48) -- (0.20,6.35);
    \draw[sunwave] (-2.42,6.04) -- (-1.25,5.32);
    \ftreeUPlate
    \ftreeUMesh
    \fill[rcblue!30,opacity=0.28] (-1.20,2.74) ellipse (1.55 and 0.40);
    \filldraw[recfacew] \ftreeURecTwo;
    \filldraw[recface] \ftreeURec;
    \filldraw[srcface] \ftreeUSrcFace;
    \draw[normSrc] (-0.872,4.026) -- (-0.872,3.366) node[right=1pt,font=\scriptsize]{$\mvec_i$};
    \fill[srcDot] (-0.872,4.026) circle (1.25pt);
    \node[ohred!80!black,font=\scriptsize] at (-1.32,3.97) {$i$};
    \draw[softray,line width=1.5pt] (-0.872,3.90) .. controls (-0.80,3.40) and (-0.76,3.10) .. (-0.78,2.92)
         node[pos=0.48,right=0.5pt,font=\scriptsize]{$\pi_{ij_1}$};
    \draw[softray,line width=1.0pt] (-0.95,3.92) .. controls (-1.45,3.55) and (-1.75,3.08) .. (-1.70,2.84)
         node[pos=0.5,left=0.5pt,font=\scriptsize]{$\pi_{ij_2}$};
    \draw[softray,line width=0.6pt] (-0.80,3.90) .. controls (0.05,2.55) and (-0.40,1.15) .. (-0.78,0.50)
         node[pos=0.86,right=1pt,font=\scriptsize]{$\pi_i^{\mathrm{bed}}$};
    \fill[recDot] (-0.78,2.92) circle (1.1pt);
    \fill[recDot] (-1.70,2.84) circle (1.1pt);
    \fill[rcblue!82!black] (-0.78,0.47) circle (1.3pt);
    \node[rcblue!82!black,font=\scriptsize] at (-0.50,2.70) {$j_1$};
    \node[rcblue!82!black,font=\scriptsize] at (-2.10,2.66) {$j_2$};
    \node[termLabel] at (1.65,5.95) {$\displaystyle\sum_j \pi_{ij}\,\mvec_i\!\otimes\!\mvec_j$};
    \draw[axisn] (-3.42,3.687) -- (-3.42,5.487) node[above,inner sep=1pt,font=\scriptsize]{$\nvec$};
  \end{scope}
\end{tikzpicture}}
\caption{Hard and soft support routing on the FTree4x mesh.  Panel (a) shows the
original particle-like SFTF step: one overhang source face $i$ is routed by a single
ray to one receiver $j$, so the tensor contribution is $\mvec_i\otimes\mvec_j$.
Panel (b) shows the differentiable replacement: the same source distributes support
responsibility over receiver candidates $j_1,j_2$ and the bed slot with probabilities
$\pi_{ij}$ and $\pi_i^{\mathrm{bed}}$.  The tensor contribution becomes the expected
normal-pair tensor $\sum_j\pi_{ij}\mvec_i\otimes\mvec_j$.}
\label{sfig:soft-routing}
\end{figure}

The soft terms corresponding to \eqref{seq:hard-p}--\eqref{seq:hard-f} are
\begin{align}
\tilde P &= \sum_i \tilde O_i\,A_i\sum_j\pi_{ij}A_j,
\label{seq:soft-p}\\
\tilde B &= \sum_i \tilde O_i\,A_i\,\pi_i^{\mathrm{bed}}
          \big(1+\alpha\,\relu(\eta_i)\big),
\label{seq:soft-b}\\
\tilde{\bm F}_{\mathrm{face}}
  &= \sum_i\sum_j\pi_{ij}
     \frac{\tilde O_i A_i A_j}{1+\alpha\,\relu(h_{ij})}\,
     \mvec_i\otimes\mvec_j, \nonumber\\
\tilde R_{\mathrm{face}}
  &= \softplus_\beta\!\big(-\nvec^\top
     \operatorname{sym}(\tilde{\bm F}_{\mathrm{face}})\nvec\big).
\label{seq:soft-f}
\end{align}
The full differentiable SFTF loss is therefore
\begin{equation}
\boxed{\;L_{\mathrm{SFTF}}(V,\nvec)
=w_R\tilde R_{\mathrm{face}}+w_P\tilde P+w_B\tilde B\; } .
\label{seq:loss}
\end{equation}

The physical support-height extension used for the intermediate TomoNV checks is the
expected overhang-area-times-drop-height under the same soft routing:
\begin{equation}
S(V,\nvec)=
\sum_i \tilde O_i A_i\left(
\pi_i^{\mathrm{bed}}\relu(\eta_i)+\sum_j\pi_{ij}\relu(h_{ij})
\right).
\label{seq:supvol-full}
\end{equation}
The concise manuscript states the production-slicer variant $S_g$, which gates this
height signal at Cura's $60^\circ$ support threshold.

\begin{assumption}[Generic hard receiver configuration]\label{sasm:generic}
At the evaluated $(V,\nvec)$, face connectivity is fixed, all triangle areas are
positive, each overhang face has either a unique nearest valid hard receiver or no
valid receiver, and all hard threshold tests have nonzero margin.
\end{assumption}

\begin{proposition}[Soft-to-hard consistency]\label{sprop:soft-hard}
Under Assumption~\ref{sasm:generic}, if
$\sigma_\ell\to0$, $\tau_b\to0$, $\epsilon_r\to0$, $\beta_n\to\infty$,
$a_0\to0^+$, $\beta\to\infty$, and the soft plate minimum sharpens to the hard
minimum, then
\[
\pi_{ij}\to \mathbf 1[j=t_i],\qquad
\pi_i^{\mathrm{bed}}\to \mathbf 1[\text{no hard receiver}],\qquad
L_{\mathrm{SFTF}}(V,\nvec)\to J_w(\nvec).
\]
\end{proposition}

\begin{proof}[Proof sketch]
The margin conditions keep each hard gate away from its switching boundary.  Logistic
gates converge to hard indicators, the lateral Gaussian collapses to the ray, the
nearest-receiver exponential suppresses all nonminimal valid receivers, and softplus
converges to the positive part.  After the normalization in \eqref{seq:pi}, the mass
therefore concentrates on the unique hard receiver when one exists and on the bed slot
otherwise.  Substituting these limits into \eqref{seq:soft-p}--\eqref{seq:soft-f}
recovers \eqref{seq:hard-p}--\eqref{seq:hard-f}.
\end{proof}

\begin{algorithm}[H]
\caption{Differentiable SFTF loss $L_{\mathrm{SFTF}}(V,\nvec)$}
\label{salg:loss}
\begin{algorithmic}[1]
\Require vertices $V$, faces $F$, build direction $\nvec$, temperatures and weights $\Theta$
\State compute $\cvec_i,\mvec_i,A_i,D$ from $(V,F)$; set $\alpha\gets1/D$ and normalize $\nvec$
\State $\tilde O_i\gets\softplus_\beta(-\mvec_i\cdot\nvec)$, optionally multiplied by a critical-angle gate
\State build receiver candidates $\mathcal C(i)$ for each source face
\For{each source face $i$ and candidate $j\in\mathcal C(i)$}
  \State compute $h_{ij}$ and $d_{ij}^2$
  \State compute $a_{ij}$ using \eqref{seq:aij}
\EndFor
\State normalize to $\pi_{ij}$ and $\pi_i^{\mathrm{bed}}$ using \eqref{seq:pi}
\State compute $z_{\mathrm{plate}}$ by a soft minimum and $\eta_i=\relu(\cvec_i\cdot\nvec-z_{\mathrm{plate}})$
\State compute $\tilde P$, $\tilde B$, and $\tilde R_{\mathrm{face}}$ using \eqref{seq:soft-p}--\eqref{seq:soft-f}
\State \Return $w_R\tilde R_{\mathrm{face}}+w_P\tilde P+w_B\tilde B$
\end{algorithmic}
\end{algorithm}

\section{Additional Figures From the Omitted Evaluation Details}

\begin{figure}[H]
\centering
\includegraphics[width=0.78\linewidth]{demo_sftf_landscape.png}
\caption{Build-direction loss landscape for $L_{\mathrm{SFTF}}(\nvec)$ over yaw and
pitch.  The smooth surface illustrates why gradient-based orientation search is
possible before the temperature is annealed to a nearly hard assignment.  Local basins
visible in this plot are the basins reached by gradient descent, while the hard SFTF
limit approaches the sampled-discrete landscape used by the original method.}
\label{sfig:landscape}
\end{figure}

\begin{figure}[H]
\centering
\includegraphics[width=0.62\linewidth]{demo_sftf_oriented.png}
\caption{Mesh aligned to the optimized build direction.  The optimized direction
$\nvec^\ast$ is rotated to world $+z$ for display, and color indicates the per-face
overhang intensity.  This figure is a visual check that the numerical minimum
corresponds to a plausible low-support pose rather than only to an abstract loss
minimum.}
\label{sfig:oriented}
\end{figure}

\begin{figure}[H]
\centering
\includegraphics[width=0.72\linewidth]{diff_sftf_highdim.png}
\caption{High-dimensional differentiability check.  The same soft receiver assignment
that makes $L_{\mathrm{SFTF}}$ differentiable in $\nvec$ also provides gradients with
respect to mesh-related variables.  This diagnostic uses a high-dimensional soft
assignment design space to show that the relaxation supplies stable descent signals,
not only scalar orientation scores.}
\label{sfig:highdim}
\end{figure}

\begin{figure}[H]
\centering
\includegraphics[width=0.62\linewidth]{demo_sftf_vs_tomo.png}
\caption{Intermediate comparison between differentiable SFTF and TomoNV physical
support-mass estimates.  TomoNV is useful as a voxelized reference for development,
but the concise manuscript treats legacy CuraEngine 15.04 as the final production
slicer target.  The figure records the intermediate evidence that the basic tensor
loss alone is a loose physical proxy (Bunny Spearman $+0.17$, Pearson $+0.25$ after
the 2026-07-03 DLL fix) and motivates the support-height term.}
\label{sfig:vstomo}
\end{figure}

\begin{figure}[H]
\centering
\includegraphics[width=\linewidth]{contour_compare_bunny.png}
\caption{Bunny build-direction contour comparison.  The panels compare hard SFTF,
soft SFTF at different temperatures, and the sharpened limit.  The relevant point is
the path from a smooth, gradient-friendly landscape to the discrete hard-SFTF
landscape: early optimization can exploit the smooth field, then annealing recovers a
ranking close to the original hard receiver rule.}
\label{sfig:contourcompare}
\end{figure}

\begin{figure}[H]
\centering
\includegraphics[width=0.92\linewidth]{demo_sftf_tuned.png}
\caption{Rank-space weight retuning against TomoNV.  The left panel uses the baseline
weights $w=(1,1,1)$, while the right panel uses cross-validated rank-space weights.
The held-out Spearman improves from $+0.21$ to $+0.40$, which is real but limited,
showing that reweighting $(R,P,B)$ cannot by
itself supply the missing physical height signal.  This is why the supplement keeps
the full support-height term \eqref{seq:supvol-full} rather than treating weights as
the only calibration mechanism.}
\label{sfig:tuned}
\end{figure}

\begin{figure}[H]
\centering
\includegraphics[width=0.9\linewidth]{demo_sftf_learned.png}
\caption{Leave-one-mesh-out generalization against TomoNV support mass.  The physical
support-height term $S$ generalizes better than the raw differentiable tensor loss and
better than the fitted Ridge, gradient-boosted, and MLP baselines used in this
ablation (mean Spearman $+0.61$ vs $+0.17$ for the raw tensor loss).  This supports
the interpretation that the dominant missing signal is
geometric support height, not model capacity.}
\label{sfig:learned}
\end{figure}

\section{Additional Application Figures}

\begin{figure}[H]
\centering
\includegraphics[width=\linewidth]{demo_sftf_shapeopt_torus_tomocpu_support.png}
\caption{Support-aware shape optimization on an arbitrary torus-like mesh.  The
optimization uses a scalable $O(F)$ support-height objective plus surface-preservation
regularization.  The deformed geometry reduces the estimated TomoCPU support mass from
$2.49$ g to $0.63$ g ($-75\%$).  Without the surface-preservation term the same
objective degenerates into fine wrinkles and the TomoCPU mass instead \emph{increases}
(to $3.94$ g), so surface preservation is essential for the scalable objective.}
\label{sfig:shapeopt-torus}
\end{figure}

\begin{figure}[H]
\centering
\includegraphics[width=0.66\linewidth]{demo_sftf_tilt.png}
\caption{Optimal tilt reporting for axisymmetric or nearly axisymmetric shapes.  When
the landscape is not well represented by a single isolated optimum, the loss can be
collapsed onto tilt relative to a detected symmetry axis.  The optimum is then reported
as an equivalent set of directions, such as a circle at fixed tilt, instead of an
arbitrary point returned by one optimizer run.}
\label{sfig:tilt}
\end{figure}

\end{document}

