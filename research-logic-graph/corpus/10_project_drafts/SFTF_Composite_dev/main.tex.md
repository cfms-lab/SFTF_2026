# LaTeX source: main.tex

Source: `D:\__SFTF_Projects(2026)\SFTF_Composite_dev\draft\main.tex`

% =====================================================================
%  main.tex — 한국섬유공학회지 투고용 (한글, 대학원생 친화 + 각주)
%  빌드:  uv run python scripts/build_pdf.py        (-> main.pdf, xelatex)
%        uv run python scripts/build_docx.py       (-> main.docx)
%  영문 SCI 버전은 main_en.tex 참조.
% =====================================================================
\documentclass[11pt]{article}

% ---- 한글 (xelatex + kotex) -----------------------------------------
\usepackage{kotex}
\usepackage{fontspec}
% Malgun Gothic has no italic shape; synthesize a slant so \emph on Korean text
% does not trigger a font-substitution warning (and still shows emphasis).
\setmainhangulfont{Malgun Gothic}[AutoFakeSlant=0.2]

% ---- 수식 / 그림 / 표 ------------------------------------------------
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

% ---- TikZ (개념도) ---------------------------------------------------
\usepackage{tikz}
\usetikzlibrary{arrows.meta, calc, positioning, decorations.pathreplacing, patterns, shapes.geometric}
\usepackage{pgfplots}
\pgfplotsset{compat=1.18}

\graphicspath{{pics/}{./}}

\newcommand{\Kabs}{\lvert K\rvert}
\newcommand{\Phidr}{\Phi_{\mathrm{drape}}}
\newcommand{\Kstar}{K^{\ast}}

% allow a little last-resort stretch so long Korean+Latin tokens never overfull
\setlength{\emergencystretch}{2em}

\title{지지흐름 텐서장(SFTF) 클러스터링의 복합재 드레이프 패치 분할로의 이식:\\
가벼운 기하 드레이프 필드 기반 제조성 분할}
\author{설인환\\
\small 금오공과대학교 소재디자인공학전공, 경상북도 구미시 39177\\
\small 이메일: snowman0@kumoh.ac.kr \quad ORCID: 0000-0003-0105-920X}
% NOTE(투고): 최종 저자 명단이 늘면 위 저자 줄과 아래 저자 기여 항목을 함께 갱신.
\date{}

\begin{document}
\maketitle

\begin{abstract}
곡면 복합재 부품을 만들려면 평평한 직물(프리프레그)을 곡면 금형에 씌워야 하는데,
이중으로 휜 곡면에서는 직물이 \emph{전단}(가위질처럼 격자가 기울어짐)으로 적응하다가
한계를 넘으면 주름이 진다. 따라서 곡면을 \textbf{주름 없이 씌울 수 있는 작은
조각(패치)들로 나누는 것}이 제조성의 핵심 문제다. 본 연구는 적층제조(3D 프린팅)용
메쉬 분할 기법인 SFTF-Clustering 의 \emph{골격}을 이 복합재 문제로 이식한다. 핵심
교체는 단 하나로, ``지지구조 흐름''을 나타내던 면별 피처를 \textbf{면별 드레이프
필드}(전단각 $\gamma$, 섬유각 $\theta$, 시드로부터의 거리 $g$, 곡률 $\Kabs$, 드레이프
상태)로 바꾸면 기존 분할 알고리즘이 거의 그대로 재사용된다. 이 필드는 공개 분할기의
입력 형식을 그대로 맞춰 설계되어 분할 엔진을 수정 없이 구동한다. 간단한 곡률 근사식
$\gamma\approx\Kabs\,g^2$ 에서 시작해, 실제 직물 거동을 흉내 내는 핀-조인트 네트
모형, 패치마다 다른 기준 방향을 쓰는 멀티시드 기법, 제조 가능한 이산 섬유각
$\{0,\pm45,90\}$ 스냅, 그리고 자동 패치 수 결정까지 단계적으로 구축한다. 해석적
시험 형상과 실측 인체/장기/공학 메쉬에서 검증하고, 곡면 분할 분야의 대표 분할 기법들
(k-means, 변분 형상 근사, 곡률 분할)과 정량 비교하며, 추가로 두 가지 평면전개 왜곡
지표(LSCM, ARAP)로 각 분할을 평가한다. 끝으로 가벼운
근사 전단장을 정밀 물리 천 시뮬레이터로 검증하며, 자유낙하 드레이프가 성형과
다르다는 점 등 한계를 정직하게 보고한다.
\end{abstract}

% =====================================================================
\section{서론}
% =====================================================================
복합재 곡면 부품은 평면 프리프레그/직물을 곡면 몰드에 씌워(드레이프\footnote{드레이프
(drape): 평평한 천을 곡면에 늘어뜨려 씌우는 것. 복합재 성형의 첫 단계다.}) 만든다.
이 과정에서 직물은 날실--씨실(warp--weft) 격자가 기울어지는 \textbf{전단(trellis
shear)}\footnote{트렐리스 전단: 직물의 두 실 방향이 직각에서 벗어나는 각도. 실 자체는
거의 늘어나지 않으므로, 이중곡률은 주로 이 전단으로 흡수된다.} 으로 이중곡률에
적응한다. 그러나 재료마다 정해진 \textbf{locking angle}\footnote{locking angle(고착각):
전단이 이 각(보통 $30\text{--}50^\circ$)을 넘으면 실이 서로 밀려 주름이 생기는 한계각.}
을 넘으면 주름이 발생한다~\citep{prodromou1997}. 따라서 복잡한 곡면을 \emph{드레이프 가능한 패치로 분할}하되
(i) 각 패치의 전단이 locking 이하이고, (ii) 섬유 배향이 일관되며, (iii) 이음매(seam)와
다트(dart, 절개)\footnote{dart: 곡면에 맞추려 천을 잘라 겹치거나 빼내는 절개. 양복의
다트와 같은 개념으로, 전단만으로 곡면을 못 덮을 때 필요하다.} 를 최소화하는 것이 핵심
문제다.

\paragraph{실무 관점: 무엇에 쓰는 도구인가.} 본 연구의 산출물은 곡면 부품의 3D
형상(메쉬)만 입력하면 \textbf{주름 없이 깔 수 있도록 어디서 몇 조각으로 나누고 각
조각의 섬유각을 어떻게 줄지를 자동으로 제안하는 빠른 사전검토 도구}다. 구체적으로
(i)~드레이프 가능한 패치 분할(``한 장으로 깔 수 있나, 안 되면 몇 조각으로''),
(ii)~이음매$\cdot$다트 위치, (iii)~패치별 제조 가능한 섬유각 메뉴 $\{0,\pm45,90\}$
추천, (iv)~locking 초과(주름 위험) 영역 지도를 실측 형상에서 1초 미만에 산출한다.
즉 ply book 설계 초기에 분할$\cdot$다트$\cdot$배향 후보를 값싸게 좁히는 \emph{스크리닝}
용도로, 정밀 드레이프 유한요소(FE) 성형해석 이전 단계에 해당한다. 다만 이는 직물
역학$\cdot$성형압을 무시한 \emph{기하 기반 1차 근사}라 절대 주름량 예측이 아니며(주름
위험이 큰 곳을 빠르게 골라내는 용도), 현재는 단층(1~ply) 기준이다.

본 연구의 출발점은 적층제조(AM)\footnote{적층제조(Additive Manufacturing): 3D 프린팅.
재료를 층층이 쌓아 부품을 만들며, 돌출부에는 임시 ``지지구조''가 필요하다.} 용 메쉬
분할기 SFTF-Clustering~\citep{sul_sftfclustering} 이다. 이 선행연구의 진짜 자산은
``지지구조''라는 \emph{응용}이 아니라 다음 \textbf{골격}이다: (a) 면별 방향-의존 값을
클러스터링 피처로 보존, (b) 각 부분이 자기만의 유리한 방향을 갖게 분할, (c) 절단 대
재배향의 이득을 비교하는 목적함수. 우리는 이 골격이 복합재 드레이프 분할로 거의
그대로 옮겨감을 보인다. 면별 지지흐름을 면별 드레이프 흐름으로 교체하면 분할
알고리즘과 목적함수, 품질 지표가 대부분 재사용된다.

\paragraph{관련 연구.} 곡면을 제조 가능한 평면 패턴/패치로 다루는 연구는 크게 세
줄기다. (1) \emph{드레이프 시뮬레이션} --- 핀-조인트 네트(fishnet)\footnote{핀-조인트
네트(fishnet 알고리즘): 직물을 길이가 고정된 실들이 핀으로 연결된 그물로 보고, 곡면
위에 측지적으로 펼쳐 전단을 기하학적으로 계산하는 고전 기법.} 기반 kinematic 드레이프
매핑~\citep{vanderweeen1991,wang1999draping} 은 비신장 격자를 곡면에 펼쳐 전단을 값싸게 추정하고, 물리
기반 접근은 Baraff--Witkin 음함수 천 솔버~\citep{baraff1998large} 처럼 막$\cdot$굽힘
에너지를 적분하며, 복합재 특화 성형해석은 보강재의 인장$\cdot$면내전단$\cdot$굽힘 강성으로부터
주름을 정밀 예측한다~\citep{boisse2011wrinkling}. (2) \emph{평면전개(flattening)} --- 등각사상
LSCM~\citep{levy2002lscm}, 각도기반 ABF++~\citep{sheffer2005abf}, 비신장
ARAP~\citep{liu2008arap} 는 곡면 패치를 왜곡 최소로 평면에 펼쳐 재단 패턴을
만든다(발전가능\footnote{발전가능(developable) 곡면: 늘이지 않고 평면으로 펼 수 있는
곡면(원통$\cdot$원뿔 등). 가우스곡률이 0이며, 전단 없이 드레이프된다.} 곡면에서 멀수록
왜곡 증가). (3) \emph{메쉬 분할} --- 좌표 k-means~\citep{lloyd1982}, 평면 프록시 기반
변분 형상 근사 VSA~\citep{cohensteiner2004vsa}, 형상 지름 함수 SDF~\citep{shapira2008sdf},
곡률 기반 분할 등이 곡면을 영역으로 나눈다. 본 연구는 이들과 달리 \emph{면별 드레이프
흐름}(전단$\cdot$곡률$\cdot$거리)을 피처로 보존하고, 각 패치가 자기 드레이프 시드를
채택하도록 분할하되 이음매를 비용으로 다는 \emph{제조성 지향} 분할이며,
\S\ref{sec:compare} 에서 위 분할 기법들과 정량 비교한다.

\paragraph{기여.} 본 논문의 기여는 다음과 같다.
\begin{enumerate}
  \item 지지흐름 $\to$ 드레이프의 \textbf{수식 매핑}과, 공개 분할기에 그대로 꽂히는
        (drop-in\footnote{drop-in: 입력$\cdot$출력 형식이 같아 기존 시스템에 코드 수정
        없이 바로 끼워 넣을 수 있는 모듈.}) \textbf{드레이프 필드} 설계.
  \item 간단한 곡률 근사에서 \textbf{핀-조인트 네트 기반 실제 트렐리스 전단}으로의
        충실도 사다리, 그리고 \textbf{멀티시드 재시딩 $+$ 이산 섬유각 스냅}.
  \item \textbf{이음매-대-재정렬 목적함수}와 자동 패치 수, 실측 메쉬에서의 검증, 그리고
        대표 분할 기법들과의 \textbf{정량 비교}.
  \item 정밀 Baraff--Witkin 천 솔버를 이용한 \textbf{근사 전단장 검증}과, 성형 경계조건을
        위해 추가한 분산 압력 항, 그리고 정직한 한계 분석.
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
  \caption{전체 파이프라인. SFTF-Clustering 골격(파란색: 분할 알고리즘, 목적함수, 자동
  패치 수)은 그대로 재사용되고, 새로 만든 것은 면별 \textbf{드레이프 필드}(주황색)
  하나뿐이다. 이 필드는 공개 분할기의 입력 형식을 맞춘 drop-in 으로, 엔진을 수정 없이
  구동한다.}
  \label{fig:pipeline}
\end{figure}

% =====================================================================
\section{배경: SFTF 와 SFTF-Clustering}
% =====================================================================

\subsection{선행연구: Support Flow Tensor Field (SFTF)}
\label{sec:sftf-bg}
본 절은 본 연구가 분할 구동기로 재사용하는 선행연구 SFTF~\citep{sul_sftf} 의 알고리즘을
요약한다. SFTF 의 목적은 슬라이서나 지지부피 격자\footnote{슬라이서$\cdot$지지부피 격자는
출력물을 얇은 층으로 잘라 실제로 필요한 지지구조 부피를 정확히 계산하는 도구다. 정확하지만
느려서 모든 방향에 다 돌릴 수는 없다.}처럼 비싼 검증을 \emph{모든} 빌드 방향에 직접
수행하는 것이 아니라, 먼저 지지구조가 적을 가능성이 높은 방향 후보를 빠르게 좁히는 것이다.
이를 위해 SFTF 는 한 빌드 방향을 가정하고, 표면의 오버행\footnote{오버행(overhang)은 아래를
향해 비스듬히 누운 면이다. 그 아래에 받쳐 주는 것이 없으면 출력 중 처지거나 무너지므로
지지구조가 필요하다.} 면에서 아래쪽으로 광선(ray)을 쏘아, 그 오버행을 \emph{다른 면}이
받치는지(면-면 자기지지) 아니면 \emph{빌드플레이트}까지 지지가 내려가야 하는지를 조사한다.
그림~\ref{fig:sftf-unified} 처럼 면-면 자기지지와 빌드플레이트 지지를 하나의 ``지지흐름''으로
해석하면, 단순한 법선 분포나 좌표 분포로는 알 수 없는 출력 적합성---즉 어느 면이 지지가
필요한지, 어느 면이 받침 역할을 하는지, 지지가 얼마나 길어지는지---을 방향별로 비교할 수 있다.
대형 메쉬에서는 모든 면을 매번 검사하는 대신 그림~\ref{fig:sftf-kray} 처럼 대표 source 면을
뽑아 여러 방향의 점수 지형(score landscape)을 빠르게 만들고, 그중 유망한 방향 주변만 정밀
검증한다. 그림~\ref{fig:sftf-landscape} 가 보이듯 실제 지지부피의 좋은 방향은 하나의 고립된
점이라기보다 넓은 저비용 영역(basin)을 이루며, 최적 방향과 최악 방향은 실제 지지구조의
양에서도 뚜렷이 다르다. 따라서 SFTF 는 전체 방향 공간을 촘촘히 다 계산하지 않고도 좋은 후보
영역을 찾는 장점이 있다. 다만 선행 SFTF 는 이 면별 지지흐름 정보를 최종적으로 \emph{방향
점수}와 \emph{방향 랭킹}으로 압축하고, 각 면이 어떤 지지 역할을 했는지의 상세 정보는 버린다.
본 연구의 출발점은 \emph{바로 이 버려지는 면별 흐름장을 보존}하여(표~\ref{tab:mapping} 의
드레이프 대응으로 재해석), 제조 적합성을 직접 반영하는 분할에 쓰는 것이다.

\begin{figure}[ht]
\centering
\includegraphics[width=0.9\linewidth]{FTree4x_fig1_unified_flow.pdf}
\caption{SFTF 의 통합 흐름(unified-flow) 관점: 면-면 지지와 면-빌드플레이트 지지를 하나의
틀로 표현한다. (선행연구~\citep{sul_sftf} 에서 인용.)}
\label{fig:sftf-unified}
\end{figure}

\begin{figure}[ht]
\centering
\includegraphics[width=\linewidth]{Bunny69k_kray3000_concept_balanced.pdf}
\caption{\emph{Bunny 69k} 에서의 SFTF source 면 표본추출과 방향 점수 지형. 대표 면 일부에서만
광선을 쏘아 방향별 비용을 싸게 추정한다. (선행연구~\citep{sul_sftf} 에서 인용.)}
\label{fig:sftf-kray}
\end{figure}

\begin{figure}[ht]
\centering
\includegraphics[width=\linewidth]{figure3_bunny_landscape_support.png}
\caption{\emph{Bunny 69k} 의 방향 점수 지형과, 1순위 최적 배향(yaw $300^\circ$, pitch
$40^\circ$)·1순위 최악 배향(yaw $240^\circ$, pitch $0^\circ$)에서 TOMO 로 계산한 실제 지지량.
좋은 방향은 한 점이 아니라 넓은 골짜기를 이룬다. (선행연구~\citep{sul_sftf} 의 방법을 공유
기준 엔진(Tomo\_Shell2026)으로 재계산.)}
\label{fig:sftf-landscape}
\end{figure}

\subsection{SFTF-Clustering: 면별 흐름장의 분할 재사용}
SFTF(Support Flow Tensor Field, 지지흐름 텐서장)~\citep{sul_sftf} 는 적층제조에서 각
면이 어느 방향으로 ``지지''를 필요로 하는지를 광선 하나로 빠르게 계산한다.
SFTF-Clustering 은 이 면별 값을 피처로 보존하여, k-medoids\footnote{k-medoids:
k-means 의 변형. 군집 중심으로 평균점 대신 실제 데이터점(medoid)을 쓰는 군집화로,
이상치에 강하다.} 등의 군집화(feature-fusion\footnote{feature-fusion: 서로 다른 종류의
피처(예: 위치 좌표 $+$ 곡률$\cdot$전단)를 정규화해 한 벡터로 이어 붙여 함께 군집화하는
방식.})와 영역 성장(region-growing\footnote{region-growing: 비슷한 인접 면들을 차례로
합쳐 영역을 키우는 분할 방식.})으로 부분을 나누고, 다음 형태의 목적함수로 절단의
이득을 평가한다:
\begin{equation}
  S(\Pi)\;\approx\;S_{\text{whole}}+\Delta S_{\text{cut}}-\Delta S_{\text{reorient}}.
  \label{eq:rayfree}
\end{equation}
여기서 $\Delta S_{\text{cut}}$ 은 경계(이음매)가 만드는 비용, $\Delta S_{\text{reorient}}$
은 각 부분이 자기 방향을 채택해 얻는 이득이다. 선행연구의 비직관적 결론은 \emph{지지
감소가 지지기둥 보존보다 각 부분의 재배향 자유도에 지배된다}는 것이며, 본 연구는 이것의
복합재 직역을 목표로 한다.

% =====================================================================
\section{방법}
% =====================================================================
전체 흐름은 그림~\ref{fig:pipeline} 과 같다. 새로 만든 면별 드레이프 필드만이 신규
모듈이고 나머지 분할 알고리즘$\cdot$목적함수$\cdot$자동 패치 수는 그대로 재사용된다.

\subsection{문제 재정의와 수식 매핑}
복잡 곡면을 제조 가능한 패치로 분할하며, 각 패치는 자기만의 \textbf{드레이프
시드}(기준 방향과 원점)를 고른다. 면 $i$ 에 대해 그 시드에서 kinematic 드레이프
매핑\footnote{kinematic 드레이프: 직물 역학(장력$\cdot$마찰)을 무시하고 순수 기하만으로
직물이 곡면을 덮는 모양을 결정론적으로 푸는 방법. 빠르지만 근사다.} 을 풀어 면별
값을 기록한다(고전 기하 드레이프 매핑~\citep{vanderweeen1991} 의 연장선). 지지흐름과의
대응을 표~\ref{tab:mapping} 에 정리한다.

\begin{table}[ht]\centering
\caption{면별 지지흐름(적층제조) $\to$ 복합재 드레이프 흐름 매핑.}
\label{tab:mapping}
\begin{tabular}{ll}
\toprule
SFTF 지지흐름 (AM) & 복합재 드레이프 흐름 \\
\midrule
overhang $O_i=\max(0,-m_i\!\cdot\! n)$ & 전단각 $\gamma_i$ (locking 위반량) \\
부호 배향 $\tau_i=m_i\!\cdot\! n$ & 시드 정렬 $s\!\cdot\! n$ / 국소 섬유각 $\theta_i$ \\
빌드플레이트 높이 $\eta_i$ & 시드로부터의 측지거리 $g_i$ \\
지지 역할 $\rho$ & 드레이프 상태 $\rho\!\in\!\{\text{dev},\text{shear},\text{dart}\}$ \\
지지 높이 $h_i$ & 전단 누적 $\Kabs\,g$ \\
receiver count $r_i$ & 곡률 집중도 $\Kabs$ \\
\bottomrule
\end{tabular}
\end{table}

피처 행렬도 같은 형태를 유지한다:
\begin{equation}
  \Phidr=\mathrm{zscore}\!\left([\,\gamma,\ \theta,\ g,\ \Kabs\,g,\ \Kabs\,]\right)\in\mathbb{R}^{N\times5},
\end{equation}
이는 기존 지지흐름 피처 자리를 그대로 대체한다($\mathrm{zscore}$ 는 각 열을 평균 0,
분산 1 로 정규화).

\subsection{드레이프 필드}
새로 만든 핵심 모듈은 \textbf{드레이프 필드}다. 고정된 곡면과 시드 방향에 대해 면별
값을 산출하며, 공개 분할기의 피처 클래스와 동일한 필드명을 가져 drop-in 으로 동작한다.
가장 간단한 전단 근사식(proxy\footnote{proxy: 비싸거나 복잡한 양을 대신하는 값싼
근사량.})은
\begin{equation}
  \gamma_i \;\approx\; \Kabs_i\, g_i^{2},
  \label{eq:proxy}
\end{equation}
로, 무차원이며 발전가능 곡면에서 $0$, (곡률)$\times$(거리)$^2$ 에 따라 증가한다.
가우스곡률\footnote{가우스곡률 $K$: 한 점에서 두 주곡률의 곱. 평면$\cdot$원통$\cdot$원뿔은
$K{=}0$(발전가능), 구는 $K{=}1/R^2{>}0$, 안장은 $K{<}0$. 여기서는 삼각형 내각의 합이
$360^\circ$에서 벗어나는 ``각결손''으로 계산한다.} $K$ 는 각결손으로, 측지거리\footnote{측지거리
(geodesic distance): 곡면 위를 따라 잰 최단거리(직선거리가 아님). 여기서는 Dijkstra
최단경로로 근사한다.} $g$ 는 Dijkstra 로 계산한다. 드레이프 상태는 국소 발전가능성
$\Kabs L^2$ 와 전단 임계 $\gamma\ge\gamma_{\text{lock}}$ 로 $\{$발전가능, 전단, 다트$\}$
로 분류한다. 단일 전역 시드만 쓰면 인체/장기 형상 대부분이 ``다트''가 되는데, 이는
``한 장으로 몸통 전체를 덮을 수 없다''는 물리를 옳게 반영하며 \emph{분할의 동기} 그
자체다.

\paragraph{식~\eqref{eq:proxy} 을 직관으로 풀면.}
평평한 직물(또는 프리프레그)을 곡면에 씌우면, 본래 직교하던 두 실 방향(날실$\cdot$씨실)이
\emph{가위처럼} 벌어지며 교차각이 $90^\circ$ 에서 어긋난다. 이 어긋난 양이 전단각 $\gamma$
이고, 곧 주름 위험의 척도다. 그런데 왜 거리의 \emph{제곱}($g^2$)일까? 시드에서 측지반지름
$g$ 인 원판 안에 쌓인 총 곡률은 가우스--보네 정리\footnote{가우스--보네(Gauss--Bonnet)
정리: 곡면의 한 영역에서 가우스곡률을 면적에 대해 적분한 값이 그 영역 경계의 회전과 같다는
정리. 여기서는 ``반지름 $g$ 원판 안에 든 곡률의 총량 $\approx K\times(\text{원판 넓이})$''
라는 사실만 쓴다.}에 의해 $\int K\,dA \approx K\cdot(\pi g^2)$ 로 \emph{면적}($\sim g^2$)에
비례한다. 직물이 이 누적 곡률을 흡수하려면 그만큼 전단해야 하므로 $\gamma\sim\Kabs\,g^2$
가 된다. 정리하면 (i) 많이 휜 곳일수록($\Kabs$ 큼), (ii) 처음 붙인 기준점(시드)에서 멀수록
($g$ 큼) 전단이 급격히 누적된다.

이 $\gamma$ 로 각 면을 세 \emph{상태(regime)}로 나눈다.
\textbf{발전가능}(developable, $\Kabs\!\approx\!0$): 원통$\cdot$원뿔처럼 늘이지 않고 평면으로
펼 수 있어 주름이 없는 곳.
\textbf{전단}(shear): 약간의 가위변형만으로 곡면을 덮을 수 있는 곳.
\textbf{다트}(dart): 전단이 재료의 locking 한계를 넘어, 천을 더 비틀 수 없으므로 \emph{쐐기를
잘라내야(dart)} 비로소 곡면에 안착하는 곳. 그림~\ref{fig:angledeficit} 은 이 다트가 왜 생기는지를
``각결손''으로 설명한다.

\begin{figure}[ht]
  \centering
  \begin{tikzpicture}[font=\footnotesize, scale=0.95]
    % (a) developable: six 60-degree wedges sum to 360 -> closes flat
    \begin{scope}
      \foreach \a in {0,60,...,300}{
        \fill[blue!10, draw=blue!55] (0,0) -- (\a:1.6) -- ({\a+60}:1.6) -- cycle;}
      \fill[black] (0,0) circle (1.2pt);
      \node at (0,-2.15) {(a) 발전가능 $K{=}0$};
      \node at (0,-2.7) {$\sum\theta=360^\circ$, 다트 없음};
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
      \node[red!75!black] at (330:1.05) {다트};
      \node at (0,-2.15) {(b) 양곡률 $K{>}0$};
      \node at (0,-2.7) {$\sum\theta<360^\circ$ = 각결손 $\delta$};
    \end{scope}
  \end{tikzpicture}
  \caption{각결손으로 본 다트의 기원. 한 꼭짓점 둘레 삼각형 내각의 합이 (a) $360^\circ$ 이면
  평면으로 완벽히 펴지지만(발전가능, $K{=}0$), (b) $360^\circ$ 보다 작으면(양의 가우스곡률)
  평면 전개 시 쐐기 모양 \emph{각결손} $\delta$ 가 남는다. 이 각결손은 \textbf{다트}의
  기하학적 대응물이며(실제 직물 다트는 전단$\cdot$경계조건$\cdot$곡률 부호에도 좌우된다),
  가우스곡률은 이 각결손을 면적으로 나눈 양이다($K\!\approx\!\delta/A$).
  드레이프 필드의 $\gamma\approx\Kabs\,g^2$ 는 시드에서 거리 $g$ 까지 누적된 이 각결손의
  양에 해당한다.}
  \label{fig:angledeficit}
\end{figure}

\begin{figure}[ht]
  \centering
  \includegraphics[width=0.62\linewidth]{Fig5_drapefield.png}
  \caption{구 캡(cap) 위의 드레이프 필드. 전단량 $\gamma\approx\Kabs\,g^2$ 는 극점
  (시드, $g{=}0$)에서 $\approx0$, 거리 $g$ 가 커질수록 가장자리로 증가한다. 발전가능
  곡면이면 $\Kabs{\approx}0$ 이라 전체가 $\gamma{\approx}0$ 이 된다.}
  \label{fig:drapefield}
\end{figure}

\subsection{핀-조인트 네트: 실제 트렐리스 전단}
\paragraph{왜 근사식만으로는 부족한가.}
식~\eqref{eq:proxy} 의 $\gamma\approx\Kabs\,g^2$ 는 \emph{섬유 방향을 무시한} 하한이다.
실제 직물은 두 실 가닥(날실$\cdot$씨실)이 교차점에서 \emph{핀으로 고정}된 그물(net)과 같아서,
실은 거의 \emph{늘어나지 않지만} 교차점을 축으로 \emph{회전}할 수 있다---이것이 트렐리스
전단(가위 변형)이다. 따라서 같은 곡면이라도 실을 어느 방향으로 깔았는지에 따라 실제 전단량이
달라지는데, 방향을 무시한 근사식은 이를 구분하지 못한다. 정확히 재려면 직물을 실제로 ``깔아
보아야'' 한다.

\paragraph{핀-조인트 네트 모형.}
정사각 격자에서 출발해, 모든 실 분절의 길이를 고정한 채(비신장,
$\text{edge\_error}\!\sim\!10^{-15}$) 곡면을 따라 그물을 한 셀씩 펼친다(측지 행진 $+$ 셀 닫힘,
임의의 삼각망에는 정확한 점-삼각형 투영 사용). 각 셀에서 날실과 씨실이 이루는 각이 $90^\circ$
에서 벗어난 양이 곧 \emph{실측} 트렐리스 전단각이다(그림~\ref{fig:trellisschem}). 이 각이
재료의 locking 각(통상 $30$--$50^\circ$)을 넘으면 그 셀은 주름진다. 단일 네트는 한 시드에서
출발하므로 하나의 일관된 패치만 덮고 경계나 고왜곡 지점에서 멈추는데(manikin 에서 시드당 약
$22/100$ 노드만 안정적으로 깔린다), 이 ``한 장으로는 다 못 덮음''이 곧 다음 절 멀티시드
분할의 동기다.

\begin{figure}[ht]
  \centering
  \begin{tikzpicture}[font=\footnotesize]
    % (a) undeformed orthogonal net
    \foreach \x in {0,1,2,3}{\draw[blue!60,thick] (\x,0)--(\x,3);}
    \foreach \y in {0,1,2,3}{\draw[blue!60,thick] (0,\y)--(3,\y);}
    \foreach \x in {0,1,2,3}{\foreach \y in {0,1,2,3}{\fill[blue!60] (\x,\y) circle (1.3pt);}}
    \draw[->] (0.04,2.0) -- (0.04,2.9) node[left=-1pt]{날실};
    \draw[->] (1.0,0.04) -- (1.9,0.04) node[below=-1pt]{씨실};
    \node at (1.5,-0.85) {(a) 변형 전: 직교 $\gamma{=}0$};
    % shear arrow between panels
    \draw[-{Stealth}, very thick, red!70] (3.5,1.5) -- (5.1,1.5)
      node[midway, above]{전단};
    % (b) sheared net (warp tilts; cm shear keeps weft horizontal)
    \begin{scope}[cm={1,0,0.5,1,(5.7cm,0cm)}]
      \foreach \x in {0,1,2,3}{\draw[orange!80,thick] (\x,0)--(\x,3);}
      \foreach \y in {0,1,2,3}{\draw[orange!80,thick] (0,\y)--(3,\y);}
      \foreach \x in {0,1,2,3}{\foreach \y in {0,1,2,3}{\fill[orange!80] (\x,\y) circle (1.3pt);}}
    \end{scope}
    % crossing-angle marker at sheared origin (absolute coords)
    \draw[red!75] (6.3,0) arc (0:63:0.6);
    \node[red!75!black] at (6.95,0.42) {\scriptsize $90^\circ{-}\gamma$};
    \node at (8.0,-0.85) {(b) 전단 후: $\gamma{>}0$ (가위 변형)};
  \end{tikzpicture}
  \caption{핀-조인트 네트의 트렐리스 전단. (a) 변형 전 두 실(날실$\cdot$씨실)은 교차점에
  핀으로 고정되어 직교한다($\gamma{=}0$). (b) 곡면을 덮을 때 실 길이는 그대로 둔 채 교차점이
  \emph{가위처럼} 회전하여 교차각이 $90^\circ-\gamma$ 로 줄어든다. 이 $\gamma$ 가 셀별 실측
  트렐리스 전단각이며, 재료 locking 각을 넘으면 그 셀이 주름진다. 모든 실 분절을 비신장으로
  유지하므로(edge\_error~$10^{-15}$) 이 각이 곧 \emph{실측} 주름 위험이다.}
  \label{fig:trellisschem}
\end{figure}

\subsection{멀티시드 재시딩과 이산 섬유각}
선행연구의 다방향 기법을 직역한다.

\paragraph{단일 시드의 한계.}
천을 곡면에 붙일 때 \emph{기준점(시드)} 을 하나만 잡으면, 식~\eqref{eq:proxy} 에 따라 그
점에서 멀어질수록 전단 $\gamma$ 가 거리 제곱으로 커진다. 그래서 큰 곡면에서는 시드에서 먼
영역이 거의 모두 ``다트''로 판정되어(그림~\ref{fig:multiseedschem}a), ``한 장으로는 못
덮는다''는 결론밖에 나오지 않는다.

\paragraph{멀티시드 재시딩.}
해법은 기준점을 여럿 두는 것이다. 멀리 퍼진\footnote{시드 위치는 최원점 표본추출
(farthest-point sampling)로 정한다: 이미 고른 시드들에서 가장 먼 면을 다음 시드로 차례로
뽑아, 시드들이 표면에 고르게 퍼지도록 한다.} $K$ 개의 시드를 놓고, 각 면 $i$ 에 대해 시드별
드레이프 비용 $c_{ik}$ 를 구한 뒤 \emph{가장 싼 시드}만 취한다($\min_k c_{ik}$). 그러면 각
면은 \emph{자기에게서 가까운} 시드로부터 덮이게 되어 측지거리 $g$ 가 작게 유지되고, 단일
시드의 다트 지배 필드가 무너진다(그림~\ref{fig:multiseedschem}b). 이것이 \emph{재시딩
자유도}이며, 선행연구의 ``각 부분이 자기 최적 방향을 고른다''는 재배향 자유도의 복합재
직역이다.

\paragraph{이산 섬유각.}
실제 layup 은 섬유를 아무 각도로나 깔 수 없고 제조 가능한 몇 개 각도로만 깐다. 따라서 각
패치에서 네트로 계산한 연속 최적각을 $\{0,\pm45,90\}^\circ$ 메뉴 중 전단이 가장 낮은 각으로
\emph{스냅}(양자화)한다.

\begin{figure}[ht]
  \centering
  \begin{tikzpicture}[font=\footnotesize]
    % (a) single seed: gamma grows with distance -> outer band is dart
    \fill[red!22]    (0,0) circle (1.7);
    \fill[yellow!35] (0,0) circle (1.15);
    \fill[green!35]  (0,0) circle (0.55);
    \fill[black] (0,0) circle (1.6pt);
    \node[above right=-2pt] at (0,0) {시드};
    \draw[-{Stealth}] (0,0) -- (35:1.7) node[midway, above, sloped]{$g$};
    \node[red!75!black] at (-1.15,1.15) {\scriptsize 다트};
    \node at (0,-2.15) {(a) 단일 시드: $\gamma\approx\Kabs g^2\!\uparrow$};
    % (b) multi-seed: region tiled by nearby seeds -> mostly low shear
    \begin{scope}[shift={(5.6,0)}]
      \fill[green!30] (0,0) circle (1.7);
      \draw[white, very thick] (0,-1.7) -- (0,1.7);
      \draw[white, very thick] (-1.7,0) -- (1.7,0);
      \draw[black!55] (0,0) circle (1.7);
      \foreach \p in {(0.8,0.8),(-0.8,0.8),(0.8,-0.8),(-0.8,-0.8)}{
        \fill[black] \p circle (1.6pt);}
      \node at (0,-2.15) {(b) 멀티시드: $\min_k c_{ik}$};
    \end{scope}
  \end{tikzpicture}
  \caption{단일 대 멀티시드의 원리. (a) 시드가 하나면 거리 제곱으로 전단이 커져
  ($\gamma\approx\Kabs g^2$) 시드에서 먼 바깥 띠가 모두 다트(붉은색)가 된다. (b) 멀리 퍼진
  여러 시드를 두고 각 면이 가장 가까운(가장 싼) 시드를 고르면($\min_k c_{ik}$) 측지거리가
  작게 유지되어 대부분이 저전단(녹색)으로 바뀐다. 이 재시딩 자유도가 다트 지배 필드를
  붕괴시킨다.}
  \label{fig:multiseedschem}
\end{figure}

\subsection{이음매-대-재정렬 목적함수와 자동 패치 수}
식~\eqref{eq:rayfree} 를 드레이프 의미로 재해석한다:
\begin{equation}
  \text{cost}(\Pi)=\sum_{\ell}\min_{\text{seed}}\sum_{i\in P_\ell}A_i\,\text{shear}_i(\text{seed})
  \;+\;w_{\text{seam}}\,\mathrm{seamlen}(\Pi),
\end{equation}
첫 항은 각 패치가 자기 시드로 재정렬하여 줄인 전단(면적 $A_i$ 가중), 둘째 항은 섬유
연속성 단절(이음매 길이)이다. 자동 패치 수 결정은 $K$ 를 바꿔가며 정규화 비용 곡선의
무릎점(knee)과 복잡도 패널티 $\alpha K/K_{\max}$ 로 최적 $\Kstar$ 를 고른다.

\subsection{실제 엔진 연동과 벤치마크}
드레이프 필드 생성 단계만 새로 추가되고, 어댑터가 공개 \texttt{partition\_mesh} 를 수정
없이 구동한다. 벤치마크는 좌표 k-medoids, 축-슬랩, 곡률, 드레이프-인지 분할을 난이도
사다리(발전가능 $\sim$ 이중곡률 $\sim$ 실측)에서 제조 지표(locking 초과면적, 다트 비율,
드레이프 순도, 이음매)로 비교한다.

\paragraph{구현 환경.}
모든 실험은 AMD Ryzen~9 9950X3D CPU(16코어/32스레드)와 125~GB RAM을 갖춘
Windows~11 워크스테이션에서 수행하였다. 드레이프 필드, 분할기, 제조 지표는
Python~3.12(NumPy, SciPy, Trimesh, scikit-learn) 기반의 단일 머신 CPU 코드이며,
스크린드-푸아송 리메시에는 선택적으로 Open3D를, \S\ref{sec:baraff} 의 정밀 검증에는
자체 Baraff--Witkin 암시적 천 솔버(\texttt{cfmsDrape}, 네이티브 DLL)를 사용하였다.
보고된 모든 실행 시간은 이 머신에서의 실측(wall-clock)이다.

% =====================================================================
\section{결과}
% =====================================================================
\subsection{재시딩 자유도가 다트 지배 필드를 붕괴시킨다}
쉽게 말하면, 표~\ref{tab:r2} 의 ``다트 비율''은 \emph{한 장의 천으로는 깔 수 없어 쐐기를
잘라내야 하는 면의 비율}이다($0$ 이면 통째로 깔 수 있고, $1$ 에 가까우면 거의 다 잘라야
한다). 시드(천을 처음 붙이는 기준점)를 하나만 쓰면 manikin 면의 $98\%$ 가 다트이지만, 패치마다
자기 시드를 쓰게 하면(멀티시드, 그림~\ref{fig:multiseedschem} 의 원리) $42\%$ 로 떨어진다
(패치별 시드 $\approx260$ 개; 시드 $8$ 개만으로는 $88\%$ 에 그쳐, 몸통형 셸은 \emph{충분히
작은} 패치가 필요함을 함께 보인다).

표~\ref{tab:r2} 와 같이, 각 패치가 자기 시드를 채택하면 다트 비율이 급감한다(manikin
$0.98\to0.42$, 해석적 구 $0.36\to0.00$). 남는 다트는 손가락$\cdot$접힘 같은 고곡률의
\emph{본질적} 영역으로, 어떤 시드로도 평평히 못 펴는 곳이다. 이는 선행연구의 재배향-
자유도 결론의 복합재 직역이다.

\begin{table}[ht]\centering
\caption{단일시드 대 멀티시드. 근사 $\gamma\approx\Kabs g^2$ 는 무차원 1차 심각도이며,
상태 분류 시 $\gamma$ 가 \emph{locking 각에 보정된 proxy 임계}를 넘으면 ``다트''로
표시한다(각도와의 직접 비교가 아님). 따라서 최소전단 열은 원시 근사 단위(스케일 의존)이고, degree 단위의
보정된 트렐리스 각은 fishnet/Baraff 검증(그림~\ref{fig:trellis})에서 얻는다.}
\label{tab:r2}
\begin{tabular}{lccc}
\toprule
메쉬 & 단일시드 다트 & 멀티시드 다트 & 최소전단 평균 (단일$\to$멀티) \\
\midrule
sphere cap (해석) & 0.36 & \textbf{0.00} ($k{=}8$) & $0.63\to0.18$ \\
manikin (13.7k 면) & 0.98 & \textbf{0.42} (패치별 시드 $\approx260$) & $13150\to6.9$ \\
liver (19.4k 면) & 0.86 & \textbf{0.45} ($k{=}16$) & $92\to3.2$ \\
\bottomrule
\end{tabular}
\end{table}

\begin{figure}[ht]
  \centering
  \includegraphics[width=0.72\linewidth]{Fig2_reseeding.png}
  \caption{재시딩 자유도. 각 패치가 자기 시드를 채택하면 다트 비율이 급감한다(manikin
  $0.98\!\to\!0.42$, 구 $0.36\!\to\!0.00$). 남는 다트는 고곡률의 본질적 영역이다.}
  \label{fig:reseeding}
\end{figure}

이산 섬유각 메뉴는 발전가능 몰드(원통)에서 정렬각 $0^\circ/90^\circ$ 가 $\sim0^\circ$
전단을, 구에서는 $45^\circ$ 가 최악 대비 $6.6\times$ 낮은 전단을 선택한다.

\subsection{이음매-대-재정렬 자동 패치 수}
표~\ref{tab:r3} 처럼 발전가능 몰드는 $\Kstar{=}1$(절단이 이득 없음), 이중곡률은 절단이
비용을 상쇄하여 무릎점에서 패치 수가 정해진다. 실측 manikin 은 근사식으로는
$\Kstar{=}1$(본질적 고곡률)이지만, 패치별 \emph{실제 네트} 비용으로 매기면 패치별 비용이
절반으로 떨어져 $\Kstar{=}5$ 로 뒤집힌다. 나아가 $\{0,\pm45,90\}$ 각도 최적화를 결합하면
발전가능 $\Kstar{=}1$ 이 복원되고(원통 $2\to1$), 구 전단이 절반($5.9^\circ\to2.8^\circ$),
manikin 은 더 적은 패치($5\to2$)로 현실적 각도 혼합을 갖는다.

\begin{table}[ht]\centering
\caption{자동 패치 수. 근사식 비용 대 실제 네트 비용.}
\label{tab:r3}
\begin{tabular}{lccc}
\toprule
몰드 & 곡률 & 근사 $\Kstar$ & 네트 $\Kstar$ \\
\midrule
plane / cylinder & 발전가능 & 1 & 1 \\
sphere cap & 이중곡률 & 6 & 4 \\
saddle & 이중곡률 & 6 & --- \\
manikin (13.7k 면) & 본질적 고곡률 & 1 & \textbf{5} \\
\bottomrule
\end{tabular}
\end{table}

\begin{figure}[ht]
  \centering
  \includegraphics[width=0.74\linewidth]{Fig3_autocount.png}
  \caption{이음매-대-재정렬 비용 대 패치 수 $K$ (공통 척도로 정규화). 발전가능 원통은
  $0$ 근처 평탄선으로 $\Kstar{=}1$(절단 이득 없음), 이중곡률 구$\cdot$안장은 절단이
  비용을 상쇄하여 무릎점에서 $\Kstar{=}6$ 을 고른다.}
  \label{fig:autocount}
\end{figure}

\subsection{실측 메쉬와 엔진 연동}
드레이프 필드는 manikin(13.7k 면) $0.34$\,s, liver(19.4k 면) $0.22$\,s 에 계산되어
공개 분할기로 직접 흐른다. 표~\ref{tab:r4} 의 $\Kabs$ 일관성(패치내 곡률표준편차 /
전역표준편차; 낮을수록 곡률-일관)은 \emph{같은 방법}에서 패치 수가 늘수록 감소하여
(k-medoids $k{=}6\to12$ 에서 $0.81\to0.61$) 분할이 단순 공간적이 아니라 비슷한 곡률을
묶음을 보인다. 드레이프-영역성장 행은 순도 $1.000$ 에 이르나 $608$/$291$ 패치에서다 ---
이 순도는 과분할 효과(작고 자명하게 균질한 패치 다수)일 뿐 $k{=}6$/$12$ k-medoids 와
동일 패치 예산 비교가 아니므로 우월성의 근거로 삼지 않는다.

\begin{table}[ht]\centering
\caption{실측 메쉬 분할. 시드 $=+z$, locking $45^\circ$. 순도(purity)는 한 패치 안의
드레이프 상태가 얼마나 한 종류로 일관된지의 비율.}
\label{tab:r4}
\begin{tabular}{llccc}
\toprule
메쉬 & 방법 & 패치 수 & 드레이프 순도 & $\Kabs$ 일관성 $\downarrow$ \\
\midrule
manikin & kmedoids $k{=}6$ & 6 & 0.977 & 0.81 \\
manikin & kmedoids $k{=}12$ & 12 & 0.977 & 0.61 \\
manikin & 드레이프-영역성장 & 608 & 1.000 & 0.49 \\
liver & kmedoids $k{=}6$ & 6 & 0.861 & 0.87 \\
liver & 드레이프-영역성장 & 291 & 1.000 & 0.49 \\
\bottomrule
\end{tabular}
\end{table}

\subsection{응용 사례: 실측 해부/형상 메쉬}
장기(간 liver, 신장 kidney)와 두상(Nefertiti)에 \emph{본 연구의 드레이프 필드}를
적용하고 feature-fusion k-medoids 로 분할한 결과를 그림~\ref{fig:app_organs}--%
\ref{fig:app_nefertiti} 에 보인다(패치 색 $=$ 드레이프-일관 패치). 드레이프 순도는
kidney $0.85$, liver $0.86$, Nefertiti $0.95$ 다. 패치 경계가 곡률/드레이프 상태를
따라 떨어진다.

\paragraph{제조 가능한 패치를 위한 후처리.}
특징공간 군집화는 각 면을 \emph{독립적으로} 라벨링하고, 게다가 임포트 메쉬 자체가 좌표는
일치하나 인덱스가 분리된 조각(triangle soup)을 품을 수 있어, 그대로는 직물을 재단$\cdot$성형
하기 어렵다. 본 연구는 네 단계 후처리를 둔다.
\textbf{(1) 입력 메쉬 정리.} 좌표가 거의 일치하는 정점을 융합(weld)해 끊긴 이음매를 다시
잇고, 중복$\cdot$퇴화 면을 제거하며, 충분히 큰 연결 성분만 남기고 면 방향(winding)을
일관화한다.
\textbf{(2) 리메시(공학 셸 한정).} 임포트 soup 이 심한 공학 셸은 표면을 다시 뽑아\footnote{모서리
세분(subdivision)은 비폐곡 메쉬를 오히려 \emph{갈라지게} 만든다(자동차에서 성분
$277\!\to\!903$). 리메시는 \emph{재표집}이라 soup 을 깨끗한 셸/성분으로 만든다.} 깨끗한 드레이프 셸/성분을
얻는다(이음매 계단이 사라진다). 두 방식을 구현했다(그림~\ref{fig:app_remesh} 비교).
\emph{(i) 복셀 리메시}는 표면을 복셀화$\cdot$내부 채움 후 행진육면체로 바깥 면을 뽑아 단일
폐곡(watertight) 셸을 주지만 복셀 해상도만큼 날카로운 모서리가 둥글어진다.
\emph{(ii) 스크린드 푸아송 재구성}~\citep{kazhdan2013poisson} 은 표면에서 방향 점을 표집해
푸아송 방정식의 등위면으로 매끄러운 셸을 복원하므로 \emph{특징을 보존}한다(차체의 도어 라인,
선체 곡면 유지). 본 연구는 (ii)를 기본으로 쓰고(open3d 사용 가능 시), open3d 가 없으면 (i)로
자동 대체한다.
\textbf{(3) 경계 정규화.} 선행연구 SFTF-Clustering 의 \emph{이면각 가중 그래프-컷}
(MRF 를 ICM\footnote{ICM(iterated conditional modes): 각 면의 라벨을 이웃을 고정한 채 비용이
최소가 되도록 차례로 갱신하기를 반복하는 그래프-컷 근사 최적화.} 으로 풂)으로 각 면을
\emph{데이터 비용}(특징공간에서 자기 패치 중심까지의 거리)과 \emph{절단 비용}($\lambda$
가중, 평탄면에서 크고 오목한 접힘선에서 작음)의 합이 최소가 되게 재배정하면, 이음매가
짧아지고 \emph{다트$\cdot$이음매가 놓일 오목 곡선}을 따라 정렬된다. 이어 다수결 이음매 평활로
삼각형 단위의 잔여 계단을 편다.
\textbf{(4) 소영역 흡수.} 면 수가 임계값 미만인 연결 성분을 경계를 가장 많이 접한 이웃 패치로
흡수해 speckle 을 제거한다($\lambda{=}3$, 선행연구와 동일).
이 후처리로 Nefertiti 의 이음매 면비율이 $0.047\!\to\!0.009$, 분리 조각 수가 $1508\!\to\!6$
으로 줄고(그림~\ref{fig:app_smooth}), 임포트 soup 이 심한 공학 셸은 푸아송 리메시 후 매끄러운
셸/성분이 되어 드레이프 순도가 항공기 $0.915$(양쪽 엔진 성분 보존)$\cdot$차체 $0.949$ 에 이르고,
개방형 요트 hull 은 $0.632$ 로 낮다. 이 공학 케이스들의 이음매 면비율은
$0.009$--$0.012$ 로 낮아진다(그림~\ref{fig:app_condition},~\ref{fig:app_remesh}). 이하 모든
응용 그림은 이 후처리를 적용한 결과다.

\begin{figure}[ht]\centering
  \includegraphics[width=0.40\linewidth]{App_nefertiti_raw.png}\hfill
  \includegraphics[width=0.40\linewidth]{App_nefertiti.png}
  \caption{\emph{경계 정규화} 전(좌)/후(우), 동일 메쉬. 좌: 원시 feature-fusion 라벨 --- 톱니진
  경계와 산재한 작은 조각(triangle soup). 우: 이면각 가중 MRF 평활 $+$ 이음매 평활 $+$ 소영역
  흡수 후 --- 매끄럽고 곡률선을 따르는 이음매, speckle 제거(이음매 면비율 $0.047\!\to\!0.009$,
  분리 조각 $1508\!\to\!6$).}
  \label{fig:app_smooth}
\end{figure}

\begin{figure}[ht]\centering
  \includegraphics[width=0.31\linewidth]{App_obj_car_supra_soup.png}\hfill
  \includegraphics[width=0.31\linewidth]{App_obj_car_supra_conditioned.png}\hfill
  \includegraphics[width=0.31\linewidth]{App_obj_car_supra.png}
  \caption{공학 셸(자동차 차체, 위에서 본 평면도)의 \emph{3단계} 정비. 좌: 임포트 원본 ---
  인덱스가 분리된 면들로 표면이 $277$ 조각으로 끊기고 경계가 계단지며 슬리버가 낀다.
  중: 정점 융합$\cdot$중복면 제거$\cdot$대성분 보존 후($8$ 성분) --- 연결되나 삼각형 단위 계단이
  남는다. 우: 스크린드 푸아송 리메시 후 --- 단일 셸에 매끄러운 곡선 이음매, 도어 라인 같은
  특징도 보존된다.}
  \label{fig:app_condition}
\end{figure}

\begin{figure}[ht]\centering
  \includegraphics[width=0.40\linewidth]{App_obj_car_supra_voxel.png}\hfill
  \includegraphics[width=0.40\linewidth]{App_obj_car_supra.png}
  \caption{리메시 방식 비교(자동차 차체). 좌: \emph{복셀 리메시} --- 단일 폐곡 셸이지만
  날카로운 모서리가 둥글어진다(외형 포락면, 순도 $0.70$). 우: \emph{스크린드 푸아송}
  ~\citep{kazhdan2013poisson} --- 도어 라인$\cdot$차체 곡면 같은 특징을 보존해 더 매끄럽고
  드레이프 순도도 높다($0.95$).}
  \label{fig:app_remesh}
\end{figure}

\begin{figure}[ht]\centering
  \includegraphics[width=0.47\linewidth]{App_kidney.png}\hfill
  \includegraphics[width=0.47\linewidth]{App_liver.png}
  \caption{신장(kidney, 12.4k 면; 좌)과 간(liver, 19.4k 면; 우)의 드레이프 필드
  분할($k{=}6$). 드레이프 순도 $0.85$ / $0.86$; 패치가 곡률 영역을 따라 나뉜다.}
  \label{fig:app_organs}
\end{figure}

\begin{figure}[ht]\centering
  \includegraphics[width=0.46\linewidth]{App_nefertiti.png}
  \caption{Nefertiti 두상(99.9k 면)의 드레이프 필드 분할($k{=}8$, 드레이프 순도
  $0.95$). 패치가 왕관$\cdot$얼굴$\cdot$목$\cdot$흉부의 곡률 영역을 따라 나뉜다.}
  \label{fig:app_nefertiti}
\end{figure}

나아가 공개 데이터셋 Thingi10K~\citep{zhou2016thingi10k} 에서 받은 이중곡률 자유곡면
셸(조개껍데기)에도 동일 분할을 적용했다(그림~\ref{fig:app_shells}). 조개껍데기는
비발전가능 곡면의 대표 예이자 그 자체로 천연 적층 복합재(진주층)로, 좋은 시험 형상이다.
세 셸 모두 드레이프 순도 $0.96\text{--}0.98$ 로 곡률을 따라 일관 패치로 나뉜다.

\begin{figure}[ht]\centering
  \includegraphics[width=0.31\linewidth]{App_thingi_turritella_shell_44704.png}\hfill
  \includegraphics[width=0.31\linewidth]{App_thingi_oxystele_shell_46774.png}\hfill
  \includegraphics[width=0.31\linewidth]{App_thingi_shell01_41909.png}
  \caption{Thingi10K 의 이중곡률 자유곡면 셸(조개껍데기) 드레이프 분할($k{=}6$):
  Turritella(좌)$\cdot$Oxystele(중)$\cdot$Shell~01(우). 드레이프 순도 $0.96$/$0.98$/$0.98$.}
  \label{fig:app_shells}
\end{figure}

끝으로 \textbf{공학 구조의 복합재 셸} --- 항공기 동체$\cdot$자동차 차체$\cdot$요트
선체 --- 에도 적용했다(그림~\ref{fig:app_eng}). Objaverse~\citep{deitke2023objaverse}
의 CC-BY 모델이며, 특히 Boeing 787 은 탄소복합재 항공기의 대표 사례다. 동체$\cdot$
날개$\cdot$선체 같은 이중곡률 셸은 드레이프 분할의 직접 응용 대상이다(반면 자전거$\cdot$
골프채는 관$\cdot$봉 구조라 셸 드레이프 대상이 아니어서 제외했다). 이들 Objaverse 공학 셸은
임포트 메쉬가 비매니폴드$\cdot$분리 조각을 품으므로 위 \emph{스크린드 푸아송 리메시}까지 거쳐
분할했고, 그 결과 특징을 보존한 매끄러운 셸/성분에서 곡선 이음매를 얻으며 항공기/차체의
드레이프 순도도 향상된다($0.915$/$0.949$). 푸아송은 데이터가 성긴 곳을 외삽한 표면을 밀도
하위분위로 잘라내므로 그 부분에서 폐곡성이 깨질 수 있는데(엄밀한 폐곡 셸이 필요하면 복셀
리메시를 쓰면 된다), 패치$\cdot$이음매 계획에는 영향이 없다. 요트처럼 난간$\cdot$개방 데크가
많은 어셈블리는 푸아송이 외형 hull 로 매끄럽게 닫아 주지만 정밀 데크 구조는 잃으므로, 이
경우 드레이프 대상은 hull 셸로 한정된다(순도 $0.632$).

\begin{figure}[ht]\centering
  \includegraphics[width=0.37\linewidth]{App_obj_airplane_b787.png}\hfill
  \includegraphics[width=0.30\linewidth]{App_obj_car_supra.png}\hfill
  \includegraphics[width=0.30\linewidth]{App_obj_yacht.png}
  \caption{공학 복합재 셸의 드레이프 필드 분할($k{=}6$): Boeing 787 여객기(좌),
  Toyota Supra 차체(중), 요트 선체(우). Objaverse(CC-BY).}
  \label{fig:app_eng}
\end{figure}

\subsection{방법론 정량 비교}
\label{sec:compare}
서론에서 소개한 분할 기법들 --- 좌표 k-means~\citep{lloyd1982}, 최장축
슬랩(axis-BSP), 곡률 클러스터링, 변분 형상 근사 VSA\footnote{VSA(Variational Shape
Approximation): 곡면을 $k$개의 ``평면 조각''으로 근사하도록, 면 법선의 편차를 최소화
하며 영역을 나누는 고전 분할 기법~\citep{cohensteiner2004vsa}.} --- 과 본 연구의
드레이프-인지 분할을 그림~\ref{fig:app_organs}--\ref{fig:app_eng} 의 9개 메쉬에 적용해
($k{=}6$, locking $45^\circ$) 제조 지표로 비교한다. 종합표(표~\ref{tab:cmp-agg})는
lock\_area$\cdot$dart$\cdot$순도$\cdot$seam 을 9개 메쉬 평균으로 보고하고,
\textbf{평면전개 왜곡} 지표는 비매니폴드 공학 임포트에서 신뢰도가 낮으므로 \textbf{비공학
메쉬 6개}에 대해 따로 보고한다(표~\ref{tab:cmp-flat}). 면별 lock\_area 표(표~\ref{tab:cmp-lock})
도 같은 6개를 쓰는데, 공학 메쉬 3개에서는 lock\_area 가 분할-무관(본질적 곡률)이기
때문이다. 평면전개 왜곡\footnote{각 패치를 평면 재단패턴으로 펼칠 때의 변형량. 발전가능
패치는 0. LSCM 은 각도보존(등각) 전개의 왜곡, ARAP 은 길이보존(비신장) 전개의 stretch 로,
ARAP 이 섬유 비신장성에 더 가깝다.} 는 LSCM~\citep{levy2002lscm} 과
ARAP~\citep{liu2008arap} 두 가지로 잰다.

\begin{table}[ht]\centering
\caption{방법론 비교 종합(9개 메쉬 평균, 분할-민감 지표만). 모든 지표는 낮을수록 우수
(순도만 높을수록). 평면전개 왜곡(LSCM/ARAP)은 비공학 메쉬 6개에 대해 표~\ref{tab:cmp-flat}
에 따로 보고한다.}
\label{tab:cmp-agg}
\begin{tabular}{lcccc}
\toprule
방법 & lock\_area $\downarrow$ & dart $\downarrow$ & 순도 $\uparrow$ & seam $\downarrow$ \\
\midrule
k-means (좌표; 제조-무관) & \textbf{0.469} & \textbf{0.643} & 0.770 & \textbf{1271} \\
axis-BSP & 0.531 & 0.692 & 0.780 & 1700 \\
curvature & 0.596 & 0.738 & \textbf{0.825} & 5253 \\
VSA~\citep{cohensteiner2004vsa} & 0.553 & 0.712 & 0.793 & 4810 \\
\textbf{드레이프-인지 (본 연구)} & \underline{0.490} & \underline{0.675} & 0.776 & 2428 \\
\bottomrule
\end{tabular}
\end{table}

\begin{table}[ht]\centering
\caption{면별 주름위험 lock\_area(전단이 locking 을 넘는 면적비, 낮을수록 우수). 표면을
모델링하는 방법(curvature$\cdot$VSA$\cdot$axis) 중 본 연구가 일관되게 최소이며, 공간
compactness 상한(k-means)에 근접한다. 공학 메쉬는 lock\_area 가 분할-무관이라 생략.}
\label{tab:cmp-lock}
\begin{tabular}{lccccc}
\toprule
메쉬 & k-means & axis-BSP & curvature & VSA & 본 연구 \\
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
\caption{비공학 메쉬 6개의 면별 ARAP 비신장 평면전개 stretch(낮을수록 평면화 용이;
발전가능=0). 곡률 클러스터링이 이 6개 메쉬 모두에서 최악이고 본 연구는 이를 일관되게
능가한다. 단 법선-프록시(VSA)$\cdot$compactness(k-means)도 평면화엔 강해 본 연구가
지배적이진 않다.}
\label{tab:cmp-flat}
\begin{tabular}{lccccc}
\toprule
메쉬 & k-means & axis-BSP & curvature & VSA & 본 연구 \\
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

\paragraph{읽기(정직하게).} 세 가지가 드러난다. (1) \emph{공간 compactness}(k-means)는
raw 비용(lock\_area, dart, seam)에 강한 baseline 이지만 곡률$\cdot$전단을 전혀
보지 않는 \emph{제조-무관} 분할이다. (2) \emph{표면을 모델링하는} 정통 분할 기법
(curvature$\cdot$VSA$\cdot$axis-BSP) 중 \textbf{본 연구가 lock\_area 가 가장 낮고}
(표~\ref{tab:cmp-lock} 의 비공학 메쉬 6개 모두에서 2위 이내, turritella, oxystele
에선 전체 1위), 종합적으로 \textbf{dart 도 이 방법들 중 최저}다(표~\ref{tab:cmp-agg}).
(3) curvature$\cdot$VSA 는 곡률$\cdot$법선만으로 묶어 순도는 높지만(곡률에서 상태가
파생되므로 거의 자명) 과분할하여 seam 이 $2\text{--}4\times$ 크다. 평면전개
용이성(ARAP 비신장 stretch, 표~\ref{tab:cmp-flat})에서는 \textbf{곡률 클러스터링이 이
6개 메쉬 모두에서 최악}이고 본 연구가 이를 일관되게 능가하나, 법선-프록시 VSA 와
compactness
k-means 도 평면화엔 강해(평면$\cdot$compact 패치는 본질적으로 잘 펴짐) 본 연구가
평면화를 \emph{지배}하지는 않는다. 본 연구의 결정적 우위는 \textbf{재시딩을 반영한
주름위험}(lock\_area, dart)이며, 거기서 표면-인지 방법 중 선두다. 즉 본 연구의
가치는 raw 비용에서 compactness 를 이기는 것이 아니라, \emph{제조-인지 피처를 쓰면서도
compactness 상한에 근접한 주름위험}을 달성하고, 그 피처가 재시딩$\cdot$이산 섬유각$\cdot$
다트 플래그$\cdot$상태 일관성을 가능케 한다는 데 있다(k-means 는 이를 제공할 수 없다).

\subsection{평면전개 교차검증과 더블돔 벤치마크}
앞 절의 평면전개 지표는 본 연구의 ARAP/LSCM 구현으로 계산하므로, 먼저 구현 정확성과
직물 물리를 분리해 확인했다. 닫힌형 해석 전개가 가능한 열린 발전가능 패치에서, 해석 전개
교차검증은 ARAP 기준 원통 \(6.73\times10^{-5}\), 원뿔 \(5.83\times10^{-5}\)의
RMS/대표길이 잔차를 보였고, edge-length-ratio 표준편차는 표시 정밀도에서 \(0.0000\)
이었다(표~\ref{tab:extra-validation}). 따라서 구현 자체는 정확한 발전가능 전개를 재현한다.
선택적 libigl 경로는 비발전가능 메쉬에 대한 제3자 교차검증용이며, 현재 환경에서는 libigl이
설치되지 않으면 건너뛴다.

다음으로 직물 복합재 성형 검증용 sanity check로 매개변수화된 더블돔 벤치마크를 사용했다
(그림~\ref{fig:double-dome-validation}). \(9434\)개 면의 더블돔에서 kinematic fishnet은
비신장성(edge error \(0.0000\), 표시 정밀도 기준)을 유지하면서 대각 단면 최대 전단
\(39.1^\circ\)를 예측했고, 이는 이 형상에서 사용한 \(45^\circ\) locking 각도보다 낮다.
반면 ARAP 평면전개는 최대 전단을 \(4.8^\circ\)로만 보고한다. 이는 앞의 비교와 같은 결론을
강화한다. ARAP은 발전가능 정확도와 패턴 왜곡 평가에는 유용하지만, 성형 전단과 주름위험은
fishnet 모델 또는 역학 솔버로 읽어야 한다. 벤치마크 스크립트에는 실험값 overlay 경로를
마련했지만, 본문에는 외부 실험값을 임의 생성해 넣지 않았다.

\begin{table}[ht]\centering
\caption{추가 평면전개 및 성형 검증 결과.}
\label{tab:extra-validation}
\begin{tabular}{lll}
\toprule
검증 & 형상 & 관찰 결과 \\
\midrule
해석 전개 & 원통, 원뿔 &
ARAP RMS/대표길이 \(6.73\times10^{-5}\), \(5.83\times10^{-5}\) \\
더블돔 & 9434 faces &
fishnet 최대 \(39.1^\circ\), ARAP 최대 \(4.8^\circ\), edge error \(0.0000\) \\
\bottomrule
\end{tabular}
\end{table}

\begin{figure}[ht]\centering
  \includegraphics[width=\linewidth]{Val_double_dome_report.png}
  \caption{더블돔 성형 벤치마크. Fishnet 모델은 edge length를 보존하면서 대각 전단 집중을
  드러내지만, ARAP 평면전개는 성형 전단을 크게 낮게 보고한다. 점선은 이 검증에서 사용한
  \(45^\circ\) locking 각도다.}
  \label{fig:double-dome-validation}
\end{figure}
\FloatBarrier

\subsection{정밀 Baraff 솔버 대비 검증}
\label{sec:baraff}
가벼운 근사 전단장을 Baraff--Witkin~\citep{baraff1998large} 음함수 천 솔버로 검증한다.
변형 형상에서 전단을 변형구배로 복원하는 지표는 해석적으로 검증되어 있다(순수신장$\to0$,
$20^\circ$ affine$\to20^\circ$, 원통$\to0$, 구$\to$증가). 결과는 \textbf{정직한 음성}
이다: \emph{중력 자유낙하 드레이프는 성형의 올바른 경계조건이 아니다}. 볼록 돔에서는
시트가 발전가능하게 미끄러져 전단을 회피(평균 $\sim2^\circ$, 상관계수
Spearman\footnote{Spearman 상관계수: 두 양의 순위가 얼마나 함께 움직이는지를 $-1\sim1$
로 나타내는 지표. $0$ 은 무관, $1$ 은 완전 동조.} $\approx0$), 오목 보울에서는 바닥에
뭉쳐 약한 상관만 남는다(표~\ref{tab:r7}).

\begin{table}[ht]\centering
\caption{근사 전단 대 Baraff 전단, cap 각도 sweep, 고정 재료.}
\label{tab:r7}
\begin{tabular}{lccc}
\toprule
몰드 & Baraff 전단(평균) & 근사 Spearman & 네트 Spearman \\
\midrule
dome (볼록, 자유낙하) & $1.8$--$2.6^\circ$ & $-0.03\ldots0.03$ & $-0.01\ldots0.04$ \\
bowl (오목, 중력) & $35$--$44^\circ$ & $-0.03\ldots0.41$ & $0.00\ldots0.27$ \\
\bottomrule
\end{tabular}
\end{table}

올바른 검증을 위해 천 솔버에 \textbf{분산 압력 항}을 중력과 동형으로 추가하고
진공/다이어프램 성형 하중을 구동했다. 구심 압력 $+$ 정점 고정 $+$ 직물 재료(고 인장$\cdot$
저 전단)로 \textbf{깨끗한 밀착}(잔차 $\sim0.8$\,cm, 전단 평균 $18.6^\circ$,
p90 $35.8^\circ$)을 달성했다.
그러나 깨끗이 성형해도 Baraff 전단은 근사 필드와 \textbf{거의 상관이 없다}
(Spearman 근사 $0.03$ / fishnet $0.05$). 두 원인을 확인했다: (i) 구면 트렐리스
전단은 날실/씨실 축에서 낮고 $\pm45^\circ$ 대각에서 높은 \textbf{4-fold 각도 패턴}
(주름 바닥 $\sim17^\circ$ 위의 완만한 $\sim3^\circ$ 끝점 대비)인데
$\gamma=\Kabs g^2$ 는 반경 대칭이라 이를 못 본다; (ii) 성형 영역은 대부분
주름(buckling) 지배다. 즉 성형도 \emph{요소별} 정량 검증을 구제하지 못하며, 이 필드의
가치는 raw 전단 예측이 아니라 상태 일관성과 재시딩 메커니즘이다.

\begin{figure}[ht]
  \centering
  \includegraphics[width=0.66\linewidth]{Fig6_trellis.png}
  \caption{성형 검증의 정직한 핵심. 깨끗이 밀착된 구면에서도 Baraff 전단은 날실/씨실
  축($|\sin2\varphi|{\approx}0$, $16.6^\circ$)에서 가장 낮고 $\pm45^\circ$
  대각($|\sin2\varphi|{\approx}1$, $19.7^\circ$)에서 가장 높은 \textbf{4-fold 트렐리스
  신호}다. 대비는 완만하고($\sim3^\circ$), 주름이 캡 전체를 $\sim17^\circ$ 로
  바닥에 깔아 중간 구간은 비단조다. 반경 대칭 근사 $\gamma=\Kabs g^2$ 는 이
  각도 구조를 보지 못해 요소별 상관이 사실상 없다.}
  \label{fig:trellis}
\end{figure}

% =====================================================================
\section{논의와 정직한 한계}
% =====================================================================
\begin{itemize}
  \item \textbf{근사의 성격.} kinematic 드레이프는 기하 결정론적 근사로, 직물 역학과
        성형력을 무시한다. 1차 검증엔 충분하나 절대 주름량은 아니다.
  \item \textbf{재료 의존성.} locking angle 은 재료 의존적이므로 결과는 임계값과 함께
        보고한다.
  \item \textbf{시드 민감도.} 시드/원점 선택이 결과를 좌우하므로 다후보$\cdot$반복으로
        통제하고 민감도를 보고한다.
  \item \textbf{단층 한정.} 1차 범위는 단일 플라이로 한정하며, 다층 적층순서$\cdot$각도
        시퀀스는 향후 확장이다.
  \item \textbf{검증 경계조건.} 자유낙하 천 드레이프는 성형의 올바른 기준이 아니다.
        분산 압력 항으로 성형 경계조건을 열었으나, 요소별 전단의 강한 정량 일치는
        4-fold 트렐리스 구조와 주름으로 인해 본질적으로 얻어지지 않는다.
\end{itemize}

% =====================================================================
\section{결론}
% =====================================================================
SFTF-Clustering 의 골격(분할 알고리즘, feature-fusion, 영역성장, 목적함수, 순도, 자동
패치 수)의 약 $80\%$ 는 그대로 살고, 새로 짠 것은 \textbf{kinematic 드레이프 필드
생성기 하나}임을 확인했다. 면별 드레이프 필드는 공개 분할기의 drop-in 이며, 멀티시드
재시딩이 다트 지배 필드를 붕괴시키고(manikin $0.98\to0.42$), 이음매-대-재정렬 자동
패치 수가 발전가능$\to\Kstar{=}1$, 이중곡률$\to$다패치를 옳게 고른다. 대표 분할
기법들과의 비교는 본 연구가 표면-인지 방법 중 주름위험에서 선두임을, Baraff 검증은
이 가벼운 필드의 가치가 raw 전단 예측이 아니라 \emph{역할-일관 패치와 재시딩
메커니즘}에 있음을 정직하게 보인다. 향후 과제는 각도/트렐리스-인지 전단 필드와 다층
적층, 그리고 성형 정답 데이터 생성을 위한 압력-구동 성형 하니스의 활용이다.

% =====================================================================
% 후행부(2026-07-06 추가; SFTF 삼부작 선언부와 lockstep)
% =====================================================================
\section*{사사}

\paragraph{AI 보조 도구 사용.}
연구 코드 구현의 일부, 그림 생성 스크립트, 원고 작성 보조에 OpenAI Codex 및
Anthropic Claude Code 등 AI 코딩 보조 도구를 사용하였다. 생성된 모든 코드,
실험 결과, 원고 수정은 저자가 검토·검증하였으며, 방법론·데이터·결과·결론의
정확성에 대한 책임은 전적으로 저자에게 있다. 연구 데이터, 새로운 연구 이미지로
제시된 그림, 참고문헌의 생성에는 생성형 AI를 사용하지 않았다.

\section*{저자 기여}
\textbf{설인환:} 연구 착상, 방법론, 소프트웨어, 검증, 정형 분석, 조사, 데이터
큐레이션, 원고 작성(초고), 원고 검토 및 편집, 시각화, 연구비 수주.
% NOTE(투고): 공저자 추가 시 위 기여(CRediT) 항목을 확장.

\section*{선언}

\paragraph{윤리적 고려사항.} 해당 없음(인간 참여자, 인체 데이터, 인체 조직,
동물을 포함하지 않음).

\paragraph{연구 참여 동의.} 해당 없음.

\paragraph{출판 동의.} 해당 없음.

\paragraph{이해상충 선언.}
저자는 본 논문의 연구, 저작 및 출판과 관련하여 잠재적 이해상충이 없음을 선언한다.

\paragraph{연구비 지원.}
본 연구는 정부(과학기술정보통신부)의 재원으로 한국연구재단의 지원을 받아
수행되었다(NRF-2022R1A2C1010072).

\paragraph{데이터 가용성.}
% NOTE(투고): 아래 저장소를 생성하고 투고 전 public 으로 전환할 것.
%   복합재 드레이프 분할이 특허 출원 대상이면, 공개 전 공지예외 타이밍
%   (삼부작 체크리스트 E절)을 먼저 확인.
본 연구 결과를 뒷받침하는 드레이프 필드 코드, 9종 메쉬 분할 캐시, 벤치마크 및
평가 스크립트는 \url{https://github.com/cfms-lab/SFTFComposite_2026} 에서
공개된다. 본 연구에 사용한 제3자 메쉬는 각 출처의 라이선스에 따라 원 출처
(Thingi10K; Objaverse, CC-BY; 및 본문에 인용된 기타 공개 저장소)에서 획득해야 한다.

% =====================================================================
\appendix
\section{직물 패턴 2D 전개도 (실무용)}
\label{app:patterns}
% =====================================================================
본 부록은 본문 응용 사례의 각 드레이프 분할을 \emph{검토용 2D 패턴 초안}으로 전개한
것이다. 이는 1차 배치 초안이며 곧바로 쓰는 재단 파일이 아니다 --- 실제 제조 패턴이 되려면
시접(seam allowance), 상세 섬유 배향(grain) 사양, 제조 가능한 최소 폭, 명시적 다트 처리,
네스팅 제약이 더해져야 한다. 각 그림에서 \textbf{왼쪽}은 본문과 동일한 3D 드레이프
분할 결과이고, \textbf{오른쪽}은 그에 대응하는 2D 패턴이다. 패치마다 ARAP(stretch 최소화)\footnote{ARAP
전개가 실패하는 패치는 LSCM(등각)으로 대체하며, 매우 큰 패치는 전개 전에 단순화(decimation)
한다. ARAP는 일반 edge-length stretch를 줄이는 근사이며, warp/weft 두 축의 비신장성과
전단만 허용하는 trellis kinematics를 명시적으로 강제하지는 않는다.} 전개로 평면화하고,
패턴의 convex hull 재단선을 충돌 polygon으로 삼아 고정 폭 직물
롤 위에 최적 배치(nesting)하였다. 이때 \emph{섬유 결(grain) 방향을 보존}하기 위해 조각은
회전하지 않는다. 별도 표기가 없으면 dimension이 없는 메쉬 전개도는 탄소 직물 폭 100 cm에
맞추어 정규화하였다. 각 조각의 색은 왼쪽 3D 패치 색과 동일하며, 검은 화살표는 marker의 긴 축,
즉 직물 길이 방향의 식서(grain/warp) 방향을 나타낸다. 점선 사각형은 직물 롤에서 사용된 marker 영역이다.
각 조각 바깥의 가는 회색 점선 곡선은 재단이 쉽도록 단순화한 패턴 convex hull 재단선이다.
평면화 시 나타나는 \emph{접힘$\cdot$겹침}은 그 패치가 발전 불가능(다트 필요)함을 그대로
드러내는 신호이며, 면적이 0이거나 재단 가능한 최소 크기 미만인 미세 조각은 생략하였다.

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
  자동차 차체 ($\approx$4.4\,m, 축소)
\end{minipage} &
\begin{minipage}{0.486\linewidth}\centering
  \includegraphics[width=0.47\linewidth,height=0.17\textheight,keepaspectratio]{App_obj_yacht.png}\hfill
  \includegraphics[width=0.47\linewidth,height=0.17\textheight,keepaspectratio]{App_obj_yacht_pattern.png}\\[-1pt]
  요트 hull ($\approx$12\,m, 축소)
\end{minipage}
\end{tabular}
  \caption{응용 사례 패턴 갤러리. 각 칸에서 왼쪽은 3D 드레이프 분할이고 오른쪽은 대응하는
  2D 직물 패턴이다. 칸 아래의 실제 평균 크기는 물체 스케일의 참고값이며, 여기서는 작은 지면에서도
  패턴 형상을 읽을 수 있도록 각 전개도를 칸별로 정규화해 크게 표시하였다. 모든 패턴은 100 cm
  직물 롤을 가정해 네스팅하되, 재단 손실을 줄이는 일반적인 marker 배치처럼 조각들을 왼쪽 edge
  쪽으로 모아 배치한다. 따라서 이 그림은 형상과 조각 배치를 비교하기 위한 가독성 중심 갤러리이고,
  서로 다른 물체 사이의 절대 크기 비교 도판은 아니다. 기존 장기, Nefertiti, 조개껍데기, 자동차
  차체, 요트 hull 부록 그림을 하나의 A4 페이지로 병합하였다.}
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
  {\small (a) 대칭성을 적용하지 않은 분할과 flattening (100 cm 롤 폭)}\\[4pt]
\begin{tabular}{@{}c@{\hspace{0.025\linewidth}}c@{\hspace{0.025\linewidth}}c@{}}
  \includegraphics[width=0.20\linewidth,height=0.18\textheight,keepaspectratio]{App_obj_airplane_b787.png} &
  \includegraphics[width=0.20\linewidth,height=0.18\textheight,keepaspectratio]{App_obj_airplane_b787_shear.png} &
  \includegraphics[width=0.36\linewidth,height=0.18\textheight,keepaspectratio]{App_obj_airplane_b787_pattern_roll100.png}
\end{tabular}\\[-2pt]
  {\small (b) 좌우 대칭 분할 + 직물 롤 폭 100 cm}\\[4pt]
\begin{tabular}{@{}c@{\hspace{0.025\linewidth}}c@{\hspace{0.025\linewidth}}c@{}}
  \includegraphics[width=0.20\linewidth,height=0.18\textheight,keepaspectratio]{App_obj_airplane_b787.png} &
  \includegraphics[width=0.20\linewidth,height=0.18\textheight,keepaspectratio]{App_obj_airplane_b787_shear.png} &
  \includegraphics[width=0.36\linewidth,height=0.18\textheight,keepaspectratio]{App_obj_airplane_b787_pattern_roll50.png}
\end{tabular}\\[-2pt]
  {\small (c) 좌우 대칭 분할 + 직물 롤 폭 50 cm 제약}
  \caption{Boeing 787 드레이프 분할과 2D 패턴 배치 변형. 각 행에서 왼쪽은 3D 드레이프
  분할, 가운데는 상대 shear-severity field로 색칠한 동일 3D 형상, 오른쪽은 대응하는 2D
  패턴 배치이다. (a)는 \textbf{대칭성을 적용하지 않은} 기준 분할로, 좌우 패치가 서로 다르게
  나뉘어 펼친 패턴도 비대칭이다. (b)와 (c)는 \textbf{좌우 대칭성을 분할 알고리즘 자체에
  적용}하여(왼쪽 열의 색상 패치가 기체 중심면을 기준으로 좌우 대칭으로 나뉜다) 펼친 2D 패턴도
  자연히 좌우 대칭을 반영한다. 검은 화살표는 marker의 긴 축, 즉 직물 길이 방향의 식서 방향을 나타내며, 가는 회색
  점선 곡선은 convex hull 재단선이다. (a)와 (b)는 100 cm 직물 롤 폭을 사용하여 대칭성 유무를
  직접 대비하며, (c)는 더 좁은 50 cm 롤 폭 제약을 사용한다.}
  \label{app:fig-airplane-pattern-variants}
\end{figure}

\clearpage

% ---- 참고문헌 -------------------------------------------------------
\bibliographystyle{plainnat}
\bibliography{references}

\end{document}

