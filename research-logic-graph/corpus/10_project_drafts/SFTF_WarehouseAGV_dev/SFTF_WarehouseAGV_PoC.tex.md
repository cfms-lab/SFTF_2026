# LaTeX source: SFTF_WarehouseAGV_PoC.tex

Source: `D:\__SFTF_Projects(2026)\SFTF_WarehouseAGV_dev\draft\SFTF_WarehouseAGV_PoC.tex`

% !TEX program = xelatex
% Directed-SFTF warehouse AGV — PoC (SimPy DES 검증, 정직한 부정 결과)
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

\title{\textbf{창고 AGV 통로 방향화에서 방향 수요장은 왜 실패하는가:\\
SimPy DES 검증이 준 3중 부정과 순환 구조의 지배}\\[2mm]
\large Directed-SFTF 인스턴스(warehouse AGV)의 개념증명(PoC) v0.1}
\author{SFTF\_WarehouseAGV\_dev}
\date{2026-07}

\begin{document}
\maketitle

\begin{abstract}
\noindent
비대칭 OD 수요 텐서의 부호 있는 통로 흐름으로 협소통로의 일방화를
제안하는 directed-SFTF warm start를, SimPy 이산사건 시뮬레이션(DES:
용량 1 통로 자원, 방향 전환 청소 지연, 무교착 노드 대기 프로토콜)으로
절차적 창고 21종$\times$수요 3족(flow-through/zoned/balanced)에서
검증했다. 결과는 \term{3중의 정직한 부정}이다. (1) 수요 흐름만으로
방향화한 naive warm start는 flow-through에서 파국적이다(평균 완료 219분
vs 전량 양방향 106분) --- \term{공차 귀환 흐름의 좌초}: 적재 흐름은
일방이어도 차량 흐름은 보존적이다. (2) 공차 재배치를 gravity 결합으로
추정해 총 차량 흐름으로 방향화한 보존 수정판도 양방향 기준선 수준에
그친다(71 vs 68분). (3) 수요-가중 거리 proxy로 순환 위상을 고르는
잔여 역할마저 실패한다(혼잡 동역학을 반영 못 하는 proxy의 배신). 이기는
것은 \term{수요 부호에 완전히 무관한 맨해튼식 교차 순환(curl)
구조}다: 중앙값 13.6분으로 최고 수요-정보 방법 대비 평균 $+9.9$분
(95\% CI $[+2.8,+18.1]$, 21창고 중 14승). 경계 조건도 계측했다:
방향 전환 지연이 0이면 양방향이 최선(일방화는 우회만 낳음)이고 지연
1분부터 순환 구조가 역전한다 --- 결론 전체가 협소통로 물리에
조건부다. DES-in-the-loop 국소탐색(예산 40평가)은 잘못된 구조
prior를 구제하지 못한다(directed 시작 $63.8\to59.1$ vs alternating
시작 $14.2\to11.5$). Helmholtz 언어로 요약하면: \term{폐쇄 차량계에서
수요의 반대칭(발산) 성분은 공차 흐름에 의해 소거되며, 유효한 방향
구조는 솔레노이드(순환) 성분이다 --- 이는 부호 있는 수요 요약으로부터
나오지 않는다}. directed-SFTF 시리즈의 여섯 번째이자 마무리 데이터
포인트: 방향장 warm start의 전제가 붕괴하는 도메인의 정확한 식별.
\end{abstract}

% ============================================================================
\section{서론}
% ============================================================================

일방통행 통로 설계는 반대칭 수요의 자연스러운 소비자처럼 보인다 ---
그래서 이 스캐폴드의 원래 가설은 "부호 있는 통로 흐름이 일방화 방향을
결정한다"였다. 본 PoC는 그 가설을 승격 조건이었던 DES(SimPy) 검증에
끝까지 통과시키는 대신, \term{어디서·왜 실패하는지}를 매칭된 사다리로
계측한 기록이다. 가족 시리즈에서 부정 결과는 폐기물이 아니라 유효
범위의 경계 측정이다.

% ============================================================================
\section{방법}
% ============================================================================

\term{DES(신뢰 검증기)}: SimPy --- 통로당 용량 1 자원(양방향 통로는 두
방향이 공유), 직전 통과 방향과 다르면 청소 지연 2분(협소통로 물리),
노드 대기 프로토콜(무교착 구성적), 시드 고정 Poisson류 작업 도착,
FIFO 함대(공차 이동 포함). 목적 = 평균 작업 완료시간$+$미완료 페널티,
DES 시드 3개 평균. \term{강한 연결성 복원}: 공차 재배치 때문에 레이아웃은
OD-쌍 연결이 아니라 전 노드 강연결이어야 한다(SCC 병합 복원 --- 초기
버전의 OD-만 복원은 차량을 좌초시켰다). \term{사다리}: bidir(전량
양방향) / random / symmetric(불균형 크기만 알고 부호 모름 --- 정칙
방향: 절반이 역방향) / directed\_naive(수요 부호) / directed(수요$+$공차
추정 = 총 차량 흐름 부호) / alternating(맨해튼 교차 순환, 수요 무관) /
curl\_field(4개 순환 위상 중 총흐름-가중 최단거리 최소 위상 선택 ---
방향장의 잔여 역할 시험). \term{인스턴스}: 격자 3--5$\times$4--7,
수요 3족, 시드 순수 함수 21종.

% ============================================================================
\section{실험}
% ============================================================================

\subsection{사다리: 순환 구조의 지배 (M1)}

\begin{table}[h]\centering\small
\caption{평균 작업 완료시간 [분] (가족별 중앙값, DES 시드 3평균).}
\label{tab:ladder}
\begin{tabular}{lccccccc}
\toprule
& bidir & random & symm. & naive & directed & \term{altern.} & curl\_f. \\
\midrule
flow-through & 106 & 47 & 165 & 219 & 86 & $\mathbf{16}$ & 51 \\
zoned & 55 & 36 & 62 & 40 & 65 & $\mathbf{14}$ & 15 \\
balanced & 46 & 45 & 51 & 61 & 60 & $\mathbf{11}$ & 12 \\
\midrule
전체 중앙값 & 68.1 & 44.0 & 64.0 & 61.4 & 71.0 & $\mathbf{13.6}$ & 15.1 \\
\bottomrule
\end{tabular}
\end{table}

부정 1(\term{공차 좌초}): naive 방향화는 flow-through에서 219분 ---
모든 통로가 출하구를 향해 정렬되면 귀환 공차가 소수의 복원 통로로
몰린다. 적재 수요는 일방이지만 \emph{차량} 흐름은 보존적이라는 사실을
수요 텐서는 모른다. 부정 2(\term{보존 수정의 한계}): 공차 흐름을
gravity 결합으로 추정해 합산하면 총 흐름의 반대칭부가 거의 소거되어,
방향화할 신호 자체가 사라진다(71분 $\approx$ bidir 68분). 부정
3(\term{proxy의 배신}): 남은 역할로 시험한 순환 위상 선택(curl\_field)
도 수요-가중 \emph{거리}가 혼잡 동역학과 어긋나 고정 위상보다 못한
선택을 한다(flow-through 51 vs 16). 이기는 것은 어떤 수요 정보도 쓰지
않는 교차 순환이다: 우회는 최대 1블록, 방향 전환은 0회
(그림~\ref{fig:ladder}). 쌍체 통계(M4): 최고 수요-정보 방법 $-$
alternating $= +9.9$분, 95\% CI $[+2.8, +18.1]$, 21중 14승.

\begin{figure}[h]\centering
\includegraphics[width=0.72\linewidth]{pics/agv_ladder.png}
\caption{수요 가족별 사다리(낮을수록 좋음). 옥색 = alternating.}
\label{fig:ladder}
\end{figure}

\subsection{경계 조건: 협소통로 물리 (M2)}

\begin{figure}[h]\centering
\includegraphics[width=0.52\linewidth]{pics/agv_changeover.png}
\caption{방향 전환 지연 스윕: 0에서는 bidir가 최선, 1분부터 순환 구조가
역전, 지연이 클수록 격차 확대.}
\label{fig:co}
\end{figure}

전환 지연 $=0$이면 일방화는 우회만 낳아 bidir(8.9분)가 alternating
(10.7분)보다 낫다. 지연 1분에서 역전(19.8 vs 11.5), 4분에서 4$\times$
(105.7 vs 24.4). \term{본 연구의 모든 결론은 협소통로(전환 지연 $>0$)
물리에 조건부}이며, 광폭 통로 창고에는 적용되지 않는다.

\subsection{구조 prior는 탐색으로 복구되지 않는다 (M3)}

DES-in-the-loop 국소탐색(통로별 방향 뒤집기/재개방, 예산 40 DES 평가):
directed 시작은 $63.8\to59.1$로 미세 개선에 그치고, alternating 시작은
이미 $14.2$에서 출발해 $11.5$까지 더 내려간다. 잘못된 구조 prior와의
격차(약 5$\times$)는 이 예산 규모의 탐색으로 복구 불가능하다 ---
\term{여기서 비싼 것은 solver이고(전 후보가 DES), 그래서 warm start가
중요해야 마땅한 도메인인데, 정작 올바른 warm start는 방향 수요장이
아니라 부호-무관 순환 구조였다}(그림~\ref{fig:search}).

\begin{figure}[h]\centering
\includegraphics[width=0.52\linewidth]{pics/agv_search.png}
\caption{DES 평가 예산 내 최고 점수 궤적(대표 인스턴스).}
\label{fig:search}
\end{figure}

% ============================================================================
\section{한계}
% ============================================================================

\begin{itemize}[leftmargin=1.6em,itemsep=1pt]
\item \term{격자 창고·단순 함대 정책.} FIFO 배차·최근접 경로만 사용.
  배차 최적화·구역 지정과의 상호작용은 미측정.
\item \term{공차 추정은 gravity 근사.} 실제 배차 정책 의존 공차 흐름의
  정밀 모델은 후속 --- 다만 어떤 공차 추정도 반대칭부 소거라는 구조적
  결론을 뒤집기 어렵다.
\item \term{전환 지연 파라미터.} 2분 기본값은 스타일화된 값이다(스윕으로
  경계는 제시).
\item \term{순환 구조는 격자 특화.} 비격자 레이아웃에서 solenoidal
  설계의 일반화는 열린 문제.
\end{itemize}

% ============================================================================
\section{결론}
% ============================================================================

DES 검증 조건을 완주한 결과는 방향 수요장의 3중 실패와 부호-무관 순환
구조의 지배였고, 그 기전(공차 귀환의 반대칭 소거, proxy-혼잡 불일치,
구조 prior의 탐색 불가 복구)과 경계(전환 지연 $>0$)까지 계측했다.
directed-SFTF 시리즈의 여섯 번째 데이터 포인트로서 이 프로젝트가
기여하는 것은 실패의 정확한 지도다: \term{폐쇄 차량계에서 수요의
발산(홀수) 성분은 소거되고 유효한 방향 구조는 솔레노이드 성분이다 ---
방향장 warm start를 쓰려면 먼저 그 도메인의 차량이 어디로 돌아오는지
물어야 한다}.

\appendix
% ============================================================================
\section{재현 방법}
% ============================================================================
저장소 루트에서:
\begin{quote}\ttfamily\small
uv sync\\
uv run pytest -q\hfill\rmfamily(수용 테스트 7개: 보존 마진·강연결·DES 결정론·ablation 역전)\\
\ttfamily uv run python scripts/build\_paper\_data.py\hfill\rmfamily(전 수치·그림, $\sim$1분)
\end{quote}
외부 데이터 없음. 창고·수요·DES가 전부 시드 순수 함수라 표·그림 수치는
비트 단위로 재현된다(\texttt{draft/paper\_data.json}).

\end{document}

