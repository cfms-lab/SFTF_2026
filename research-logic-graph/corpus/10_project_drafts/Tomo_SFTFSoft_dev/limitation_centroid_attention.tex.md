# LaTeX source: limitation_centroid_attention.tex

Source: `D:\__SFTF_Projects(2026)\Tomo_SFTFSoft_dev\draft\limitation_centroid_attention.tex`

% ==========================================================================
% limitation_centroid_attention.tex
% Suggested insertion for main_en.tex: as the LAST subsection of
% "Results and Discussion" (after \subsection{Applications and Degenerate
% Optima}), or immediately before \section{Conclusion}.
%
% Uses only macros already defined in main_en.tex:
%   \cvec \mvec \nvec \sigmoid \softplus \relu
% Cross-reference targets to fix on insertion:
%   \ref{sec:softflow}  -> label of \subsection{From Hard Routing to Soft Flow}
%                          (add \label{sec:softflow} there if absent)
% ==========================================================================

\subsection{Limitation: the Sharp Limit of the Centroid Receiver Attention}
\label{sec:centroid-limit}

The convergence statement of Section~\ref{sec:softflow} requires one
qualification, which we state explicitly rather than leave implicit in the
generic-position wording.  As the temperature parameters sharpen, the
attention $\pi_{ij}$ concentrates on the candidate that \emph{maximizes the
compatibility} $a_{ij}$, and this candidate need not be the ray-cast receiver
$t_i$.  The lateral factor $\exp\!\bigl(-d_{ij}^2/2(\sigma_\ell D)^2\bigr)$
measures the distance from the \emph{centroid} of a candidate face to the
build ray, whereas the hard assignment is decided by ray--triangle
\emph{intersection}.  These two orderings can disagree: a face that the
downward ray does not intersect at all may have a laterally closer centroid
than the face it does hit.

A minimal counterexample makes the failure mode concrete.  Place a source
sample at the origin height $1$ with the downward ray along $-\nvec$.  A
large receiver triangle with vertices $(-2,-1,0)$, $(2,-1,0)$, $(0,3,0)$ is
intersected by the ray, but its centroid $(0,\tfrac13,0)$ has squared lateral
distance $d^2=\tfrac19$.  A small distractor face at height $0.5$ with
vertices $(\tfrac1{50},-\tfrac1{100},\tfrac12)$,
$(\tfrac2{25},-\tfrac1{100},\tfrac12)$,
$(\tfrac1{20},\tfrac1{50},\tfrac12)$ is \emph{missed} by the ray, yet its
centroid $(0.05,0,0.5)$ has squared lateral distance $d^2=\tfrac1{400}$.  The
log-affinity margin in favor of the distractor,
$\bigl(\tfrac19-\tfrac1{400}\bigr)/\bigl(2\sigma_\ell^2D^2\bigr)$, is
positive for every $\sigma_\ell$ and \emph{diverges} as
$\sigma_\ell\rightarrow0$: sharpening strengthens the misassignment instead
of correcting it.  The vertical factors compound the effect here, since the
distractor is also nearer in height.  Consequently the precise statement of
the sharp limit is conditional: $L_{\mathrm{SFTF}}\rightarrow J_w$ holds
whenever the affinity maximizer over $\mathcal C(i)\cup\{\mathrm{bed}\}$
coincides with the hard receiver $t_i$ (or plate) for every source face,
while the $\softplus_\beta$ overhang, sigmoid gate, and soft-min plate
ingredients converge unconditionally.  The centroid attention is therefore a
\emph{proximity-heuristic gradient router}, not a relaxed visibility model,
and we no longer claim pointwise convergence of the receiver assignment in
general position.

Three observations bound the practical impact on the results reported in
this paper.  First, the prediction headline is untouched: $S_g$ and
$S_g^{\mathrm{hard}}$ contain no receiver attention by construction, so the
$+0.80$/$+0.87$ Cura correlations do not depend on the router.  Second, every
orientation and shape-optimization outcome is validated externally by
CuraEngine on the optimized geometry; a misrouted gradient can slow or stall
the optimizer, but it cannot inflate the reported support-removal figures,
which are measured by the slicer, not by $L_{\mathrm{SFTF}}$.  Third, the
failure requires a laterally near, vertically near face that the ray
nevertheless misses; on the dense, roughly uniform meshes used here the
affinity maximizer and the ray-cast receiver typically agree, which is
consistent with the observed optimization behavior --- but adversarial
geometry of the kind above exists in ordinary mechanical parts (thin ribs,
pins, and brackets beside an overhang), so the condition is a genuine
restriction rather than a technicality.

The principled repair is to make the relaxation \emph{visibility
consistent}: order candidates by front-to-back occlusion along the ray and
assign soft weights through a transmittance recursion (a soft first hit), so
that the sharp limit recovers the ray-cast receiver by construction rather
than by assumption.  Developing this occlusion-aware formulation, together
with an exact interval-union treatment of overlapping support columns, is
ongoing work outside the scope of this paper; here we scope all claims to
the conditional statement above.

% ==========================================================================
% END of insertion.
% ==========================================================================

