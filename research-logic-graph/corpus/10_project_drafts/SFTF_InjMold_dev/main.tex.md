# LaTeX source: main.tex

Source: `D:\__SFTF_Projects(2026)\SFTF_InjMold_dev\draft\main.tex`

% =====================================================================
%  main.tex — 한글 논문 초안 (xelatex + kotex 로 컴파일)
%
%  빌드:  uv run python scripts/build_pdf.py        (-> main.pdf)
%        uv run python scripts/build_docx.py       (-> main.docx, 그림 포함)
%        uv run python scripts/make_paper_figures.py  (그림 -> draft/pics/)
%
%  ※ 초안 단계 — 분량/용량은 최종 단계에서 줄임.
% =====================================================================
\documentclass[11pt]{article}

% ---- 한글 (xelatex + kotex) -----------------------------------------
\usepackage{kotex}
\usepackage{fontspec}
\setmainhangulfont{Malgun Gothic}

% ---- 수식 / 그림 / 표 ------------------------------------------------
\usepackage{amsmath,amssymb,amsfonts,bm}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{array}
\usepackage{geometry}
\geometry{a4paper, margin=25mm}
\usepackage{hyperref}
\usepackage[numbers]{natbib}

% ---- TikZ (개념도) ---------------------------------------------------
\usepackage{tikz}
\usetikzlibrary{arrows.meta, calc, positioning, decorations.pathreplacing, patterns, shapes.geometric}
\usepackage{pgfplots}
\pgfplotsset{compat=1.18}

\graphicspath{{pics/}{./}}

\newcommand{\dvec}{\mathbf{d}}
\newcommand{\nvec}{\mathbf{n}}

\title{사출 금형 발형 방향·언더컷 사전선별을 위한\\
Support Flow Tensor Field의 이식:\\[2pt]
견적 단계 의사결정 도구}
\author{설인환 외}
\date{\today}

\begin{document}
\maketitle

\begin{abstract}
사출/주조 금형 설계의 가장 이른 단계인 \emph{견적}에서, 부품의 발형(發型, draw)
방향과 그에 따른 언더컷·슬라이드(side action)·다이락(die-lock)을 빠르게
사전선별하는 것은 금형비와 납기를 좌우한다. 본 연구는 적층제조(AM)의 빌드 배향
후보 생성기인 \emph{Support Flow Tensor Field}(SFTF)\citep{sul_sftf}의 세 가지
재사용 가능한 엔진—(1) 방향 의존 비대칭 \emph{entrapment} 흐름 텐서, (2)
ground-node Rayleigh 통합, (3) 값싼 warm-start와 적응 검증 escalation(AVE)—을
금형 발형 문제로 이식한다. 발형 축은 $S^2$가 아니라 사영평면 $\mathbb{RP}^2$ 위의
고비용 블랙박스 최적화이며, AM의 ``overhang을 서포트로 항상 해소''라는 가정이
``언더컷마다 충돌 없는 이형 방향이 존재해야 한다''는 \emph{중첩} 문제로 바뀐다.
우리는 ray-cast 접근성에 기반한 \emph{정확} 검증기(oracle)를 구현하고, 언더컷
면을 호환 pull 방향에 대한 \emph{최소 set-cover}로 묶어 슬라이드 수를 산정하며,
각진 pull(lifter)과 진짜 die-lock을 구분한다. 그 위에 금형판 SFTF 후보
생성기가 수 밀리초 사전선별로 비싼 검증기를 ${\pm}$윈도우 warm-start로만
호출하도록 한다. 해석적 난이도 사다리(T0--T3)와 DFM 교과서 부품 코퍼스에서,
제안 방법은 바운딩박스 6면 휴리스틱이 놓치는 off-axis 최적 발형을 복원하고(side-
action 일치율 1.00 대 0.80), die-lock recall 1.00을 달성한다. 점수 가중치는
검증기 대비 rank-tuning과 leave-one-mesh-out(LOMO) 교차검증으로 보정하여 과적합
(optimism)을 정량화한다. 나아가 이형축이 질량 주축과 어긋난 실제 Thingi10K 부품
46개에서 SFTF는 PCA보다 적은 슬라이드를 견적하여(평균 3.20 대 3.85, 참 최적 2.93)
가설을 실증한다. 본 시스템은 부품 투입에서 1초 내에 상위 발형 전략과
슬라이드 수, die-lock 플래그를 제시하는 견적 단계 의사결정 시트로 마무리된다.
\end{abstract}

% =====================================================================
\section{서론}
% =====================================================================
사출 금형의 견적은 보통 3차원 부품 모델 하나만으로 수 시간 내에 이루어진다. 이
단계에서 가장 비싼 실수는 발형 방향을 잘못 가정해 \emph{필요한 슬라이드 수}를
적게 잡거나, 재설계가 필요한 \emph{die-lock} 부품을 ``몰드 가능''으로 오판하는
것이다. 슬라이드(또는 리프터) 하나는 금형비와 사이클타임에 직접적으로 더해지고,
견적 시점에 놓친 die-lock은 가장 비싼 사고로 이어진다. 따라서 견적 도구에
필요한 것은 단일 ``최적'' 발형이 아니라, \emph{빠르고}, \emph{보수적으로
안전하며}(die-lock을 놓치지 않고), \emph{설명 가능한}(슬라이드 수·이형 방향·
Class-A 충돌을 분해해 주는) 다중 후보 선별이다.

발형 방향은 단위구 $S^2$, 더 정확히는 2판 금형에서 $\dvec$와 $-\dvec$가 같은
축이므로 사영평면 $\mathbb{RP}^2$ 위의 탐색 문제다. 각 후보 축의 진짜 비용
(언더컷·슬라이드·die-lock)은 면 단위 접근성 판정과 충돌 검사를 요구하는 고비용
블랙박스다. 풀스윕은 정확하지만 느리고, 바운딩박스 6면이나 주성분 축 같은
값싼 휴리스틱은 축이 격자에 정렬되지 않은 부품에서 최적을 놓친다.

본 연구의 출발점은, 외형이 전혀 다른 문제인 \emph{적층제조의 빌드 배향}에서
이미 동일한 구조—``$\mathbb{RP}^2$/$S^2$ 위의 고비용 블랙박스를 값싼 방향 의존
텐서로 사전선별''—를 푸는 SFTF\citep{sul_sftf}가 존재한다는 관찰이다. SFTF의
진짜 자산은 ``서포트 배향''이라는 응용이 아니라 세 가지 엔진이며, 이들은 금형
발형으로 거의 그대로 옮겨간다. 본 논문의 기여는 다음과 같다.
\begin{itemize}
  \item \textbf{문제 이식(\S\ref{sec:problem}).} AM의 overhang/서포트 수식을
    금형의 언더컷/슬라이드로 사상하고, $\mathbb{RP}^2$ antipodal 식별과
    ``이형 방향 존재''라는 중첩 제약을 정식화한다.
  \item \textbf{정확 검증기(\S\ref{sec:verifier}).} ray-cast 접근성으로 면을
    분류하고, 언더컷 면을 호환 pull 방향에 대한 \emph{최소 set-cover}로 묶어
    슬라이드 수를 산정한다(분리된 언더컷의 병합, 한 클러스터의 분할을 모두
    처리). 각진 lifter와 진짜 die-lock을 구분하고, draft 결손과 파팅 밴드
    복잡도를 독립 채널로 보고한다.
  \item \textbf{값싼 후보 생성기와 AVE(\S\ref{sec:sftf}--\ref{sec:ave}).} 방향
    의존 entrapment 텐서 + cone-refined 샘플링으로 좁은 basin(예: 관통홀 축)을
    시드 없이 포착하고, warm-start가 비싼 검증기를 ${\pm}$윈도우에서만 호출하며,
    검증 신뢰도 신호(윈도우 경계·섭동 민감도·die-lock)로만 단조적으로
    escalation 한다.
  \item \textbf{검증과 보정(\S\ref{sec:exp}).} 해석적 사다리와 DFM 교과서
    코퍼스에서 산업 지표(슬라이드 수 일치, die-lock recall, 검증 예산)로 평가하고,
    점수 가중치를 LOMO로 보정해 과적합을 정량화한다.
  \item \textbf{견적 단계 도구(\S\ref{sec:demo}).} 부품 투입에서 상위 발형
    전략·슬라이드 수·die-lock·pull 화살표를 담은 자체완결 의사결정 시트와 STL
    업로드 엔드포인트를 제공한다.
\end{itemize}

% =====================================================================
\section{배경 및 관련 연구}
% =====================================================================
\paragraph{발형 방향과 이형성.} 발형 방향 결정과 언더컷 인식은 금형
CAD 자동화의 고전 문제로, 가시성 기반 파팅 방향 탐색\citep{khardekar2006moldability},
다편 금형의 기하 알고리즘\citep{priyadarshi2004parting}, 언더컷 특징 인식
\citep{ahn2002undercut} 등이 연구되었다. 본 연구는 정밀한 파팅면 합성이 아니라
\emph{견적 단계의 빠른 사전선별}—발형 축·슬라이드 수·die-lock의 다중 후보
스크리닝—에 범위를 한정한다.

\paragraph{AM의 SFTF.} SFTF\citep{sul_sftf}는 서포트를 요구하는 적층제조에서
빌드 배향 후보를 빠르게 생성한다. 각 면이 자기 빌드 방향으로 ray를 쏘아 받는
면(receiver)을 찾고, 면-대-면 entrapment를 비대칭 텐서 $\mathbf{F}(\dvec)$로
인코딩하여 통합 Rayleigh 비용 $R(\dvec)=\dvec^{\!\top}\mathbf{F}(\dvec)\dvec$로
배향을 랭크한다. 512방향 Fibonacci 거친 샘플 → 콘 재샘플 → 각도 NMS로 상위
basin을 뽑고, 비싼 검증(TOMO)은 그 주변 좁은 윈도우에서만 적응적으로 호출한다.
본 연구는 이 \emph{엔진}을 금형 발형으로 이식한다.

% =====================================================================
\section{문제 정의}\label{sec:problem}
% =====================================================================
부품을 외향 일관된 삼각 메시 $(\mathbf{V},\mathbf{F})$로 두고, 발형 축
$\dvec\in\mathbb{RP}^2$를 찾는다. 2판 금형은 $+\dvec$(캐비티)와 $-\dvec$(코어)
두 반쪽으로 면을 가른다. 면 $i$의 외향 법선을 $\nvec_i$, 면적을 $A_i$, 정렬값을
$s_i=\nvec_i\!\cdot\!\dvec$라 하면, 이형 구배(draft) 각 $\alpha$에 대해 면은
\[
  \text{cavity } (s_i>\sin\alpha),\quad
  \text{core } (s_i<-\sin\alpha),\quad
  \text{wall } (|s_i|\le\sin\alpha)
\]
로 1차 분류된다. \textbf{언더컷}은 자기 반쪽 방향으로 빠지려는데 다른 면에
가려(occlusion) 못 빠지는 면이다. 캐비티 면은 $+\dvec$로, 코어 면은 $-\dvec$로
ray가 무한대로 탈출해야 접근 가능하며, 탈출하지 못하면 언더컷이다(벽 면은
$\pm\dvec$ 양쪽 모두 막히면 언더컷). 언더컷을 해소하려면 부품과 충돌하지 않는
\emph{이형 방향}으로 빠지는 슬라이드(또는 각진 리프터)가 필요하고, 그런 방향이
전혀 없으면 \textbf{die-lock}이다.

\paragraph{AM--금형 대응.} 표~\ref{tab:mapping}이 SFTF 수식의 이식을 요약한다.
핵심은 (i) 탐색 공간이 antipodal 식별된 $\mathbb{RP}^2$이고(후보 절반, $2\times$
가속), (ii) overhang이 서포트로 \emph{항상} 해소되던 것이 ``언더컷마다 충돌
없는 이형 방향이 존재하는가''라는 중첩 문제가 되며, (iii) ground 항의 부호가
penalty에서 reward(깨끗한 이형)로 뒤집힌다는 점이다. 통합 비용은
\[
  U(\dvec)=\!\!\sum_{(i,j)\in S,\pm}\!\! g_i\, w_{ij}\,(\nvec_i\!\cdot\!\dvec)(\nvec_j\!\cdot\!\dvec)
  \;-\;\lambda\!\!\sum_{i\in\text{clean}}\!\! g_i,
\]
이며 $\mathbf{F}^{\pm}(\dvec)=\sum g_i^{\pm} w_{ij}\,(\nvec_i\otimes\nvec_j)$가
``어느 면이 어느 면에 갇히는가''라는 방향 의존 entrapment를 비대칭 텐서로
인코딩한다—SFTF의 원래 구조 그대로다.

\begin{table}[ht]
\centering\small
\caption{SFTF(AM) 수식의 금형 발형 이식.}\label{tab:mapping}
\begin{tabular}{@{}ll@{}}
\toprule
SFTF (AM) & 금형 발형 \\
\midrule
빌드 방향 $\dvec$ (중력, 한쪽)        & 발형 축 $\dvec$, \textbf{$\pm\dvec$ 양쪽 패스} \\
임계각 $\theta_c$                     & 이형 구배 draft 각 $\alpha$ \\
overhang 계수 $o_i(\dvec)$            & 이형 대상 가중치 / draft 결손 \\
ray로 receiver 탐색(내부 가시성)      & ray로 occlusion(언더컷) 판정 \\
면-대-면 서포트                       & 내부 언더컷(면 $i$가 $j$에 가려 못 빠짐) \\
receiver 없음 $\to$ build plate       & ray가 부품 밖 탈출 $\to$ 깨끗한 이형(reward) \\
서포트 부피(비싼 TOMO)               & 언더컷 부피 / 슬라이드 수(비싼 CAE) \\
$S^2$ 탐색                            & \textbf{$\mathbb{RP}^2$} (antipodal 식별) \\
\bottomrule
\end{tabular}
\end{table}

\begin{figure}[ht]
\centering
\begin{tikzpicture}[>=Stealth, node distance=10mm and 16mm,
   box/.style={draw, rounded corners, align=center, font=\small, inner sep=4pt}]
  \node[box, fill=blue!8]   (part) {부품 메시\\ $(\mathbf{V},\mathbf{F})$};
  \node[box, fill=green!8, right=of part] (sftf) {SFTF 후보 생성기\\ (값싼, 수\,ms)\\ cone-refined};
  \node[box, fill=orange!10, right=of sftf] (ws) {warm-start\\ ${\pm}$윈도우 검증};
  \node[box, fill=red!8, right=of ws] (ave) {AVE\\ 신뢰도 escalation};
  \node[box, fill=gray!12, below=12mm of ws] (sheet) {의사결정 시트\\ top-$K$ 전략 / 슬라이드 / die-lock};
  \node[box, draw=black!50, below=8mm of sftf] (ver) {정확 검증기(oracle)\\ ray-cast 접근성\\ set-cover 슬라이드};
  \draw[->] (part) -- (sftf);
  \draw[->] (sftf) -- (ws);
  \draw[->] (ws) -- (ave);
  \draw[->] (ws) -- (ver);
  \draw[->] (ave) to[out=-90,in=0] (sheet);
  \draw[->] (ver) to[out=-90,in=180] (sheet);
\end{tikzpicture}
\caption{파이프라인. 값싼 SFTF 후보 생성기가 발형 basin을 랭크하고, 비싼
정확 검증기는 상위 후보의 ${\pm}$윈도우에서만 호출된다(warm-start). AVE는 검증
신뢰도 신호로만 단조적으로 예산을 추가한다.}\label{fig:pipeline}
\end{figure}

% =====================================================================
\section{정확 검증기 (oracle)}\label{sec:verifier}
% =====================================================================
검증기는 느리지만 신뢰할 수 있는 기준값(AM의 TOMO 자리)이다. 단일 발형 축
$\dvec$에 대해 구조화된 결과—면 단위 라벨, 언더컷/draft 결손/이형 면적, 언더컷
$\to$ 슬라이드 그룹화와 이형 방향, die-lock 플래그—를 반환한다.

\paragraph{접근성.} 벡터화된 Möller--Trumbore ray
caster\citep{moeller1997raytri}로, 각 면의 중심에서 법선 방향으로 미소 오프셋한
원점에서 $\pm\dvec$로 ray를 쏘아 무한대 탈출 여부를 판정한다. 자기면은
명시적으로 제외하여 axis-aligned 기하에서의 grazing을 피한다.

\paragraph{슬라이드 = 최소 set-cover.} 토목공이 짓는 슬라이드 수는 ``edge로
연결된 언더컷 덩어리 수''가 아니라 \emph{공유되는 pull 방향 수}로 제한된다.
우리는 후보 pull 방향(발형 축에 대략 수직인 ring과, 각진 lifter를 포함하는 콘
샘플 + 언더컷 면 법선 시드)에 대한 coverage를 만들고, 모든 언더컷 면을 덮는
\emph{최소 개수의 pull 방향}을 greedy하게 고른다. 이는 (i) 같은 pull을 공유하는
분리된 언더컷을 \emph{병합}하고, (ii) 두 pull이 필요한 한 클러스터를
\emph{분할}한다. 각 pull은 그 각도로 slide(${\approx}$수직)와
lifter(각진)로 분류되며, 어떤 pull도 못 빠지는 면은 die-lock으로 별도 보고된다.

\paragraph{draft·파팅 채널.} 언더컷과 독립적으로, draft 결손을 면적 가중
$\sum_i A_i\max(0,\sin\alpha-|s_i|)$로, 파팅 밴드($|s_i|\le\sin\alpha$)의 면적과
발형 축 방향 산포(평면 파팅이면 낮고, 계단형이면 높음)를 별도 피처로 보고한다.
그림~\ref{fig:render}는 관통홀 부품을 홀 축에 수직으로 뽑았을 때 검증기가 내부
벽을 언더컷(빨강)으로 분류한 예다.

\begin{figure}[ht]
\centering
\includegraphics[width=0.52\linewidth]{fig_moldability_rect_tube.png}
\caption{정확 검증기 출력 예(\texttt{rect\_tube}, $\dvec=+z$). 면 색은 cavity/
core/wall/undercut 라벨, 검은 선은 발형 축. 홀 축에 수직으로 뽑으면 내부 벽이
갇혀(언더컷) 슬라이드가 필요하고, 홀 축으로 뽑으면 0 슬라이드로 이형된다.}
\label{fig:render}
\end{figure}

% =====================================================================
\section{금형판 SFTF 후보 생성기}\label{sec:sftf}
% =====================================================================
각 후보 축에 대해, 표본 면 집합(전체가 아님)으로부터 방향 의존 entrapment 흐름
텐서 $\mathbf{F}(\dvec)$와 draft·파팅 피처를 추정한다. 비용은
$\mathcal{O}(n_{\text{samples}}\!\cdot\! n_{\text{faces}})$로 검증기의 전체
$n_{\text{faces}}^2$ 접근성·슬라이드 탐색보다 값싸다. 피처
$\{P,R,\text{draft},\text{band},B\}$를 부품 내에서 $[0,1]$로 rank 정규화하고
가중합으로 점수화한다(낮을수록 몰드 가능).

\paragraph{cone-refined 샘플링.} 단일 Fibonacci 패스는 좁은 basin(예: 관통홀
축)을 \emph{건너뛴다}. 따라서 거친 Fibonacci로 basin 윤곽을 잡고, 상위 basin
주변 좁은 콘($2$--$8^\circ$)을 결정적으로 재샘플해 함께 재점수화한다. 이로써
\texttt{rect\_tube}에서 홀 축에 가장 가까운 후보가 $10.5^\circ\!\to\!5.9^\circ$로
좁혀지고, 거친 패스가 놓치던 entrapment-free($P{=}0$) 후보가 \emph{시드 없이}
떠오른다.

\paragraph{비편향 source 샘플링.} 대형 메시에서 ``가중치 큰 면만 취하기''는
편향된다. 우리는 누적 가중치 위 등간격 티켓으로 가중치 비례 결정적
systematic PPS 샘플링을 하고, Horvitz--Thompson 가중치 $G/n$으로 텐서 합을
\emph{비편향} 추정한다(소형 메시에서는 전 면을 정확히 합산하므로 거동 불변).

% =====================================================================
\section{Warm-start와 적응 검증 escalation}\label{sec:ave}
% =====================================================================
warm-start는 SFTF 상위 $K$ basin 각각에 대해 비싼 검증기를 \emph{좁은 윈도우의
국소 격자}에서만 호출한다. 핵심 지표는 \emph{검증 예산}—같은 해상도 풀스윕 대비
실제 평가한 비율—이다. AVE는 선택이 \emph{불확실}하고 escalation이 결과를 바꿀
수 있을 때만 예산을 추가한다. 우리는 트리거를 placeholder(``die-lock 또는 슬라이드
$>0$'')에서 검증 신뢰도 신호로 재정의한다: (i) \textbf{die-lock}(아직 가용 축
없음), (ii) \textbf{윈도우 경계}(최선 셀이 시드 중심에서 $\ge 0.8\,w$—진짜 최적이
윈도우 밖일 수 있음), (iii) \textbf{섭동 민감}(이미 검증된 이웃이 슬라이드 수
불일치—국소적으로 불안정). 확신 있는 0-슬라이드 선택은 이미 최적이므로 신호가
켜져도 예산을 쓰지 않는다. escalation은 검증만 추가하고 마지막에 더 큰 집합에서
재최소화하므로 선택값을 \emph{결코 악화시키지 않는다}(단조성).

% =====================================================================
\section{제약 조건부 발형 탐색}\label{sec:constraints}
% =====================================================================
산업 채택을 위해 $\mathbb{RP}^2$ 마스크를 추가한다: \emph{금지 축}(예: 이젝션
코어 측)은 하드 제외, \emph{선호 축}(기능 축 정렬)은 소프트 보너스, 그리고
\emph{Class-A 면}이 파팅 밴드에 걸리면 면적 가중 벌점을 부과한다. 이들은 슬라이드
수를 1순위로 유지한 채 동점만 가른다(제약이 없으면 랭킹 불변).

% =====================================================================
\section{구현과 성능}
% =====================================================================
코어 검증기는 numpy만으로 작성되어 면 단위로 감사 가능하다. ray caster를 origin에
대해서도 청크 단위 벡터화하여 전체 수용 테스트가 ${\sim}11$분에서 ${\sim}3$분으로
단축되었고(결과 비트 동일), $10^5$ 면 이상에서는 동일 시그니처 뒤에서
trimesh/embree 경로로 자동 디스패치한다(오류 시 numpy로 폴백). AM 원논문의 기준
검증기인 TOMO 엔진은 공유 배포본(\texttt{Tomo\_Shell2026.dll}; solid·shell 겸용,
CPU/CUDA 동일 시그니처)으로 프로젝트에 연결되어 빌드 해시를 테스트로 고정하며,
AM--금형 교차 비교의 기준 참조로 쓴다. 전체 시스템은
75개의 수용 테스트로 고정된다.

% =====================================================================
\section{실험}\label{sec:exp}
% =====================================================================
\paragraph{데이터셋.} (i) \emph{해석적 사다리}는 정답이 알려진 파라메트릭 부품
T0--T3로, 발형 탐색을 bbox 정렬 휴리스틱과 변별하는 위생 검사다. (ii)
\emph{DFM 교과서 코퍼스}(표~\ref{tab:dfm})는 사출 금형 DFM 레슨—깨끗한 draft,
코스메틱 draft 결손/교정, 측면 홀 슬라이드, off-axis 보어, 공유/분리 슬라이드,
lifter 보어, die-lock—을 재현 가능한 부품으로 큐레이션하고 오라클 GT를
\texttt{.stl}+매니페스트로 기록한다. 실제 Thingi10K\citep{zhu2010thingi} 부품은
같은 폴더에 STL을 넣으면 동일 경로로 수집된다.

\paragraph{베이스라인·지표.} 베이스라인은 바운딩박스 6면(bbox6), 주성분 축(PCA),
대칭 support tensor 고유벡터, 그리고 풀스윕 오라클이다. 1순위 지표는 \emph{슬라이드
수 일치율}(슬라이드 1개 = 금형비·사이클 직결), 2순위는 \emph{die-lock recall}
(견적 단계에서 놓친 die-lock이 가장 비싼 사고), 그리고 검증 예산이다.

\paragraph{결과.} 표~\ref{tab:bench}와 그림~\ref{fig:bench}가 요약한다. 핵심
변별 부품은 off-axis로 회전된 관통홀로, bbox6은 최적 발형을 놓쳐 슬라이드 수를
과다 산정하는 반면(slide 일치율 0.80), 발형 탐색(SFTF-warmstart)과 PCA는 0-슬라이드
축을 복원한다(1.00). 모든 방법이 die-lock recall 1.00을 달성한다. 흥미롭게도, 각진
lifter 검색을 도입한 뒤 bbox6의 실패 양상은 \emph{거짓 die-lock}에서 \emph{슬라이드
수 과다}로 바뀌었다—검증기가 더 정직해진 결과다.

\begin{table}[ht]
\centering\small
\caption{해석적 사다리 벤치마크 집계(북극성 지표).}\label{tab:bench}
\begin{tabular}{@{}lcccc@{}}
\toprule
방법 & 슬라이드 일치 & 슬라이드 ${\pm}1$ & die-lock recall & 평균 검증 호출 \\
\midrule
bbox6           & 0.80 & 0.80 & 1.00 & 3 \\
pca             & 1.00 & 1.00 & 1.00 & 3 \\
support\_tensor & 1.00 & 1.00 & 1.00 & 3 \\
sftf\_warmstart & 1.00 & 1.00 & 1.00 & 324 \\
\bottomrule
\end{tabular}
\end{table}

\begin{figure}[ht]
\centering
\includegraphics[width=0.72\linewidth]{fig_method_comparison.png}
\caption{방법별 북극성 지표. off-axis 부품이 bbox6의 슬라이드 일치율을 끌어내린다.}
\label{fig:bench}
\end{figure}

\paragraph{점수 보정과 LOMO.} SFTF 점수 가중치는 placeholder이므로, 공유 축 풀을
검증기로 라벨링한 뒤 best-of-$K$ 검증 비용을 좌표하강으로 최소화해 보정하고,
\emph{leave-one-mesh-out}(LOMO) 교차검증으로 과적합을 정량화한다(그림~\ref{fig:cal}).
보정은 best-of-$K$를 $1.00\!\to\!0.25$로 개선하고, SFTF(LOMO)는 bbox6(0.50)을
이기지만 이 \emph{해석적} 셋에서는 PCA(0.00)에 진다. 이는 길쭉한 튜브에서 PCA
주축이 곧 이형축이기 때문으로, SFTF의 우위는 주축과 이형축이 무관한 \emph{실제}
부품에서 비로소 드러난다—다음 \S\ref{sec:realparts}에서 이를 실제 Thingi10K
부품으로 확인한다.

\begin{figure}[ht]
\centering
\includegraphics[width=0.72\linewidth]{fig_calibration.png}
\caption{보정 best-of-$K$(슬라이드 수, 낮을수록 좋음): 기본 가중치 대비 개선,
in-sample 대 LOMO 과적합, 그리고 baseline 대비. 막대 best-of-$K$는 윈도우 없는
raw 풀 기준이라 배포 warm-start의 보수적 하한이다.}\label{fig:cal}
\end{figure}

\begin{table}[ht]
\centering\small
\caption{DFM 교과서 코퍼스(오라클 GT).}\label{tab:dfm}
\begin{tabular}{@{}llll@{}}
\toprule
부품 & 티어 & 오라클 GT & DFM 레슨 \\
\midrule
drafted\_box        & T0 & 0 슬라이드   & 깨끗한 draft, $+z$ 이형 \\
cosmetic\_panel     & T0 & 0 슬라이드   & 무draft 코스메틱 벽 $\to$ 큰 draft 벌점 \\
drafted\_panel      & T0 & 0 슬라이드   & $3^\circ$ draft 교정본 \\
rect\_tube          & T1 & 0 슬라이드   & 측면 관통홀: 보어 축으로 이형 \\
rect\_tube\_rotated & T2 & 0 슬라이드   & off-axis 보어: bbox6 놓침 \\
twin\_parallel      & T2 & 0 슬라이드   & 공유 pull: 한 슬라이드(set-cover 병합) \\
two\_perp           & T2 & 1 슬라이드   & 수직 보어: 한 축 정렬 시 슬라이드 1 \\
tilted\_tube        & T2 & 0 슬라이드   & 경사 보어: 각진 lifter 필요 \\
sealed\_shell       & T3 & die-lock     & 밀폐 캐비티 $\to$ 재설계 \\
\bottomrule
\end{tabular}
\end{table}

\subsection{실제 부품 감사: 이형축이 주축과 어긋난 경우}\label{sec:realparts}
해석적 사다리에서는 PCA가 SFTF와 대등하거나 앞선다. 이는 PCA가 회전 등변
(rotation-equivariant)이어서 \emph{해석적} 부품의 이형축이 질량 주축에 묶이기
때문이다(\S\ref{sec:discuss}). SFTF의 가설상 우위—이형축이 주축과 \emph{무관한}
부품에서의 우세—를 실제로 시험하기 위해, 우리는 Thingi10K\citep{zhu2010thingi}에서
정합(oriented)·솔리드·폐곡·매니폴드·자기교차 없음·genus$\,\ge 1$인 깨끗한 부품
배치를 받아(모델별 경량 데이터로 다운로드), 값싼 스크리닝(오라클+PCA, warm-start
없이; embree 백엔드)으로 \emph{PCA가 최적을 놓치거나} 이형축이 모든 PCA 축에서
$20^\circ$ 이상 떨어진 \emph{off-principal} 부품을 선별하였다. 302개의 깨끗한 부품을
스크리닝하여 off-principal 후보 49개를 얻고, 이들에 풀스윕 오라클($160$축)과
warm-start를 포함한 정밀 감사를 수행하였다(정밀 해상도에서 이격이 $20^\circ$
이하로 떨어진 3개는 제외, 최종 46개).

표~\ref{tab:realparts}와 그림~\ref{fig:realparts}가 off-principal 부품 46개에 대한 결과다.
산업적으로 의미 있는 지표는 \emph{평균 슬라이드 수}(낮을수록 금형비 절감)이며,
오라치(풀스윕)가 찾은 최소 슬라이드가 참값에 해당한다. SFTF는 PCA보다 평균 슬라이드를
적게 견적하여 참 최적에 더 가깝다—PCA는 질량 주축으로 발형하여 슬라이드를
\emph{과다 산정}한다. 일부 부품에서는 warm-start의 국소 윈도우 탐색이 유한 해상도
오라클(Fibonacci 샘플)이 놓친 더 값싼 축을 찾아, SFTF가 오라클보다도 적은 슬라이드를
보고한다. 따라서 유한 해상도 오라클에 대한 \emph{정확 일치}율은 SFTF를 과소평가하며,
평균 슬라이드 수가 더 정직한 비교다.

\begin{table}[ht]
\centering\small
\caption{실제 off-principal Thingi10K 부품 46개에서의 평균 슬라이드 수(낮을수록 좋음).
오라클 = 풀스윕이 찾은 최소 슬라이드(참 최적의 근사).}\label{tab:realparts}
\begin{tabular}{@{}lcccc@{}}
\toprule
지표 & 오라클 & \textbf{SFTF} & PCA & bbox-6 \\
\midrule
평균 슬라이드 수 & 2.93 & \textbf{3.20} & 3.85 & 3.43 \\
\bottomrule
\end{tabular}
\end{table}

\begin{figure}[ht]
\centering
\includegraphics[width=0.6\linewidth]{fig_realparts.png}
\caption{실제 off-principal Thingi10K 부품에서의 평균 슬라이드 수. SFTF의 방향
탐색이 PCA보다 적은 슬라이드를 견적하여 참 최적에 더 가깝다. PCA는 질량 주축으로
발형해 슬라이드를 과다 산정한다.}\label{fig:realparts}
\end{figure}

(주의: 정확 일치율 같은 단일 지표 대신 평균 슬라이드 수로 보고하는 이유는, 유한 해상도
오라클을 warm-start가 이따금 능가하기 때문이다. 표본은 302개 부품을 자동 스크리닝하여
얻은 off-principal 부품 46개로, 부품 선택에서 SFTF에 유리한 편향이 들어가지 않도록
선별 기준을 이형축-주축 이격($\ge 20^\circ$)으로만 고정하였다.)

% =====================================================================
\section{견적 단계 의사결정 시트}\label{sec:demo}
% =====================================================================
시스템은 부품 투입에서 1초 내에 상위 $K$ 발형 전략을 담은 자체완결 HTML 시트를
생성한다: 각 전략의 슬라이드 수·die-lock·언더컷 \%·이형 방향, plotly 3D
언더컷 뷰, slide/lifter pull 화살표, die-lock 면의 별도 색조, 그리고 선택 전략을
toolmaker용 JSON으로 내보내는 한 번 클릭 export. 대형 메시는 언더컷/die-lock 면을
보존한 채 뷰를 다운샘플하고, 의존성 없는 STL 업로드 엔드포인트로 견적자가 부품을
떨구면 시트를 받는다.

% =====================================================================
\section{논의와 한계}\label{sec:discuss}
% =====================================================================
\paragraph{왜 실제 부품이 필요한가.} PCA는 회전 등변(rotation-equivariant)이므로
\emph{해석적} 부품의 이형축은 질량 주축에 묶인다—실측에서 PCA의 best-of-3은
회전된 관통홀($8^\circ$)과 경사 보어($15^\circ$)를 모두 복원한다. 이형축이 주축과
\emph{무관한} 부품은 실제 기능형 지오메트리에서만 나오며, 이것이 SFTF 대 PCA
변별이 실제 데이터를 요구하는 이유다. \S\ref{sec:realparts}에서 우리는 실제
Thingi10K 부품 중 이런 off-principal 부품 46개를 자동 선별하여, SFTF가 PCA보다 적은
슬라이드를 견적함을 확인하였다(평균 3.20 대 3.85, 참 최적 2.93). 표본은 302개 부품
스크리닝으로 확보하였으며, 보다 대규모 코퍼스로의 확장은 후속 과제다.

\paragraph{범위.} 본 연구는 ``발형/언더컷 사전선별''로 주장을 못 박는다—게이트·
냉각·휨·정밀 파팅면 합성은 별개의 후속 문제다. best-of-$K$ 막대 수치는 윈도우 없는
raw 풀 기준으로, 배포 warm-start(윈도우+AVE)의 보수적 하한임을 명시한다. 또한
부품 선택 편향을 피하기 위해 T2·T3(경쟁 발형·die-lock)를 필수 포함하고, 독립 GT
(오라클)와 전문가 주석·상용 CAE 교차검증의 삼중 GT 프로토콜을 향후 과제로 둔다.

% =====================================================================
\section{결론}
% =====================================================================
우리는 AM 빌드 배향 생성기 SFTF의 세 엔진을 사출 금형 발형 방향·언더컷 사전선별로
이식하였다. 핵심 신규 구성요소는 (i) 호환 pull 방향에 대한 최소 set-cover로
슬라이드 수를 산정하고 lifter/die-lock을 구분하는 정확 검증기, (ii) cone-refined·
비편향 샘플링으로 좁은 발형 basin을 시드 없이 포착하는 값싼 후보 생성기, (iii)
검증 신뢰도 신호로만 단조적으로 escalation 하는 AVE이다. 해석적 사다리와 DFM
코퍼스에서 제안 방법은 off-axis 최적 발형을 복원하고 die-lock recall 1.00을
달성하며, LOMO 보정으로 과적합을 정직하게 정량화한다. 전체는 견적 단계에서 1초
내에 다중 발형 전략을 제시하는 의사결정 도구로 마무리된다. 향후 과제는 실제 양산
부품의 회고적 파일럿(추천 발형이 실제 채택과 일치했는가, 비싼 ECO를 견적 시점에
잡았는가)과 삼중 GT 검증이다.

% ---- 참고문헌 -------------------------------------------------------
\bibliographystyle{plainnat}
\bibliography{references}

\end{document}

