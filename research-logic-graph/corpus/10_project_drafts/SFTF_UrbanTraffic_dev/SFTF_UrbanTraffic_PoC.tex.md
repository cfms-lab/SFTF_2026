# LaTeX source: SFTF_UrbanTraffic_PoC.tex

Source: `D:\__SFTF_Projects(2026)\SFTF_UrbanTraffic_dev\draft\SFTF_UrbanTraffic_PoC.tex`

% !TEX program = xelatex
% D-SFTF reversible lanes — PoC (EXPERIMENT_PLAN M2-M4 완주)
% 수치·그림: uv run python scripts/build_paper_data.py (draft/paper_data.json)
\documentclass[11pt]{article}

\usepackage{kotex}
\usepackage{fontspec}
\setmainfont{Latin Modern Roman}
\setsansfont{Latin Modern Sans}
\setmonofont{Latin Modern Mono}
\setmainhangulfont{Malgun Gothic}
\setsanshangulfont{Malgun Gothic}

\usepackage[a4paper,margin=25mm]{geometry}
\usepackage{amsmath,amssymb}
\usepackage{booktabs}
\usepackage{graphicx}
\usepackage{caption}
\captionsetup{font=small,labelfont=bf}
\usepackage{enumitem}
\usepackage{xcolor}
\usepackage[colorlinks=true,linkcolor=blue!55!black,citecolor=teal!60!black,
            urlcolor=blue!55!black]{hyperref}

\newcommand{\term}[1]{\textbf{#1}}

\title{\textbf{가역차로 배분의 시공간 D-SFTF 필드:\\
warm start는 언제 가치가 있는가 --- 정확 DP·독립 UE 기준의 정직한 계측}\\[2mm]
\large Directed-SFTF 인스턴스(reversible lanes)의 개념증명(PoC) v0.1}
\author{SFTF\_UrbanTraffic\_dev}
\date{2026-07}

\begin{document}
\maketitle

\begin{abstract}
\noindent
시간 의존 비대칭 수요 $q^\pm[e,t]$의 정규화 반대칭 성분을 데이터 항으로,
회랑 결합·시간 연속·이력(hysteresis)을 정규화로 갖는 JAX 미분가능
\term{D-SFTF 필드}로 가역차로 배분을 warm start하는 파이프라인의 검증
계획(M2--M4)을 완주했다. 기준은 셋: 동일 설정의 하류 투영경사
solver(BPR 완화 목적), \term{정확 동적계획 최적해}(전이비용 포함 이산
문제의 전역 최적), 그리고 계획이 한 번도 보지 못한 \term{독립
Frank--Wolfe 사용자균형(UE) 재채점}. 5 시나리오 $\times$ 30시드의 쌍체
계측이 준 첫 번째 답은 \term{사전 주장(M2)의 기각}이다: 저렴하고 강한
하류 solver는 초기화 흔적을 지운다 --- 어떤 시드에서 출발해도 최종
gap은 DP 대비 $0.0$--$0.6\%$로 동일하고, 반복 절감도 없다(dsftf/local의
초기 gap이 이미 $-1$--$2\%$라 잴 여지 자체가 없음). warm start의 실제
가치는 두 곳에서 나타난다. (i) \term{solver 없이 쓰는 직접 투영 계획}:
D-SFTF 필드의 즉석 정수 계획은 DP 대비 $2.4$--$4.7\%$로 fixed
($14$--$22\%$)·random($110$--$362\%$)을 압도하며, (ii) 관측이 노이즈일
때 국소 비례 배분과 갈라진다 --- \term{25\% 예보 노이즈에서 local
$8.5\%$ vs D-SFTF $3.1\%$}(전환 수 9$\to$6): 정규화가 노이즈 필터로
작동한다. 독립 UE 재채점에서는 D-SFTF/local 직접 계획이 BPR-정확
DP 계획과 동급이거나 그보다 낫다(reversal: 12.37 vs 12.44분) ---
proxy 최적 $\ne$ UE 최적이라는 모델 불일치까지 그대로 보고한다.
$\lambda$ 민감도는 이 코퍼스에서 공간 결합이 직접 계획을 오히려
해치고($1.5\to4.8\%$) 이력 항은 소폭 돕는다는 비직관적 결과를 남겼다.
가족 시리즈의 다섯 번째 데이터 포인트: \term{warm start의 가치는 하류
solver의 강도에 반비례하며, 강한 solver 앞에서 필드의 몫은 초기화가
아니라 solver-free 대체 계획 --- 특히 노이즈 관측 레짐 --- 에 있다}.
\end{abstract}

% ============================================================================
\section{서론}
% ============================================================================

가역차로는 시간대별로 방향 배분을 바꾸는, 반대칭 수요 성분의 가장
직설적인 소비자다. 본 PoC는 스캐폴드에 이미 구현된 D-SFTF 필드(M1:
미분가능 목적·차로 보존 투영·국소 비례 퇴화 검증·Mathematica 대칭
검사)를 이어받아, 계획 문서의 남은 검증(M2 하류 최적화, M3 시나리오
연구, M4 독립 검증)을 실행한 기록이다. 주장 범위는 초기화·구조화이며
교통 배정을 대체하지 않는다(Agents.md).

% ============================================================================
\section{방법}
% ============================================================================

\term{필드}: $x\in[-1,1]^{T\times E}$가
$\sum w(x-d)^2+\lambda_s\sum c_{eg}(x_e-x_g)^2+\lambda_t\sum(\Delta_t
x)^2+\lambda_h\sum(x-x_{\rm prev})^2$를 최소화($d$= 정규화 반대칭 수요,
JAX 투영경사). $\lambda{=}0$이면 $x{=}d$(국소 비례)로 정확히
퇴화 --- local 대조군은 사다리의 이전 세대다. \term{사다리}: fixed(고정
3:3)/random/local/D-SFTF, 전부 \emph{예보} 수요만 보고 시딩하며 평가는
참 수요로 한다. \term{하류 solver}: BPR 평균통행시간$+$평활 전환
페널티의 투영경사(동일 설정). \term{신뢰 기준 1}: 결합 상태공간 동적
계획의 전역 최적(이산 차로$+$전이비용). \term{신뢰 기준 2}: 독립
UE --- 방향별 총수요가 세 회랑에 Frank--Wolfe 균형으로 분산될 때의
평균 통행시간(proxy가 가정한 고정 배정과 \emph{다른} 모델).
\term{시나리오}: balanced/commuter/incident/reversal/forecast-noise
(25\% 관측 노이즈), 시드 순수 함수, 30시드 쌍체.

% ============================================================================
\section{실험}
% ============================================================================

\subsection{M2의 기각: 강한 solver는 초기화를 지운다}

모든 시나리오에서 하류 solver를 수렴까지 돌리면 \term{최종 gap은 출발점과
무관하게 동일}하다(DP 대비 0.0--0.6\%; random에서 출발해도 같다). 반복
절감 주장도 성립하지 않는다: dsftf/local의 \emph{초기} 완화 목적이 이미
DP 최적의 $-1$--$2\%$ 수준이라 절감을 측정할 하강 구간 자체가 없다.
계획 문서의 M2 기대("반복·최초 가능해 도달 시간 단축")는 이 설정에서
\term{기각}이며, 저렴한 1차 solver가 수천 반복을 공짜로 돌 수 있는
문제에서는 warm start가 애초에 불필요하다는 것이 정직한 결론이다.

\subsection{warm start의 실제 가치: solver-free 직접 계획}

\begin{table}[h]\centering\small
\caption{직접 투영 계획(하류 solver 없이 필드를 그대로 정수화)의 DP
대비 gap [\%] / 차선 전환 수 (30시드 중앙값).}
\label{tab:direct}
\begin{tabular}{lcccc}
\toprule
& fixed & random & local & \term{D-SFTF} \\
\midrule
balanced & 0.0 / 0 & 110 / 22 & 0.0 / 0 & 0.0 / 0 \\
commuter & 13.8 / 0 & 248 / 22 & 2.0 / 6 & 2.4 / 6 \\
incident & 22.3 / 0 & 305 / 22 & $\mathbf{1.9}$ / 6 & 2.5 / 6 \\
reversal & 15.9 / 0 & 362 / 22 & 4.8 / 6 & $\mathbf{4.7}$ / 6 \\
forecast-noise & 13.8 / 0 & 248 / 22 & 8.5 / 9 & $\mathbf{3.1}$ / $\mathbf{6}$ \\
\bottomrule
\end{tabular}
\end{table}

즉석 계획으로서 D-SFTF는 DP의 2--5\% 안에 든다. 깨끗한 관측에서는
국소 비례(local)와 동률이거나 소폭 뒤진다(incident 1.9 vs 2.5 ---
정직 보고). 사다리가 갈라지는 곳은 \term{관측이 노이즈일 때}다:
25\% 예보 노이즈에서 local은 노이즈를 그대로 추종해 $8.5\%$/전환 9회로
밀리고, D-SFTF의 정규화가 필터로 작동해 $3.1\%$/전환 6회를 지킨다
(그림~\ref{fig:gap}). 이것이 이 도메인에서 시공간 결합 필드의 존재
이유다.

\begin{figure}[h]\centering
\includegraphics[width=0.66\linewidth]{pics/urb_gap.png}
\caption{시나리오별 직접 투영 계획의 DP 대비 gap(30시드 중앙값).
forecast-noise에서만 local(주황)과 D-SFTF(파랑)가 갈라진다.}
\label{fig:gap}
\end{figure}

\subsection{M4: 독립 UE 재채점과 모델 불일치}

\begin{table}[h]\centering\small
\caption{직접 계획의 UE 평균 통행시간 [분] (20시드 중앙값). UE는 계획
과정이 보지 못한 모델이다.}
\begin{tabular}{lccccc}
\toprule
& fixed & random & local & \term{D-SFTF} & DP(exact) \\
\midrule
commuter & 13.07 & 14.91 & 12.35 & 12.37 & 12.35 \\
reversal & 13.14 & 14.12 & 12.39 & $\mathbf{12.37}$ & 12.44 \\
\bottomrule
\end{tabular}
\end{table}

수요 인지 계획(local/D-SFTF)의 proxy 이득은 독립 모델에서도 유지된다
(fixed 대비 $-0.7$분, random 대비 $-2.5$분). 흥미로운 정직 발견:
reversal에서 \term{BPR-정확 DP 계획이 D-SFTF 직접 계획보다 UE에서
나쁘다}(12.44 vs 12.37) --- proxy의 전역 최적이 UE 최적이 아니다.
"정확 solver"의 정확성은 그 목적함수 안의 이야기라는, 검증 사다리
설계의 일반 교훈이다.

\subsection{$\lambda$ 민감도 (M3b, 정직 보고)}

직접 계획 기준(commuter, 10시드): 공간 결합 $\lambda_s$는 키울수록
해롭다($0\to1$에서 gap $1.5\to4.8\%$) --- 데이터 항이 이미 강한 이
코퍼스에서 회랑 간 평활화는 과잉이다. $\lambda_t$는 중립($2.4$--$2.7\%$),
$\lambda_h$는 소폭 이득($0\to0.5$에서 $2.6\to2.1\%$). 전환 수는 전부
5--6으로 불변. 기본값이 최적이 아니라는 것, 그리고 정규화의 진짜 몫은
$\lambda$ 축이 아니라 \emph{노이즈 레짐}(위 8.5$\to$3.1\%)에서
나타난다는 것을 그대로 남긴다.

% ============================================================================
\section{한계}
% ============================================================================

\begin{itemize}[leftmargin=1.6em,itemsep=1pt]
\item \term{작은 합성 회랑망.} 3회랑$\times$6기간, 파라미터화된 수요.
  실측 검지기 데이터·대규모 격자망은 후속.
\item \term{UE는 정적·평행 회랑.} SUMO 마이크로시뮬레이션(M4의 원안)은
  미실행 --- 독립 검증은 정적 UE까지다.
\item \term{하류 solver가 저렴한 문제.} 초기화 가치의 부정 결과는 이
  문제 크기에 조건부다. 반복이 비싼 solver(대규모 조합 최적화)에서는
  결론이 뒤집힐 수 있으며, 그것이 후속 실험의 정확한 위치다.
\item \term{$\lambda$ 기본값 비최적.} 공간 결합의 역효과는 코퍼스
  의존일 수 있다.
\end{itemize}

% ============================================================================
\section{결론}
% ============================================================================

계획된 검증을 끝까지 돌린 결과, 이 문제에서 D-SFTF의 가치는 계획
문서가 기대한 곳(solver 반복 절감)에 있지 않았고 --- 강한 하류 solver는
초기화를 지운다는 기각을 쌍체 30시드로 확정했다 --- 실제 가치는
\term{solver-free 직접 계획}(DP 2--5\%, fixed/random 압도)과 \term{노이즈
관측 레짐의 정규화 필터}(local 8.5\% vs D-SFTF 3.1\%)에 있었다. 독립
UE 재채점은 이 이득이 proxy 밖에서도 유지됨을, 그리고 proxy-정확
최적이 UE 최적이 아님을 함께 보여준다. 가족 시리즈 다섯 번째 데이터
포인트: \term{warm start의 가치는 solver 강도에 반비례한다 --- 필드가
빛나는 곳은 초기화가 아니라, solver를 생략해야 하거나 관측을 믿을 수
없는 곳이다}.

% Keep the short reproducibility appendix with the conclusion page.
\enlargethispage{3\baselineskip}
\appendix
% ============================================================================
\section{재현 방법}
% ============================================================================
저장소 루트에서:
\begin{quote}\ttfamily\small
uv sync\\
uv run pytest -q\hfill\rmfamily(수용 테스트 13개: 퇴화·JAX 기울기·DP$\le$휴리스틱·UE 균형)\\
\ttfamily uv run python scripts/build\_paper\_data.py\hfill\rmfamily(전 수치·그림, $\sim$2분)
\end{quote}
외부 데이터 없음. 시나리오·시드·solver가 전부 결정론이며
\texttt{draft/paper\_data.json}에 수치가 고정된다. Mathematica 대칭
검사는 \texttt{scripts/verify\_dsftf.wls}.

\end{document}

