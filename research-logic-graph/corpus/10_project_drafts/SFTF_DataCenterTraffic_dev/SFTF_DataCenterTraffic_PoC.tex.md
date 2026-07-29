# LaTeX source: SFTF_DataCenterTraffic_PoC.tex

Source: `D:\__SFTF_Projects(2026)\SFTF_DataCenterTraffic_dev\draft\SFTF_DataCenterTraffic_PoC.tex`

% !TEX program = xelatex
% Directed-SFTF warm starts for asymmetric DC traffic — PoC
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

\title{\textbf{비대칭 데이터센터 트래픽의 방향 분해 warm start:\\
$T=S+A$ 사다리와 LP 하한 기준의 매칭된 계측}\\[2mm]
\large Directed-SFTF 인스턴스(multi-commodity routing)의 개념증명(PoC) v0.1}
\author{SFTF\_DataCenterTraffic\_dev}
\date{2026-07}

\begin{document}
\maketitle

\begin{abstract}
\noindent
데이터센터 트래픽 행렬 $T$의 전치 분해 $T=S+A$(대칭$+$반대칭)에서,
반대칭부 $A$ --- 통신의 순방향(net direction) --- 를 유지하는 것이
multi-commodity 라우팅 warm start에 얼마나 기여하는지, 문헌의 공개
토폴로지 4족(leaf-spine, fat-tree $k{=}4$, BCube(4,1), Jellyfish)과
비대칭 TM 3족(gravity/hotspot/permutation, $\|A\|/\|T\|$ 중앙값
$0.62$--$0.66$)에서 매칭된 사다리로 계측했다. 사다리는 oblivious(수요
무시) / random(순서 무작위) / \term{symmetric(이전 세대 요약: 쌍의
수요를 $S_{ij}$로 추정 --- 9/1 편중과 5/5 균등을 구분 못 하는 부호
맹목)} / \term{directed(참 $T$)}이며, 전부 동일한 결정론적 국소탐색
solver와 splittable-flow LP 하한(신뢰 기준)을 공유한다. 결과의 몸통은
\term{warm start 자체}다: oblivious 시드는 solver 수렴에 4--47스윕을
쓰거나 영구 gap($+$9--$200\%$p)을 남기지만, 수요 인지 warm start는
1--2스윕에 수렴한다(장애 복구에서도 동일: 28 vs 1스윕). 그 위에서 부호
정보의 몫은 \term{완만하지만 일관}된다: 엘리펀트가 1:1 패브릭에 걸리는
fat-tree에서 directed gap 3\% vs symmetric 4\%(oblivious 12\%), 통제된
비대칭 다이얼 $T(\alpha)=S+\alpha A$에서 $\alpha{=}0$ 앵커는 정확히
동률(3.3\%)이고 $\alpha{>}0$에서 symmetric이 0.4--2.1\%p 뒤처진다
($\alpha{=}0.75$ 동률 1점 포함 --- 정직 보고). 균일 플로우(permutation)
에서는 수요 추정의 단조변환 불변성 때문에 두 렁이 정확히 동률이 되는
것을 기전과 함께 보고한다. 부수 발견 두 가지도 정직하게 남긴다: 초기
symmetric 렁 설계(풀링 혼잡 추정)는 수요 신호를 절반화해 한 스파인에
49개 플로우가 몰리는 병리를 만들었고(설계 교정의 기록), permutation의
전 방법 공통 gap $\sim$100\%는 unsplittable 정수성 갭(LP는 분할 가능)
이라 사다리 비교에는 영향이 없다.
\end{abstract}

% ============================================================================
\section{서론}
% ============================================================================

데이터센터 트래픽은 생산자$\ne$소비자(gravity), incast(hotspot), 일방
전송(permutation)으로 본질적으로 전치 비대칭이다. SFTF 가족의 directed
확장이 묻는 것: 수요 요약을 대칭 텐서 $S$까지만 유지하는 것과 반대칭
$A$(부호)까지 유지하는 것의 차이가, 동일 solver·동일 예산에서 얼마나
계측되는가. SFTF는 warm starter일 뿐이며 최종 답은 항상
solver(국소탐색$+$LP 기준)가 낸다(Agents.md 규칙 1).

% ============================================================================
\section{방법}
% ============================================================================

\term{토폴로지}: 문헌 공개 4족의 절차적 구현 --- leaf-spine(8리프
$\times$4스파인, 32호스트), fat-tree $k{=}4$(Al-Fares), BCube(4,1),
Jellyfish(랜덤 정규 그래프). \term{병목 배치는 의도적}이다: 호스트
링크는 과잉(40), 패브릭은 타이트(10--12) --- 강제 호스트 링크가 LP
하한을 지배하면 어떤 라우팅 선택도 그 하한을 못 움직여 전 방법이
동률로 묶인다(초기 설정에서 관측된 천장, 교정 기록). \term{TM}: gravity
(로그정규 in/out 질량), hotspot(소수 싱크로 70\%), permutation(일방,
호스트당 엘리펀트 1개), symmetric 대조. 총량은 엘리펀트가 패브릭 용량
스케일에 걸리도록 고정. \term{사다리}: 공통 탐욕 시딩(혼잡 투영
가중치)에서 가시성만 다르다 --- oblivious는 혼잡 무시, random은 순서
무작위, symmetric은 \emph{결정 시 수요 추정을 $S_{ij}$로}(링크 물리는
방향별 그대로 --- 잃는 것은 쌍의 부호 분배), directed는 참 $t_{ij}$.
\term{solver}: 최악 이용률 엣지의 플로우를 재배치하는 결정론적 국소탐색
(이용률 내림차순 스캔, first-improvement); \term{신뢰 기준}:
source-집계 splittable-flow LP 하한(HiGHS). 지표: 시드/최종 max
utilization의 LP 대비 gap, 수렴 스윕 수, 시드당 10 시드 중앙값.

% ============================================================================
\section{실험}
% ============================================================================

\subsection{사다리 $\times$ 토폴로지 $\times$ TM (M2)}

\begin{table}[h]\centering\small
\caption{LP 하한 대비 최종 gap [\%] / 수렴 스윕(중앙값, 10시드).
발췌 --- 전체는 \texttt{paper\_data.json}.}
\label{tab:ladder}
\begin{tabular}{llcccc}
\toprule
& & oblivious & random & symmetric & \term{directed} \\
\midrule
fat-tree & gravity & 12 / 4 & 11 / 1 & 4 / 1 & $\mathbf{3}$ / 1 \\
BCube & gravity & 3 / 9 & 7 / 4 & 3 / 1 & $\mathbf{2}$ / 1 \\
leaf-spine & gravity & 2 / 47 & 0 / 9 & 0 / 1 & 0 / $\mathbf{1}$ \\
Jellyfish & hotspot & 7 / 23 & 9 / 12 & 10 / 2 & 9 / $\mathbf{1}$ \\
fat-tree & permutation & 300 / 1 & 100 / 1 & 100 / 1 & 100 / 1 \\
\bottomrule
\end{tabular}
\end{table}

세 층위의 결론이 갈린다. (i) \term{warm start의 존재}가 지배적이다:
oblivious는 gap(fat-tree gravity 12\%, permutation 300\%)이나 solver
스윕(leaf-spine 47)으로 대가를 치른다. (ii) \term{수요 순서}도 유의미:
random은 fat-tree gravity에서 $+8$\%p. (iii) \term{부호(A)}의 몫은
완만하다: directed$\le$symmetric이 전 셀에서 성립하지만 격차는 엘리펀트
레짐에서 1\%p 수준이고, 균일 플로우(permutation)에서는 \emph{정확히
동률} --- 모든 수요가 같으면 $S$ 추정은 참값의 단조변환이라 같은 경로를
고른다(기전 설명 가능한 동률). permutation의 전 방법 gap $\sim$100\%는
unsplittable 정수성 갭이다(엘리펀트 8 둘이 용량 12를 나누면 1.33 vs LP
0.8) --- 하한 자체가 도달 불가하며 사다리 비교에는 중립.

\subsection{비대칭 다이얼 (M3)}

fat-tree(1:1 패브릭$+$엘리펀트 --- 크기 오추정이 무는 레짐)에서
$T(\alpha)=S+\alpha A$:

\begin{table}[h]\centering\small
\caption{다이얼별 gap [\%] 중앙값. $\alpha{=}0$은 두 렁이 정의상 같은
결정을 내리는 앵커다.}
\begin{tabular}{lcccccc}
\toprule
$\alpha$ & 0.00 & 0.25 & 0.50 & 0.75 & 1.00 & 1.50 \\
$\|A\|/\|T\|$ & .000 & .216 & .404 & .552 & .662 & .702 \\
\midrule
symmetric & 3.3 & 4.0 & 4.5 & 3.5 & 4.4 & 4.8 \\
\term{directed} & 3.3 & $\mathbf{1.9}$ & $\mathbf{2.5}$ & 3.5 &
$\mathbf{3.5}$ & $\mathbf{4.4}$ \\
\bottomrule
\end{tabular}
\end{table}

앵커 정확 동률(3.3\%) 후 symmetric이 4/5 지점에서 뒤처진다
($+0.4$--$2.1$\%p; $\alpha{=}0.75$ 동률 1점 --- 정직 보고). 완만한
곡선이며, 부호 정보의 가치가 "결정적"이었던 subMarine/Assembly와 달리
이 도메인에선 \term{일관되지만 온건}하다(그림~\ref{fig:alpha}).

\begin{figure}[h]\centering
\includegraphics[width=0.58\linewidth]{pics/dct_alpha.png}
\caption{비대칭 비율 vs LP 대비 gap: symmetric(주황) vs directed(파랑).}
\label{fig:alpha}
\end{figure}

\subsection{장애 복구와 ablation (M4--M5)}

패브릭 스위치 1기(Jellyfish는 링크) 제거 후 재시딩: 최종 gap은 전 방법
비슷하지만 \term{복구 속도}가 갈린다 --- oblivious 3--28스윕 vs directed
1스윕(leaf-spine 28$\to$1). 혼잡 가중 ablation: 순서만 유지하고 혼잡
항을 끄면(leaf-spine) gap 2.1\%/47스윕으로 후퇴 --- \term{warm start의
동력은 혼잡 투영이고, 분해는 그 위의 정밀화}다
(그림~\ref{fig:ladder}).

\begin{figure}[h]\centering
\includegraphics[width=0.49\linewidth]{pics/dct_ladder.png}
\includegraphics[width=0.49\linewidth]{pics/dct_iters.png}
\caption{토폴로지별 평균 gap(좌)과 수렴 스윕(우), TM 3족 평균.}
\label{fig:ladder}
\end{figure}
\begin{figure}[h]\centering
\phantom{.}
\label{fig:iters}
\end{figure}

\subsection{설계 병리의 기록 (정직 노트)}

초기 symmetric 렁은 혼잡 추정을 링크 양방향 풀링으로 정의했는데, 이는
부호만이 아니라 \emph{수요 크기 신호까지 절반화}해 대칭 트래픽
($\alpha{=}0$)에서조차 한 스파인에 49개 플로우가 몰리는 병리(시드 util
0.96 vs directed 0.52$=$LP)를 만들었고, 쌍둥이 plateau 탓에 단일 이동
국소탐색으로 복구되지 않았다. "대칭 요약이 잃는 것은 쌍의 부호 분배"
라는 정의로 교정한 뒤 $\alpha{=}0$ 앵커가 정확히 동률이 되었다 ---
대조군 설계가 비교 대상보다 약하게 \emph{구현}되면 사다리 전체가
오염된다는, 가족 방법론 차원의 교훈으로 남긴다.

% ============================================================================
\section{한계}
% ============================================================================

\begin{itemize}[leftmargin=1.6em,itemsep=1pt]
\item \term{합성 TM·절차적 토폴로지.} 실측 트래픽 트레이스(예: 공개
  클러스터 트레이스) 검증은 후속. 토폴로지 규모도 LP가 PC에서 도는
  수준(수십 노드)으로 제한.
\item \term{solver는 국소탐색.} 상용급 TE 최적화기(MIP/column
  generation) 대비가 아니라, 동일 solver를 공유한 시드 비교다.
\item \term{부호 효과는 온건.} 이 도메인의 헤드라인은 warm start 존재
  자체이며, $A$의 몫은 엘리펀트 레짐 1--2\%p — 과장하지 않는다.
\item \term{splittable LP 하한의 한계.} unsplittable 정수성 갭이 큰
  레짐(permutation)에서는 절대 gap 해석에 주의.
\end{itemize}

% ============================================================================
\section{결론}
% ============================================================================

공개 토폴로지 4족$+$비대칭 TM 3족$+$LP 하한의 매칭된 사다리에서, 수요
인지 warm start는 solver 반복을 4--47$\to$1로 줄이거나 영구 gap을
제거하며, 장애 복구에서도 같은 이득을 보인다. 반대칭부 $A$를 유지하는
directed 렁은 symmetric 렁을 전 셀에서 하회하지 않고 엘리펀트 레짐에서
0.4--2.1\%p 앞선다 --- $\alpha{=}0$ 앵커 동률과 균일-플로우 동률의
기전까지 포함해, 부호 정보의 가치가 도메인마다 다르게 계량된다는 가족
시리즈("필요 모멘트 차수는 도메인이 정한다")의 네 번째 데이터 포인트다:
\term{이 도메인에서 1차(부호)는 완만·일관, 지배 요인은 warm start
자체}.

\appendix
% ============================================================================
\section{재현 방법}
% ============================================================================
저장소 루트에서:
\begin{quote}\ttfamily\small
uv sync\\
uv run pytest -q\hfill\rmfamily(수용 테스트 9개: 분해·부호 계약·LP$\le$휴리스틱·결정론)\\
\ttfamily uv run python scripts/build\_paper\_data.py\hfill\rmfamily(전 수치·그림, $\sim$1.5분)
\end{quote}
외부 데이터 없음. 토폴로지·TM·시드·솔버가 전부 결정론이라 표·그림
수치는 비트 단위로 재현된다(\texttt{draft/paper\_data.json}).

\end{document}

