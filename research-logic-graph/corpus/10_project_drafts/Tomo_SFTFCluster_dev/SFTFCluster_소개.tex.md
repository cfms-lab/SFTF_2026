# LaTeX source: SFTFCluster_소개.tex

Source: `D:\__SFTF_Projects(2026)\Tomo_SFTFCluster_dev\draft\SFTFCluster_소개.tex`

\documentclass[11pt,a4paper]{article}

% ---- 한글 + 수식 ----
\usepackage{kotex}
\usepackage{amsmath,amssymb,amsfonts,bm}
\usepackage{graphicx}
\graphicspath{{pics/}}
\usepackage{booktabs}
\usepackage{float}
\usepackage{geometry}
\geometry{margin=25mm}
\usepackage[hidelinks]{hyperref}
\usepackage{enumitem}
\usepackage{tcolorbox}
\usepackage{xcolor}
\usepackage[font=small,labelfont=bf]{caption}
\renewcommand{\figurename}{그림}
\renewcommand{\tablename}{표}

\renewcommand{\thefootnote}{\arabic{footnote}}
\setlist{itemsep=2pt,topsep=4pt}

\newtcolorbox{readbox}[1][]{
  colback=blue!4, colframe=blue!40!black, boxrule=0.4pt,
  left=6pt,right=6pt,top=4pt,bottom=4pt, #1}

\newtcolorbox{notebox}[1][]{
  colback=orange!6, colframe=orange!55!black, boxrule=0.4pt,
  left=6pt,right=6pt,top=4pt,bottom=4pt, #1}

\title{\textbf{SFTF-Cluster 쉽게 읽기}\\[4pt]
\large 3D 모델을 ``어떻게 나누면'' 각 조각을 서포트 적게 출력할까\\[2pt]
\normalsize ── 인문계 고등학생을 위한 개념·수식·실험 결과 풀어 읽기 ──}
\author{}
\date{}

\begin{document}
\maketitle

\begin{readbox}
\textbf{이 글의 목표.} 앞선 \textbf{SFTF}는 ``한 물체를 어느 방향으로 출력할까''를
빠르게 추천하는 방법이었습니다. \textbf{SFTF-Cluster}는 한 걸음 더 나아가,
``물체를 몇 조각으로 나누고, 각 조각을 자기에게 좋은 방향으로 세우면 서포트가 더
줄어들까?''를 묻습니다. 이 글은 논문의 수식과 실험을 고등학생도 따라 읽을 수 있도록,
어려운 말에는 각주를, 중요한 식에는 바로 밑에 우리말 설명을 붙인 해설본입니다.
마지막에는 실제 오픈소스 슬라이서 \textbf{CuraEngine}으로 열두 개 형상을 검증한
결과와, 거기서 배운 \emph{정직한 결론}까지 함께 읽습니다.
\end{readbox}

\tableofcontents
\bigskip

%======================================================================
\section{먼저 큰 그림: 왜 3D 모델을 나누는가}
%======================================================================

\subsection{3D 프린팅과 ``서포트''라는 골칫거리}

3D 프린터는 물체를 아래에서 위로 한 층씩 쌓습니다. 그래서 아래에 받침이 없는
부분, 즉 \textbf{오버행}\footnote{오버행(overhang): 처마처럼 아래가 비어 있는데
옆으로 튀어나온 부분. FDM 프린팅에서는 너무 누운 면이 흘러내릴 수 있어 임시 받침인
서포트가 필요합니다.}에는 임시 받침인 \textbf{서포트}\footnote{서포트(support):
공중에 뜬 부분을 받치려고 함께 출력하는 임시 구조물. 출력이 끝나면 뜯어내
버리므로, 재료·시간 낭비이자 표면 흠집의 원인입니다. 그래서 ``서포트를 줄이는 것''이
3D 프린팅의 큰 목표입니다.}가 필요합니다. 서포트는 다 쓰고 버리는 구조라, 재료와
시간을 낭비하고 표면에 흔적을 남깁니다.

앞선 SFTF는 ``이 물체를 통째로 놓는다면 어느 방향이 서포트를 적게 만들까''를 빠르게
골라 줍니다. 그런데 어떤 물체는 통째로는 좋은 방향을 찾기 어렵습니다. 예를 들어 사람
모형(마네킨)을 생각해 봅시다. 몸통에 좋은 방향이 팔에는 나쁠 수 있고, 머리에 좋은
방향이 다리에는 나쁠 수 있습니다. 물체를 몇 조각으로 나누면 각 조각을 \emph{자기에게
좋은 방향}으로 세워 출력할 수 있습니다. 게다가 프린터 작업 공간보다 큰 대형 물체는
애초에 나누지 않으면 출력조차 안 됩니다.

\begin{notebox}
\textbf{하지만 마음대로 자르면 안 됩니다.} 조각을 나누면 서포트가 줄 수도 있지만,
새로운 절단면이 생기고, 나중에 조립해야 하며, 원래 한 물체 안에서 서로 받쳐 주던
관계가 끊길 수도 있습니다. SFTF-Cluster의 목표는 ``출력에 도움이 되는 방향으로''
나누는 것입니다.
\end{notebox}

\subsection{SFTF-Cluster의 아이디어 한 문장}

\begin{readbox}
\textbf{한 줄 요약.} SFTF-Cluster는 SFTF가 계산 도중에 이미 알고 있던
\textbf{면별 지지흐름 정보}를 버리지 않고 보존한 뒤, ``비슷한 지지 역할을 하는 면들''을
같은 조각으로 묶어 주는 메쉬 분할 방법입니다.
\end{readbox}

여기서 \textbf{메쉬 분할}\footnote{메쉬(mesh)는 3D 물체 표면을 잘게 쪼갠 삼각형들의
모임입니다. 메쉬 분할은 이 삼각형들을 여러 그룹으로 나누어 ``조각''을 만드는 일입니다.}은
``수많은 삼각형 면을 몇 개의 그룹으로 나누는 일''입니다. 기존 방법은 보통 면의 위치나
모양만 봅니다. SFTF-Cluster는 여기에 ``이 면은 지지가 필요한가, 바닥까지 떨어지는가,
다른 면이 받쳐 주는가'' 같은 \textbf{출력 물리 정보}를 더합니다. 그림~\ref{fig:taxonomy}는
여러 분할 방법을 한눈에 정리한 ``지도''입니다.

\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{fig_method_taxonomy_from_pdf-1.png}
\caption{여러 분할 방법의 지도. \textbf{왼쪽}은 면의 위치·모양만 보는 기존 방법들(좌표
$k$-평균, 평면으로 자르기, 그래프 기반 방법 등)입니다. \textbf{오른쪽}이 이 글의 주제인
SFTF 기반 방법으로, SFTF가 계산해 둔 ``지지 정보''를 분할에 함께 사용합니다.}
\label{fig:taxonomy}
\end{figure}

\subsection{이 글의 두 부분}

이 글은 크게 두 부분입니다. 앞의 \S2--\S5는 \emph{방법}, 즉 ``어떻게 나누고 어떻게
채점하는가''를 그림과 수식으로 풀어 읽습니다. 뒤의 \S6--\S8은 \emph{실험 결과}, 즉
``실제 슬라이서로 열두 개 형상을 돌려 보니 무엇이 사실이었나''를 정직하게 정리합니다.
특히 뒷부분에는 처음 예상과 달랐던 \textbf{반전 결과}가 세 가지 있으니 끝까지 읽어 보세요.

%======================================================================
\section{준비물: 이 정도 개념이면 충분합니다}
%======================================================================

\subsection{면, 법선, 빌드방향}

각 삼각형 면 $i$에 대해 세 가지를 씁니다.

\begin{itemize}[leftmargin=1.6em]
\item $c_i$: 면의 중심점. 삼각형 한가운데 위치입니다.
\item $m_i$: 면의 법선벡터\footnote{법선벡터(normal vector): 면에 수직인 길이 1짜리
화살표. 그 면이 어느 쪽을 바라보는지 나타냅니다.}. 면이 바라보는 방향입니다.
\item $A_i$: 면의 넓이. 큰 면은 작은 면보다 더 중요하게 다룹니다.
\end{itemize}

출력 방향은 길이 1인 화살표 $n$으로 씁니다. 두 화살표의 내적\footnote{내적(dot product):
두 화살표가 얼마나 같은 쪽을 향하는지 재는 곱셈. 여기서는 결과가 $-1$(정반대)에서
$+1$(같은 방향) 사이 값입니다.} $m_i\cdot n$은 ``면이 출력 방향과 얼마나 같은 쪽을
보는가''를 알려 줍니다. 같은 쪽이면 양수, 반대쪽이면 음수, 직각이면 0입니다.

\subsection{군집화: 비슷한 것끼리 묶기}

SFTF-Cluster에서 ``Cluster''는 \textbf{군집화}\footnote{군집화(clustering): 비슷한
데이터끼리 자동으로 묶는 방법입니다. 예를 들어 학생들의 키와 몸무게를 보고 비슷한
체형끼리 그룹을 만드는 일을 생각하면 됩니다.}를 뜻합니다. 각 면을 하나의 데이터 점으로
보고, 그 면의 위치와 지지 특징이 비슷하면 같은 조각에 넣습니다.

\begin{notebox}
\textbf{중요한 차이.} 좌표만 보는 군집화는 ``가까운 면''을 잘 묶습니다. 하지만
SFTF-Cluster는 ``출력할 때 같은 역할을 하는 면''도 같이 봅니다. 그래서 멀리 떨어져
있어도 서로 받치고 받는 관계라면 같은 조각에 묶일 수 있습니다.
\end{notebox}

%======================================================================
\section{SFTF에서 가져오는 면별 특징}
%======================================================================

\subsection{먼저 기준 빌드방향을 고른다}

SFTF-Cluster는 아무 방향이나 기준으로 삼지 않습니다. SFTF v2가 면적에 비례해 뽑은
표면 표본과 무차원 높이를 이용해 $2{,}048$개 후보 방향을 평가하고, 서로 $12^\circ$ 이상
떨어진 점수 분지 가운데 가장 좋은 방향을 $n^\ast$로 고릅니다. 이 방향에서 각 면이 어떤
지지 역할을 하는지 조사하므로, 물체 크기를 바꾸어도 방향 판정의 의미가 유지됩니다.

\begin{readbox}
\textbf{한 줄 요약.} 원래 SFTF는 최종 점수만 남기고 면별 중간 정보를 버렸습니다.
SFTF-Cluster는 그 버려지던 중간 정보를 ``분할의 힌트''로 다시 사용합니다.
\end{readbox}

\subsection{기본 면 특징 세 가지}

기준 방향을 $n=n^\ast$라고 합시다. 먼저 바닥판 높이를 정합니다.

\[
z_{\mathrm{plate}}(n)=\min_{v\in V} v\cdot n
\]

\noindent\textit{읽기:} 모든 꼭짓점 $v$를 출력 방향 $n$으로 재서, 가장 낮은 값을
바닥판 높이로 둡니다. 즉 물체가 프린터 바닥에 닿는 높이입니다.

각 면의 세 기본 특징은 다음입니다.

\[
O_i(n)=\max(0,-m_i\cdot n)
\]
\noindent\textit{읽기:} 면이 아래로 처질수록 값이 커집니다. 위를 보는 면은 0입니다.
즉 $O_i$는 ``오버행 정도''입니다.

\[
\tau_i(n)=m_i\cdot n
\]
\noindent\textit{읽기:} 면이 위를 보면 양수, 아래를 보면 음수입니다. $O_i$가
``아래로 처진 정도만'' 세는 값이라면, $\tau_i$는 위아래 방향 정보를 그대로 남겨 둡니다.

\[
\eta_i(n)=\frac{c_i\cdot n-z_{\mathrm{plate}}(n)}{D}
\]
\noindent\textit{읽기:} 면 중심이 바닥판에서 얼마나 높이 떠 있는지를 바운딩박스 대각선
$D$로 나눈 무차원 높이입니다. 높이 떠 있는 오버행은 긴 서포트 기둥이 필요할 가능성이
크지만, 같은 모양을 확대했다고 점수의 뜻이 달라지지는 않습니다.

\subsection{지지 역할: none, face, bed}

오버행 면에서 아래쪽 $-n$ 방향으로 가상의 빛줄기를 쏘면, 바로 아래에서 받쳐 주는 면을
찾을 수 있습니다. 이를 \textbf{레이캐스팅}\footnote{레이캐스팅(ray casting): 한 점에서
가상의 직선을 쏘아 처음 부딪히는 대상을 찾는 계산입니다. 여기서는 ``오버행 아래에
받쳐 줄 면이 있는가''를 찾습니다.}이라고 합니다. 그 결과 각 면은 세 역할 중 하나가 됩니다.

\[
\rho_i\in\{\mathrm{none},\mathrm{face},\mathrm{bed}\}
\]

\begin{itemize}[leftmargin=1.6em]
\item $\mathrm{none}$: 오버행이 아니라 지지가 필요 없는 면.
\item $\mathrm{face}$: 오버행이지만 아래의 다른 면이 받쳐 주는 면.
\item $\mathrm{bed}$: 아래에 받쳐 줄 면이 없어 바닥판까지 서포트가 내려가야 하는 면.
\end{itemize}

그림~\ref{fig:flow}는 이 두 지지 방식을 그림으로 보여 줍니다. 추가로 $h_i$는 받침까지의
높이, $t_i$는 받쳐 주는 면 번호, $r_i$는 다른 오버행들이 이 면으로 들어오는 횟수입니다.
$r_i$가 크면 ``여러 면을 받쳐 주는 중요한 받침면''입니다. 바로 이 $\rho_i$(어느 종류의
받침으로 흐르는가)가 SFTF가 최종 점수로 압축하며 버렸던 정보이고, SFTF-Cluster가
되살리는 핵심입니다.

\begin{figure}[H]
\centering
\includegraphics[width=0.82\textwidth]{FTree4x_fig1_unified_flow_supp-1.png}
\caption{오버행 면이 지지받는 두 가지 방식. 아래로 처진 면은 (1) 바로 아래 다른 면이
받쳐 주거나(\emph{면-면} 지지), (2) 받쳐 줄 면을 못 찾아 바닥판까지 서포트 기둥이
내려가야 합니다(\emph{바닥} 지지). SFTF는 이 흐름을 하나의 점수로 합쳐 버리지만,
SFTF-Cluster는 면마다 ``어떤 지지를 하는지''를 그대로 기억해 분할에 씁니다.}
\label{fig:flow}
\end{figure}

\subsection{특징행렬 만들기}

이제 각 면을 다섯 숫자로 표현합니다.

\[
\Phi_{\mathrm{SFTF}}
=\operatorname{zscore}\big([O_i,\tau_i,\eta_i,h_i/D,r_i]\big)
\]

\noindent\textit{읽기:} 각 면마다 오버행, 기울기, 높이, 지지 높이, 받는 횟수를 모아
표를 만듭니다. $\operatorname{zscore}$는 숫자들의 단위를 맞추는 표준화입니다.

\begin{notebox}
\textbf{왜 표준화가 필요한가.} 높이는 mm 단위이고, 오버행은 0에서 1 사이 숫자이며,
횟수는 정수입니다. 그냥 섞으면 큰 단위를 가진 값이 군집화를 지배합니다. 그래서 평균을
빼고 표준편차로 나누어 모두 비슷한 척도로 맞춥니다(성적으로 치면 국어·영어·수학 점수를
표준점수로 바꿔 공평하게 비교하는 것과 같습니다).
\end{notebox}

%======================================================================
\section{어떻게 조각으로 나누는가}
%======================================================================

\subsection{방법 I: 순수 지지흐름 분할}

첫 번째 방법은 SFTF의 지지 물리 정보만으로 나눕니다. 군집화 라이브러리 없이도
부품 수를 스스로 정하는, 해석하기 쉬운 방법입니다. 대표적으로 두 변형이 있습니다.

\subsubsection*{support\_flow: 받치고 받는 면을 같이 묶기}

레이캐스팅이 찾아낸 ``오버행 면 $i$ $\to$ 받침면 $t_i$'' 관계를 그대로 씁니다.
서로 받치고 받는 면은 같은 조각에 넣습니다. 또 같은 지지 역할을 하면서 이웃한 면들도
같은 조각으로 합칩니다.

\begin{readbox}
\textbf{비유.} 빗물이 지붕의 여러 면을 타고 같은 배수구로 모이면 하나의 배수 구역으로
볼 수 있습니다. \texttt{support\_flow}도 ``지지 흐름이 모이는 구역''을 하나의 조각으로
봅니다.
\end{readbox}

장점은 지지 기둥을 잘 보존한다는 것입니다. 받쳐 주는 면과 받침을 받는 면이 같은 조각에
남으므로, 자른 뒤에도 그 관계가 끊기지 않습니다. (다만 뒤에서 보겠지만, 이 ``기둥 보존''이
꼭 서포트를 줄여 주지는 \emph{않았습니다}.)

\subsubsection*{flow\_region: 같은 역할과 비슷한 법선을 묶기}

두 이웃 면 $i,j$가 같은 지지 역할을 하고, 법선 방향도 충분히 비슷하면 합칩니다.

\[
\rho_i=\rho_j
\quad\text{and}\quad
m_i\cdot m_j\ge \cos\theta_{\mathrm{sim}}
\]

\noindent\textit{읽기:} 두 면이 같은 일을 하고, 서로 비슷한 방향을 바라보면 같은
영역으로 키웁니다. $\theta_{\mathrm{sim}}$은 ``얼마나 비슷해야 하느냐''를 정하는
각도이며, 논문은 기본값 $35^\circ$를 씁니다.

두 방법 모두 조각들이 톱니처럼 우툴두툴하게 잘릴 수 있어서, 조립하기 쉽도록 경계를
매끄럽게 다듬는 후처리(경계 평활화)를 덧붙입니다. 다만 너무 세게 다듬으면 조각이 커지고
서포트가 다시 늘 수 있어, 논문은 적당한 세기($\lambda=3$)를 실험으로 골랐습니다.

\subsection{방법 II: 좌표와 SFTF 특징을 섞은 군집화}

두 번째 방법은 기존 군집화에 SFTF 특징을 섞습니다.

\[
M=
\big[\,w_s\,\operatorname{zscore}(C)\ \big|\
w_f\,\Phi_{\mathrm{SFTF}}\ \big|\
w_d\,W\,\big]
\]

\noindent\textit{한 줄씩 읽기.}
\begin{itemize}[leftmargin=1.6em]
\item $C$: 각 면의 중심 좌표입니다. 가까운 면끼리 묶는 데 필요합니다.
\item $\Phi_{\mathrm{SFTF}}$: 방금 만든 지지흐름 특징입니다.
\item $W$: 여러 빌드방향 중 각 면이 어느 방향을 좋아하는지 나타내는 선택 정보입니다.
\item $w_s,w_f,w_d$: 좌표, 지지 특징, 방향 선호를 각각 얼마나 중요하게 볼지 정하는
가중치입니다.
\end{itemize}

이렇게 만든 표 $M$을 $k$-medoids, $k$-means, DBSCAN 같은 군집화 알고리즘에 넣습니다.
그중 $k$-medoids\footnote{$k$-medoids: 군집의 ``대표''로 평균 지점이 아니라 실제
데이터 점 하나를 고르는 군집화. 특이한 값에 덜 흔들려 안정적입니다. 이 연구의 구현은
큰 메쉬에서도 빠르도록 거리표를 통째로 만들지 않고 계산합니다.}가 뒤의 실험(특히 실제
슬라이서 검증)에서 가장 좋은 성적을 냈습니다.

\begin{notebox}
\textbf{숨은 중요한 한 단계: ``떨어진 조각''은 따로 센다.} 군집화가 같은 색(라벨)을
칠해도, 그 면들이 실제로는 공중에서 서로 떨어져 있을 수 있습니다. SFTF-Cluster는
색칠이 끝난 뒤 \emph{실제로 붙어 있는 덩어리}끼리 다시 나눕니다. 그래야 떨어진 덩어리마다
자기 방향을 따로 고를 수 있고, 이 한 단계가 뒤 실험의 결론을 크게 바꿉니다.
\end{notebox}

\subsection{여러 빌드방향을 동시에 보기}

한 조각은 위쪽으로 세우는 게 좋고, 다른 조각은 옆으로 눕히는 게 좋을 수 있습니다.
그래서 후보 풀 라우터가 고른 $K$개 조건화 방향 $n_1,\dots,n_K$를 함께 봅니다.

\[
c_{ik}=O_i(n_k)=\max(0,-m_i\cdot n_k),\qquad
b_i=\arg\min_k c_{ik}
\]
\noindent\textit{읽기:} 왼쪽 식은 면 $i$가 방향 $n_k$에서 얼마나 오버행이 되는지이며,
작을수록 그 면에 좋은 방향입니다. 오른쪽 $\arg\min$은 ``값을 가장 작게 만드는 방향
번호를 찾으라''는 뜻으로, 면마다 가장 좋은 방향을 하나 고릅니다. 하나만 딱 고르는 대신
여러 방향에 비율로 나누어 줄 수도 있으며, 이 방법을 \texttt{build\_direction}이라 부릅니다.

%======================================================================
\section{분할이 좋은지 어떻게 채점하는가}
%======================================================================

\subsection{전체 생각: 자르면 손해도 있고 이득도 있다}

분할 $\Pi$는 여러 조각 $\mathcal{P}_1,\mathcal{P}_2,\dots$의 모임입니다.
SFTF-Cluster는 분할의 서포트 양을 다음처럼 생각합니다.

\[
S(\Pi)\approx
S_{\mathrm{whole}}
+\Delta S_{\mathrm{cut}}(\Pi)
-\Delta S_{\mathrm{reorient}}(\Pi)
\]

\noindent\textit{읽기:} 통째로 출력할 때 필요한 서포트에서 시작합니다. 자르면서 새로 생기는
서포트는 더하고($+\Delta S_{\mathrm{cut}}$), 각 조각을 자기 좋은 방향으로 세워 아끼는
서포트는 뺍니다($-\Delta S_{\mathrm{reorient}}$).

\begin{readbox}
\textbf{한 줄 요약.} 좋은 분할은 ``자르면서 생기는 손해''보다 ``조각별로 방향을 바꾸며
얻는 이득''이 더 큰 분할입니다.
\end{readbox}

\subsection{절단 비용: 지지 기둥을 끊으면 손해}

어떤 오버행 면 $i$가 같은 물체 안의 받침면 $t_i$ 위에 잘 기대고 있었다고 합시다.
그런데 분할 때문에 $i$와 $t_i$가 서로 다른 조각으로 갈라지면($\ell(i)\ne\ell(t_i)$),
그 받침 관계가 끊겨 새 서포트가 필요할 수 있습니다.

\[
\Delta S_{\mathrm{cut}}(\Pi)
=
\sum_{i:\ \rho_i=\mathrm{face},\ \ell(i)\ne\ell(t_i)}
A_i\,O_i\,\eta_i
\]

\noindent\textit{읽기:} 원래 다른 면이 받쳐 주던 오버행($\rho_i=\mathrm{face}$) 가운데,
받침과 서로 다른 조각으로 갈라진 것만 골라, ``넓이$\times$처진 정도$\times$높이''를
더합니다. 넓고, 많이 처졌고, 높이 떠 있을수록 새 서포트 비용이 큽니다.

\subsection{재배향 이득: 조각마다 자기 좋은 방향을 고르면 이득}

각 조각은 통짜 물체와 달리 자기에게 가장 좋은 방향으로 세울 수 있습니다. 방향 $d$에서
면 $i$의 간단한 지지 크기를 다음처럼 둡니다.

\[
s_i(d)=A_i\,\mathbf{1}\{-m_i\cdot d>\cos\theta_c\}\,\max(0,-m_i\cdot d)
\]
\noindent\textit{읽기:} 임계각\footnote{임계각(critical angle) $\theta_c$: 이보다 심하게
누운 면에만 서포트를 붙인다고 보는 기준 각도. FDM에서는 보통 $45^\circ$를 씁니다.}
$\theta_c$보다 심하게 누운 면만 켜고($\mathbf{1}\{\cdot\}$가 1), 그 면이 아래를 볼수록,
넓을수록 큰 값을 줍니다.

조각 $\mathcal{P}_\ell$의 방향 $d$에서의 지지는 면별 값을 더하면 됩니다
($P_\ell(d)=\sum_{i\in\mathcal{P}_\ell}s_i(d)$). 이렇게 더하기가 가능한 이유는 SFTF
흐름이 면별 기여의 합으로 이루어지는 \textbf{가산성}\footnote{가산성(additivity): 전체
값이 작은 조각들의 합으로 계산된다는 성질. 시험 총점이 각 과목 점수의 합인 것과
같습니다.}을 갖기 때문입니다. 그러면 ``나눠서 각자 세우는 이득''은 다음처럼 씁니다.

\[
\Delta S_{\mathrm{reorient}}(\Pi)
=
\sum_\ell\left[P_\ell(n^\ast)-\min_d P_\ell(d)\right]
\]

\noindent\textit{읽기:} 통짜 기준 방향 $n^\ast$에서의 조각 비용과, 그 조각이 자기에게 가장
좋은 방향을 골랐을 때의 비용 차이를 더합니다. 이 값이 클수록 나눠 세우는 이득이 큽니다.

\subsection{ray-free 예측 지지량 \texorpdfstring{$\hat S$}{S-hat}}

마지막으로 매우 빠른 예측 지표를 만듭니다.

\[
\hat S(\Pi)=
\sum_\ell \min_d \sum_{i\in\mathcal{P}_\ell}s_i(d)
\]

\noindent\textit{읽기:} 각 조각마다 가능한 방향을 훑어 가장 서포트가 적은 방향을 고르고,
그 최소값들을 모두 더합니다. 레이캐스팅이나 슬라이서 같은 비싼 계산 없이 면 법선과
면적만으로 계산하므로 \textbf{ray-free}(광선 없이)라고 부릅니다. 실제로 이 지표는
슬라이서보다 약 \textbf{110배} 빨라서(형상 하나당 약 0.1초 대 11초), 수많은 후보 분할을
순식간에 훑을 수 있습니다.

\begin{notebox}
\textbf{정확한 계산기는 아닙니다.} $\hat S$는 빠른 대리값(스크리닝 지표)입니다.
후보 분할을 넓게 걸러 내는 데는 좋지만, \emph{실제 서포트 양을 그대로 맞히지는 못합니다.}
그래서 최종 비교는 반드시 진짜 슬라이서로 해야 합니다. 이 점이 이번 연구에서 특히 정직하게
확인된 부분입니다(\S6--\S7).
\end{notebox}

%======================================================================
\section{데이터와 검증: 무엇을, 어떤 슬라이서로 확인했나}
%======================================================================

\subsection{어떤 형상으로 실험했나}

방법이 특정 모양에서만 통하는 우연이 아님을 보이려면 여러 종류의 형상이 필요합니다.
그래서 성격이 아주 다른 \textbf{열두 개 형상}으로 실험했습니다.

\begin{itemize}[leftmargin=1.6em]
\item \textbf{단순 도형}: 토러스(도넛), 후크(갈고리)
\item \textbf{스캔 해부 형상}: anat-D1/D3/D9 (그중 anat-D9는 조각 241개로 부서진, 일부러
넣은 ``까다로운'' 스캔)
\item \textbf{장기}: 간(liver), 신장(kidney) --- 의료용 3D 모델
\item \textbf{그래픽스 스캔}: 드래곤, 해피 부처, 루시 --- 미술관 스캔처럼 정교한 곡면
\item \textbf{인체형}: 네페르티티 흉상, 전신 마네킨
\end{itemize}

크기는 삼각형 면이 약 1,600개인 후크부터 약 100,000개인 드래곤·네페르티티까지 다양합니다.
이 열두 형상을 여덟 가지 분할 방법으로 나눈 뒤, \emph{나온 조각 하나하나}를 실제 슬라이서로
검증했습니다. 조각은 모두 \textbf{2,876개}, 방향까지 바꿔 가며 슬라이싱한 횟수는
약 \textbf{13만 회}(각 조각을 48방향으로 슬라이싱)에 이릅니다.

\subsection{슬라이서가 무엇이고, 왜 CuraEngine인가}

지금까지의 $\hat S$나 SFTF 점수는 모두 \emph{빠른 근사}입니다. 진짜 서포트 양을 알려면
\textbf{슬라이서}\footnote{슬라이서(slicer): 3D 모델을 실제 프린터가 이해하는 한 층 한 층의
경로(G-code)로 바꾸어 주는 프로그램. 이 과정에서 ``어디에 서포트를 얼마나 세울지''도
정해집니다. 즉 슬라이서가 계산한 서포트 양이 실제 출력에 가장 가깝습니다.}를 돌려 봐야
합니다. 이번 연구는 기준 슬라이서로 누구나 내려받아 똑같이 재현할 수 있는 오픈소스
\textbf{CuraEngine}(legacy 15.04, 임계각 $45^\circ$)을 사용했습니다.

\begin{readbox}
\textbf{왜 오픈 슬라이서인가.} 예전에는 회사 전용 엔진(TOMO 등)으로 검증했지만, 그러면
다른 연구자가 똑같이 확인하기 어렵습니다. 누구나 접근할 수 있는 CuraEngine으로 검증하면
결론을 \emph{공개적으로 재현}할 수 있습니다. (참고로 빠른 근사 엔진 TOMO는 물체를
\emph{통째로} 놓고 방향만 볼 때는 CuraEngine과 잘 맞았지만(상관 약 0.93), 작은 \emph{조각}
단위에서는 어긋났습니다. 그래서 근사는 후보를 거르는 데만 쓰고, 최종 판정은 CuraEngine에
맡깁니다.)
\end{readbox}

\subsection{반전 1: proxy가 고른 방향은 슬라이서에게 너무 나빴다}

먼저 각 조각을 ``SFTF/proxy가 좋다고 고른 방향''에 세우고 CuraEngine으로 서포트를 재
봤더니, 뜻밖의 결과가 나왔습니다. 그 방향은 실제 슬라이서 기준으로는 서포트를 \textbf{1.2배에서
많게는 30배까지 과하게} 만들었습니다. 즉 빠른 근사가 고른 방향은 ``빠른 근사 세계에서만''
좋았던 것입니다.

\subsection{해결: slicer-in-the-loop --- 슬라이서가 직접 방향을 고른다}

그래서 방식을 바꿨습니다. SFTF는 \emph{후보 분할과 출발 방향}만 제안하고, \textbf{각 조각의
최종 방향은 CuraEngine이 직접 여러 방향을 슬라이싱해 보며 고르게} 했습니다. 이렇게
``슬라이서를 계산 고리 안에 넣는(slicer-in-the-loop)'' 방식으로 바꿨습니다. 공통 48방향
검증에서 최종 Cura 방향은 v2 진단 방향보다 서포트를 \textbf{1.9배에서 19.7배까지} 줄였습니다.

또한 SFTF v2는 예전의 tuned/uniform 라우터 대신, 고정된 면적 표본과 무차원 높이,
대칭 Rayleigh 점수와 바닥 지지 점수를 사용합니다. 같은 입력에는 항상 같은 후보와 점수를
내고, v1 API는 재현용으로 별도 보존됩니다. 최종 슬라이서 결과는 이 후보 생성에 쓰지 않아
평가 누출을 막습니다.

\begin{readbox}
\textbf{여기서 얻는 큰 교훈.} 실제 출력에서 서포트를 줄이는 가장 결정적인 힘은
``어떻게 나누느냐''보다 \textbf{각 조각을 어느 방향으로 세우느냐}였습니다. 방향 선택은
반드시 근사가 아니라 \emph{진짜 슬라이서}가 해야 합니다.
\end{readbox}

%======================================================================
\section{결과를 어떻게 읽어야 하는가}
%======================================================================

\subsection{슬라이서가 방향을 고르면 누가 이기나 (응용 형상 3종)}

각 조각을 CuraEngine이 고른 최적 방향에 세워 서포트를 비교하면, 응용 형상 세 가지의 최저
방법은 서로 달랐습니다. 간은 좌표 $k$-means, 네페르티티는 다방향 분할, 마네킨은 SFTF 특징을
섞은 $k$-medoids가 최저입니다(표~\ref{tab:siloop}). 그림~\ref{fig:manikin}은 마네킨을 여러
방법으로 나눈 모습입니다.

\begin{table}[H]
\centering
\caption{CuraEngine이 각 조각의 방향을 직접 고른 뒤의 서포트 양(g, 낮을수록 좋음).
형상마다 최저 방법이 다르며, 맨 아래는 다섯 방법의 평균 순위(1등에 가까울수록 좋음).}
\label{tab:siloop}
\begin{tabular}{lrrrrr}
\toprule
형상 & $k$-medoids & $k$-means & flow\_region & support\_flow & build\_direction\\
\midrule
\input{generated_v2/sftf_v2_application_cura_rows_ko.tex}
\end{tabular}
\end{table}

\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{support_manikin_review_paired.png}
\caption{마네킨을 여러 방법으로 나눈 예. 각 칸은 나눈 결과(왼쪽)와, 조각들을 각자
좋은 방향으로 세웠을 때 예상되는 서포트(빨간색)를 보여 줍니다. SFTF 특징을 섞은
$k$-medoids는 작고 서포트가 적은 조각을, 순수 지지흐름 방법은 지지 역할이 또렷한
조각을 만듭니다.}
\label{fig:manikin}
\end{figure}

\subsection{반전 2: 지지 기둥을 지키는 것이 최선은 아니었다}

\begin{readbox}
\textbf{가장 반직관적인 결론.} 지지 기둥을 절대 끊지 않는 것이 항상 최선은 아니었습니다.
실제로 서포트를 크게 줄인 힘은 ``기둥을 보존하는 것''보다 \textbf{각 조각이 자기 좋은
방향으로 다시 설 수 있는 자유도}였습니다.
\end{readbox}

표~\ref{tab:siloop}을 보면, 지지 기둥을 거의 끊지 않도록 설계한 \texttt{support\_flow}보다
재배향 자유가 큰 $k$-medoids의 서포트가 마네킨에서 훨씬 적습니다(8.32\,g 대 0.84\,g).
그래서 SFTF-Cluster는 ``지지 관계를 무조건 지켜라''가 아니라, ``절단 손해와 재배향 이득을
\emph{함께} 보라''고 말합니다.

\subsection{반전 3: 보편적인 1등은 없다 --- 정직한 결론 (열두 형상 전체)}

응용 형상 3종을 넘어 열두 형상 전체로 넓혀 보면, \emph{모든 형상에서 이기는 단 하나의
방법은 없었습니다.} 표~\ref{tab:broad}는 아홉 방법의 평균 순위입니다. $k$-medoids가
평균 1등(2.58)으로 전반적으로 가장 좋지만, 형상별로 보면 서로 다른 방법이
1등을 합니다.

\begin{table}[H]
\centering
\caption{열두 형상 전체에 대한 아홉 방법의 평균 순위(낮을수록 좋음). $k$-medoids가
평균 1위이지만, 아래 설명처럼 ``항상'' 1위는 아닙니다. (``무분할''은 나누지 않고 통짜로
방향만 고른 기준선입니다.)}
\label{tab:broad}
\begin{tabular}{lrrrrrrrrr}
\toprule
방법 & 무분할 & $k$-means & 평면 & Gao & 분지 & 영역 & \textbf{메도이드} & 다방향 & 자동\\
\midrule
평균 순위 & 5.54 & 3.25 & 4.00 & 6.92 & 6.83 & 4.38 & \textbf{2.58} & 5.08 & 6.42\\
\bottomrule
\end{tabular}
\end{table}

실제로 열두 형상에서 1등을 나눠 가진 모습은 이렇습니다.
\begin{itemize}[leftmargin=1.6em]
\item $k$-medoids: 열두 중 네 형상에서 1등(후크, 마네킨, 해피, 신장).
\item 좌표 $k$-means: 간과 드래곤에서 1등.
\item 무분할(통짜): 이미 길쭉한 anat-D1에서 1등 --- \emph{나누는 것이 오히려 손해}인 경우.
\item 평면 자르기: 토러스와 부서진 스캔 anat-D9에서 1등.
\item 다방향 분할: anat-D3와 네페르티티, 지지흐름 영역 분할: 루시에서 1등.
\end{itemize}

\begin{notebox}
\textbf{왜 이 정직함이 중요한가.} 처음에는 ``특정 SFTF 분할이 항상 서포트를 최소화한다''고
말하고 싶었지만, 오픈 슬라이서로 넓게 검증해 보니 그 주장은 과했습니다. 방법에 따라 결과가
\emph{우연이 아니라 뚜렷하게 달랐다}는 것은 통계적으로 확인됐지만(방법 간 차이가 유의미함),
$k$-medoids가 좌표 $k$-means보다 낫다는 것은 열두 형상만으로는 통계적으로 단정하기 어려웠습니다.
더구나 최종 부품 수를 맞추면 좌표 $k$-means가 열두 형상 모두에서 더 낮았습니다. 그래서
논문은 결론을 정직하게 낮춰, \emph{``$k$-medoids는 기본 설정의 전체 평균 순위 1위이지만,
그 우위는 주로 더 많은 부품의 재배향 자유를 반영하며 고정 부품 예산의 보편 최저는 아니다''}로
씁니다. 실제 데이터가 말하는 만큼만
주장하는 것이 좋은 과학입니다.
\end{notebox}

%======================================================================
\section{그래도 확실히 남는 것과, 정직한 한계}
%======================================================================

\subsection{확실히 남는 것: 순도(역할 또렷함) 우위}

서포트 양은 형상과 방향에 따라 출렁이지만, \textbf{지지 클래스 순도}\footnote{순도(purity):
``각 조각이 한 가지 지지 역할로만 이루어졌는가''를 0$\sim$1로 잰 값. 1에 가까울수록 ``오버행
조각'', ``바닥 조각''처럼 성격이 또렷하게 갈렸다는 뜻입니다.}는 슬라이서와 무관한 기하적
성질이라 흔들리지 않습니다. 세 응용 형상 모두에서 SFTF 방법의 순도가 좌표·기하 기준선보다
일관되게 높았습니다(표~\ref{tab:purity}). 그림~\ref{fig:nefertiti}는 그 차이를 눈으로
보여 줍니다.

\begin{table}[H]
\centering
\caption{좌표만 쓰는 기준선과 SFTF 방법의 지지 클래스 순도(높을수록 좋음). 형상이
복잡할수록 차이가 큽니다.}
\label{tab:purity}
\begin{tabular}{lrr}
\toprule
형상 & 좌표 전용 $k$-means & SFTF 계열(최고)\\
\midrule
\input{generated_v2/sftf_v2_brief_purity_rows_ko.tex}
\end{tabular}
\end{table}

\begin{figure}[H]
\centering
\includegraphics[width=0.85\textwidth]{support_nefertiti_equal_scale.png}
\caption{네페르티티 흉상을 나눈 두 방식의 차이. 좌표만 보는 방법은 그냥 ``가까운 면끼리''
공간을 뭉텅뭉텅 자릅니다. SFTF 방법은 스스로 잘 서는 왕관·뒤통수를, 서포트가 필요한 얼굴·턱
아래와 \emph{역할로} 갈라 놓습니다.}
\label{fig:nefertiti}
\end{figure}

좌표만 보는 군집화는 가까운 면끼리 잘 묶지만, 그 면들이 출력할 때 어떤 역할을 하는지는
모릅니다. SFTF 특징을 넣으면 오버행, 바닥 지지, 면-면 지지, 받침 역할이 분할에 반영되어,
한 조각 안에 서로 다른 지지 역할이 마구 섞이는 일이 줄어듭니다. 즉 SFTF 분할은
\emph{사람이 이해하기 쉬운, 역할이 또렷한 조각}을 만들어 줍니다.

\subsection{선행 연구(Gao 2019)와의 비교}

서포트를 직접 최소화하도록 설계된 선행 연구 Gao 2019와도 비교했습니다. Gao는 설계 목표대로
빠른 근사 기준 서포트에서는 강했습니다. 실제 CuraEngine 검증에서 $k$-medoids는 마네킨
(0.84\,g 대 6.59\,g)과 네페르티티(7.59\,g 대 30.70\,g)에서 Gao보다 낮지만, 간에서는 둘 다
좌표 $k$-means(4.72\,g)에 뒤집니다. Gao는 \emph{방향}만 최적화하므로 분할이 지지 역할을
따르지 않아 해석 가능성(순도)이 낮았습니다(간에서 0.60 대 0.94$\sim$0.96).
즉 SFTF-Cluster는 같은 정보 하나에서 \emph{역할이 또렷한 조각 + 조각별 재배향 자유도 +
빠른 예측 지표}를 함께 얻는다는 점이 다릅니다.

\subsection{정직한 한계}

\begin{notebox}
\textbf{SFTF-Cluster도 최종 슬라이서를 대체하지 않습니다.} $\hat S$는 빠른 분할 탐색용
지도일 뿐, 최종 슬라이서 예측자가 아닙니다(간에서는 proxy가 모두 0으로 퇴화해 순위 상관조차
정의되지 않습니다). 실제 출력에서는 접합면 품질, 부품 수, 작업부피, 조립 가능성, 슬라이서 설정까지
같이 봐야 합니다.
\end{notebox}

또한 작은 조각을 너무 많이 만들면 조립이 어려워집니다. 그래서 실제 사용에서는
``서포트 감소''와 ``부품 수/조립 난이도'' 사이의 균형을 잡아야 합니다. 논문은 이를 위해
부품 수 $K$에 벌점을 주어 프린터 작업부피 안에 들어오도록 부품 수를 자동으로 정하는
아이디어도 제시하지만, 이 자동 선택도 최종적으로는 몇 개 후보를 실제 슬라이서로 확인하는
것이 안전합니다.

\subsection{실용 지침 한 줄}

\begin{readbox}
\textbf{전체 한 줄 정리.} SFTF-Cluster는 SFTF가 계산한 면별 지지흐름 정보를 이용해,
3D 모델을 ``출력하기 좋은 조각''으로 나누는 방법입니다. \emph{해석 가능한 자동 분할}이
필요하면 \texttt{support\_flow}나 특징 융합 $k$-medoids를 쓰되, \emph{서포트 최소화나 지정
부품 수}가 중요하면 같은 부품 수의 좌표 기준선도 함께 비교해야 합니다. 그리고 \textbf{각
조각의 최종 방향은 반드시 진짜 슬라이서(CuraEngine)로 고르는} 것이 이번 연구가 실제 출력으로
확인한 핵심 지침입니다.
\end{readbox}

\end{document}

