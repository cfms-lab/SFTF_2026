# LaTeX source: SFTF_ThermalChip_PoC.tex

Source: `D:\__SFTF_Projects(2026)\SFTF_ThermalChip_dev\draft\SFTF_ThermalChip_PoC.tex`

% !TEX program = xelatex
% SFTF -> 반도체 칩 열방출(써멀비아/히트싱크 배치, peak-온도 프록시) PoC
% 빌드: xelatex (MiKTeX) + kotex.  latexmk -xelatex SFTF_ThermalChip_PoC.tex
% 수치·그림 재현: uv run python scripts/build_paper_data.py  (draft/paper_data.json)
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
  flowarr/.style={->,thick,blue!55!black},
  trunk/.style={->,very thick,orange!75!black},
}

% 색상 강조 명령
\newcommand{\term}[1]{\textbf{#1}}
\newcommand{\R}{\ensuremath{R}}
\newcommand{\PP}{\ensuremath{P}}
\newcommand{\Bsum}{\ensuremath{B_{\mathrm{sum}}}}
\newcommand{\Bpeak}{\ensuremath{B_{\mathrm{peak}}}}
\newcommand{\J}{\ensuremath{J}}
\newcommand{\Tpeak}{\ensuremath{T_{\mathrm{peak}}}}
\newcommand{\Tmean}{\ensuremath{T_{\mathrm{mean}}}}

\title{\textbf{SFTF $\rightarrow$ 반도체 칩 열방출:\\
써멀비아/히트싱크 배치와 peak-온도 프록시}\\[2mm]
\large 적층제조 서포트 흐름 텐서장의 열설계 이식: 개념증명(PoC)}
\author{SFTF\_ThermalChip\_dev}
\date{2026-07}

\begin{document}
\maketitle

\begin{abstract}
\noindent
적층제조(AM)의 빌드방향 후보생성기 \textbf{SFTF}(Support Flow Tensor Field)는
``부하가 소수의 루트로 흘러내리고, 비용은 부하$\times$거리에 지배된다''는 구조를
닫힌형 텐서 계산으로 요약한다. 본 개념증명은 \textbf{오버행 $=$ 셀의 발열밀도
$P_i$}, \textbf{receiver $=$ 최저열저항 싱크 경로의 이웃 셀},
\textbf{빌드플레이트(ground node) $=$ 히트싱크/써멀비아($T=T_{\mathrm{amb}}$)}라는
치환으로 SFTF의 서포트 흐름 트리가 곧 \emph{열유속망}이 되고, 서포트 물량
최소화가 곧 \emph{온도상승 최소화}가 됨을 보인다. 자매 PoC(PDN IR-drop)와의
동형성 위에 이 도메인 고유의 질문을 하나 얹었다: 칩 열의 1차 신뢰성 지표는 합이
아니라 \textbf{최고온도(peak)}인데, peak 목적에는 peak-인지 프록시가 필요한가?
합성 다이($48^2$, 정상상태 전도 사인오프 $K t = P$ 대비)에서 얻은 답은
\emph{질문을 올바로 세울 때만 그렇다}이다: 싱크 \emph{개수}가 섞인 후보 풀에서는
peak와 mean이 강결합($\rho \approx 0.94$)되어 합 프록시 \Bsum\ 이 peak-$T$ 순위까지
이미 잡아내며($\rho=0.945$), peak 프록시 \Bpeak\ 는 40시드 중 11승에 그친다.
반면 \emph{비아 예산을 고정하고 배치만} 고르는 진짜 설계 질문에서는 peak/mean이
분리($\rho\approx0.78$)되고 \Bpeak\ 가 예산 9·16·25에서 $73{\sim}83\%$ 승률로
우월해진다. 후보생성기로서의 실용 가치는 shortlist regret으로 확정했다: 프록시
상위 $k{=}3$개만 정밀해석하면 진짜 최적 대비 초과 peak-$T$가 평균 $1.4\%$
(랜덤 셔틀리스트는 $17.8\%$)로, 정밀해 호출을 풀 전수 대비 $20\times$ 줄이고도
거의 최적 배치에 도달한다. per-평가 비용 이득이 소박한 소형 2D 격자
($2{\sim}3\times$)에서도 성립하는, \emph{호출 횟수}를 줄이는 무학습
후보생성기라는 가치 명제를 정직하게 정량화했다. 결론의 강건성은 네 방향으로
확인했다: (i) 이상화된 Dirichlet 싱크를 유한 비아 열저항의 \emph{컴팩트
모델}로 바꿔도 고정예산 우위가 유지되고($70\%$ 승률), (ii) \emph{실칩
발열맵}(HotSpot Alpha EV6, gcc 트레이스)에서 proxy 1위안이 진짜 최적 배치와
일치하며($k{=}1$ regret $0.0\%$, 랜덤 $47.2\%$) 레짐 경계(과소$\to$충분
예산에서 \Bpeak$\to$\Bsum)가 발열맵에 의존함을 추가로 규명했고, (iii) gcc
트레이스 100 인터벌의 \emph{과도} 시간-최대 peak를 진실로 하면 \Bsum\
shortlist는 실패($k{=}5$ regret $45.9\%$)하고 \Bpeak\ 만 수렴($1.4\%$)하며
--- 과도 레짐에서 peak-인지는 필수가 된다, (iv) \emph{3D 적층}(HotSpot
EV6\_3D, 캐시 2층$+$코어층)에서 두께-합산 맵에 적용한 2D 프록시가 3층 결합
진실을 랭킹한다(\Bpeak\ 승률 $100\%$, $\Delta\rho=0.13$). 아울러 텐서
가산성의 열 대응인 \emph{per-zone 가산 분해}가 재해석 없이 병목 열도메인을
식별한다(존 순위 $\rho=0.79$, 최열존 적중 $67\%$ vs 우연 $12.5\%$).
\end{abstract}

% ============================================================================
\section{서론: peak 목적에는 peak 프록시가 필요한가}
% ============================================================================

반도체 칩의 열방출 설계 --- 히트싱크에 닿는 써멀비아/TSV를 \emph{몇 개, 어디에}
둘 것인가 --- 는 정밀 열해석(FEM/CFD, 컴팩트 열모델)이 비싸다는 이유로
후보 선별(screening) 단계를 필요로 한다. 자매 개념증명에서 우리는 적층제조
서포트 흐름 텐서장(SFTF)의 골격이 PDN IR-drop 패드배치로 그대로 이식됨을
보였다: 정상상태 열전도와 정적 IR-drop은 수학적으로 동형이므로
(\S\ref{sec:mapping}), 그 결과는 단위만 바꾸면 열 도메인에도 성립한다.

그래서 이 PoC의 기여는 동형성의 재확인이 아니라, 열 도메인이 \emph{추가로}
요구하는 한 가지에 있다. PDN·하수 이식에서 비용은 \emph{합}(총 IR-drop, 총
굴착량)이었지만, 칩 열의 1차 지표는 \emph{최고온도} \Tpeak\ 다. 핫스팟 하나가
신뢰성을 결정하므로, 합 기반 ground-node 항 \Bsum\ 외에 흐름 트리를 따라
열저항$\times$누적열을 누적하는 \term{peak-인지 프록시} \Bpeak\ 를 도입했다
(\S\ref{sec:mapping-peak}).

검증 결과는 예상보다 미묘했고, 우리는 그 미묘함 자체가 이 논문의 핵심 결과라고
생각한다(\S\ref{sec:exp}):

\begin{itemize}[leftmargin=1.6em,itemsep=1pt]
\item \term{음성(negative).} 싱크 개수가 서로 다른 배치들을 한 풀에서 비교하면
  --- 문헌의 스크리닝 벤치마크가 흔히 취하는 설정 --- 총 싱크 접근량이 peak와
  mean을 \emph{함께} 끌어올려 둘이 강결합되고($\rho\approx0.94$), \Bsum\ 이
  peak-$T$ 순위까지 이미 잘 잡는다. \Bpeak\ 는 이기지 못한다(40시드 중 11승).
  국소 $P\varphi$·Jacobi 확산·그린함수 등 물리기반 대체 프록시 3종도 전부
  \Bsum\ 에 패했다.
\item \term{양성(positive).} 비아 \emph{예산을 고정}하고 배치만 최적화하는 ---
  실제 설계 흐름의 ``어디에 둘까'' --- 질문에서는 peak/mean이 분리
  ($\rho\approx0.78$)되고, \Bpeak\ 가 예산 9·16·25에서 승률 $73{\sim}83\%$로
  우월해진다.
\item \term{실용 가치.} 프록시 상위 $k$개만 정밀해석하는 shortlist 운용에서,
  $k{=}3$이면 초과 peak-$T$가 $1.4\%$(\Bsum\ $1.8\%$, 랜덤 $17.8\%$)다.
  즉 \emph{값싼 프록시 $+$ 극소 검증예산}으로 거의 최적 배치에 도달한다.
\end{itemize}

요컨대 peak-인지의 가치는 ``비아를 \emph{몇 개}''가 아니라 ``\emph{어디에}''를
정할 때 있다. 이 규명은 도메인 적응(목적함수 형태)의 성공 사례이자, 이식이
자동으로 성립하지는 않는다는 정직한 한계 보고이기도 하다.

% ============================================================================
\section{배경}
% ============================================================================

\subsection{SFTF 요약: 흐름 텐서와 세 개의 항}\label{sec:bg-sftf}

SFTF는 삼각망의 각 면 $i$가 중력을 등진 정도(오버행 $O_i$)를 ``흘러내리는
부하''로 보고, 부하가 receiver 면 또는 빌드플레이트로 흘러가는 경로를 닫힌형으로
집계한다. 점수는 세 항의 가중합이다:
방향 텐서의 Rayleigh 항 $\R$, 면쌍 근접 항 $\PP$, 그리고 빌드플레이트로 빠지는
부하를 거리 가중으로 집계하는 \term{ground-node 항} $B$. 자매 PoC들이 보였듯
고정 기하·고정 싱크 도메인에서 살아남는 것은 주로 $B$ 항이다 --- PDN에서는
방향 텐서 \R\ 항이 구조적으로 소멸함을 수치로 확인했고, 본 도메인도 같은 구조를
공유하므로 본 논문의 주인공은 $B$ 계열(\Bsum, \Bpeak)이다.

\subsection{정상상태 열전도와 PDN 동형성}\label{sec:bg-iso}

정상상태 열전도와 정적 IR-drop은 같은 타원형 방정식이다:
\begin{equation}
\nabla\!\cdot\!(k\,\nabla T) = -P_{\mathrm{diss}},\qquad
\nabla\!\cdot\!(\sigma\,\nabla V) = -I_{\mathrm{inject}},
\label{eq:iso}
\end{equation}
싱크 경계조건 $T=T_{\mathrm{amb}}$ 는 패드 $V=0$ 에 대응하고, 상사는
$V\!\leftrightarrow\!T$, 전류$\leftrightarrow$열유속, 전도도
$\sigma\!\leftrightarrow\!k$, 패드$\leftrightarrow$히트싱크/써멀비아다.
따라서 자매 PoC의 저항망 솔버 $G v = i$ 는 단위만 바꾸면 그대로 열 솔버
$K t = P$ 가 된다. 푸리에 법칙 $q=-k\nabla T$ 는 중력 퍼텐셜 $-\nabla\Phi$ 와
같은 ``퍼텐셜$\to$싱크'' 구조라, AM 서포트 흐름과의 대응이 전기장보다 오히려
깨끗하다.

% ============================================================================
\section{수식 매핑: SFTF $\to$ ThermalChip}\label{sec:mapping}
% ============================================================================

\begin{table}[h]\centering\small
\caption{기호 대응표. 자매 PDN PoC와의 차이는 마지막 두 행이다.}
\label{tab:mapping}
\begin{tabular}{lll}
\toprule
SFTF (적층제조) & ThermalChip PoC & 기호 \\
\midrule
빌드방향 $n\in S^2$ & 백사이드 싱크 시 $-z$ 로 거의 균일 & $n$ \\
면 $i$ / 오버행 $O_i(n)$ & 칩 격자 셀 / 발열밀도 & $P_i\ge0$ \\
receiver 탐색(레이캐스트) & $\varphi$ 최급강하 이웃(싱크 방향) & $\mathrm{rec}(i)$ \\
지지 높이 $h_{ij}$ & 열저항거리 & $r_{ij}$ \\
빌드플레이트(ground node) & 히트싱크/써멀비아 ($T=T_{\mathrm{amb}}$) & \Bsum \\
분할 $+$ 재배향 & 열도메인 분할 $+$ 다(多)싱크 & \\
\midrule
비용 $=$ 총 서포트(합) & 비용 $=$ \term{peak 온도(max)} & \Bpeak \\
--- & 고정 비아예산 하 배치최적화(\S\ref{sec:exp-budget}) & \\
\bottomrule
\end{tabular}
\end{table}

\subsection{싱크거리 퍼텐셜 $\varphi$ = 표고}

싱크 집합 $S$가 주어지면 각 셀 $i$의 퍼텐셜을 최근접 싱크까지의 거리변환
$\varphi_i=\mathrm{dist}(i,S)$ 로 둔다. AM에서 표고(빌드방향 좌표)가 하던 역할을
$\varphi$ 가 대신한다: 열은 $\varphi$ 가 감소하는 쪽으로 ``흘러내린다.''

\subsection{receiver와 흐름 트리}

각 셀의 receiver를 $\varphi$ 최급강하 이웃으로 두면
$\mathrm{rec}: i \mapsto j$ 는 싱크를 루트로 하는 포레스트가 되고, 셀 $i$를
통과하는 누적열 $\mathrm{accum}_i$ (자기 발열 $+$ 상류 유입)이 정의된다.
이는 SFTF의 서포트 흐름 트리와 정확히 같은 자료구조다.

\subsection{합 프록시 \Bsum\ 와 peak 프록시 \Bpeak}\label{sec:mapping-peak}

ground-node 항의 직역은 발열$\times$거리 가중합이다:
\begin{equation}
\Bsum \;=\; \sum_i P_i\,\bigl(1+\alpha\,\varphi_i\bigr),
\label{eq:bsum}
\end{equation}
평균/총 온도상승의 1차 법칙이며, 자매 PoC에서 사인오프 순위를 재현한 바로 그
항이다. 열 도메인 고유의 추가는 흐름 트리를 따라 내려가며 열저항$\times$누적열을
누적하는 \term{peak-인지 프록시}다:
\begin{equation}
t^{\mathrm{proxy}}_i \;=\; t^{\mathrm{proxy}}_{\mathrm{rec}(i)}
   \;+\; \alpha\,\mathrm{accum}_i\, r_i,
\qquad
\Bpeak \;=\; \max_i\, t^{\mathrm{proxy}}_i .
\label{eq:bpeak}
\end{equation}
싱크에서 멀고($r$ 누적) 상류 발열이 많은($\mathrm{accum}$) 셀이 큰 값을 받아,
핫스팟 \emph{위치}의 순위를 겨냥한다. 전체 점수는 자매 PoC와 같은 형태
$\J = w_R \R + w_P \PP + w_B \Bsum$ 를 유지하되, 본 논문의 비교는 \Bsum\ 대
\Bpeak\ 에 집중한다.

\begin{figure}[h]\centering
\begin{tikzpicture}[node distance=6mm]
  \node[box] (am) {AM: 오버행 부하 $O_i$\\ $\downarrow$ 흘러내림\\ 빌드플레이트};
  \node[box,right=18mm of am] (th) {칩: 발열 $P_i$\\ $\downarrow$ $\varphi$ 최급강하\\ 싱크 $T=T_{\mathrm{amb}}$};
  \node[hl,right=18mm of th] (proxy) {\Bsum: 합(식~\ref{eq:bsum})\\[1mm] \Bpeak: max(식~\ref{eq:bpeak})};
  \draw[trunk] (am) -- node[above,font=\scriptsize]{치환} (th);
  \draw[flowarr] (th) -- node[above,font=\scriptsize]{닫힌형} (proxy);
\end{tikzpicture}
\caption{이식의 뼈대. 서포트 흐름 트리 $=$ 열유속망, ground node $=$ 싱크.
도메인 고유의 추가는 합($\Bsum$)이 아닌 max(\Bpeak) 목적이다.}
\label{fig:concept}
\end{figure}

\subsection{열도메인 분할 = SFTF-Clustering의 이식}

SFTF-Clustering의 cut-induced(분할 비용)/reorientation(조각별 이득) 구조는
``한 열도메인을 분리해 별도 비아 군을 다는 비용'' 대 ``각 도메인이 자기 최적
싱크 집합에 서는 이득''으로 옮겨지고, 텐서 가산성 $F(\mathrm{part})=\sum
F_{\mathrm{part}}$ 로 분할안마다 재해석 없이 추정할 수 있다. 열 대응에서 두
가산 추정자(식~\ref{eq:bsum}--\ref{eq:bpeak})는 per-셀 합이므로, Voronoi
존으로 제한한 부분합이 곧 그 존의 비용이 된다 --- 추가 해석 없이. 이 per-zone
가산 분해의 정량 검증은 \S\ref{sec:exp-zones}에서 수행한다.

% ============================================================================
\section{구현}\label{sec:impl}
% ============================================================================

구현은 자매 저장소 \texttt{SFTF\_PDNElectric\_dev}의 포크로, numpy/scipy만
사용한다(학습 없음, GPU 없음). 모듈은 \texttt{python/src/thermal/}:
\texttt{chip.py}(합성 다이·싱크 배치·$\varphi$ 거리변환),
\texttt{heat\_field.py}(흐름 트리·\Bsum·\Bpeak·방향 텐서),
\texttt{verify.py}(사인오프 4층위; 순위상관·hit@k·shortlist regret),
\texttt{zones.py}(도메인 분할·per-zone 가산 분해),
\texttt{realchip.py}(HotSpot .flp/.ptrace/.lcf 로더·면적가중 래스터화),
\texttt{cli.py}(데모). 수용 테스트는 34개이며 본 논문 수치 전체는
\texttt{scripts/build\_paper\_data.py} 한 번으로 재현된다(부록~\ref{sec:repro}).

정밀검증(사인오프)은 네 층위다. \term{스탠드인}(\texttt{thermal\_solve})은 격자
라플라시안 $K$에 싱크 셀을 Dirichlet($T=0$)로 제거한 뒤 $K t = P$ 를 직접해로
푼다. \term{컴팩트 모델}(\texttt{signoff\_thermal})은 그 이상화를 HotSpot식
유한 수직 열저항으로 대체한다: 전 셀이 패키지를 통해 약하게($g_{\mathrm{bg}}$)
주변으로 새고, 비아 셀은 강하지만 \emph{유한한} 수직 전도 $g_{\mathrm{via}}$ 를
갖는 $(K_{\mathrm{lat}} + \mathrm{diag}\,g)\,t = P$ 다.
$g_{\mathrm{via}}\!\to\!\infty$ 극한에서 스탠드인을 회복함을 회귀 테스트로
고정했다. \term{과도 솔버}(\texttt{transient\_solve})는
$C\dot T = -(K_{\mathrm{lat}}+\mathrm{diag}\,g)T + P(t)$ 를 전력 트레이스
인터벌마다 implicit(backward-Euler) 1스텝으로 적분한다 --- 시스템 행렬이
상수라 LU 분해 1회를 전 스텝에 재사용하며, 지표는 시간-최대 peak다.
\term{3D 적층 솔버}(\texttt{signoff\_thermal\_3d})는 층별 lateral 라플라시안을
TIM/TSV 층의 per-셀 수직 전도 $g_z$ 로 결합하고 싱크-근접 층에 패키지
누설·비아 전도를 둔다; 1층이면 컴팩트 모델로 정확히 환원된다(회귀 테스트).
실단위 보정·대류·전기-열 결합은 이 훅 계열에 HotSpot/FEM 호출을 연결해
확장한다.

% ============================================================================
\section{실험}\label{sec:exp}
% ============================================================================

\subsection{설정}\label{sec:exp-setup}

합성 다이는 저전력 베이스라인 $+$ 고전력 핫스팟 4개 $+$ 잡음의 $48\times48$
격자($\texttt{synthetic\_chip}$, 시드별 재현)다. 후보 풀은 두 종류다:
\begin{itemize}[leftmargin=1.6em,itemsep=1pt]
\item \term{개수혼합 풀}(varying-count): 정규 격자 배치 7개($k\times k$ 및
  오프셋) $+$ 불규칙 랜덤 배치 40개 --- 배치마다 비아 개수가 다르다.
\item \term{고정예산 풀}(fixed-budget): 비아 개수를 예산 $b$로 고정하고
  \emph{배치만} 랜덤하게 바꾼 40$\sim$60개.
\end{itemize}
평가는 각 배치에 대해 프록시(\Bsum, \Bpeak)와 정밀해(\Tpeak, \Tmean)를 모두
계산하고 Spearman 순위상관 $\rho$, 승률(시드별 $\rho_{\mathrm{peak}}$ 비교),
shortlist regret으로 요약한다. 그림~\ref{fig:fields}에 시드-0 다이의 발열밀도,
$\varphi$ 퍼텐셜, 정밀해 온도장을 보였다.

\begin{figure}[h]\centering
\includegraphics[width=\linewidth]{pics/thermal_die_fields.png}
\caption{시드-0 합성 다이($48^2$)와 예산-16 배치(프록시 \Bpeak\ 1위안,
$\times$ 표시). 왼쪽: 발열밀도 $P$. 가운데: 싱크거리 퍼텐셜 $\varphi$.
오른쪽: 정상상태 전도 정밀해 온도장 $T$ --- 핫스팟과 싱크 배치의 상호작용이
peak 위치를 결정한다.}
\label{fig:fields}
\end{figure}

\subsection{음성 결과: 개수혼합 풀에서는 합 프록시로 충분하다}\label{sec:exp-neg}

개수혼합 풀에서 \Bsum\ 은 \Tmean\ 순위를 $\rho=+0.969$, \emph{\Tpeak\ 순위까지}
$\rho=+0.945$ 로 재현한다(시드-0, 47배치). peak를 겨냥해 설계한 \Bpeak\ 는
$\rho=+0.918$ 로 오히려 뒤진다. 40시드로 확장하면 \Bpeak\ 승률은 $11/40$,
평균 $\Delta\rho=-0.015$ 다. 원인은 풀의 구조에 있다: 배치마다 싱크 개수
($=$ 총 열접근량)가 다르면 그 접근량이 peak와 mean을 \emph{함께} 좌우해 둘의
순위상관이 $\rho\approx0.936$ 에 이르고, mean을 잡는 \Bsum\ 이 peak도 자동으로
잡는다. 물리기반 대체 프록시 3종(국소 $P\varphi$, Jacobi 확산 스무딩, 이미지법
2D 로그 그린함수)도 전부 \Bsum\ 에 패했다. SFTF의 \emph{이산} 서포트 트리와
달리 열은 \emph{확산}이라 sum$\leftrightarrow$max 구분이 그대로 전이되지
않는다 --- 이것이 이식의 첫 번째 정직한 경계다.

\subsection{양성 결과: 고정예산 배치최적화에서 peak-인지가 이긴다}\label{sec:exp-budget}

실제 설계 흐름은 대개 비아 예산이 먼저 정해지고(비용·면적 제약) 그 다음
\emph{어디에} 둘지를 고른다. 예산을 고정하면 총 접근량이 일정해져 peak/mean이
분리되고($\rho\approx0.78$), 표~\ref{tab:budget}과 그림~\ref{fig:budget}처럼
\Bpeak\ 가 우월해진다: 예산 9·16·25에서 승률 $73.3\%$·$83.3\%$·$76.7\%$,
평균 $\rho_{\mathrm{peak}}\approx0.85 > \rho_{\mathrm{sum}}\approx0.80$.
승률은 예산에 다소 민감하나(예산 12: $63.3\%$, 단 $\rho$ 우위는 유지) 부호는
일관된다. 과소 예산($b=4$)은 고정해도 접근량 자체가 지배해 실패한다 ---
적용 범위의 두 번째 정직한 경계다.

\begin{table}[h]\centering\small
\caption{고정예산 배치전용 풀(30시드 $\times$ 40배치). 승률 $=$ 시드별
$\rho(\Bpeak,\Tpeak)>\rho(\Bsum,\Tpeak)$ 비율.}
\label{tab:budget}
\begin{tabular}{rcccc}
\toprule
예산 $b$ & \Bpeak\ 승률 & mean $\rho(\Bpeak,\Tpeak)$ & mean $\rho(\Bsum,\Tpeak)$
        & $\rho(\Tpeak,\Tmean)$ \\
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
\includegraphics[width=0.78\linewidth]{pics/thermal_budget.png}
\caption{비아 예산별 \Bpeak\ 승률(막대)과 평균 순위상관(선). 예산이 과소하지
않은 전 구간($b\ge9$)에서 peak-인지 프록시가 우월하다.}
\label{fig:budget}
\end{figure}

\begin{figure}[h]\centering
\includegraphics[width=0.78\linewidth]{pics/thermal_scatter.png}
\caption{예산-16 시드-0 풀의 프록시--정밀해 산점도. \Bpeak(왼쪽)가 \Tpeak\ 와
더 단조적인 관계를 보인다.}
\label{fig:scatter}
\end{figure}

\subsection{shortlist regret: 후보생성기의 진짜 지표}\label{sec:exp-regret}

단일 최적배치 적중(hit@1)은 $19/60\,(32\%)$ 로 낮지만, 이는 최상위 배치들이
거의 동률이기 때문이다(프록시 결함이 아님): \Bpeak\ 가 고른 1위안의 실제
\Tpeak\ 는 진짜 최적보다 평균 $4.1\%$(best$\to$worst 정규화)만 높다. 실제
사용법은 ``프록시로 top-$k$ 를 추려 그 $k$개만 정밀해석''이므로, 올바른 지표는
shortlist regret이다. 표~\ref{tab:regret}과 그림~\ref{fig:regret}이 60시드
$\times$ 60배치(예산 16) 결과다: $k{=}3$이면 \Bpeak\ regret $1.4\%$ ---
정밀해 호출을 전수(60회) 대비 $20\times$ 줄이고도 사실상 최적 배치에 도달한다.
\Bpeak\ 는 검증예산이 빠듯한 작은 $k$(1$\sim$3)에서 \Bsum\ 보다 낮은 regret을
보이고($k{=}1$: $4.1\%$ vs $4.6\%$; $k{=}3$: $1.4\%$ vs $1.8\%$), $k\ge5$에서는
수렴한다 --- peak-인지의 이득은 검증이 비쌀수록 집중된다.

\begin{table}[h]\centering\small
\caption{shortlist regret (60시드 $\times$ 60배치, 예산 16). 낮을수록 좋다.}
\label{tab:regret}
\begin{tabular}{rccc}
\toprule
$k$ & \Bpeak & \Bsum & 랜덤 \\
\midrule
 1 & $\mathbf{4.1\%}$ & $4.6\%$ & $36.3\%$ \\
 3 & $\mathbf{1.4\%}$ & $1.8\%$ & $17.8\%$ \\
 5 & $0.9\%$ & $\mathbf{0.8\%}$ & $11.4\%$ \\
10 & $0.2\%$ & $0.2\%$ & $6.8\%$ \\
\bottomrule
\end{tabular}
\end{table}

\begin{figure}[h]\centering
\includegraphics[width=0.62\linewidth]{pics/thermal_regret.png}
\caption{검증예산 $k$ 대 shortlist regret. $k{=}3$이면 프록시 셔틀리스트가
랜덤 대비 $12\times$ 낮은 초과 peak-$T$로 수렴한다.}
\label{fig:regret}
\end{figure}

\subsection{비용: 이득은 per-평가가 아니라 호출 횟수에 있다}\label{sec:exp-timing}

정직하게 보고한다: 소형 2D 격자에서는 희소 직접해 자체가 싸서, 프록시
(흐름장 $+$ $B$ 항)의 per-평가 이득은 $2{\sim}3\times$에 그친다
(표~\ref{tab:timing}). 자매 PDN PoC의 $42{\sim}122\times$ 와 다른 이유는
검증기 차이다(저항망 vs 격자 라플라시안 직접해). 그러나 후보생성기의 가치
명제는 per-평가 속도가 아니라 \emph{정밀해 호출 횟수}의 절감이다: \S\ref{sec:exp-regret}의
운용($k{=}3$/풀 60)은 사인오프 호출을 $20\times$ 줄였고, 이 절감은 검증기가
비쌀수록(실제 FEM/CFD 사인오프, 과도해석) 그대로 커진다. 프록시 비용은 격자
크기에 선형, 직접해는 초선형이므로 격자가 클수록 per-평가 격차도 벌어진다
($192^2$에서 $3.1\times$).

\begin{table}[h]\centering\small
\caption{배치 1개당 평가 비용 (예산 16, 20회 평균, 단일 코어).}
\label{tab:timing}
\begin{tabular}{rccc}
\toprule
다이 & 프록시($B$ 항) & 정밀해 $Kt=P$ & 비율 \\
\midrule
$48^2$  & $1.6$ ms & $3.9$ ms & $2.4\times$ \\
$96^2$  & $6.8$ ms & $15.2$ ms & $2.2\times$ \\
$192^2$ & $29.8$ ms & $91.0$ ms & $3.1\times$ \\
\bottomrule
\end{tabular}
\end{table}

\subsection{강건성 1: 컴팩트 모델 사인오프에서도 결론이 유지된다}\label{sec:exp-signoff}

지금까지의 정밀해는 싱크를 이상적 Dirichlet 셀로 둔 스탠드인이었다. 검증기를
유한 비아 열저항의 컴팩트 모델(\S\ref{sec:impl})로 바꿔 같은 고정예산 실험
(예산 16, 30시드 $\times$ 40배치)을 반복하면: \Bpeak\ 승률 $70.0\%$,
$\rho_{\mathrm{peak}}=0.793 > \rho_{\mathrm{sum}}=0.762$, shortlist regret은
$k{=}1$에서 $8.2\%$ vs $11.3\%$, $k{=}3$에서 $2.4\%$ vs $3.9\%$
($k{=}5$에서는 $1.5\%$ vs $0.9\%$로 역전 --- 작은 $k$ 집중 패턴 재확인).
절대 상관은 Dirichlet 대비 다소 낮아지지만(검증기가 더 어려워짐), \emph{부호와
운용 결론은 그대로다}: peak-인지의 이득은 고정예산 배치 문제, 그중에서도
검증예산이 빠듯한 소수-shortlist 레짐에 있다.

\subsection{강건성 2: 실칩 발열맵(HotSpot Alpha EV6)}\label{sec:exp-realchip}

합성 다이 결론이 실제 프로세서의 발열 분포에서도 성립하는지, HotSpot 표준
벤치마크~\cite{hotspot}의 Alpha EV6 플로어플랜($16\,\mathrm{mm}\times16\,\mathrm{mm}$, 19블록)
$+$ gcc 전력 트레이스(시간평균)를 면적가중 래스터화($64^2$)해 검증했다
(그림~\ref{fig:ev6}). 트레이스 총전력 $\approx99.6\,\mathrm{W}$, 발열은 FP
클러스터·정수 코어에 집중된 전형적 실칩 맵이다.

\begin{table}[h]\centering\small
\caption{EV6/gcc 실칩 맵, 고정예산 배치전용 풀(30풀 $\times$ 40배치, 스탠드인
검증). regret은 예산 16.}
\label{tab:ev6}
\begin{tabular}{rccc}
\toprule
예산 $b$ & \Bpeak\ 승률 & mean $\rho(\Bpeak,\Tpeak)$ & mean $\rho(\Bsum,\Tpeak)$ \\
\midrule
 9 & $\mathbf{100.0\%}$ & $\mathbf{0.913}$ & $0.855$ \\
16 & $66.7\%$ & $0.888$ & $0.889$ \\
25 & $16.7\%$ & $0.862$ & $\mathbf{0.872}$ \\
\midrule
\multicolumn{4}{l}{regret($b{=}16$): $k{=}1$: \Bpeak\ $\mathbf{0.0\%}$ /
\Bsum\ $0.7\%$ / 랜덤 $47.2\%$;\quad $k{\ge}3$: 두 프록시 모두 $0.0\%$} \\
\bottomrule
\end{tabular}
\end{table}

두 가지가 확인된다. 첫째, \term{후보생성기로서의 가치는 실칩에서 더 강하다}:
예산 16에서 \Bpeak\ 1위안이 30풀 전부에서 진짜 최적 배치와 일치했다($k{=}1$
regret $0.0\%$; 랜덤은 $47.2\%$). 실칩 맵은 핫스팟이 소수·대형이라 프록시가
표적을 놓치기 어렵다. 둘째, \term{레짐 경계는 발열맵에 의존한다}: 합성 다이에서
$b{=}9{\sim}25$ 전 구간 \Bpeak\ 우위였던 것과 달리, EV6에서는 $b{=}9$(핫스팟
대비 비아 희소)에서 $100\%$ 승, $b{=}25$(충분 예산)에서는 \Bsum\ 이 다시
이긴다. 즉 peak-인지가 값을 하는 것은 ``비아가 핫스팟 대비 \emph{희소}할
때''이고, 예산이 충분해지면 어느 프록시든 좋은 배치를 찾는다 --- \S\ref{sec:exp-neg}의
개수혼합 결론과 일관된, 적용 범위의 세 번째 정직한 경계다.

\begin{figure}[h]\centering
\includegraphics[width=0.86\linewidth]{pics/thermal_ev6_fields.png}
\caption{HotSpot Alpha EV6 $+$ gcc 트레이스(시간평균)의 발열밀도(왼쪽)와,
\Bpeak\ 1위 비아 16개 배치의 컴팩트 모델 온도장(오른쪽, $\times$ 표시가 비아).}
\label{fig:ev6}
\end{figure}

\subsection{강건성 3: 과도(transient) 사인오프 --- peak-인지가 필수가 되는 레짐}\label{sec:exp-transient}

정상상태가 아니라 실제 gcc 구동 트레이스(100 인터벌)의 \emph{시간-최대} peak를
진실로 삼으면 어떻게 되는가? backward-Euler 과도 솔버(\S\ref{sec:impl})로
EV6 다이($64^2$, 예산 16, 15풀 $\times$ 30배치)를 재검증했다. 이 레짐은
질적으로 다르다: 100 인터벌의 버스트 동안 열이 비아 배치를 충분히 ``보지''
못해, 배치 간 시간-최대 peak의 스팬이 정상상태의 $278\%$에서 $21\%$로
압축되고 정상상태 진실과의 상관도 $0.59$까지 떨어진다(전 배치에서 최대는
마지막 프레임 --- 즉 램프 레짐). 이 어려운 진실에 대해:
$\rho_{\mathrm{peak}}=0.783>\rho_{\mathrm{sum}}=0.764$(승률 $60\%$)로 순위
우위는 완만하지만, \term{shortlist에서는 차이가 극적이다}: \Bsum\ 은 $k{=}5$
에도 regret $45.9\%$로 실패하는 반면 \Bpeak\ 는 $1.4\%$로 수렴한다($k{=}3$:
$30.5\%$ vs $68.0\%$). 짧은 버스트의 시간-최대 peak는 핫스팟 \emph{국소}
가열이 지배하므로, 전역 합 \Bsum\ 은 표적을 잃고 위치를 겨냥한 \Bpeak\ 만
유효하다 --- 과도 진실에서 peak-인지는 선택이 아니라 필수가 된다. 단 top-1
신뢰는 낮으므로($k{=}1$ regret $70\%$; 스팬 압축 레짐의 동률 잡음) 과도
운용에서는 $k\ge5$ shortlist를 권장한다.

\subsection{강건성 4: 3D 적층(HotSpot EV6\_3D) --- 2D 프록시가 스택을 랭킹한다}\label{sec:exp-3d}

HotSpot example4의 EV6\_3D 테스트케이스 --- 캐시 다이 2층 $+$ 코어 다이
1층(TIM/TSV 개재, 총전력 $\approx36\,\mathrm{W}$) --- 로 3D 적층을
검증했다. 비아는 싱크-근접 코어층에 배치하고(예산 16), 프록시는 \emph{두께
합산} 2D 맵에 그대로 적용하며, 진실은 3층 결합 컴팩트 모델
(\texttt{signoff\_thermal\_3d})의 전층 peak다(20풀 $\times$ 30배치).
결과: \Bpeak\ 승률 $\mathbf{100\%}$(20/20풀),
$\rho_{\mathrm{peak}}=0.826 \gg \rho_{\mathrm{sum}}=0.693$, shortlist는
$k{=}3$에서 두 프록시 모두 regret $0.0\%$($k{=}1$은 \Bsum\ $8.7\%$ vs
\Bpeak\ $15.7\%$로 혼전). 최열 셀은 600케이스 전부에서 싱크-원거리 캐시층에
서 발생 --- 물리적으로 정합적이다. 요컨대 층간 수직 결합이 끼어도 값싼 2D
프록시가 3D 진실을 랭킹하며, 오히려 \Bpeak\ 의 순위 우위가 커진다
($\Delta\rho=0.13$; 합산 맵의 mean은 층 배분을 뭉개지만 peak 경로는
살아남기 때문).

\subsection{열도메인 분할(D3): per-zone 가산 분해가 병목 존을 찾는다}\label{sec:exp-zones}

텐서 가산성의 열 대응을 정량 검증했다. 비아 8개를 랜덤 배치한 뒤 Voronoi
열도메인으로 나누고, \emph{추가 해석 없이} per-zone 부분합(식~\ref{eq:bpeak}의
존 내 최대)으로 예측한 존별 위험도를, 컴팩트 모델 정밀해의 존별 peak-$T$와
비교했다(30시드): 존 순위 Spearman 평균 $0.790$, \term{최열(bottleneck) 존
적중률 $67\%$}(8존 우연 기대 $12.5\%$의 $5.3\times$). 설계자가 ``어느
도메인부터 보강할까''를 정밀해 없이 답할 수 있다는 뜻이다. 아울러
SFTF-Clustering의 반직관 이식 --- 하나의 큰 싱크보다 분산형 다(多)비아 ---
도 정밀해로 확인했다: 중앙 싱크 1개 대비 $3\times3$ 분산 비아는 컴팩트 모델
peak-$T$를 $29\%$ 낮추고, 가산 프록시는 이 이득의 부호를 해석 없이 예측한다.

% ============================================================================
\section{관련연구와 포지셔닝}\label{sec:related}
% ============================================================================

칩 열설계 문헌은 크게 네 갈래다: (1) 수치 열 사인오프(FEM/FDM·컴팩트 열모델,
HotSpot 계열), (2) 열-인지 플로어플랜/배치(SA·해석적·force-directed로 블록·
TSV·마이크로채널·열도메인 배치)~\cite{floorplan3d,atplace25d}, (3) 써멀비아/TSV
플래닝, (4) ML 열 대체모델(CNN·연산자학습·트랜스포머 온도맵
예측)~\cite{mlcad2022,surrogate2025,operator2025}. 본 PoC의 차별점:

\begin{itemize}[leftmargin=1.6em,itemsep=1pt]
\item \term{(D1) 무학습 후보생성기.} ML 대체모델(갈래 4)은 기술노드/설계별
  재학습이 필요하다. SFTF 이식은 닫힌형 계산으로 학습데이터 0에서 후보를
  랭킹하고, 상위 소수만 정밀 솔버에 넘긴다.
\item \term{(D2) ground-node 닫힌형.} \Bsum\ 은 온도상승 1차항의 텐서 해석으로,
  ``발열$\times$싱크거리'' 휴리스틱에 유도 가능한 근거를 부여한다.
\item \term{(D3) 텐서 가산성.} 열도메인 분할을 재-FEM 없이 추정 --- per-zone
  가산 분해가 병목 존을 $67\%$ 적중(\S\ref{sec:exp-zones})으로 식별.
\item \term{(D5) peak-인지 프록시 --- 범위 한정.} 합이 아닌 max 목적의 도메인
  적응이 본 논문의 고유 기여다. 단 \S\ref{sec:exp}가 보였듯 그 효력은
  \emph{고정 비아예산 하의 배치 랭킹}에 한정되며, 싱크 개수가 변하는 비교에서는
  \Bsum\ 으로 충분하다. 이 범위를 명시하는 것 자체가 문헌의 스크리닝 벤치마크
  설정(개수혼합 비교)에 대한 방법론적 경고다.
\end{itemize}

% ============================================================================
\section{한계와 향후 과제}\label{sec:limits}
% ============================================================================

\begin{itemize}[leftmargin=1.6em,itemsep=1pt]
\item \term{확산 vs 이산 트리.} 전도장은 확산이라 SFTF의 이산 흐름 트리는
  근사다. 방향 텐서 \R\ 항은 자매 PDN 도메인과 같은 이유로 기여가 제한적이며,
  백사이드 싱크처럼 방향이 거의 균일한 구성에서 특히 그렇다. 본 논문이 $B$
  계열에 집중한 이유다.
\item \term{PoC 단위의 컴팩트 모델.} 사인오프 4층위(스탠드인·컴팩트·과도·3D)는
  전부 scipy 스탠드인이며 실단위 보정 전이다. 과도 열용량·수직 전도는
  타당성 스케일이고, 실단위 보정은 \texttt{signoff\_thermal()} 훅 계열에
  HotSpot/FEM을 연결하는 몫이다. 대류(마이크로채널)·전기-열 결합은 미포함
  (대류 채널은 자매 하수 PoC의 흐름망 기계를 재사용할 수 있다).
\item \term{실칩 검증의 폭.} 실칩은 HotSpot EV6/gcc(2D)와 EV6\_3D(3층) 2종이다.
  레짐 경계(\S\ref{sec:exp-realchip})가 발열맵에 의존함을 확인한 만큼, 더 많은
  플로어플랜·워크로드 트레이스 스윕으로 경계 지도를 그리는 것이 다음 단계다.
\item \term{분할 검증의 범위.} per-zone 분해는 \emph{고정 배치의 병목 식별}을
  검증했다. 분할 후보 풀 전체의 랭킹(cut/reorientation 트레이드오프 최적화)은
  향후 과제다.
\item \term{미분가능화.} 열 비용은 매끄러우므로 soft-attention 완화로
  비아/싱크 위치를 경사하강 최적화하는 확장(자매 미분가능 SFTF 계열)이
  자연스럽다.
\end{itemize}

% ============================================================================
\section{결론}
% ============================================================================

적층제조 서포트 흐름과 칩 열방출은 ``부하가 소수의 싱크로 흘러내리고 비용은
부하$\times$거리에 지배된다''는 뼈대를 공유하며, PDN 동형성을 경유한 SFTF
이식은 열 도메인에서도 성립한다. 이 위에 본 PoC는 열 고유의 질문 --- peak
목적에는 peak 프록시가 필요한가 --- 를 던지고, 답이 \emph{조건부}임을
정량화했다: 개수혼합 비교에서는 \Bsum\ 으로 충분하고(40시드 중 \Bpeak\ 11승),
고정예산 배치최적화에서만 \Bpeak\ 가 이긴다($73{\sim}83\%$ 승률). 후보생성기
운용의 최종 지표인 shortlist regret에서 \Bpeak\ top-3 정밀검증은 초과
peak-$T$ $1.4\%$(랜덤 $17.8\%$)로, 사인오프 호출 $20\times$ 절감과 사실상
최적 배치를 동시에 달성한다. 결론의 강건성은 네 방향으로 세웠다: 유한 비아 열저항의 컴팩트 모델
사인오프에서도 우위가 유지되고($70\%$ 승률), 실칩 발열맵(HotSpot EV6/gcc)에서는
proxy 1위안이 진짜 최적과 일치하며($k{=}1$ regret $0.0\%$), 과도(gcc 100
인터벌) 진실에서는 \Bsum\ shortlist가 실패하고 \Bpeak\ 만 수렴해 peak-인지가
필수가 되며, 3D 적층(EV6\_3D)에서는 두께-합산 2D 프록시가 3층 결합 진실을
$100\%$ 승률로 랭킹한다. per-zone 가산 분해는 병목 열도메인을 해석 없이
$67\%$ 적중한다. 동시에 레짐 경계가 발열맵·비아 희소도·검증 시간척도에
의존함을 확인해 적용 범위를 매번 명시적으로 좁혔다. 무엇이
이식되고(ground-node·흐름 트리·regret 운용·가산 분해), 무엇이
조건부이며(peak-인지의 레짐), 무엇이 남는가(실단위 보정·경계 지도·분할 풀
랭킹)를 수치로 확정한 것이 본 개념증명의 기여다.

% ============================================================================
\begin{thebibliography}{9}\small
\bibitem{floorplan3d}
Anonymous, ``Thermal-aware floorplanner for 3D IC, including TSVs, liquid
microchannels and thermal domains,'' arXiv:2402.14627, 2024.
\url{https://arxiv.org/abs/2402.14627}
\bibitem{atplace25d}
Q.~Wang et al., ``ATPlace2.5D: Analytical thermal-aware chiplet placement
framework for large-scale 2.5D-IC,'' \emph{Proc. ICCAD}, 2024.
\url{https://yibolin.com/publications/papers/PLACE_ICCAD2024_Wang.pdf}
\bibitem{mlcad2022}
R.~Ranade et al., ``A thermal machine learning solver for chip simulation,''
\emph{Proc. MLCAD}, 2022. \url{https://arxiv.org/pdf/2209.04741}
\bibitem{surrogate2025}
Anonymous, ``Fast thermal-aware chiplet placement assisted by surrogate,''
arXiv:2504.03808, 2025. \url{https://arxiv.org/html/2504.03808v1}
\bibitem{operator2025}
Anonymous, ``From self-attention to operator learning: 3D-IC thermal
simulation,'' arXiv:2510.15968, 2025. \url{https://arxiv.org/html/2510.15968}
\bibitem{hotspot}
K.~Skadron, M.~R. Stan, W.~Huang, S.~Velusamy, K.~Sankaranarayanan, and
D.~Tarjan, ``Temperature-aware microarchitecture,'' \emph{Proc. ISCA}, 2003;
HotSpot benchmark suite (ev6.flp, gcc.ptrace),
\url{https://github.com/uvahotspot/HotSpot}.
\end{thebibliography}

\appendix
% ============================================================================
\section{재현 방법}\label{sec:repro}
% ============================================================================
저장소 루트에서:
\begin{quote}\ttfamily\small
uv sync\\
uv run pytest python/src/thermal -q\hfill\rmfamily(수용 테스트 17개)\\
\ttfamily uv run python -m thermal.cli demo --budget 16\hfill\rmfamily(고정예산 데모)\\
\ttfamily uv run python scripts/repro\_paper\_data.py\hfill\rmfamily(\S\ref{sec:exp} 수치, $\sim$70 s)\\
\ttfamily uv run python scripts/build\_paper\_data.py\hfill\rmfamily(본 논문 전체 수치·그림)
\end{quote}
마지막 명령이 \texttt{draft/paper\_data.json}(모든 수치)과
\texttt{draft/pics/thermal\_*.png,svg}(모든 데이터 그림)를 재생성한다. 난수
시드는 전부 고정되어 있어 표·그림의 수치는 비트 단위로 재현된다(타이밍 표만
기계 의존). 실칩 데이터는 공식 HotSpot 저장소~\cite{hotspot}의
\texttt{examples/example1/\{ev6.flp, gcc.ptrace\}} 사본으로,
\texttt{data/hotspot\_ev6/}에 동봉된다.

\end{document}

