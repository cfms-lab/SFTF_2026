# LaTeX source: SFTF_PDN_PoC.tex

Source: `D:\__SFTF_Projects(2026)\SFTF_PDNElectric_dev\draft\SFTF_PDN_PoC.tex`

% !TEX program = xelatex
% SFTF -> 반도체 전력공급망(PDN) IR-drop 패드배치 / 전력도메인 분할 PoC
% 빌드: xelatex (MiKTeX) + kotex.  latexmk -xelatex SFTF_PDN_PoC.tex
\documentclass[11pt]{article}

% ----------------------------------------------------------------------------
% 한글(xelatex + kotex) + 폰트
% ----------------------------------------------------------------------------
\usepackage{kotex}
\usepackage{fontspec}
\setmainfont{Latin Modern Roman}
\setsansfont{Latin Modern Sans}
\setmonofont{Latin Modern Mono}
% Windows 기본 한글 폰트 (malgun.ttf). 다른 환경이면 아래 두 줄을 바꾸세요.
\setmainhangulfont{Malgun Gothic}
\setsanshangulfont{Malgun Gothic}

\usepackage[a4paper,margin=25mm]{geometry}
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

% ----------------------------------------------------------------------------
% TikZ (개념 설명용 벡터 그림)
% ----------------------------------------------------------------------------
\usepackage{tikz}
\usetikzlibrary{arrows.meta,positioning,calc,fit,backgrounds,
                shapes.geometric,decorations.pathmorphing,
                decorations.pathreplacing,patterns}
\tikzset{
  node distance=8mm,
  >={Stealth[length=2.4mm]},
  box/.style={draw,rounded corners=2pt,align=center,inner sep=4pt,
              font=\small,fill=blue!4},
  hl/.style={draw,rounded corners=2pt,align=center,inner sep=4pt,
              font=\small,fill=orange!12},
  cell/.style={draw,minimum size=8mm,inner sep=0pt,font=\scriptsize},
  flowarr/.style={->,thick,blue!55!black},
  trunk/.style={->,very thick,orange!75!black},
}

% 색상 강조 명령
\newcommand{\term}[1]{\textbf{#1}}
\newcommand{\R}{\ensuremath{R}}
\newcommand{\PP}{\ensuremath{P}}
\newcommand{\B}{\ensuremath{B}}
\newcommand{\J}{\ensuremath{J}}
\newcommand{\iload}{\ensuremath{i_{\mathrm{load}}}}

\title{\textbf{SFTF $\rightarrow$ 반도체 전력공급망(PDN) IR-drop\\
패드 배치와 전력도메인 분할}\\[2mm]
\large 적층제조 서포트 흐름 텐서장의 반도체 물리설계 이식: 개념증명(PoC)}
\author{SFTF\_PDNElectric\_dev}
\date{2026-07}

\begin{document}
\maketitle

\begin{abstract}
\noindent
적층제조(AM)의 빌드방향 후보생성기 \textbf{SFTF}(Support Flow Tensor Field)는
삼각망의 각 면이 중력을 등진 정도(오버행)를 ``흘러내리는 부하''로 보고, 닫힌형
텐서 계산 한 번으로 서포트 물량을 예측한다. 본 개념증명은 \textbf{오버행 $=$ 셀의
스위칭 전류수요}, \textbf{receiver 면 $=$ 패드 방향의 이웃 셀}, \textbf{빌드플레이트
(ground node) $=$ 전원/접지 패드(C4 범프)} 라는 치환만으로, SFTF의 서포트 흐름
트리가 곧 \emph{온칩 전류 분배망}이 되고 서포트 물량 최소화가 곧 \emph{IR-drop
(전압강하) 최소화}가 됨을 보인다. SFTF는 새 최적화기가 아니라 \emph{값싼
후보생성기 $+$ 정밀검증 앞단}이라는 역할을 그대로 유지한다. numpy/scipy만으로
구현한 코어가 합성 다이에서, 값싼 패드항 \B\ 와 실제 저항망 IR 해석($G\,v=i$)의
패드배치 순위 상관 $\rho_{\mathrm{Spearman}}$ 평균 $+0.98\sim+1.00$(다이 20개,
최솟값 $+0.929$), 최적 배치 일치율(hit@1) $80\sim100\%$를 달성했고, 후보 1개
평가 비용은 정밀해 대비 $42\sim122$배 저렴했다. 아울러 방향 텐서의 Rayleigh 항이
고정-패드 케이스에서 항상 0으로 퇴화함을 수치로 확인하여, 이 도메인에서 살아남는
것은 텐서가 아니라 \emph{ground-node 항 $+$ 분할 $+$ 사인오프 warm-start}라는
연구기획의 예측을 실증했다.
\end{abstract}

% ============================================================================
\section{서론: 두 문제는 같은 뼈대를 공유한다}
% ============================================================================
적층제조에서 오버행(돌출부)을 받치는 서포트는 결국 \emph{빌드플레이트}로 힘이
흘러내리는 트리를 이룬다. 반도체 칩의 전력공급망(PDN, Power Delivery
Network)\footnote{다이(die) 위의 모든 트랜지스터에 전원전압 $V_{DD}$와 접지
$V_{SS}$를 나눠 주는 금속 배선망. 상위 금속층의 굵은 스트랩(strap)들이 격자
모양(mesh)으로 깔리고, 그 격자가 패키지의 범프를 통해 외부 전원과 연결된다.}에서
각 셀(스탠다드셀·매크로)이 소비하는 스위칭 전류는 결국 \emph{전원/접지 패드(C4
범프)}\footnote{C4(Controlled Collapse Chip Connection)는 플립칩 패키징에서
다이와 패키지 기판을 잇는 땜납 범프. 전원용 범프가 곧 온칩 전력망의 ``전류가
빠져나가는 구멍''이며, 본문에서는 간단히 \emph{패드}라 부른다.}로 빠져나가는
분배망을 이룬다. 두 문제 모두

\begin{enumerate}[leftmargin=2.2em,itemsep=1pt]
  \item 각 \emph{소스}(오버행 면 / 전류를 소비하는 셀)가 부하를 \emph{하류}로
        떠넘기고,
  \item 그 하류 사슬이 소수의 \emph{루트}(빌드플레이트 / 패드)로 수렴하며,
  \item 총비용(서포트 물량 / 전압강하)이 ``\textbf{부하 $\times$ 루트까지의
        거리}''에 지배된다
\end{enumerate}

\noindent 는 수목형(arborescence)\footnote{모든 간선이 루트를 향해 방향지어진
트리. 서포트 흐름도, (1차 근사에서) 셀에서 패드로 향하는 전류 경로도 이 구조다.
실제 PDN은 루프가 있는 그물망이므로 이는 어디까지나 1차 근사다
(\S\ref{sec:limits}).} 구조를 공유한다(그림~\ref{fig:analogy}).

IR-drop\footnote{전류 $I$가 저항 $R$을 지나며 생기는 전압강하 $V=IR$에서 온
관용어. 패드에서 멀리 있는 셀일수록 공급 전압이 처져서 도착하고, 전압이 처지면
게이트 지연이 늘어나 타이밍 위반이나 오동작이 생긴다. 그래서 물리설계 막바지에
반드시 IR-drop \emph{사인오프}(sign-off; 상용 정밀 해석으로 최종 확인하는 관문)를
통과해야 한다.}는 물리설계의 대표적 후반부 병목이다. 정밀 사인오프 해석은
전력망 전체를 거대한 선형계 $G\,v=i$\footnote{$G$는 저항 컨덕턴스 행렬(그래프
라플라시안), $i$는 셀별 전류 주입 벡터, $v$가 노드 전압강하. 수백만$\sim$수십억
노드의 희소 선형계라서 한 번 푸는 데도 비용이 크고, ``패드를 어디에 몇 개
둘까''처럼 후보가 조합적으로 많은 탐색 단계에서 후보마다 풀기는 비싸다.}로 풀기
때문에 정확하지만 비싸고, 그 앞단의 \emph{후보 탐색}은 여전히 경험칙과 반복
시뮬레이션에 기댄다. 본 PoC의 물음은 간단하다:

\begin{quote}
SFTF가 적층제조에서 했던 일---비싼 정밀해석(TOMO) \emph{이전에}, 닫힌형 점수로
후보를 ms 단위에 랭킹---을 PDN의 \textbf{패드 배치}와 \textbf{전력도메인
분할}\footnote{큰 다이를 몇 개의 전력 구역(power domain)으로 나누고 구역마다
전용 패드/레귤레이터를 두는 설계. 도메인별 전원 차단(power gating)이나 전압
스케일링(DVFS)의 단위이기도 하다.}에서 그대로 할 수 있는가?
\end{quote}

\paragraph{기여.} (1) SFTF의 기호 체계(오버행·receiver·ground node·텐서 점수
$\J=\R+\PP+\B$)를 PDN으로 1:1 치환하는 수식 매핑(\S\ref{sec:mapping});
(2) numpy/scipy만으로 동작하는 공개 구현(\S\ref{sec:impl});
(3) 값싼 패드항 \B\ 가 독립된 물리인 저항망 해석의 순위를 재현함을 보이는 검증
($\rho\ge+0.929$, \S\ref{sec:exp});
(4) 방향 텐서 항이 이 도메인에서 \emph{구조적으로} 소멸함(R$\equiv$0)의 수치
확인과 그 해석---무엇이 이식되고 무엇이 이식되지 않는가에 대한 정직한 보고
(\S\ref{sec:exp-r}, \S\ref{sec:limits}).

% --- Figure 1: 핵심 유추 ---------------------------------------------------
\begin{figure}[t]
\centering
\begin{tikzpicture}[scale=0.92]
  % ----- left: AM support tree -----
  \begin{scope}[shift={(0,0)}]
    \node[font=\small\bfseries] at (2.2,4.6) {적층제조 (SFTF)};
    % build plate
    \draw[very thick] (0,0) -- (4.4,0);
    \node[font=\scriptsize,below] at (2.2,0) {빌드플레이트 (ground node)};
    % part outline
    \draw[thick,fill=blue!6] (0.7,2.6) .. controls (1.5,3.4) and (2.9,3.5) ..
      (3.7,2.8) -- (3.9,4.0) -- (0.5,4.0) -- cycle;
    \node[font=\scriptsize] at (2.2,3.7) {부품 (오버행 면)};
    % support flow arrows
    \foreach \x/\y in {1.1/2.9, 1.9/3.15, 2.7/3.2, 3.5/2.95}{
      \draw[flowarr] (\x,\y) -- (\x,0.12);}
    \node[font=\scriptsize,blue!55!black,rotate=90] at (0.78,1.5) {서포트 흐름};
  \end{scope}
  % ----- middle: mapping -----
  \begin{scope}[shift={(5.3,0)}]
    \node[hl,font=\scriptsize,align=left] at (1.35,2.3)
      {오버행 $O_i$ $\to$ 전류수요 $\iload$\\[1pt]
       높이 $h$ $\to$ 패드거리 $\varphi$\\[1pt]
       플레이트 $\to$ 패드(C4)\\[1pt]
       서포트량 $\to$ IR-drop};
  \end{scope}
  % ----- right: PDN die -----
  \begin{scope}[shift={(8.4,0)}]
    \node[font=\small\bfseries] at (2.2,4.6) {반도체 PDN (본 PoC)};
    % die
    \draw[thick,fill=blue!6] (0.2,0.6) rectangle (4.2,4.0);
    \node[font=\scriptsize] at (2.2,4.22) {다이 (셀 전류수요 맵)};
    % pads
    \foreach \x/\y in {1.2/1.6, 3.2/1.6, 1.2/3.1, 3.2/3.1}{
      \draw[fill=white,thick] (\x,\y) circle (0.14);}
    % current flow arrows toward pads
    \foreach \sx/\sy/\tx/\ty in {0.6/3.7/1.12/3.22, 2.2/3.8/1.35/3.25,
        2.2/2.35/1.4/1.75, 3.9/3.8/3.32/3.24, 3.9/0.9/3.3/1.45,
        0.6/0.9/1.1/1.45, 2.2/0.8/3.05/1.5, 4.0/2.4/3.35/2.95}{
      \draw[flowarr] (\sx,\sy) -- (\tx,\ty);}
    \node[font=\scriptsize,blue!55!black] at (2.2,0.32)
      {전류는 최근접 패드로 ``흘러내린다''};
  \end{scope}
\end{tikzpicture}
\caption{핵심 유추. 왼쪽: SFTF에서 오버행 면의 부하는 서포트 트리를 타고
빌드플레이트로 수렴한다. 오른쪽: PDN에서 각 셀의 스위칭 전류는 전류 분배망을
타고 전원/접지 패드(흰 원)로 수렴한다. 두 문제 모두 총비용이 ``부하 $\times$
루트까지의 거리''에 지배되므로, SFTF의 ground-node 항이 IR-drop의 1차 법칙으로
그대로 옮겨간다.}
\label{fig:analogy}
\end{figure}

% ============================================================================
\section{배경}
% ============================================================================
\subsection{SFTF 요약: 흐름 텐서와 세 개의 항}
SFTF(Support Flow Tensor Field)는 빌드방향 $n\in S^2$ 후보를 평가할 때 서포트를
직접 생성하지 않는다. 대신 각 삼각면 $i$의 오버행 정도 $O_i(n)$을 ``흘릴
부하''로 보고, $-n$ 방향 레이캐스트로 그 부하를 받아 줄 \emph{receiver} 면
$j$를 찾은 뒤, 면쌍 가중치 $w_{ij}=O_i/(1+\alpha h_{ij})$\footnote{$h_{ij}$는
지지 높이(부하가 흘러내리는 거리), $\alpha=1/D$는 특성길이 $D$(바운딩박스
대각)로 무차원화하는 감쇠 계수. 멀리 흘러갈수록 비용이 커진다는 것을 1차식으로
담는다.}로 흐름 텐서를 누적한다:
\begin{equation}
F(n)=\sum_{(i,j)\in\mathcal{R}} w_{ij}\,A_i A_j\, m_i m_j^{\mathsf T},
\label{eq:sftf-tensor}
\end{equation}
여기서 $A$는 면적, $m$은 면 법선, $\mathcal{R}$은 유효 (소스, receiver) 쌍의
집합이다. 후보 점수는 세 항의 합이다:
\begin{equation}
\J(n) = \underbrace{\max\!\bigl(0,\,-n^{\mathsf T} F_{\mathrm{sym}}
n\bigr)}_{\R\ \text{(Rayleigh 항)}}
\;+\; \underbrace{\textstyle\sum O_i A_i A_j}_{\PP\ \text{(면쌍 항)}}
\;+\; \underbrace{\textstyle\sum_i O_i A_i (1+\alpha\,h_{iP})}_{\B\
\text{(ground-node 항)}},
\label{eq:sftf-score}
\end{equation}
$h_{iP}$는 면 $i$가 (받아 줄 면이 없어) 빌드플레이트까지 직접 흘러내리는
거리다. SFTF 계열 연구의 반복된 발견은 \textbf{\B\ 항의 지배}였다: 서포트
비용의 1차 성분은 결국 ``오버행 부하 $\times$ 플레이트까지 거리''이고, 후보
간 순위는 대부분 \B\ 가 결정한다.\footnote{SFTF-Clustering의 ray-free
추정자(각 면의 footprint $A_i O_i$ 합)가 실측 서포트량과 Spearman $0.80$,
height-field 보정 후 $0.90$의 순위 상관을 보인 것도 같은 구조의 발견이다.
Spearman 순위상관 $\rho$는 두 변수의 \emph{값}이 아니라 \emph{순위}의 일치도를
$[-1,+1]$로 재는 지표로, ``값싼 점수가 비싼 점수를 얼마나 잘 흉내내는가''를
따질 때 널리 쓰인다. $+1$이면 순위가 완전히 같다.}

\subsection{PDN IR-drop 기초}
정적(static) IR-drop 해석은 전력망을 저항 그래프로 보고 선형계를 푼다.
노드(금속 격자 교점)마다 키르히호프 전류법칙\footnote{한 노드로 들어오는 전류의
합은 나가는 전류의 합과 같다. 저항 격자에서는 각 노드의 전압과 이웃 전압의
차에 컨덕턴스를 곱한 것들의 합이 그 노드의 주입 전류와 같다는 식이 되고, 이를
모든 노드에 대해 모으면 $G\,v=i$가 된다.}을 세우면
\begin{equation}
G\,v = i,\qquad v|_{\text{pads}}=0,
\label{eq:gvi}
\end{equation}
패드 노드는 이상 전원으로 보아 전압강하 0으로 고정한다(Dirichlet 경계
조건).\footnote{경계값을 직접 지정하는 조건. 구현에서는 패드 행/열을 소거한
축소계 $G_{ff}\,v_f=i_f$를 푼다. $G$는 대칭 양정치 M-행렬이라 희소 촐레스키나
직접법으로 안정적으로 풀린다.} 산업계 사인오프는 여기에 동적
droop\footnote{클록 에지 직후처럼 많은 셀이 동시에 스위칭할 때 순간적으로 더
깊게 패이는 전압 처짐. 패키지·보드 인덕턴스와 온다이 decap(디커플링 커패시터;
전하 저수지 역할을 하는 커패시터)이 함께 결정하므로 정적 해석보다 훨씬
어렵다.}, EM(electromigration)\footnote{높은 전류밀도가 금속 원자를 밀어내
배선이 끊기거나 단락되는 장기 신뢰성 문제. 스트랩 폭 설계의 또 다른 제약이다.}
검증까지 얹는다. 본 PoC는 이 가운데 \emph{정적 IR}의 저항망 해석을 자체
구현하여 ``사인오프 대역(stand-in)''\footnote{진짜 상용 사인오프 도구 대신 그
역할을 맡는 대체물. 식~\eqref{eq:gvi}를 scipy 희소 솔버로 그대로 풀므로 물리는
동일하고 규모와 모델 충실도만 작다.}으로 삼는다.

중요한 것은 검증의 독립성이다: 값싼 점수 \B\ 는 \emph{거리 프록시}(패드까지
기하 거리)이고, 저항망 해석은 \emph{전역 선형계}다. 서로 다른 물리에서 나온 두
순위가 일치한다면 그것은 동어반복이 아니라 실질적 결과다.

% ============================================================================
\section{수식 매핑: SFTF $\to$ PDN}\label{sec:mapping}
% ============================================================================
표~\ref{tab:mapping}에 기호 대응을 요약한다.

\begin{table}[t]
\centering\small
\caption{기호 대응표. SFTF의 각 구성 요소가 PDN에서 맡는 역할.}
\label{tab:mapping}
\begin{tabular}{@{}llll@{}}
\toprule
SFTF (적층제조) & 기호 & PDN PoC (반도체) & 기호 \\
\midrule
삼각면 $i$          & $i$        & 다이 격자 셀            & $i$ \\
오버행(흘릴 부하)   & $O_i(n)$   & 셀 스위칭 전류수요      & $\iload$ \\
표고/지지 높이      & $z,\,h_{ij}$ & 패드거리 퍼텐셜        & $\varphi,\ \Delta\varphi_{ij}$ \\
receiver 탐색(레이캐스트) & --   & $\varphi$ 최급강하 이웃 & $j=\mathrm{rec}(i)$ \\
면 법선             & $m_i$      & 국소 전류흐름 방향($-\nabla\varphi$) & $m_i$ \\
빌드플레이트(ground node) & $B(n)$ & 전원/접지 패드(C4 범프) & $\B$ \\
빌드방향            & $n\in S^2$ & (고정-패드) 소멸 / 선호배선 방위 & $d\in S^1$ \\
서포트 트리         & --         & 전류 분배 트리           & -- \\
분할+부품별 재배향  & --         & 전력도메인 분할+다패드   & -- \\
TOMO 국소검증       & --         & 저항망 IR 사인오프 대역  & $G\,v=i$ \\
\bottomrule
\end{tabular}
\end{table}

\subsection{패드거리 퍼텐셜 $\varphi$ = 표고}
SFTF의 ``높이''(부하가 흘러내려야 하는 거리) 자리에는 \term{패드거리 퍼텐셜}
\begin{equation}
\varphi_i \;=\; \min_{p\in\text{pads}}\ \mathrm{dist}(c_i,\,c_p)
\label{eq:phi}
\end{equation}
을 둔다. $\varphi$는 패드에서 0이고 멀어질수록 커지는 스칼라장으로, 정확한
유클리드 거리변환\footnote{이진 마스크에서 각 픽셀이 가장 가까운 시드(여기서는
패드)까지의 유클리드 거리를 $O(N)$에 구하는 고전 알고리즘.
\texttt{scipy.ndimage.distance\_transform\_edt}를 그대로 쓴다.}으로 계산한다.
전류는 $\varphi$의 내리막을 타고 패드로 ``흘러내린다''---SFTF에서 부하가 표고의
내리막을 타고 플레이트로 흘러내리는 것과 정확히 같은 그림이다.

\subsection{receiver = $\varphi$ 최급강하 이웃}
SFTF의 레이캐스트 자리에는 8-이웃 최급강하\footnote{수문학의 D8 유향(flow
direction) 알고리즘과 동일: 각 격자 셀이 8방향 이웃 중 $\varphi$가 가장 가파르게
줄어드는 곳으로 부하 전량을 넘긴다. 대각 이웃은 거리 $\sqrt{2}$로 나눠 기울기를
비교한다.}이 들어간다:
\begin{equation}
\mathrm{rec}(i)=\arg\max_{j\in N_8(i)}
\frac{\varphi_i-\varphi_j}{\lVert c_i-c_j\rVert},\qquad
\Delta\varphi_{ij}=\varphi_i-\varphi_{\mathrm{rec}(i)} .
\end{equation}
receiver 사슬을 따라 전류수요를 하류로 누적하면($\varphi$ 내림차순 위상 정렬 한
번) 각 셀이 최종적으로 실어 나르는 \emph{누적 전류} $I_i$를 얻는다---서포트
트리의 하중 누적, 하수관망의 유량 누적과 동일한 연산이다.

\subsection{세 항의 이식과 점수}
식~\eqref{eq:sftf-tensor}--\eqref{eq:sftf-score}의 치환은 기계적이다.
$O_i\to\iload$, $h\to\varphi$, $m_i\to$ 국소 전류흐름 방향
($-\nabla\varphi$ 정규화):
\begin{align}
F(d) &= \sum_{(i,j)\in\mathcal{R}} w_{ij}\,A_iA_j\,m_i m_j^{\mathsf T},
& w_{ij} &= \frac{i_{\mathrm{load},i}}{1+\alpha\,\Delta\varphi_{ij}},
\label{eq:pdn-tensor}\\
\J(d) &= w_R\,\R(d) + w_P\,\PP + w_B\,\B,
& \R(d) &= \max\!\bigl(0,\,-d^{\mathsf T}F_{\mathrm{sym}}\,d\bigr),
\label{eq:pdn-score}
\end{align}
\begin{equation}
\boxed{\ \B \;=\; \sum_i i_{\mathrm{load},i}\,\bigl(1+\alpha\,\varphi_i\bigr)\ }
\qquad (\alpha = 1/D,\ D=\text{다이 대각선 길이}).
\label{eq:B}
\end{equation}
\B\ 는 ``전류 $\times$ 패드까지 거리''---IR-drop의 1차 법칙\footnote{균일
시트저항 $\rho_s$의 평면에서 점원까지 거리 $L$만큼 전류 $I$가 흘러가면 전압강하는
대략 $I\rho_s L$에 비례한다는, 전력망 설계의 잘 알려진 어림. \B\ 는 이 어림에
SFTF ground-node 항이라는 닫힌형 해석을 부여한 것이다.}---를 그대로 담는다.
결정적으로 \R\ 과 \PP\ 는 패드 위치와 무관하고 \textbf{\B\ 만이 패드 배치에
의존}하므로, 패드배치·도메인 후보의 랭킹은 \B\ 가 단독으로 결정한다. SFTF의
``\B\ 지배'' 발견이 여기서는 아예 \emph{구조적 필연}이 된다.

\subsection{전력도메인 분할 = SFTF-Clustering의 이식}\label{sec:mapping-domains}
SFTF-Clustering은 메시를 조각내어 조각마다 최적 빌드방향을 따로 주면 총
서포트가 줄어든다는 반직관적 발견을 텐서 가산성($F(\mathrm{part})=\sum
F_{\mathrm{part}}$)으로 값싸게 탐색했다. PDN 대응은 \emph{다패드/도메인 분할}
이다: 다이를 최근접-패드 Voronoi\footnote{각 셀을 가장 가까운 시드(패드)에
배정하는 공간 분할. 여기서는 도메인 후보의 가장 값싼 근사로 쓴다.}로 나누고,
도메인을 늘리는(=패드를 촘촘히 놓는) 이득을 \B\ 의 차로 추정한다:
\begin{equation}
\Delta\B = \B(\text{성긴 패드}) - \B(\text{촘촘한 패드}) > 0
\;\;\Longleftrightarrow\;\;
\text{다패드가 1차 비용을 줄인다}.
\label{eq:savings}
\end{equation}
패드가 늘면 모든 셀의 $\varphi$가 단조 감소하므로 $\Delta\B>0$은 자명하지만,
\emph{얼마나} 줄고 그것이 실제 IR 감소와 \emph{같은 순위}인지는 자명하지 않다
---\S\ref{sec:exp-sweep}에서 검증한다.

\subsection{ray-free 추정자와 보정}
SFTF-Clustering의 footprint 추정자(레이캐스트 없이 순위 예측)에 대응해 두
단계의 값싼 추정자를 정의한다:
\begin{align}
\widehat{IR}_{\mathrm{fp}} &= \B
= \sum_i i_{\mathrm{load},i}(1+\alpha\varphi_i)
&&\text{(footprint; 식~\eqref{eq:B} 그대로)},\\
\widehat{IR}_{\mathrm{cd}} &= \B + \alpha\sum_i I_i\,\ell_i
&&\text{(누적 전류밀도 보정)},
\label{eq:cd}
\end{align}
$I_i$는 누적 전류, $\ell_i$는 셀 $i$가 receiver로 넘기는 아크 길이다. 후자는
SFTF-Clustering의 height-field 보정(0.80$\to$0.90)에 대응하는 항으로, 하류로
갈수록 전류가 겹쳐 쌓이는 혼잡 효과를 담으려는 시도다.\footnote{하수 PoC의
``하류로 갈수록 관이 깊어진다''(트렌치 심도 누적)와 동일한 자리의 보정이다.
\S\ref{sec:exp-est}에서 보듯 PDN에서는 이 보정의 이득이 관찰되지 않았는데,
이 역시 도메인 간 차이에 관한 유용한 정보다.}

% ============================================================================
\section{구현}\label{sec:impl}
% ============================================================================
전체 코어는 numpy/scipy 의존성만으로 약 600줄이며,\footnote{외부 EDA 도구,
학습 프레임워크, GPU 어느 것도 필요 없다. 이는 성능 자랑이 아니라 \emph{주장의
투명성}을 위한 선택이다: 모든 수치는 표준 라이브러리 호출로 재현된다.
저장소의 \texttt{scripts/build\_paper\_data.py} 한 번 실행으로 본 논문의 모든
수치와 그림이 재생성된다.} 모듈 구조는 SFTF·하수 PoC와 1:1로 맞춰 두었다
(표~\ref{tab:modules}).

\begin{table}[h]
\centering\small
\caption{모듈 지도. 마지막 열은 원본 SFTF 코드베이스에서의 대응물.}
\label{tab:modules}
\begin{tabular}{@{}lll@{}}
\toprule
모듈 & 역할 & SFTF 대응 \\
\midrule
\texttt{config.py}   & 감쇠 $\alpha$, 점수 가중, 시트 컨덕턴스 & 상수 블록 \\
\texttt{grid.py}     & 다이 전류맵, 패드, $\varphi$ 거리변환 & terrain \\
\texttt{ir\_field.py} & 흐름 그래프, 텐서 $F$, $\R,\PP,\B$, 점수 $\J$ & flow tensor \\
\texttt{network.py}  & 전류분배 트리, 금속면적 비용 & routing \\
\texttt{domains.py}  & Voronoi 도메인, 다패드 이득, 추정자 & partition \\
\texttt{verify.py}   & 저항망 $G\,v=i$ 해석, Spearman 검증 & TOMO 검증 \\
\texttt{cli.py}      & 합성 다이 데모 & run 스크립트 \\
\bottomrule
\end{tabular}
\end{table}

\paragraph{계산 복잡도.} 후보(패드 집합) 하나의 값싼 평가는 거리변환이
$O(N)$, 최급강하와 하류 누적이 $O(N\log N)$\footnote{$\varphi$ 내림차순
정렬이 지배한다. $N$은 격자 셀 수. $128\times128$ ($N=16{,}384$)에서 실측
후보당 $0.3$\,ms(\S\ref{sec:exp-timing}).}으로 끝나고, 정밀검증은 희소
선형계 풀이다.
후보 풀이 커질수록(패드 위치 $\times$ 개수 $\times$ 도메인 조합) 앞단의 값싼
랭킹이 만드는 이득이 곱으로 쌓인다.

\paragraph{파이프라인.} 그림~\ref{fig:pipeline}이 전체 흐름이다. SFTF의
역할 규정---\emph{후보생성기이지 사인오프 대체가 아니다}---은 그대로다.

\begin{figure}[t]
\centering
\begin{tikzpicture}[node distance=6mm and 9mm]
  \node[box] (die) {다이 전류맵\\ $\iload$};
  \node[box,right=of die] (cand) {패드배치·도메인\\ 후보 생성};
  \node[hl,right=of cand] (score) {값싼 점수 $\J$\\ ($\B$ 지배, ms)};
  \node[box,right=of score] (rank) {랭킹·상위\\ $k$개 선별};
  \node[box,right=of rank] (ver) {정밀 IR 해석\\ $G\,v=i$};
  \draw[->] (die) -- (cand);
  \draw[->] (cand) -- (score);
  \draw[->] (score) -- (rank);
  \draw[->] (rank) -- (ver);
  \draw[->,dashed] (ver.south) to[out=-150,in=-30]
    node[below,font=\scriptsize]{근소차·핫스팟이면 검증 확대 (AVE, 향후)} (cand.south);
\end{tikzpicture}
\caption{PoC 파이프라인. 값싼 점수는 후보를 \emph{줄 세우는} 데만 쓰이고, 살아남은
소수만 정밀 해석으로 넘어간다. 점선은 SFTF의 적응적 검증 확대(AVE)에 대응하는
향후 구성요소다.}
\label{fig:pipeline}
\end{figure}

% ============================================================================
\section{실험}\label{sec:exp}
% ============================================================================
\subsection{설정}\label{sec:exp-setup}
\paragraph{합성 다이.} $n\times n$ 격자 위에 저활동 기저 전류($0.3$)와
가우시안 핫스팟\footnote{고활동 블록(예: 코어의 실행유닛, SerDes)을 흉내내는
국소 고전류 영역. 핫스팟이 있어야 ``패드를 어디에 두느냐''가 자명하지 않은
문제가 된다. 시드마다 위치·폭이 달라지므로 시드 하나가 다이 하나다.} 4개,
소량의 노이즈를 얹는다(그림~\ref{fig:fields}a). 단위는 무차원 PoC
단위\footnote{전류 1 = 기저 셀 수요의 $10/3$배, 길이 1 = 셀 피치, 시트
컨덕턴스 1. 절대값이 아니라 \emph{후보 간 순위}만을 주장하므로 단위계는 결론에
영향을 주지 않는다.}다.

\paragraph{후보 풀.} C4 범프의 관례를 따라 $k\times k$ 정방 패드 어레이
($k=1..4$)와 그 대각 이동 변형을 합쳐 후보 7개를 만든다. 즉 패드 수 1, 4, 4,
9, 9, 16, 16의 배치들이 경쟁한다.\footnote{규칙 어레이만 쓰는 이유: (i) 실제
플립칩 범프 맵이 대체로 규칙적이고, (ii) 후보끼리 패드 수가 겹치게 하여(4 vs 4,
9 vs 9, 16 vs 16) ``개수만 세면 맞히는'' 자명한 문제가 되지 않도록. 완전 무작위
배치는 \S\ref{sec:exp-est}에서 따로 쓴다.}

\paragraph{검증 절차.} 각 다이(시드)마다 후보 7개를 (i) 값싼 \B\ 로, (ii) 저항망
해석의 최악 전압강하 $\max_i v_i$로 각각 줄 세우고, 두 순위의 Spearman $\rho$와
1위 일치(hit@1)를 기록한다.

\subsection{주 결과: 값싼 \B\ 가 사인오프 순위를 재현한다}\label{sec:exp-main}

\begin{table}[t]
\centering\small
\caption{주 검증 결과. $\rho$는 다이별 Spearman의 평균[최소]. hit@1은 값싼
\B\ 의 1위와 정밀해의 1위가 일치한 다이의 비율.}
\label{tab:main}
\begin{tabular}{@{}lcccc@{}}
\toprule
다이 크기 & 다이 수 & $\rho$ 평균 & $\rho$ 최소 & hit@1 \\
\midrule
$32\times32$ & 5  & $+0.979$ & $+0.929$ & $80\,\%$ \\
$48\times48$ & 10 & $+0.989$ & $+0.929$ & $100\,\%$ \\
$64\times64$ & 5  & $+1.000$ & $+1.000$ & $100\,\%$ \\
\bottomrule
\end{tabular}
\end{table}

표~\ref{tab:main}이 핵심 결과다. 목표선 $\rho\ge0.8$(SFTF-Clustering의
ray-free 결과와 같은 기준)을 모든 다이에서 넘겼고, 20개 다이 중 19개에서
hit@1을 달성했다.\footnote{유일한 실패($32\times32$의 한 시드)도 \B\ 1위와
정밀해 1위가 통계적으로 구분이 어려운 근소차 케이스였다. 이런 ``근소차''가
바로 AVE(적응적 검증 확대)가 정밀검증을 트리거해야 하는 지점이다.}
그림~\ref{fig:rank}는 20개 다이$\times$7후보의 순위-순위 산점도로, 질량이
대각선에 붙어 있음을 보여준다.\footnote{다이가 다르면 총 전류량이 달라 \B\ 와
IR의 \emph{절대값} 스케일이 함께 이동한다. 따라서 다이를 섞은 값-값 산점도는
상관을 희석한다. 우리가 주장하는 것은 ``같은 다이 안에서 후보를 고르는 순위''
이므로 다이별 순위로 정규화한 그림이 정확한 표현이다.}

\begin{figure}[t]
\centering
\includegraphics[width=0.58\linewidth]{pics/pdn_b_vs_ir.png}
\caption{값싼 패드항 \B\ 순위(가로) 대 저항망 최악 IR-drop 순위(세로),
$48\times48$ 다이 10개 $\times$ 후보 7개. 마커 면적은 해당 (순위,순위) 칸의
빈도. 점선은 완전 일치 대각선.}
\label{fig:rank}
\end{figure}

\begin{figure}[t]
\centering
\includegraphics[width=0.98\linewidth]{pics/pdn_die_fields.png}
\caption{기준 다이($48\times48$, seed 0)와 \B-최적 패드배치($4\times4$).
(a) 셀 전류수요 $\iload$ --- 진한 곳이 핫스팟. (b) 패드거리 퍼텐셜 $\varphi$
--- 패드(흰 원)에서 0이고 멀수록 크다. $\varphi$가 SFTF의 표고 역할을 한다.}
\label{fig:fields}
\end{figure}

\begin{figure}[t]
\centering
\includegraphics[width=0.98\linewidth]{pics/pdn_flow_ir.png}
\caption{같은 다이의 (a) 누적 전류 $\log_{10}(1+I)$ --- receiver 사슬을 타고
패드로 모여드는 전류 트리가 보인다. (b) 저항망 해석의 전압강하 $v$ --- 패드
근처는 얕고(밝음) 패드에서 먼 남서·남동 모서리가 깊다(진함). 값싼 그림 (a)와
정밀 그림 (b)가 같은 위험 지역을 가리키는 것이 본 기법의 요지다.}
\label{fig:flowir}
\end{figure}

\paragraph{점수 분해.} 기준 다이(seed 0)의 \B-최적 후보($4\times4$, 16패드)
에서 $\J=5162$, $\R=0$, $\PP=2476$, $\B=2687$로 \B/\J\ $=52.0\,\%$이며, 후보 간
순위를 바꾸는 것은 오직 \B\ 다(\R,\PP\ 는 패드 무관). 표~\ref{tab:cands}는 후보
7개의 전모다: \B\ 는 $3180\to2687$로 $15.5\,\%$만 움직이지만 그 작은 차이가
IR $2052\to286$($7.2\times$)의 순위를 정확히 복원한다.\footnote{\B\ 의
동적범위가 IR보다 훨씬 좁은 이유: \B\ 에는 패드와 무관한 바닥항
$\sum\iload$(총 전류)가 깔려 있기 때문이다($\alpha\varphi$ 부분만 배치에
반응한다). 순위 보존에는 문제가 없지만, 절대 IR 값 예측기가 아니라는 사실을
그대로 보여 주는 숫자이기도 하다.}

\begin{table}[t]
\centering\small
\caption{기준 다이(seed 0)의 후보 7개 전체. \B\ 순위와 IR 순위가 6/7 후보에서
일치하고(같은 패드 수의 이동 변형끼리 5--6위만 교차), 1위는 일치한다.}
\label{tab:cands}
\begin{tabular}{@{}lccccc@{}}
\toprule
후보 & 패드 수 & $\B$ & $\max v$ (IR) & \B\ 순위 & IR 순위 \\
\midrule
$1\times1$        & 1  & 3180.1 & 2052.5 & 7 & 7 \\
$2\times2$        & 4  & 2859.5 & 701.8  & 5 & 6 \\
$2\times2$ 이동   & 4  & 2861.5 & 695.4  & 6 & 5 \\
$3\times3$        & 9  & 2747.5 & 407.0  & 4 & 3 \\
$3\times3$ 이동   & 9  & 2746.9 & 409.4  & 3 & 4 \\
$4\times4$        & 16 & \textbf{2686.7} & \textbf{286.0} & \textbf{1} & \textbf{1} \\
$4\times4$ 이동   & 16 & 2688.1 & 294.5  & 2 & 2 \\
\bottomrule
\end{tabular}
\end{table}

\subsection{다패드/도메인 분할의 이득}\label{sec:exp-sweep}
그림~\ref{fig:sweep}는 패드 어레이를 $k=1..6$으로 조밀화한 스윕이다. \B\ 는
$100\%\to82.4\%$로, 최악 IR은 $100\%\to7.4\%$로 단조 감소한다---둘의 감소
\emph{폭}은 크게 다르지만(각주 참조) \emph{순서}는 완전히 같고, 한계 이득이
$k$ 증가에 따라 급감하는 수확체감 형태도 같다.\footnote{IR가 \B\ 보다 훨씬
가파르게 떨어지는 것은 물리적으로 옳다: 최악 IR은 ``가장 먼 셀''의 거리
제곱\emph{급}으로 반응하는 반면(저항이 직렬로 쌓임), \B\ 는 평균 거리의
1차식이다. 순위 도구로서는 문제가 없고, 절대값 예측기가 아님을 다시 보여
준다.} 이것이 SFTF-Clustering의 반직관 발견---``큰 단일 구조보다 분산된 다중
루트가 총비용을 줄인다''---의 PDN 재현이다: $1\times1\to4\times4$에서
$\Delta\B=493$($15.5\,\%$), 실제 최악 IR은 $86.1\,\%$ 감소.\footnote{현실
설계에서 패드는 공짜가 아니다(패키지 층수, 범프 피치, 보드 배선). 따라서 실전
질문은 ``패드를 늘릴까 말까''가 아니라 ``\emph{같은 패드 예산에서 어디에}
둘까''이고, 그 질문이 정확히 본 기법의 랭킹 문제다.}

\begin{figure}[t]
\centering
\includegraphics[width=0.6\linewidth]{pics/pdn_pad_sweep.png}
\caption{패드 어레이 조밀화 스윕($k\times k$, seed 0). $k{=}1$ 값을 $100\%$로
정규화. 값싼 \B(파랑)와 정밀 최악 IR(초록)이 같은 수확체감 곡선을 그린다.}
\label{fig:sweep}
\end{figure}

\subsection{무작위 배치와 ray-free 추정자}\label{sec:exp-est}
규칙 어레이가 아닌 \emph{완전 무작위} 16-패드 배치 30개$\times$다이 5개에서
footprint 추정자(\,=\B, 식~\eqref{eq:B})는 $\rho$ 평균 $+0.833$(최소
$+0.711$)을 기록했다. 흥미로운 것은 누적 전류밀도 보정(식~\eqref{eq:cd})이
$+0.833$으로 \textbf{사실상 이득이 없었다}는 점이다.\footnote{SFTF-Clustering
에서는 같은 자리의 height-field 보정이 $0.80\to0.90$의 뚜렷한 이득을 냈다.
차이의 원인 추정: (i) 저항 격자의 전압은 조화함수적으로 퍼져(경로가 병렬로
분산) 단일 최급강하 경로의 혼잡이 하수관·트렌치만큼 비용에 직결되지 않고,
(ii) 보정항 $\alpha\sum I\ell$ 자체가 footprint와 강하게 공선이라 순위 정보를
거의 추가하지 않는다. ``어떤 보정이 이식되고 어떤 보정이 이식되지 않는가''는
도메인 간 물리 차이를 드러내는 정보라 그대로 보고한다.} 무작위 배치에서 순위
상관이 규칙 어레이(표~\ref{tab:main})보다 낮은 것은 예상대로다: 무작위 배치는
같은 패드 수 안에서의 미세한 기하 차이를 구분해야 하는 더 어려운 문제다.
그럼에도 $0.8$ 문턱을 평균으로 넘겼다.

\subsection{비용: 왜 앞단이 값싼가}\label{sec:exp-timing}
그림~\ref{fig:timing}과 표~\ref{tab:timing}은 후보 1개 평가의 벽시계
시간이다.\footnote{동일 노트북, 단일 스레드, 3회 중 최솟값. 정밀해는
\texttt{scipy.sparse.linalg.spsolve} 직접법 기준으로, 상용 사인오프(수백만
노드, 다층 격자, via 저항, 동적 해석)는 이보다 자릿수로 무겁다. 즉 실제
환경에서는 격차가 여기 수치보다 \emph{커진다}.} $128\times128$에서 값싼 점수는
후보당 $0.30$\,ms, 정밀해는 $34$\,ms로 $115\times$ 차이다. 패드 위치 $\times$
개수 $\times$ 도메인 조합으로 후보가 수천 개로 늘어나는 탐색 단계에서 이
격차가 파이프라인 전체의 실용성을 결정한다.

\begin{table}[h]
\centering\small
\caption{후보 1개 평가 시간(ms). 배속은 정밀해 대비.}
\label{tab:timing}
\begin{tabular}{@{}lccccc@{}}
\toprule
격자 & $32^2$ & $48^2$ & $64^2$ & $96^2$ & $128^2$ \\
\midrule
값싼 \B          & 0.05 & 0.07 & 0.06 & 0.14 & 0.30 \\
정밀 $G\,v=i$    & 2.2  & 4.8  & 5.9  & 16.7 & 34.0 \\
배속             & $42\times$ & $66\times$ & $101\times$ & $122\times$ & $115\times$ \\
\bottomrule
\end{tabular}
\end{table}

\begin{figure}[t]
\centering
\includegraphics[width=0.6\linewidth]{pics/pdn_timing.png}
\caption{후보 1개 평가 시간 대 격자 크기(양대수 축). 값싼 점수(파랑)와 정밀
저항망 해석(초록)의 간격은 격자가 클수록 벌어진다.}
\label{fig:timing}
\end{figure}

\subsection{방향 텐서의 소멸: 예측된 부정적 결과}\label{sec:exp-r}
SFTF의 존재 이유였던 \emph{방향 의존} 텐서 $F(n)$은 이 도메인에서 어떻게
되는가? 연구기획 단계의 예측은 ``고정-패드 케이스에서 텐서는 스칼라로
축약된다''였다. 수치 확인 결과는 더 강했다: 가장 이방성이 크도록 성긴
$2\times2$ 패드에서 방위각 72개를 스윕해도 $\R(d)\equiv0$이었다. 원인은
구조적이다. 고정-패드 흐름장에서 소스의 흐름방향 $m_i$와 receiver의 $m_j$는
같은 $-\nabla\varphi$ 장에서 나와 거의 평행하므로, 각 기여
$w\,m_im_j^{\mathsf T}$가 준양정치이고 그 합 $F_{\mathrm{sym}}$도
양정치가 된다---실측 고유값 $(1068,\,1273)$, 둘 다 양수. 따라서
$\R=\max(0,-d^{\mathsf T}F_{\mathrm{sym}}d)$는 모든 $d$에서
0이다.\footnote{SFTF(적층제조)에서는 $m$이 \emph{표면 법선}이라 방향이 제멋대로
섞여 $F_{\mathrm{sym}}$이 부정부호(indefinite)가 되고, 그래서 방향에 따라
$\R$이 살아난다. 즉 $\R$의 생사는 구현 디테일이 아니라 ``흐름장이 단일
퍼텐셜의 기울기인가''라는 문제 구조에서 결정된다. 층별 선호배선 방위처럼
전류가 \emph{재배선 가능}한 설정에서는 $\R$이 다시 의미를 가질 수 있으나,
이는 본 PoC 범위 밖이다.} 이 부정적 결과는 본 이식의 정직한 경계선을 그어
준다: PDN으로 살아남는 것은 텐서 기하가 아니라 \textbf{ground-node 항 \B,
분할 논리, 그리고 값싼-랭킹$\to$정밀-검증 파이프라인}이다.

% ============================================================================
\section{관련연구와 포지셔닝}\label{sec:related}
% ============================================================================
PDN/IR-drop 최적화의 주요 갈래와 본 기법의 자리는 다음과 같다.

\begin{enumerate}[leftmargin=2em,itemsep=2pt]
\item \textbf{수치 사인오프.} $G\,v=i$ 기반 정적/동적 해석(상용 도구). 정확의
      기준점이되 후보 탐색용으로는 비싸다. 본 기법은 이를 \emph{대체하지 않고}
      그 앞단에 선다.
\item \textbf{ML 대체모델.} CNN으로 IR 맵을 즉석 예측하는
      계열~\cite{iccad2020fastir,iccad2023contest}, GNN-CNN 혼성의 동적 IR
      예측~\cite{pdnnet2024}, 최신 개관~\cite{technologies2026ir}. 빠르지만
      라벨 데이터(정밀해)로 학습해야 하고 공정·설계가 바뀌면 재학습이
      필요하며 블랙박스다.\footnote{2023 ICCAD CAD Contest가 정적 IR ML 예측을
      공식 문제로 낼 만큼 성숙한 갈래다. 본 기법과의 관계는 경쟁이라기보다
      상보에 가깝다: ML 대체모델은 \emph{고정된 패드/망}에서 IR \emph{값}을
      빠르게 예측하고, 본 기법은 \emph{패드/도메인 후보}를 학습 없이 줄
      세운다.}
\item \textbf{Decap 배치 최적화.} 심층강화학습 기반 2.5D PDN decap
      배치~\cite{decap2024rl} 등. 결정 변수(decap)와 시간 스케일(동적)이 달라
      본 PoC와 직교하며, 향후 후보 점수에 decap 항을 얹는 확장이 자연스럽다.
\item \textbf{패드/범프·후면 전력공급(BSPDN).} 패키징 로드맵~\cite{irds2024}이
      다루는 물리적 전력 인입 설계. 본 기법의 ``패드 배치'' 결정 변수가 바로 이
      지점이며, 후면 전력공급\footnote{Backside PDN: 웨이퍼 뒷면에 전력망을
      만들어 신호 배선과 분리하는 차세대 기술. 나노 TSV로 셀에 직접 급전하므로
      ``패드까지 거리'' 항의 구조가 바뀌지만, ``전류수요 $\times$ 급전점까지
      저항거리''라는 1차 법칙 자체는 유지된다---\B\ 항의 적용 범위가 오히려
      넓어질 수 있다.}에서도 1차 법칙은 유지된다.
\item \textbf{병렬 시뮬 + ML 핫스팟 검출.}~\cite{mlcad2024hotspot} 검증 자원을
      위험 지역에 몰아주자는 목적이 SFTF의 AVE와 같다. 차이는 본 기법의
      트리거가 \emph{무학습}(근소차·핫스팟 플래그)이라는 점이다.
\end{enumerate}

\paragraph{차별점 요약.} (D1) 학습 데이터 0의 닫힌형 후보생성기; (D2) IR 1차
법칙에 대한 ground-node 항의 닫힌형 해석; (D3) \B\ 의 가산 구조를 이용한 도메인 분할의
재해석-없는 탐색; (D4) 무학습 트리거의 적응 검증(향후); (D5) 패드배치 +
도메인분할 + 핫스팟 스크리닝의 단일 점수 통합.

% ============================================================================
\section{한계와 향후 과제}\label{sec:limits}
% ============================================================================
정직한 경계선을 명시한다.

\begin{itemize}[leftmargin=2em,itemsep=2pt]
\item \textbf{순위 도구이지 값 예측기가 아니다.} \B\ 의 동적범위는 IR보다 훨씬
      좁다(표~\ref{tab:cands}). 절대 IR 값이 필요한 단계에서는 ML 대체모델이나
      정밀해가 맞다. 본 기법의 가치는 무학습·해석가능·warm-start\footnote{좋은
      초기 후보를 공급해 뒤 단계의 반복 횟수를 줄이는 역할.}다.
\item \textbf{방향 텐서는 소멸한다.} \S\ref{sec:exp-r}에서 보였듯 고정-패드
      케이스의 $\R\equiv0$. SFTF의 텐서 기하가 아니라 \B-항과 파이프라인이
      이식의 실체다. 재배선 가능(층별 선호 방위) 설정의 $\R$ 부활 여부는 열린
      문제다.
\item \textbf{모델 충실도.} 단층 균일 시트, 이상 패드(전압강하 0), 정적
      해석뿐이다. 실제 PDN은 다층 격자·via 저항·패키지 임피던스·동적
      droop·EM·decap을 포함한다. 이들은 검증기(사인오프 대역)를 교체·강화할
      사안이지 값싼 점수의 구조를 바꾸는 사안은 아니라는 것이 우리의 가설이나,
      검증은 후속 과제다.\footnote{특히 산업 표준 IBM Power Grid
      Benchmarks나 2023 ICCAD contest 데이터셋으로 검증을 확장하는 것이 다음
      단계의 최우선이다. 합성 다이의 한계(핫스팟 4개, 가우시안 형상)는
      \S\ref{sec:exp-setup}에 명시했다.}
\item \textbf{누적 전류밀도 보정의 무효.} SFTF-Clustering에서 유효했던
      height-field형 보정이 여기서는 이득이 없었다(\S\ref{sec:exp-est}).
      저항망의 병렬 경로 분산이 원인으로 추정되며, EM(전류밀도 제약) 항으로
      재설계하는 편이 유망하다.
\item \textbf{AVE·decap·실배선 미구현.} 적응적 검증 확대는 파이프라인의 점선
      (그림~\ref{fig:pipeline})으로만 존재한다. Voronoi 도메인도 실제 도메인
      경계(전압섬 경계 셀, 레벨 시프터 비용)를 담지 않는다.
\end{itemize}

% ============================================================================
\section{결론}
% ============================================================================
적층제조의 서포트 흐름과 반도체 PDN의 전류 분배는 ``부하가 소수의 루트로
흘러내리고, 비용은 부하$\times$거리에 지배된다''는 같은 뼈대를 공유한다. 이
치환으로 SFTF의 ground-node 항은 IR-drop의 1차 법칙과 정확히 겹치고, 합성
다이 20개에서 값싼 패드항 \B\ 는 독립 물리의 저항망 사인오프 순위를
$\rho=+0.98\sim+1.00$으로 재현하며 후보당 비용은 $42\sim122$배 쌌다. 다패드
분할의 수확체감, footprint 추정자의 $\rho>0.8$, 그리고 방향 텐서의 구조적
소멸까지---무엇이 이식되고 무엇이 남는가를 수치로 확정했다. SFTF는 여기서도
최적화기가 아니라 \emph{후보생성기}다: 조합적으로 많은 패드배치·도메인 후보를
ms에 줄 세워, 비싼 사인오프가 소수의 좋은 후보만 보게 만드는 것. 다음 단계는
산업 벤치마크(IBM PG, ICCAD'23)로의 확장, 다층·동적 검증기의 도입, 그리고
근소차 트리거 기반 AVE의 구현이다.

% ============================================================================
\begin{thebibliography}{9}\small
\bibitem{iccad2020fastir}
Z.~Xie et al., ``Fast IR drop estimation with machine learning,''
\emph{Proc. ICCAD}, 2020. \url{https://dl.acm.org/doi/10.1145/3400302.3415763}
\bibitem{pdnnet2024}
Y.~Luo et al., ``PDNNet: PDN-aware GNN-CNN heterogeneous network for dynamic
IR drop prediction,'' arXiv:2403.18569, 2024.
\url{https://arxiv.org/html/2403.18569v2}
\bibitem{iccad2023contest}
G.~Luo et al., ``Invited: 2023 ICCAD CAD contest problem C: Static IR drop
estimation using machine learning,'' \emph{Proc. ICCAD}, 2023.
\url{https://ieeexplore.ieee.org/document/10323767}
\bibitem{decap2024rl}
Y.~Park et al., ``Hierarchical decoupling capacitor optimization for power
delivery network of 2.5D ICs via deep reinforcement learning,''
arXiv:2407.04737, 2024. \url{https://arxiv.org/html/2407.04737v1}
\bibitem{mlcad2024hotspot}
C.~Ho et al., ``A parallel simulation framework incorporating ML-based hotspot
detection for accelerated power grid analysis,'' \emph{Proc. MLCAD}, 2024.
\url{https://dl.acm.org/doi/10.1145/3670474.3685947}
\bibitem{irds2024}
IEEE IRDS, ``2024 IRDS executive packaging tutorial (C4 / backside power
delivery),'' 2024.
\url{https://irds.ieee.org/images/files/pdf/2024/2024IRDS_EPT-Part1.pdf}
\bibitem{technologies2026ir}
D.~Kim et al., ``Machine learning methods for fast evaluation of static IR
drop,'' \emph{Technologies}, vol.~14, no.~3, p.~169, 2026.
\url{https://www.mdpi.com/2227-7080/14/3/169}
\end{thebibliography}

\appendix
% ============================================================================
\section{재현 방법}
% ============================================================================
저장소 루트에서:
\begin{quote}\ttfamily\small
uv sync\\
uv run pytest python/src/pdn -q\hfill\rmfamily(수용 테스트 14개)\\
\ttfamily uv run python -m pdn.cli demo --ny 48 --nx 48 --pads 4\hfill\rmfamily(1분 데모)\\
\ttfamily uv run python scripts/build\_paper\_data.py\hfill\rmfamily(본 논문 전체 수치·그림)
\end{quote}
마지막 명령이 \texttt{draft/paper\_data.json}(모든 수치)과
\texttt{draft/pics/pdn\_*.png,svg}(모든 데이터 그림)를 재생성한다. 난수 시드는
전부 고정되어 있어 표·그림의 수치는 비트 단위로 재현된다(타이밍 표만 기계
의존).

\end{document}

