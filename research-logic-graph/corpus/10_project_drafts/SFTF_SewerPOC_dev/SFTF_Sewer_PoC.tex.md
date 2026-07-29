# LaTeX source: SFTF_Sewer_PoC.tex

Source: `D:\__SFTF_Projects(2026)\SFTF_SewerPOC_dev\draft\SFTF_Sewer_PoC.tex`

% !TEX program = xelatex
% SFTF -> 자연유하 하수·우수 관망 라우팅 PoC
% 빌드: xelatex (MiKTeX) + kotex.  latexmk -xelatex SFTF_Sewer_PoC.tex
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

\title{\textbf{SFTF $\rightarrow$ 자연유하 하수·우수 관망 라우팅}\\[2mm]
\large 적층제조 서포트 흐름 텐서장의 토목 이식: 개념증명(PoC)}
\author{SFTF\_SewerPOC\_dev}
\date{2026-06}

\begin{document}
\maketitle

\begin{abstract}
\noindent
적층제조(AM)의 \emph{빌드방향 후보생성기} \textbf{SFTF}(Support Flow Tensor Field)는
삼각망 각 면이 중력(빌드방향)에 등돌린 정도를 흐름으로 보고, 닫힌형 텐서 한 번으로
서포트 물량을 예측한다. 본 PoC는 \textbf{빌드방향 $n=$ 중력}, \textbf{receiver 면 $=$
하류 노드}, \textbf{빌드플레이트(ground node) $=$ 방류구(outfall)} 라는 1:1 치환만으로
SFTF의 서포트 흐름 트리가 곧 \emph{자연유하 배수망}이 되고, 서포트 물량 최소화가 곧
\emph{굴착·관거 비용 최소화}가 됨을 보인다. SFTF는 새 최적화기가 아니라 \emph{값싼
후보생성기 + 적응적 정밀검증}이라는 역할을 그대로 유지한다. numpy/scipy만으로 구현한
코어가 합성 지형에서 값싼 점수 \J\ 와 실제 EPA-SWMM 비용의 순위 상관
$\rho_{\text{Spearman}}=1.0$ 을 달성했고, \emph{적응적 수리검증 확대}(AVE)는 후보의
$23\%$ 만 검증하고도 전수검증과 동일한 최적 방류구를 찾았다.
\end{abstract}

% ============================================================================
\section{서론: 두 문제는 같은 뼈대를 공유한다}
% ============================================================================
적층제조에서 오버행(돌출부)을 받치는 \emph{서포트}는 결국 \emph{빌드플레이트}로
힘이 흘러내리는 트리를 이룬다. 토목의 자연유하 하수·우수 관망에서 빗물·오수는 결국
\emph{방류구}로 물이 흘러내리는 트리를 이룬다. 두 문제 모두

\begin{enumerate}[leftmargin=2.2em,itemsep=1pt]
  \item 각 \emph{소스}(오버행 면 / 유출 노드)가 \emph{하류}로 부하를 떠넘기고,
  \item 그 하류 사슬이 단일 \emph{루트}(빌드플레이트 / 방류구)로 수렴하며,
  \item 총비용(서포트 물량 / 굴착·관거량)이 ``부하 $\times$ 루트까지 거리''에
        지배된다
\end{enumerate}

\noindent 는 \emph{수목형(arborescence)} 구조를 공유한다(그림~\ref{fig:analogy}).
SFTF는 이 구조를 텐서 한 번의 contraction으로 점수화하여, 비싼 정밀해석(AM의 TOMO,
토목의 SWMM) 이전 단계에서 유망 후보를 ms 단위로 랭킹한다. 본 PoC의 기여는 이
프레이밍이 토목 배수망에 \emph{닫힌형으로} 옮겨감을 보이고, 코드와 실제 SWMM 검증으로
실증하는 것이다.

% --- Figure 1: 핵심 유추 ---------------------------------------------------
\begin{figure}[t]
\centering
\begin{tikzpicture}[scale=1.0]
  % ---- 좌: AM 서포트 트리 ----
  \begin{scope}
    \node[font=\small\bfseries] at (2,4.5) {적층제조: 서포트 흐름 트리};
    % build plate
    \draw[line width=1.2pt] (-0.2,0) -- (4.2,0);
    \node[font=\scriptsize] at (3.4,-0.3) {빌드플레이트 (ground node)};
    % build direction
    \draw[->,gray] (4.6,0.3) -- (4.6,2.3) node[midway,right,font=\scriptsize]{$n$};
    % overhang faces (sources)
    \foreach \x/\y in {0.6/3.4, 1.7/3.8, 2.9/3.3, 3.6/2.6}{
      \fill[blue!55!black] (\x,\y) circle (1.6pt);
    }
    % flow edges to a collector then plate
    \coordinate (c1) at (1.6,1.9);
    \draw[flowarr] (0.6,3.4) -- (c1);
    \draw[flowarr] (1.7,3.8) -- (c1);
    \draw[flowarr] (2.9,3.3) -- (c1);
    \draw[flowarr] (3.6,2.6) -- (c1);
    \draw[trunk] (c1) -- (1.6,0);
    \node[font=\scriptsize,blue!55!black] at (0.2,3.4) {$O_i$};
  \end{scope}
  % ---- 화살표 ----
  \node at (5.6,2.2) {\Large $\Longleftrightarrow$};
  % ---- 우: 하수 배수망 ----
  \begin{scope}[xshift=6.4cm]
    \node[font=\small\bfseries] at (2,4.5) {하수·우수: 자연유하 배수망};
    % outfall
    \fill[orange!75!black] (1.6,0) circle (2.4pt);
    \node[font=\scriptsize] at (3.0,-0.3) {방류구 (ground node)};
    % gravity
    \draw[->,gray] (4.6,2.3) -- (4.6,0.3) node[midway,right,font=\scriptsize]{$g$};
    % runoff nodes (sources)
    \foreach \x/\y in {0.6/3.4, 1.7/3.8, 2.9/3.3, 3.6/2.6}{
      \fill[blue!55!black] (\x,\y) circle (1.6pt);
    }
    \coordinate (d1) at (1.6,1.9);
    \draw[flowarr] (0.6,3.4) -- (d1);
    \draw[flowarr] (1.7,3.8) -- (d1);
    \draw[flowarr] (2.9,3.3) -- (d1);
    \draw[flowarr] (3.6,2.6) -- (d1);
    \draw[trunk] (d1) -- (1.6,0);
    \node[font=\scriptsize,blue!55!black] at (0.2,3.4) {$q_i$};
  \end{scope}
\end{tikzpicture}
\caption{핵심 유추. 오버행 면의 흐름량 $O_i$ 가 유출 부하 $q_i$ 로, receiver 탐색이
하류 노드 탐색으로, \term{빌드플레이트}가 \term{방류구}로 1:1 대응한다. 양쪽 모두
부하가 간선(굵은 화살표)을 타고 단일 루트로 수렴하는 수목형 구조다.}
\label{fig:analogy}
\end{figure}

% ============================================================================
\section{기호 대응표}
% ============================================================================
표~\ref{tab:map} 은 SFTF 원식의 기호를 하수 PoC로 옮긴 사전이다. 핵심은 \emph{고정
중력} 케이스에서는 빌드방향 $n$ 이 상수 $\hat z$ 가 되어 방향성이 사라지고, 부하가
지형 법선 대신 \emph{수문 부하} $q_i$ 로 대체된다는 점이다. 재성토 가능한 신규단지에서는
주배수 \emph{방위} $\varphi\in S^1$ 가 자유 설계변수로 부활한다.

\begin{table}[h]
\centering\small
\begin{tabular}{@{}lll@{}}
\toprule
\textbf{SFTF (적층제조)} & \textbf{기호} & \textbf{Sewer PoC (하수/우수)} \\
\midrule
빌드방향(단위벡터) & $n\in S^2$ & 중력(고정 $\hat z$) 또는 주배수 방위 $\varphi\in S^1$ \\
삼각면 $i$ & $i$ & 배수 노드(맨홀·우수받이·DEM 셀) \\
면 법선 / 면적 / 중심 & $m_i,A_i,c_i$ & 지표 경사벡터 / 집수면적 / 좌표 \\
오버행 계수 & $O_i(n)=\max(0,-m_i\!\cdot\!n)$ & 유출 부하 $q_i=C\,i_r A_i$ \\
receiver 탐색 & $j=$ 첫 레이 적중 & 하류 노드 $j=\mathrm{downslope}(i)$ (D8) \\
지지 높이 & $h_{ij}=(c_i-c_j)\!\cdot\!n$ & 표고 낙차 $\Delta z_{ij}=z_i-z_j$ \\
면-면 가중 & $w_{ij}=O_i/(1+\alpha h_{ij})$ & $w_{ij}=q_i/(1+\alpha d_{ij})$ \\
바닥판 항 & $B(n)$ & 방류구 항 $B_{\text{sewer}}$ \\
통합 Rayleigh & $\tilde R=R+B$ & 통합 배수비용 $\tilde R_{\text{sewer}}$ \\
분할 + 재배향 & partition+reorient & 소유역 분할 + 다방류구 \\
TOMO 검증 + AVE & verify+escalate & SWMM 검증 + 적응확대 \\
\bottomrule
\end{tabular}
\caption{SFTF $\leftrightarrow$ Sewer 기호 대응. $\alpha=1/D$, $D=$ 대상 유역의
특성길이(바운딩박스 대각선).}
\label{tab:map}
\end{table}

% ============================================================================
\section{수식 매핑}
% ============================================================================

\subsection{유출(소스) 항: overhang $\rightarrow$ runoff}
SFTF는 면이 빌드방향에 등돌린 정도를 ``받쳐야 할 양''으로 본다. 하수에서 ``흘려보내야
할 양''은 지형 법선이 아니라 합리식 부하다:
\begin{equation}
  q_i \;=\; C_i\, i_r\, A_i \qquad (C:\text{유출계수},\; i_r:\text{강우강도},\;
  A_i:\text{집수면적}).
\end{equation}

\subsection{receiver 탐색: 레이캐스트 $\rightarrow$ D8 흐름방향}
SFTF는 면 $i$ 에서 $-n$ 으로 레이를 쏴 첫 유효 receiver 면을 찾는다. 하수에서는 노드
$i$ 의 8-이웃 중 \emph{최급강하} 방향을 택한다(그림~\ref{fig:d8}). 이는 GIS 수문학의
D8 흐름방향 $+$ 흐름누적과 동형이며, 유효 아크 집합 $R(n)=\{(i\!\to\! j)\}$ 가 곧
배수망 위상이다.

% --- Figure 2: D8 ----------------------------------------------------------
\begin{figure}[h]
\centering
\begin{tikzpicture}[scale=1.0]
  % 3x3 grid of cells with elevations
  \def\vals{{ {9.0,8.4,7.1}, {8.2,6.0,5.2}, {7.0,4.1,3.0} }}
  \foreach \r in {0,1,2}{
    \foreach \c in {0,1,2}{
      \pgfmathsetmacro\val{\vals[\r][\c]}
      \node[cell] (n\r\c) at (\c*1.0, -\r*1.0) {\val};
    }
  }
  \node[font=\scriptsize] at (1,0.85) {셀 표고 $z$ (낮을수록 하류)};
  % center cell n11 = 6.0 ; 8 neighbors; steepest descent to n22 (3.0) diag
  \foreach \r/\c in {0/0,0/1,0/2,1/0,1/2,2/0,2/1}{
    \draw[->,gray!55] (n11) -- (n\r\c);
  }
  % chosen steepest descent (to lowest reachable -> n22=3.0, diagonal)
  \draw[trunk] (n11) -- (n22);
  \node[font=\scriptsize,orange!75!black,anchor=west]
        at (2.7,-2.0) {최급강하 receiver $j=\mathrm{downslope}(i)$};
  \node[font=\scriptsize,blue!55!black] at (-0.65,-1.0) {$i$};
\end{tikzpicture}
\caption{D8 최급강하 receiver. 중심 노드 $i$ 의 8개 이웃 중 단위거리당 표고 낙차
$\Delta z_{ij}/d_{ij}$ 가 최대인 이웃 하나를 하류 $j$ 로 택한다(굵은 화살표). 대각
이웃은 거리 $\sqrt2$ 로 정규화한다.}
\label{fig:d8}
\end{figure}

\subsection{흐름 텐서 $F$ 와 점수 항 $R,P$}
유효 아크 집합 위에서 SFTF의 텐서 누적을 그대로 옮긴다:
\begin{align}
  F(d) &= \sum_{(i,j)\in R} w_{ij}\, A_i A_j\, m_i m_j^{\!\top},
        \qquad w_{ij}=\frac{q_i}{1+\alpha\,\Delta z_{ij}}, \\
  \R &= \max\!\big(0,\; -\,d^{\!\top} F_{\text{sym}}\, d\big),
        \qquad F_{\text{sym}}=\tfrac12(F+F^{\!\top}), \\
  \PP &= \sum_{(i,j)\in R} q_i\, A_i A_j .
\end{align}
재성토 케이스에서 $\R(\varphi)$ 는 주배수 방위별 \emph{총 관거비용 프록시}가 된다.
고정 중력 케이스에서는 텐서 contraction이 스칼라 누적비용으로 축약된다. $\R,\PP$ 는
지형과 D8에만 의존하므로 \emph{방류구 선택과 무관}하다 --- 이 사실이 다음 절의 핵심
결과로 이어진다.

\subsection{$\star$ ground node $=$ 방류구}
SFTF에서 받쳐 줄 면이 없는 오버행은 결국 빌드플레이트가 받친다. 이를 ``법선이 $n$ 인
가상 receiver(ground node)''로 두면 빌드플레이트 항 $B(n)$ 이 augmented 텐서의 정확한
Rayleigh 기여가 된다. 하수에서 어떤 노드의 흐름도 결국 방류구로 빠지므로
(그림~\ref{fig:ground}),
\begin{equation}
  \B \;=\; \sum_{i} q_i\,\big(1+\alpha\, L_{iP}\big),
  \qquad L_{iP}=\underbrace{\lVert \mathbf{x}_i-\mathbf{x}_P\rVert}_{\text{수평거리}}
        +\;\lambda\,\underbrace{\max(0,\,z_P-z_i)}_{\text{펌프 페널티}} ,
  \label{eq:B}
\end{equation}
여기서 $P$ 는 방류구, $\lambda$ 는 방류구보다 \emph{낮은} 부하(자연유하 불가 $\to$
펌프 필요)에 매기는 벌점이다. \term{$B$ 만이 방류구에 의존}하므로, 방류구·분할 후보의
순위는 전적으로 $B$ 가 결정한다 --- 적층제조에서 ``$B$(빌드플레이트 항)가 가장 강한
단일 예측자''였던 결과의 직접적 재현이다. 흥미롭게도 식~\eqref{eq:B} 는 기존 하수문헌의
\emph{누적유량 최소화(minimum cumulative flow)} 목적과 같은 자리를 가리키며, SFTF의
ground-node 텐서가 그 휴리스틱에 \emph{닫힌형 텐서 해석}을 부여한다.

% --- Figure 3: ground node = outfall --------------------------------------
\begin{figure}[h]
\centering
\begin{tikzpicture}[scale=1.0]
  % several nodes draining to a single virtual outfall
  \foreach \x/\y/\nm in {0/3/a, 1.3/3.4/b, 2.6/3.1/c, 3.7/2.6/d, 0.7/2.2/e}{
    \fill[blue!55!black] (\x,\y) circle (1.7pt);
  }
  \node[draw,fill=orange!75!black,circle,inner sep=1.6pt,label=below:{\scriptsize 방류구 $P$ (가상 receiver)}]
       (P) at (2.0,0.4) {};
  \foreach \x/\y in {0/3, 1.3/3.4, 2.6/3.1, 3.7/2.6, 0.7/2.2}{
    \draw[flowarr,dashed] (\x,\y) -- (P);
  }
  \node[font=\scriptsize,blue!55!black] at (-0.35,3) {$q_i$};
  \draw[<->,gray] (4.3,0.4) -- (4.3,2.6)
        node[midway,right,font=\scriptsize]{$L_{iP}$};
  \node[font=\small] at (2.0,4.1)
        {모든 부하 $\to$ 단일 가상 receiver: $\tilde R = R + B$};
\end{tikzpicture}
\caption{ground-node 텐서. 방류구 $P$ 를 ``법선이 배수방향인 가상 노드''로 추가하면
모든 잔여 부하 $q_i$ 가 $P$ 로 수렴하고, 그 기여 $B=\sum_i q_i(1+\alpha L_{iP})$ 가
augmented Rayleigh $\tilde R=R+B$ 의 정확한 항이 된다.}
\label{fig:ground}
\end{figure}

\subsection{후보 점수 \J}
최종 후보 점수는 세 항의 가중합이다:
\begin{equation}
  \boxed{\;\J_{\text{sewer}} \;=\; w_R\,\R \;+\; w_P\,\PP \;+\; w_B\,\B\;}
  \qquad (\text{기본값 } w_R=w_P=w_B=1).
  \label{eq:J}
\end{equation}
$\R,\PP$ 가 방류구 무관이므로 후보 간 \J\ 의 \emph{순서}는 $B$ 가 지배한다. 합성
지형 데모에서 최적 방류구의 $B/\J = 58.4\%$ 로, 단일 항이 점수의 과반을 차지함을
관측했다.

\subsection{분할 $=$ 다방류구 (SFTF-Clustering 이식)}
SFTF-Clustering은 분할 비용을 \emph{cut-induced}(간선을 끊는 비용)와
\emph{reorientation}(각 조각이 자기 최적 방향에 서는 이득)으로 분해하고, 텐서
가산성 $F(\text{partition})=\sum_{\text{parts}} F_{\text{part}}$ 로 후자를 \emph{재최적화
없이} 얻는다. 하수에서는 유역을 소유역으로 나눠 각자 가까운 방류구로 빠지게 하는
것에 대응한다(그림~\ref{fig:partition}). 본 구현은 지형+표고+흐름누적을 융합한 특징
공간에서 $k$-medoids 로 소유역을 나누며, medoid 노드가 곧 후보 방류구가 된다.

% --- Figure 4: partition = multi-outfall ----------------------------------
\begin{figure}[h]
\centering
\begin{tikzpicture}[scale=1.0]
  % three sub-basins as shaded regions with a medoid outfall each
  \begin{scope}
    \fill[blue!7]   (0,0) rectangle (2.4,2.4);
    \fill[teal!9]   (2.4,0) rectangle (4.8,2.4);
    \fill[orange!9] (0,2.4) rectangle (4.8,4.0);
    \draw[gray!50] (0,0) rectangle (4.8,4.0);
    \draw[gray!50,dashed] (2.4,0)--(2.4,2.4) (0,2.4)--(4.8,2.4);
  \end{scope}
  % medoid outfalls
  \foreach \x/\y in {1.2/0.5, 3.6/0.5, 2.4/2.9}{
    \node[draw,fill=orange!75!black,circle,inner sep=1.4pt] at (\x,\y) {};
  }
  % sample nodes draining to nearest medoid
  \foreach \x/\y/\ox/\oy in {
     0.6/1.8/1.2/0.5, 1.8/1.5/1.2/0.5,
     3.2/1.7/3.6/0.5, 4.2/1.2/3.6/0.5,
     1.4/3.4/2.4/2.9, 3.4/3.5/2.4/2.9}{
     \fill[blue!55!black] (\x,\y) circle (1.3pt);
     \draw[flowarr] (\x,\y) -- (\ox,\oy);
  }
  \node[font=\scriptsize] at (2.4,-0.4)
       {소유역 3개 $\to$ 방류구 3개 (medoid)};
\end{tikzpicture}
\caption{소유역 분할 $=$ 다방류구. 융합 특징공간의 $k$-medoids 가 유역을 소유역으로
나누고, 각 medoid(주황)가 그 소유역의 방류구가 된다. 텐서 가산성으로 분할안마다
SWMM/MIP 재실행 없이 비용변화를 닫힌형으로 추정한다.}
\label{fig:partition}
\end{figure}

% ============================================================================
\section{PoC 파이프라인과 구현}
% ============================================================================
구현은 numpy/scipy만으로 동작하는 코어와, 선택적 외부 의존성(EPA-SWMM, DEM 로더)으로
나뉜다(그림~\ref{fig:pipeline}). 핵심 가설은 \emph{값싼 \J\ 의 순위가 비싼 SWMM 비용의
순위를 잘 예측}(목표 $\rho\ge0.8$)하여, 상위 소수만 정밀검증하면 된다는 것이다.

% --- Figure 5: pipeline ----------------------------------------------------
\begin{figure}[h]
\centering
\begin{tikzpicture}[node distance=6mm and 9mm]
  \node[box] (terr) {지형/DEM\\\scriptsize \texttt{terrain.py}};
  \node[box,right=of terr] (d8) {D8 라우팅\\흐름누적\\\scriptsize \texttt{flow\_tensor}};
  \node[box,right=of d8] (score) {점수 $\J{=}R{+}P{+}B$\\\scriptsize \texttt{drainage\_score}};
  \node[hl,right=of score] (ave) {AVE 적응검증\\\scriptsize \texttt{escalate.py}};
  \node[box,right=of ave] (swmm) {EPA-SWMM\\\scriptsize \texttt{swmm\_io.py}};
  \draw[flowarr] (terr)--(d8);
  \draw[flowarr] (d8)--(score);
  \draw[flowarr] (score)--(ave);
  \draw[flowarr] (ave)--node[above,font=\scriptsize]{상위 K}(swmm);
  % partition branch
  \node[box,below=10mm of score] (part) {소유역 분할\\$k$-medoids\\\scriptsize \texttt{partition.py}};
  \draw[flowarr] (d8) |- (part);
  \draw[flowarr] (part) -| (ave);
  % feedback
  \draw[flowarr,dashed] (swmm.south) to[out=-90,in=-90]
        node[below,font=\scriptsize]{불확실 $\to$ 검증 확대}(ave.south);
\end{tikzpicture}
\caption{PoC 파이프라인. 파란 단계는 numpy/scipy만으로 동작하고, 주황 AVE 단계가
검증 예산을 제어한다. SWMM(외부 엔진)은 상위 K 후보에만 호출되며, 불확실 신호가
켜지면 검증을 확대한다.}
\label{fig:pipeline}
\end{figure}

% ============================================================================
\section{적응적 수리검증 확대 (AVE)}
% ============================================================================
기존 메타휴리스틱은 모든 후보에 시뮬레이터를 \emph{균일하게} 호출한다. AVE는 값싼 \J\
로 후보를 정렬한 뒤 상위 \texttt{init\_k} 개만 먼저 검증하고, \emph{불확실성 트리거}가
켜질 때만 한 후보씩 검증을 넓힌다(그림~\ref{fig:ave}):
\begin{description}[leftmargin=2.0em,itemsep=1pt]
  \item[근소차(near-tie)] 다음 후보의 \J\ 가 현재 최선과 (상대) $\le$ \texttt{gap\_rel}
        이면 값싼 점수로 분간 불가 $\to$ 검증.
  \item[순위역전(inversion)] 검증된 것 중 \emph{검증기 최선}이 \J\emph{-최선}과
        불일치하면 값싼 순서를 덜 신뢰 $\to$ 더 탐색.
  \item[위험 플래그(risk)] 월류(surcharge)·경계해 등 외부 위험함수가 켜지면 강제 확대.
\end{description}
적층제조에서 AVE는 최악비율을 $17.57\to1.37$ 로 줄였다. 본 PoC의 합성 지형(후보 13개)
에서 AVE는 \term{3개($23\%$)만 검증}하고도 전수검증과 \emph{동일한} 최적 방류구를
찾았다(절감 10회).

% --- Figure 6: AVE ---------------------------------------------------------
\begin{figure}[h]
\centering
\begin{tikzpicture}[scale=1.0]
  % candidates sorted by J (bars), top-k verified, escalate on trigger.
  % color passed directly per bar: orange=verified, red=escalated, lightblue=skipped
  \foreach \i/\h/\col in {
      0/2.4/{orange!75!black}, 1/2.2/{orange!75!black}, 2/2.1/{orange!75!black},
      3/1.5/{red!70!black}, 4/1.2/{blue!18}, 5/1.0/{blue!18},
      6/0.9/{blue!18}, 7/0.8/{blue!18}}{
    \pgfmathsetmacro\xx{\i*0.62}
    \fill[\col] (\xx,0) rectangle (\xx+0.46,\h);
  }
  \draw[->] (-0.2,0) -- (5.3,0) node[right,font=\scriptsize]{후보 (\J\ 오름차순)};
  \draw[->] (-0.2,0) -- (-0.2,2.8) node[above,font=\scriptsize]{\J};
  % brackets
  \draw[decorate,decoration={brace,amplitude=4pt}]
       (0,2.6) -- (1.7,2.6) node[midway,above,font=\scriptsize,yshift=2pt]
       {init\_k 검증};
  \draw[decorate,decoration={brace,amplitude=4pt}]
       (1.86,1.7) -- (2.48,1.7) node[midway,above,font=\scriptsize,yshift=2pt]
       {근소차 $\to$ 확대};
  \node[font=\scriptsize,blue!30!black] at (4.4,1.3)
       {미검증 (예산 절감)};
\end{tikzpicture}
\caption{AVE 동작. 후보를 값싼 \J\ 로 정렬(막대 높이)한 뒤 상위 \texttt{init\_k}
(주황)만 검증하고, 근소차 트리거가 켜진 후보(빨강)만 한 칸씩 확대 검증한다. 나머지
(연파랑)는 검증하지 않아 시뮬레이터 예산을 아낀다.}
\label{fig:ave}
\end{figure}

% ============================================================================
\section{결과}
% ============================================================================
합성 지형(경사평면 $+$ 가우시안 구릉 $+$ 잡음, $50\times50$, seed $0$)에서 측정한
PoC 지표를 표~\ref{tab:results} 에 정리한다. 값싼 \J\ 가 \emph{해석적 검증기}와
\emph{실제 EPA-SWMM 엔진} 양쪽 모두와 완전한 순위 일치($\rho=1.0$)를 보였고, AVE는
예산의 $23\%$ 만으로 동일 최적해를 회복했다.

\begin{table}[h]
\centering\small
\begin{tabular}{@{}lc@{}}
\toprule
\textbf{지표} & \textbf{값} \\
\midrule
$\rho_{\text{Spearman}}(\J,\;\text{해석적 비용})$ & $+1.000$ \quad(목표 $\ge0.8$) \\
$\rho_{\text{Spearman}}(\J,\;\text{실제 SWMM 비용})$ & $+1.000$ \\
hit@1 (\J\ 최선 $=$ 검증기 최선) & 참 \\
최적해의 항 분해 $B/\J$ & $58.4\%$ \\
AVE 검증 예산 & $3/13\;(23\%)$, 절감 $10$ \\
SWMM 유량연속성 오차 & $0.0\%$ \\
수용 테스트 & $28$ 통과 (numpy-only $23$ $+$ guarded $5$) \\
\bottomrule
\end{tabular}
\caption{PoC 핵심 지표. 실제 SWMM 검증은 D8 수목망으로부터 \texttt{.inp} 를 자동
작성·실행하고 월류(surcharge) 체적을 판독하여 산출했다.}
\label{tab:results}
\end{table}

% ============================================================================
\section{최신문헌 대비 차별점}
% ============================================================================
기존 하수 관망 최적설계는 (a) 위상(layout) 최적화와 (b) 수리설계(diameter/slope)
최적화로 나뉘며, 대표 갈래는 MIP$+$최단경로, 신장트리$+$PSO, Steiner tree, 그래프이론
기반 (분산형) 레이아웃, 누적유량 최소화 등이다. SFTF-Sewer의 포지셔닝은 다음과 같다.

\begin{description}[leftmargin=2.4em,itemsep=2pt]
  \item[(D1) 최적화기가 아닌 후보생성기·웜스타트] 닫힌형 텐서$+$ground-node 스칼라로
        유망 방류구·분할을 ms 단위로 \emph{랭킹}한 뒤 상위 소수만 MIP/SWMM에 넘긴다.
  \item[(D2) ground-node 텐서 $=$ 방류구의 닫힌형 해석] $\tilde R=R+B$ 라는 단일
        contraction이 ``누적유량 최소화'' 휴리스틱에 물리적·텐서적 근거를 부여한다.
  \item[(D3) 텐서 가산성으로 분할비용을 재최적화 없이 추정] $F(\text{partition})
        =\sum F_{\text{part}}$ 로 소유역별 재배향 이득을 닫힌형으로 얻는다.
  \item[(D4) 적응적 수리검증 확대(AVE)] 불확실 케이스에만 SWMM 예산을 확대한다
        (본 PoC: 예산 $23\%$).
  \item[(D5) DEM 흐름라우팅과 망 최적화의 명시적 결합] receiver 탐색을 D8 흐름방향과
        동일시하여 수문(흐름누적)과 최소비용 arborescence를 하나의 텐서 점수로 잇는다.
\end{description}

% ============================================================================
\section{정직한 한계와 향후 과제}
% ============================================================================
\begin{itemize}[leftmargin=1.6em,itemsep=1pt]
  \item SFTF가 주는 것은 \emph{위상·방류구·분할의 웜스타트}이지 정밀 수리설계가 아니다.
        관경·경사·관저고·최소토피·자정유속은 여전히 SWMM/MIP의 몫이다.
  \item 굴착비용은 하류로 깊이가 누적되며 비선형으로 커진다. 단순 $1/(1+\alpha d)$
        감쇠는 1차 근사이며, 깊이 누적 보정항(Clustering의 $0.80\to0.90$ 보정과 동형)이
        정확도를 끌어올릴 것이다.
  \item 가압식 상수도(루프·다중소스)에는 단일 방향 텐서 $F(n)$ 이 부적합하며, 거기서는
        (D1)(D4) 전략만 전이된다.
  \item 현재 SWMM 검증은 DWF 정상상태 부하 기반이다. 실 DEM $+$ 실 강우 시계열을 쓴
        동적 검증, 재성토 방위 $\varphi$ 스윕의 CLI 노출이 다음 단계다.
\end{itemize}

% ============================================================================
\section{결론}
% ============================================================================
빌드방향 $\to$ 중력, receiver 면 $\to$ 하류 노드, 빌드플레이트 $\to$ 방류구라는 세
치환만으로 적층제조 서포트 흐름 텐서장이 자연유하 배수망 라우팅으로 옮겨감을 보였다.
값싼 텐서 점수 \J\ 가 실제 EPA-SWMM 비용 순위를 완전히 예측했고($\rho=1.0$), AVE는
검증 예산의 $23\%$ 만으로 동일 최적해를 회복했다. SFTF는 토목 배수망에서도 \emph{값싼
후보생성기 $+$ 적응적 정밀검증}이라는 역할을 일관되게 유지한다.

\bigskip
\noindent\footnotesize\textit{재현:} \texttt{uv sync --python 3.12} 후
\texttt{uv run python -m sewer.cli demo --ny 50 --nx 50 --seed 0};
테스트 \texttt{uv run pytest python/src/sewer -q}.
수식 매핑 원본은 \texttt{draft/SFTF\_Sewer\_research\_plan.md} 참조.

\end{document}

