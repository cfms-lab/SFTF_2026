# LaTeX source: SFTF_BatteryThermal_PoC.tex

Source: `D:\__SFTF_Projects(2026)\SFTF_BatteryThermal_dev\draft\SFTF_BatteryThermal_PoC.tex`

% !TEX program = xelatex
% SFTF -> 리튬이온 배터리 냉각수 채널 레이아웃·온도 균일도 PoC
% 빌드: xelatex (MiKTeX) + kotex.  latexmk -xelatex SFTF_BatteryThermal_PoC.tex
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
\usepackage{graphicx}
\graphicspath{{pics/}}
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
  cell/.style={draw,minimum size=7mm,inner sep=0pt,font=\scriptsize},
  flowarr/.style={->,thick,blue!55!black},
}

\newcommand{\term}[1]{\textbf{#1}}
\newcommand{\Tin}{\ensuremath{T_{\mathrm{in}}}}
\newcommand{\Tcool}{\ensuremath{T_{\mathrm{cool}}}}
\newcommand{\spear}{\ensuremath{\rho_{\mathrm{Spearman}}}}

\title{\textbf{SFTF $\rightarrow$ 리튬이온 배터리 냉각수 채널 레이아웃}\\[2mm]
\large 적층제조 서포트 흐름 텐서장의 열관리 이식:
온도 균일도 후보생성기와 적응검증(개념증명)}
\author{SFTF\_BatteryThermal\_dev}
\date{2026-06}

\begin{document}
\maketitle

\begin{abstract}
\noindent
적층제조(AM)의 \emph{빌드방향 후보생성기} \textbf{SFTF}(Support Flow Tensor Field)는
삼각망 각 면이 빌드방향에 등돌린 정도를 흐름으로 보고 닫힌형 텐서 한 번으로 서포트
물량을 예측한다. 본 PoC는 \textbf{오버행 $=$ 셀 발열 $Q$}, \textbf{receiver $=$ 냉각수
채널로의 전도}, \textbf{빌드플레이트(ground node) $=$ 냉각수 채널}이라는 치환으로 SFTF를
\emph{리튬이온 배터리 팩의 냉각수 채널 레이아웃·온도 균일도} 문제로 이식한다. 단,
배터리는 세 가지가 다르다: (i) 냉각수가 하류로 데워지는 \emph{비등온 ground node}
(advection), (ii) 목적이 최댓값이 아니라 \emph{온도 균일도}, (iii) 콜드플레이트 전도.
냉각수 하류 가열을 하수 PoC의 흐름누적과 동형으로 닫힌형화하여, numpy/scipy만으로 구현한
값싼 프록시가 공액(advection$+$전도) 해의 균일도 순위를 advection 우세 영역에서
\spear$=1.0$(다중 seed 평균 $0.91$)으로 추종한다. 다섯 가지 결과를 보고한다:
(1) \emph{역류(counter-flow)} 채널이 최댓값을 약간 희생하고 균일도를 높이는 실제 BTMS의
\emph{최댓값 vs 균일도 trade-off}를 재현하되, 이 긴장이 max$-$min이 아니라 \emph{분포형상
(표준편차)}에 산다는 점을 규명한다. (2) 단일 seed의 높은 상관이 통계적 허상일 수 있어
\emph{다중 seed 분포}로 검증을 강화한다. (3) 냉각 존 분할의 advection 비용이 \emph{존별
독립$=$가산적}이라 재-solve 없이 분할을 평가하고(가산 추정이 공액해를 \spear$=1.0$ 추종),
\emph{절단비용 vs 분할이득}으로 최적 존 수를 정한다. (4) 적응검증(AVE)은 후보의 $12\%$만
공액 검증하고도 전수검증의 최적 레이아웃을 $100\%$ 회수한다. (5) 하드 레이캐스트를
soft-attention으로 완화한 \emph{미분가능 SFTF}로 채널 경로를 경사하강 최적화하여 균등배치
대비 참 균일도를 $\sim\!20\%$ 낮춘다. SFTF는 새 최적화기가 아니라 \emph{값싼 후보생성기
$+$ 적응적 정밀검증}이라는 역할을 그대로 유지한다.
\end{abstract}

% ============================================================================
\section{서론: 서포트 흐름과 배터리 발열은 뼈대를 공유한다}
% ============================================================================
적층제조에서 오버행을 받치는 \emph{서포트}는 결국 \emph{빌드플레이트}로 흘러내려 응집된다.
SFTF는 이 ``흐름''을 면 단위 텐서로 닫힌형 누적하여, 비싼 시뮬레이션 없이 빌드방향 후보를
ms 단위로 랭킹한다. 리튬이온 배터리 팩에서 셀이 만드는 \emph{발열}$Q$도 가장 가까운
\emph{냉각수 채널/콜드플레이트}로 전도되어 빠져나간다. 두 문제는 ``소스에서 발생한 양이
가장 가까운 싱크로 흘러 누적된다''는 동일한 뼈대를 공유한다(표~\ref{tab:map}).

그러나 배터리에는 적층제조(및 앞선 ThermalChip 이식)와 결정적으로 다른 \term{세 가지}가 있다.
\begin{enumerate}[leftmargin=1.4em,itemsep=1pt]
\item \term{비등온 ground node (하류 가열).} 냉각수는 채널을 흐르며 상류 셀의 열을 흡수해
  \emph{데워진다}. 출구쪽 셀은 더 뜨거운 냉각수를 만난다. ground node가 등온이던 SFTF/
  ThermalChip과 달리, 냉각수 온도가 흐름방향으로 단조 상승한다. 이는 자연유하 하수의
  ``유량이 하류로 누적''과 \emph{동형}이라, 하수 PoC의 흐름누적 기계를 그대로 재사용한다.
\item \term{목적이 최댓값/합이 아니라 온도 균일도.} 셀 간 온도차는 노화·용량불균형을 부른다.
  비용은 $\max_i T_i-\min_i T_i$ 또는 표준편차로, SFTF의 합/최댓값 비용과 \emph{함수 형태}가
  다르다 --- 도메인 적응의 핵심이며, 본 논문이 가장 공들인 지점이다(\S\ref{sec:tradeoff}).
\item \term{콜드플레이트 전도.} 셀이 콜드플레이트로 열을 전도한다(빌드플레이트$=$콜드플레이트).
  여기까지는 ThermalChip과 동일하게 이식된다.
\end{enumerate}

\begin{table}[t]\centering
\caption{기호 대응 (SFTF $\leftrightarrow$ Battery).}
\label{tab:map}
\small
\begin{tabular}{@{}lll@{}}
\toprule
SFTF (적층제조) & Battery PoC & 비고 \\
\midrule
오버행 $O_i$ & 셀 발열 $Q_i$ & $I^2R+$엔트로피$+$반응열 \\
receiver(레이캐스트) & 최근접 채널로의 전도 $+$ 채널 따라 advection & \\
높이/감쇠 & 채널까지 거리 $\varphi_i$ & 전도 열저항거리 \\
빌드플레이트(ground node) & \term{냉각수 채널} & \term{비등온}(하류 가열) \\
분할$+$재배향 & \term{다채널·역류·냉각 존 분할} & \S\ref{sec:zones} \\
비용 $=$ 총 서포트(합) & \term{온도 균일도(max$-$min/std)} & \S\ref{sec:tradeoff} \\
TOMO 검증 $+$ AVE & 공액(advection$+$전도) 사인오프 $+$ AVE & \S\ref{sec:verify},\ref{sec:ave} \\
\bottomrule
\end{tabular}
\end{table}

% ============================================================================
\section{닫힌형 프록시: advection 누적 $+$ 전도}
\label{sec:proxy}
% ============================================================================
$ny\times nx$ 격자 위 셀 발열 $Q_i$ 와 후보 \emph{채널 레이아웃}(흐름순서가 보존된 노드열의
집합)이 주어졌을 때, 셀 온도장을 다음 닫힌형으로 추정한다.
\begin{align}
\varphi_i &= \text{셀 } i \to \text{최근접 채널셀 거리(거리변환)},\quad
   \mathrm{assign}(i)=\text{최근접 채널셀}, \label{eq:phi}\\
\Tcool[c] &= \Tin + \alpha_{\mathrm{adv}} \!\!\sum_{\mathrm{order}(c')\le \mathrm{order}(c)}\!\!
   Q_{\mathrm{pickup}}[c'], \label{eq:adv}\\
T_i &= \Tcool[\mathrm{assign}(i)] \;+\; \alpha_{\mathrm{cond}}\, t^{\mathrm{cond}}_i. \label{eq:T}
\end{align}
식~\eqref{eq:adv}는 냉각수 하류 가열로, 채널셀 $c$ 가 자신과 그에 배정된 셀들의 발열
$Q_{\mathrm{pickup}}[c]$ 을 받아 흐름순서를 따라 누적한다(각 채널은 자기 입구에서 리셋).
이는 하수 흐름누적과 정확히 같은 구조다 --- \term{ground node의 비등온성을 닫힌형으로
반영}하는 부분이다. $t^{\mathrm{cond}}_i$ 는 전도 상승으로, $\varphi$ 경사를 따라 열을
채널로 밀어내며 저항$\times$열을 적분한다($t_i=t_{\mathrm{rec}(i)}+\alpha\,\mathrm{accum}_i\,
\ell_i$). 균일도 프록시는 $T$ 의 max$-$min 또는 표준편차다. 모든 연산이 닫힌형이라 한
레이아웃 평가가 ms 단위다.

% ============================================================================
\section{공액 검증과 다중 seed 강화}
\label{sec:verify}
% ============================================================================
\paragraph{진실값(공액 stand-in).} 프록시는 후보생성기일 뿐, 검증 대상은 \emph{공액 정상해}다:
(a) advection으로 채널 냉각수온 \Tcool\ 을 구하고, (b) 전도 $K\,t=Q$ 를 채널셀
Dirichlet$=$\Tcool\ 로 풀어(\texttt{scipy.sparse}) 셀 온도장을 얻는다. 즉 \emph{비등온
콜드플레이트로의 전도}를 정확히 푼다. 검증지표는 프록시 균일도 순위와 공액해 균일도 순위의
스피어만 상관 \spear\ 이다.

\paragraph{regime의 존재.} 냉각수 하류 가열의 세기를 $\alpha_{\mathrm{adv}}$(코드의
\texttt{rise})로 조절하면 두 영역이 나타난다: \emph{전도 우세}(짧은 채널/저 발열)와
\emph{advection 우세}(긴 채널/고 C-rate). 후자가 본 PoC가 겨냥하는, 냉각수 온도상승이
설계를 지배하는 영역이다.

\paragraph{단일 숫자의 함정.} 단일 모듈$\times$6 레이아웃의 \spear($n{=}6$)는 취약하다.
\emph{확장 후보군}(16 레이아웃: 채널위치·serpentine 길이·평행/역류 채널수)을
\emph{다중 seed}(20개 합성 모듈)에 걸쳐 평가하여 \spear\ \emph{분포}를 본다(표~\ref{tab:spear}).

\begin{table}[t]\centering
\caption{\spear(프록시 균일도, 공액해 균일도) 분포. 20 seed $\times$ 16 레이아웃, $32\times48$.}
\label{tab:spear}
\small
\begin{tabular}{@{}lcccc@{}}
\toprule
regime & 평균 \spear & 최소 & $\Pr[\rho\ge0.8]$ & trade-off 실현 \\
\midrule
A. 전도 우세 (\texttt{rise}$=1$, max$-$min) & $0.785$ & $0.74$ & $0.35$ & $0.15$ \\
B. advection 우세 (\texttt{rise}$=5$, std) & $\mathbf{0.914}$ & $\mathbf{0.81}$ & $\mathbf{1.00}$ & $\mathbf{0.55}$ \\
\bottomrule
\end{tabular}
\end{table}

\begin{figure}[t]\centering
\includegraphics[width=0.74\textwidth]{fig_spearman}
\caption{프록시--공액해 균일도 순위상관의 \emph{분포}(점 하나가 seed 하나). 전도 우세
영역(A)은 평균이 목표선 아래($\rho{=}0.785$)인 반면, advection 우세 영역(B)은 모든 seed가
$\rho\ge0.8$ 이다 --- 프록시가 배터리 관점에서 중요한 영역에서 더 견고하다.}
\label{fig:spearman}
\end{figure}

\paragraph{정직한 발견.} 단일 seed에서 관찰되던 $\approx0.9$ 는 부분적으로 $n{=}6$ 의
\emph{허상}이었다: 확장 후보군에서 전도-우세 영역의 평균 상관은 $0.785$ 로 목표 $0.8$ 에
못 미친다. 원인은 프록시의 전도항(8-이웃 최급강하 적분)이 진실값(4-이웃 확산)과 가장
어긋나는 곳이 전도 우세 영역이기 때문이다. 반대로 \emph{advection 우세 영역에서는} 프록시와
진실값이 \emph{같은 advection 식}을 공유하므로 상관이 견고하다($\Pr[\rho\ge0.8]=1.0$).
요컨대 \term{프록시는 배터리 관점에서 중요한 영역에서 오히려 더 믿을 만하다}. 이는 단일
숫자로는 보이지 않던 결론이다.

% ============================================================================
\section{최댓값 vs 균일도: 역류 trade-off는 분포형상에 산다}
\label{sec:tradeoff}
% ============================================================================
실제 BTMS 설계의 핵심 논점은 \emph{핫스팟 최소화}와 \emph{셀 간 균일도}가 다른 레이아웃을
요구한다는 것이다. 이 trade-off를 본 모델에서 재현하려면 두 가지가 필요하다.

\paragraph{(i) 흐름방향 축.} 자원 무제한이면 ``냉각을 더 깔수록'' 최댓값과 균일도가 동시에
개선되어 긴장이 없다. 긴장은 \emph{냉각수 흐름방향}에서 온다: 기하학적으로 동일한
\emph{평행류}(모든 채널 입구가 같은 쪽)와 \emph{역류}(인접 채널이 반대 방향)를 비교한다.
평행류는 입구-냉각/출구-가열 공간구배가 커서 최댓값은 낮아도 비균일하고, 역류는 인접한
뜨거운 출구와 차가운 입구가 전도로 상쇄되어 균일하지만 최댓값이 약간 높다.

\paragraph{(ii) 분포형상 지표.} max$-$min(spread)은 극값에 지배되어 사실상 최댓값을
추종한다(모든 레이아웃의 최솟값이 차가운 입구에 고정되므로 spread$\approx$peak). 따라서
spread로 보면 두 최적이 항상 일치한다. trade-off는 \term{분포형상(표준편차)}에 살며, 이것이
셀-노화 균일도가 실제로 보는 양이다(표~\ref{tab:tradeoff}).

\begin{table}[t]\centering
\caption{advection 우세 영역(\texttt{rise}$=5$, std)에서 평행 vs 역류. $32\times48$, seed 0.}
\label{tab:tradeoff}
\small
\begin{tabular}{@{}lcc@{}}
\toprule
레이아웃 & 공액 최댓값 (peak) & 공액 균일도 (std) \\
\midrule
\texttt{multi\_channel} (평행) & $\mathbf{113.7}$ \;(최소) & $27.64$ \\
\texttt{counterflow\_channels} (역류) & $141.8$ \;($+25\%$) & $\mathbf{26.02}$ \;(최소) \\
\bottomrule
\end{tabular}
\end{table}

\begin{figure}[t]\centering
\includegraphics[width=0.72\textwidth]{fig_tradeoff}
\caption{advection 우세 영역의 공액해 최댓값(가로) vs 균일도 std(세로). 평행
(\texttt{multi\_channel})은 최댓값이 가장 낮지만 std가 더 크고, 역류
(\texttt{counterflow\_channels})는 최댓값을 약간 내주고 std가 가장 낮다 --- 두 최적이
갈린다. (\texttt{edge\_plate}는 척도 밖 베이스라인이라 제외.)}
\label{fig:tradeoff}
\end{figure}

그 결과 \term{최댓값-최적($=$평행) $\ne$ 균일도-최적($=$역류)}이 성립한다. 이 trade-off는
seed 0 의 우연이 아니라 $20$ seed 중 $55\%$ 에서 재현되며(표~\ref{tab:spear}), 프록시는 이
영역에서 균일도 순위를 \spear$=1.0$ 으로 정확히 추종한다. \emph{전도 우세} 영역이거나
\emph{spread} 지표에서는 두 최적이 여전히 일치한다 --- trade-off의 발현 조건을 명확히
한정한다.

% ============================================================================
\section{냉각 존 분할: advection 비용의 텐서 가산성}
\label{sec:zones}
% ============================================================================
SFTF-Clustering의 \emph{분할$+$재배향}을 이식한다. 팩을 $K$개 수평 \emph{존}으로 나누고 각
존에 자기 채널과 자기 차가운 입구를 준다. 각 존의 냉각수가 자기 입구에서 \emph{리셋}되므로
\term{하류 가열(advection) 비용이 존별로 독립$=$가산적}이다 --- SFTF 텐서 가산성의 배터리판.
밴드 분할에서는 각 존이 \emph{독립 sub-module}이므로, 분할의 비용을 \term{재-solve 없이}
존별 평가의 조립으로 얻는다.

세 가지를 공액해로 검증한다(표~\ref{tab:zones}). (1) \term{재배향 이득}: 존이 늘수록 각
존의 경로가 짧아져 균일도가 단조 개선된다($K{:}1\to8$ 에서 std $89\to9$). (2) \term{가산
추정의 충실도}: 존별 독립(재-solve-free) 추정이 전역 공액해의 분할 순위를 \spear$=1.0$ 으로
추종한다. 가산 추정은 존간 전도 평활을 무시해 균일도를 $\sim\!15\text{--}20\%$ 과대평가하나
\emph{순위}에는 영향이 없다. (3) \term{절단비용 vs 분할이득}: 각 추가 존은 입구/매니폴드
비용을 부른다. $\arg\min_K\big[\text{uniformity}(K)+\lambda\,(K-1)\big]$ 가 유한 최적 $K$ 를
준다($\lambda{=}0\!\to\!K{=}8$, $\lambda{=}5\!\to\!K{=}4$, $\lambda{=}12\!\to\!K{=}3$).

\begin{table}[t]\centering
\caption{냉각 존 분할(\texttt{rise}$=5$, std). 가산$=$존별 독립(재-solve-free) 추정.}
\label{tab:zones}
\small
\begin{tabular}{@{}cccc@{}}
\toprule
존 수 $K$ & 가산 추정 (uni) & 공액해 (uni) & 경계결합 오차 \\
\midrule
1 & $68.9$ & $88.7$ & $0\%$ \\
4 & $22.0$ & $19.0$ & $18.5\%$ \\
8 & $11.2$ & $9.4$ & $19.5\%$ \\
\midrule
\multicolumn{4}{l}{\footnotesize \spear(가산 추정, 공액해) over $K=\{1,2,3,4,6,8\}$: $\mathbf{+1.000}$}\\
\bottomrule
\end{tabular}
\end{table}

\begin{figure}[t]\centering
\includegraphics[width=0.70\textwidth]{fig_zones}
\caption{냉각 존 수 $K$ 에 따른 균일도. 존이 늘수록 각 존의 냉각수 경로가 짧아져 균일도가
단조 개선된다. \emph{재-solve-free 가산 추정}(점선)이 공액해(실선)와 순위가 정확히 같다
(\spear$=1.0$). 가산 추정은 존간 전도 평활을 무시해 절대값을 약간 과대평가한다.}
\label{fig:zones}
\end{figure}

% ============================================================================
\section{적응검증 확대 (AVE)}
\label{sec:ave}
% ============================================================================
프록시는 \emph{완벽한 picker}가 아니라 \emph{완벽한 shortlister}다. 확장 후보군(16개)에서
프록시의 단일 최선 추측은 $40\%$ 만 적중하지만(recall@1$=0.40$), 참-최적은 \emph{항상}
프록시 상위 2개 안에 있다(recall@2$=1.0$). 따라서 전수 공액 검증 대신, 판정을 뒤집을 수
있는 \term{접전권 후보}(프록시 최선의 $(1{+}\text{margin})$ 이내)와 hotspot 후보에만 공액
solve 예산을 \emph{적응적}으로 쓴다. margin이 적응적이라 명확한 승자면 적게, 접전이면 많이
검증한다.

$20$ seed 감사 결과(표~\ref{tab:ave}): AVE는 평균 \term{후보의 $12\%$($\approx 2/16$)만 공액
검증}하고도 전수검증의 최적 레이아웃을 \term{$100\%$ 회수}한다. 프록시 단독이 $60\%$
틀리는 것과 대비된다. 이는 하수 PoC의 AVE($23\%$ 검증으로 동일 최적 회수)와 같은 원리의
배터리판이다.

\begin{table}[t]\centering
\caption{AVE 감사. 20 seed, 16 후보, advection 우세(\texttt{rise}$=5$, std), margin $0.25$.}
\label{tab:ave}
\small
\begin{tabular}{@{}lc@{}}
\toprule
지표 & 값 \\
\midrule
AVE 참-최적 회수율 & $\mathbf{1.00}$ \\
프록시 단독 recall@1 & $0.40$ \\
평균 공액 solve 수 & $\mathbf{2.0\ /\ 16}$ \;($12\%$) \\
\bottomrule
\end{tabular}
\end{table}

% ============================================================================
\section{미분가능 SFTF: 채널 경로 경사하강}
\label{sec:diff}
% ============================================================================
하드 프록시는 각 셀을 \emph{최근접} 채널에 배정한다(argmin$=$레이캐스트) --- 미분 불가라
채널 위치를 경사 최적화할 수 없다. 이를 \term{soft-attention}으로 완화한다:
\begin{equation}
w_{i,k} = \mathrm{softmax}_k\!\big(-\,\mathrm{dist}(\text{cell}_i,\text{channel}_k)/\tau\big).
\label{eq:soft}
\end{equation}
$\tau\to0$ 이면 하드 최근접 레이캐스트를 복원하고, $\tau>0$ 이면 온도장과 균일도 목적이
연속 채널행 $\mathbf{y}=(y_1,\dots,y_K)$ 의 \emph{매끄러운} 함수가 된다. 하위 연산(soft
배정·기대거리·냉각수 누적 \texttt{cumsum}·표준편차)이 모두 미분가능하므로 $\mathbf{y}$ 를
경사하강한다. 채널이 hotspot 쪽으로 이동하여, \term{참 공액해 표준편차를 균등배치 대비
$\sim\!20\%$ 낮춘다}(seed 0: soft $20.0\!\to\!17.4$; 공액 std $22.4\!\to\!18.0$, $-19.8\%$;
seed 0--2 모두 개선; 그림~\ref{fig:diff}). numpy-only 제약상 경사는 유한차분으로 구하며($K$
가 작아 저렴), 해석적/autograd 경사와 NN 물리일관성 항·GNN은 본 미분가능 SFTF의 확장이다.

\begin{figure}[t]\centering
\includegraphics[width=0.70\textwidth]{fig_diffsftf}
\caption{미분가능 SFTF의 경사하강 수렴. soft 균일도가 균등배치 시작값에서 단조 감소하며,
최적화된 채널행을 하드 레이아웃으로 스냅한 뒤 \emph{참 공액해}로 평가하면 std가 균등배치
대비 $19.8\%$ 낮아진다.}
\label{fig:diff}
\end{figure}

% ============================================================================
\section{구현과 성능}
\label{sec:impl}
% ============================================================================
코어는 numpy/scipy만 쓴다(모듈 \texttt{module, layouts, coolant, verify, partition,
ave, diffsftf}; CLI \texttt{demo/validate/zones/ave/optimize}; 단위테스트 32개). 전도항의
숲(receiver forest) 누적은 \emph{레벨-동기 벡터화}로 두 개의 $O(n)$ 파이썬 노드 루프를
제거했다: 노드를 트리 깊이별로 버킷팅하여 레벨당 numpy 연산 한 번으로 처리한다(트리 깊이가
$\sim\!\sqrt{n}$ 로 작게 자람). 결과는 기존과 \emph{비트 동일}이며 $6\text{--}13\times$
빠르다($24{,}576$ 셀에서 $37\,\mathrm{ms}\!\to\!5\,\mathrm{ms}$).

전도항 \emph{정확도}를 싸게 올리려는 시도는 실패했고, 이를 정직히 기록한다: 다중수신자(MFD)
누적은 무효였고($\rho\,0.774\!\to\!0.776$), 참 연산자의 Jacobi 스윕은 $\rho\approx0.97$ 에
$\sim\!200$ 스윕(직접 solve보다 비쌈)이 필요했다. 전도 우세 영역의 오분류는 대부분
\emph{serpentine}(긴 단일채널) 전용이고 다채널/역류 후보는 정확히 랭킹되며 \emph{top-1(최적
레이아웃)은 맞으므로}, warm-start 목적에는 충분하다.

% ============================================================================
\section{최신문헌 대비 차별점, 한계}
% ============================================================================
대표 갈래는 CFD/공액 토폴로지 최적화, 다목적 메타휴리스틱(NSGA-II 등), ML 대체모델$+$최적화,
열저항망 해석이다. 이들 대비 본 연구의 차별점:
\begin{enumerate}[leftmargin=1.4em,itemsep=1pt]
\item[\textbf{D2}] \emph{비등온 ground-node의 닫힌형} --- 냉각수 하류 가열을 하수식 누적으로
  닫힌형화(등온 가정 1차 모델보다 advection을 싸게 반영). [\S\ref{sec:proxy}]
\item[\textbf{D3}] \emph{텐서 가산성으로 냉각 존 분할을 재-CFD 없이 추정.} [\S\ref{sec:zones}]
\item[\textbf{D4}] \emph{적응검증(AVE)} --- 접전권·hotspot 후보에만 공액 solve 확대. [\S\ref{sec:ave}]
\item[\textbf{D5}] \emph{균일도-인식 프록시} --- 합/최댓값이 아닌 분포형상 목적에 맞춘
  도메인 적응. [\S\ref{sec:tradeoff}]
\item[\textbf{D6}] \emph{미분가능화} --- soft-attention 완화로 채널 경로 경사하강. [\S\ref{sec:diff}]
\end{enumerate}

\paragraph{정직한 한계.}
(1) 전도장은 확산(이산 트리 아님)이라 텐서 가산성은 부분적이며, 전도 우세 영역에서 랭킹
프록시가 약하다(평균 $\rho\approx0.79$). 정확도 향상은 별도 솔버/대체모델 몫이다.
(2) 정상상태·단순 advection만 다룬다 --- \emph{과도(드라이브사이클)·CFD 압력강하·전기-열
결합·PCM}은 별도 정밀 솔버 몫이다(\texttt{verify.signoff\_cfd} 가드만 존재).
(3) 균일도 \emph{절대값} 예측이 아니라 레이아웃 \emph{랭킹/warm-start}가 목표다 --- 절대
정확도는 학습 대체모델/CFD가 높으며, 본 연구의 가치는 무학습·해석가능·warm-start다.
(4) 미분가능 SFTF의 경사는 유한차분이고 soft 전도항은 선형 surrogate다(랭킹은 공액해로 검증).

\paragraph{결론.} SFTF의 ``값싼 후보생성기 $+$ 적응적 정밀검증''이라는 정체성은 도메인을
적층제조에서 배터리 열관리로 옮겨도 유지된다. 비등온 ground node와 균일도 목적이라는 두
도메인 차이를 닫힌형으로 흡수하고, 텐서 가산성·AVE·미분가능화를 그대로 이식하여, CFD/ML
파이프라인 앞단의 무학습 warm-start로 기능함을 합성 검증으로 보였다.

% ============================================================================
\section*{참고문헌 (확인용 URL)}
% ============================================================================
\small
\begin{itemize}[leftmargin=1.3em,itemsep=0pt]
\item Multi-objective topology optimization of cold plates (branched/streamlined
  mini-channels) for Li-ion battery module. \emph{J. Energy Storage} 2023.
  \url{https://www.sciencedirect.com/science/article/abs/pii/S2352152X23017590}
\item Topological optimization of cold plates with non-uniform heat sources.
  \emph{Appl. Therm. Eng.} 2024.
  \url{https://www.sciencedirect.com/science/article/abs/pii/S1359431124015904}
\item Optimization of Thermal Non-Uniformity in Liquid-Cooled Li-ion Packs using
  NSGA-II. \emph{ASME J. Electrochem. En.} 2025.
  \url{https://asmedigitalcollection.asme.org/electrochemical/article/22/4/041002/1206931}
\item Topology optimization of liquid cooling plate (bionic leaf-vein).
  \emph{Int. J. Heat Mass Transf.} 2024.
  \url{https://www.sciencedirect.com/science/article/abs/pii/S0017931024007294}
\item Design of a liquid-cooled BTMS using neural networks $+$ cheetah/salp swarm.
  \emph{Sci. Rep.} 2025. \url{https://www.nature.com/articles/s41598-025-15359-0}
\item ML-enhanced control co-design of immersion-cooled BTMS.
  \emph{J. Appl. Phys.} 2024.
  \url{https://pubs.aip.org/aip/jap/article/136/2/025001/3302670}
\end{itemize}

\end{document}

