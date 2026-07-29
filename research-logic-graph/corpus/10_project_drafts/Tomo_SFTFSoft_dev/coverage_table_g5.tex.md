# LaTeX source: coverage_table_g5.tex

Source: `D:\__SFTF_Projects(2026)\Tomo_SFTFSoft_dev\draft\coverage_table_g5.tex`

% ---------------------------------------------------------------------------
% Experiment x mesh-group coverage table (trilogy 5-group protocol, g5test)
% 사용법: 본문 또는 보충자료의 적절한 위치에
%     \input{coverage_table_g5}
% 로 삽입한다.  Datasets 절에는 "메쉬 정체성은 기반 SFTF 연구의 5그룹 벤치마크를
% 따르며, 표~\ref{tab:coverage-g5} 가 실험별 사용 부분집합을 정리한다"는 문장을
% 이미 넣어 두었다(main.tex / main_en.tex / SFTFSoft_TDP_draft.tex).
% 2026-07-11 갱신: CuraEngine 검증을 A/B/C 전 그룹으로 확장(헤드라인 18 + 퇴화 3 = 21).
% ---------------------------------------------------------------------------
% 기호: wasysym 의 \CIRCLE(꽉 찬 원)/\LEFTcircle(반원).  패키지가 없어도 컴파일되도록
% 아래 폴백을 제공한다(패키지가 이미 있으면 정의를 덮어쓰지 않는다).
\providecommand{\CIRCLE}{\ensuremath{\bullet}}
\providecommand{\LEFTcircle}{\ensuremath{\circ}}
\begin{table}[H]
\centering
\caption{Experiment coverage over the trilogy five-group mesh benchmark
(\textbf{A} basic shapes, \textbf{B} simple functional parts, \textbf{C}
organic scans, \textbf{D} Thingi10K set~1, \textbf{E} Thingi10K set~2
large meshes) plus the synthetic gradient-check shapes.
$\CIRCLE$~=~full group, $\LEFTcircle$~=~subset (noted below),
--~=~not used.  Group identities are identical to the base SFTF study; only
the resolution is adapted where a method constraint requires it.}
\label{tab:coverage-g5}
\begin{tabular}{lcccccc}
\toprule
Experiment & Synth. & A & B & C & D & E \\
\midrule
Gradient / finite-difference checks (\S4.1)        & $\CIRCLE$ & -- & -- & -- & -- & -- \\
Soft$\to$hard relaxation sweep (\S4.1)             & $\CIRCLE$ & -- & $\LEFTcircle^{a}$ & $\LEFTcircle^{b}$ & -- & -- \\
Intermediate TomoNV / LOMO correlation (\S4.1)     & -- & -- & $\LEFTcircle^{a}$ & $\CIRCLE$ & -- & -- \\
CuraEngine support-mass validation (\S4.2, Table~\ref{tab:cura}) & -- & $\CIRCLE^{c}$ & $\CIRCLE^{c}$ & $\CIRCLE$ & $\LEFTcircle^{d}$ & $\LEFTcircle^{e}$ \\
End-to-end orientation percentile (\S4.2)          & -- & $\LEFTcircle^{f}$ & $\LEFTcircle^{a}$ & $\CIRCLE$ & $\LEFTcircle^{d}$ & -- \\
Vertex-gradient shape optimization (\S4.3)         & -- & $\LEFTcircle^{f}$ & $\LEFTcircle^{a}$ & $\LEFTcircle^{b}$ & -- & -- \\
Degenerate-optimum (symmetry) reporting (\S4.3)    & -- & $\CIRCLE$ & $\LEFTcircle^{a}$ & -- & -- & -- \\
Label-free GNN LOO demo (\S4.3 / Supp.)            & -- & $\LEFTcircle^{f}$ & $\LEFTcircle^{a}$ & $\CIRCLE$ & -- & -- \\
Mesh-resolution / coarse-to-fine (App.~\ref{app:mesh-mg})   & -- & -- & -- & $\LEFTcircle^{b}$ & -- & $\LEFTcircle^{e}$ \\
Runtime and method comparison (App.~\ref{app:runtime})      & -- & -- & -- & $\LEFTcircle^{b}$ & -- & -- \\
\bottomrule
\end{tabular}

\medskip
\raggedright\footnotesize
$^{a}$ B without \emph{hollow\_box} (four parts: U-bracket, hook, c-clamp,
pipe-elbow).\quad
$^{b}$ \emph{Bunny} only, or as listed in the corresponding table.\quad
$^{c}$ Full A/B groups are sliced (all five each), but the CuraEngine table's
\emph{headline} 18-mesh mean uses only shapes on which rank validation is well-posed:
A's \emph{cube} and \emph{sphere} and B's \emph{hollow\_box} are reported in a
separate block and excluded from the headline --- the sphere's support landscape is
flat under rotation, the cube is a near-degenerate 12-face solid, and the hollow box's
support is governed by an internal cavity invisible to surface-normal predictors.\quad
$^{d}$ three Thingi10K set-1 mechanical parts (IDs as listed in
Table~\ref{tab:cura}).\quad
$^{e}$ E-group meshes ($5\times10^{5}$--$10^{6}$ faces) exceed the all-pairs
$O(F^{2})$ receiver set of the reference implementation; they enter only
through the fixed-parameter vertex-clustering decimation of Appendix~\ref{app:mesh-mg}
(mesh \emph{identity} preserved, resolution reduced and disclosed).\quad
$^{f}$ A without \emph{cube} (near-degenerate 12-face geometry) --- \emph{sphere},
\emph{cylinder}, \emph{cone}, \emph{torus} appear where noted; the sphere/cylinder are
the rotationally degenerate cases of the symmetry study by design.
\end{table}
% ---------------------------------------------------------------------------

