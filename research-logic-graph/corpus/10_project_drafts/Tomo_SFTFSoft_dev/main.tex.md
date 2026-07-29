# LaTeX source: main.tex

Source: `D:\__SFTF_Projects(2026)\Tomo_SFTFSoft_dev\draft\main.tex`

% =====================================================================
%  main.tex — 한글(SCI 국문) 원고 (xelatex + kotex 로 컴파일)
%
%  빌드:  uv run python scripts/build_pdf.py        (-> main.pdf)
%        uv run python scripts/build_docx.py       (-> main.docx, 그림 포함)
%        uv run python scripts/export_tikz_svg.py  (TikZ -> draft/pics/*.svg 백업)
%
%  Lockstep: 이 파일은 draft/main_en.tex (영문)과 한 쌍이다. 한쪽에 추가/수정한
%  내용·그림·절은 같은 리비전에서 반대쪽에도 미러링한다. 국문판은 각주로 용어/기호를
%  처음 쓸 때 정의하고, 영문판은 각주 없이 그 직관을 본문 산문에 녹인다.
%
%  ※ 초안 단계에서는 분량/용량을 신경 쓰지 않습니다(최종에 줄임).
% =====================================================================
\documentclass[11pt]{article}

% ---- 한글 (xelatex + kotex) -----------------------------------------
\usepackage{kotex}
\usepackage{fontspec}
\setmainhangulfont{Malgun Gothic}

% ---- 수식 / 그림 / 표 / 의사코드 ------------------------------------
\usepackage{amsmath,amssymb,amsfonts,bm}
\usepackage{amsthm}
\newtheorem{assumption}{가정}
\newtheorem{proposition}{명제}
\usepackage{graphicx}
\usepackage{svg}                 % \includesvg 로 .svg 직접 삽입 (inkscape 필요)
\usepackage{float}
\usepackage{booktabs}
\usepackage{array}
\usepackage{algorithm}
\usepackage{algpseudocode}
\usepackage{geometry}
\geometry{a4paper, margin=25mm}
\usepackage{hyperref}
\usepackage[numbers]{natbib}

% ---- TikZ (개념도) ---------------------------------------------------
\usepackage{tikz}
\usetikzlibrary{arrows.meta, calc, positioning, decorations.pathreplacing, decorations.pathmorphing, patterns, shapes.geometric}
\usepackage{pgfplots}
\pgfplotsset{compat=1.18}

\graphicspath{{pics/}{./}}

% ---- 기호 매크로 -----------------------------------------------------
\newcommand{\nvec}{\bm{n}}
\newcommand{\mvec}{\bm{m}}
\newcommand{\cvec}{\bm{c}}
\newcommand{\softplus}{\operatorname{softplus}}
\newcommand{\relu}{\operatorname{relu}}

% ---- fig:soft 용 2.5D 솔리드 매크로 (오블리크 깊이 (0.5,0.32)) ----------
% 한 블록(앞·윗·오른쪽 면)을 그린다: \sftfbox{x0}{z0}{x1}{z1}{색}
\newcommand{\sftfbox}[5]{%
  \fill[#5!12] (#1,#2) rectangle (#3,#4);
  \fill[#5!22] (#1,#4) -- (#3,#4) -- ($(#3,#4)+(0.5,0.32)$) -- ($(#1,#4)+(0.5,0.32)$) -- cycle;
  \fill[#5!32] (#3,#2) -- (#3,#4) -- ($(#3,#4)+(0.5,0.32)$) -- ($(#3,#2)+(0.5,0.32)$) -- cycle;
  \draw[#5!55!black,line width=0.3pt] (#1,#2) rectangle (#3,#4);
  \draw[#5!55!black,line width=0.3pt] (#1,#4) -- ($(#1,#4)+(0.5,0.32)$) -- ($(#3,#4)+(0.5,0.32)$) -- (#3,#4);
  \draw[#5!55!black,line width=0.3pt] (#3,#2) -- ($(#3,#2)+(0.5,0.32)$) -- ($(#3,#4)+(0.5,0.32)$);
}
% 공통 솔리드: 받침기둥 + 가로보(오버행) + 수신 계단 j1 + 바닥
\newcommand{\sftfbase}{%
  \fill[pattern=north east lines, pattern color=black!35] (-1.3,-0.18) rectangle (3.7,0);
  \draw[black!55] (-1.3,0) -- (3.7,0);
  \sftfbox{-0.2}{0}{0.8}{3.2}{gray}      % 받침기둥
  \sftfbox{-0.2}{3.2}{3.2}{3.9}{gray}    % 가로보 (밑면 z=3.2, x>0.8 이 오버행)
  \sftfbox{1.8}{0}{2.6}{1.4}{gray}       % 수신 계단 j1
  \draw[gray!35,line width=0.2pt] (-0.2,0)--(0.8,3.2) (0.8,0)--(-0.2,3.2); % 메쉬 느낌 대각
}

\title{미분가능 SFTF 손실항: 수식, 구현, 그리고 검증\\[2mm]
\large Differentiable Support Flow Tensor Field as a Loss Term}
\author{익명 저자}
\date{\today}

\begin{document}
\maketitle

\begin{abstract}
이전 연구의 SFTF (Support Flow Tensor Field)\footnote{Support Flow Tensor Field. 적층제조에서
빌드방향에 따른 지지구조 비용을 면별 레이캐스팅으로 추정하는 기법.}는 빌드방향
$\nvec$ 에 대한 지지비용
$J_{\mathrm{SFTF}}(\nvec)=\tilde R_{\mathrm{aug}}(\nvec)+P(\nvec)=R(\nvec)+B(\nvec)+P(\nvec)$ 를
면별 레이캐스팅으로 계산해
최적 빌드방향을 \emph{이산 구면 샘플링}으로 고른다. 문제는 이 비용이 유용한 물리 직관을
갖고 있으면서도, 기울기를 요구하는 현대적 최적화에는 바로 쓰기 어렵다는 점이다.

본 연구는 같은 SFTF 비용을 \textbf{빌드방향 $\nvec$ 과 정점 좌표 $V$ 양쪽에 대해 미분가능}한
손실항 $L_{\mathrm{SFTF}}(V,\nvec)$ 로 완화하고, PyTorch 참조구현으로 검증한다. 핵심 관찰은
간단하다. 비미분 연산은 본질적으로 각 오버행 면을 단일 수신면(또는 바닥)으로 보내는
\emph{하드 레이캐스팅} 하나이며, 오버행 강도·면적·법선·높이는 이미 $V,\nvec$ 의 매끄러운
함수다. 따라서 하드 레이캐스팅만 \textbf{후보 수신면과 바닥 슬롯에 대한 소프트
어텐션}\footnote{여러 후보에 가중치(softmax 확률)를 분배해 부드럽게 합산하는 연산. 가중치를
날카롭게 만들면 하나의 후보로 수렴한다.}으로 바꾸면 된다.

이 완화는 온도(temperature)\footnote{소프트 어텐션의 날카로움을 조절하는 매개변수. 낮을수록
(또는 $\beta$ 가 클수록) 분포가 한 점으로 집중된다.}를 sharpen 할 때
$L_{\mathrm{SFTF}}\to J_w$ 로 수렴하며(유한차분 기울기와 해석적 기울기의 상대오차
$3\times10^{-10}$), $L_{\mathrm{SFTF}}$ 의 역할은 지지량 \emph{예측}이 아니라 이전 SFTF
파이프라인의 미분가능 재현(\emph{SFTF-정합} 목적)이다. 물리 예측은 같은 완화 기계장치로
\emph{게이트}한 물리항이 맡는다. 첫째, 손실을 \textbf{실제 생산 슬라이서}(3DWOX 가 정적 링크한
legacy CuraEngine 15.04/DP103) 자신의 임계각($60^\circ$)에서 게이트한 지지높이 항 $S_g$ 는 실제
Cura 지지질량을 메쉬평균 순위상관 $\mathbf{+0.80}$(프리미티브·기계부품·유기 대형 스캔을 아우르는
g5test 헤드라인 18메쉬 \emph{전부} 양, $95\%$ CI $[{+}.74,{+}.84]$)으로 예측해 복셀 추정기
TomoNV($+0.46$)를 크게 앞선다. 하드 게이트 대조군이 이 정확도의 원천을 격리한다: $S_g$ 의 모든
매끄러운 성분을 날카로운 극한으로 바꾼 --- 텐서도 어텐션도 완화도 없는 --- 순수 게이트
오버행면적$\times$높이 합 $S_g^{\mathrm{hard}}$ 가 오히려 약간 더 잘 예측하고($+0.87$),
게이트 항에 텐서 손실을 더하면 오히려 내려간다($+0.58$). 즉 예측은 슬라이서-게이트
물리가 전부 견인하며, 완화의 가치는 기울기 공급에 있다. 둘째, 같은 매끄러운
게이트가 정점 기울기 $\partial L/\partial V$ 를 살린다: 재튜닝 없는 단일 레시피로 9개 메쉬를
자기지지 형상으로 변형하면, 실제 지지재가 필요한 \textbf{6개 메쉬 전부}에서 Cura support-only
질량이 $-96\%$--$-100\%$ 제거된다(합계 $14.2\to0.23$ g) --- 방향 샘플링이 원리적으로 불가능한
수만-자유도 설계공간에서 미분가능성만이 주는 성과다. 다만 이 둘째 결과는 첫째와 달리
\emph{슬라이서에 특이적}이며 그대로 보고한다: 같은 형상을 PrusaSlicer 로 재슬라이스하면 제거율이
$-2.7\%$ 에 그친다. 면 각도 기준의 목적함수는 바닥판에 점으로 만나도 무방하기 때문이다 ---
그러면 오버행은 $0$ 이 되지만 슬라이서가 메워야 할 공극은 오히려 높아지고, 최적화된 메쉬 둘은
인쇄 가능한 첫 레이어조차 없다. 게이트를 계단함수 극한으로 조이면 이
최적화가 붕괴함을 절제실험으로 보여, \emph{부드러운 게이트가 기울기의 원천}임을 확인한다.
순전파는 하드, 역전파만 시그모이드인 straight-through 게이트는 소프트 게이트의 최적화
성능(Cura 제거율 $98.0\%$ 대 $98.4\%$)을 유지한 채 게이트 축의 예측 편향을 없앤다.
다중 메쉬 목적 자체가 텐서 항을 포함하지 않으며, 텐서를 더해도 결과가 달라지지 않고
텐서만으로는 실패한다 --- SFTF 텐서는 어느 헤드라인도 견인하지 않는다.
이 밖에 지지부피 항 $S$ 는 TomoNV 와의 메쉬 간 일반화를 거의 2배로 높이고, 회전대칭
퇴화형(구·원기둥)은 임의의 단일 방향 대신 최적해 \emph{집합}(점·원·구면)으로 보고하며,
라벨 없는 GNN 분할상환 추론을 개념증명한다(TomoNV 기준 보류 메쉬 지지질량 백분위 평균
$0.28$, 무작위 $0.41$, 메쉬별 oracle $0.13$) --- 다만 결정 지표인 실제 Cura 백분위에서는
50k--100k면 메쉬를 포함한 GPU 재실험에서도 이점이 확인되지 않아, 기여가 아닌 개념증명으로만 보고한다.
\end{abstract}

\section{서론}
적층제조(3D 프린팅)에서 빌드방향은 지지구조의 양, 표면 품질, 후처리 비용을 좌우하는
일차 설계변수다. 이전 연구의 SFTF~\citep{sftf_engine}는 삼각 메쉬의 각 면에서 빌드방향
반대로 가상의 레이를 쏘아 \emph{어느 면이 어느 면을 떠받치는지}를 찾고, 그 지지관계로부터
빌드방향 지지비용 $J(\nvec)$ 를 만든 뒤 구면을 촘촘히 샘플링해 최적 방향을 고른다. 이
방식은 직관적이고 견고하지만, 핵심 연산인 \emph{레이캐스팅이 미분 불가능}하다는 한계가
있다. 즉 비용 $J(\nvec)$ 의 기울기를 직접 쓸 수 없어, (a) 빌드방향 최적화는 전수에 가까운
샘플링에 의존하고, (b) 형상 자체를 지지친화적으로 바꾸거나 (c) 신경망의 학습 신호로
쓰는 일이 불가능하다.

본 연구는 이 병목을 다음 순서로 푼다. 먼저 SFTF 의 하드 레이캐스팅을 소프트 어텐션으로
완화해 SFTF 비용과 같은 의미를 가진 미분가능 손실을 만든다. 다음으로 그 손실이 SFTF의 하드 비용으로
되돌아가는지, 실제 물리 지지량과는 얼마나 맞는지, 그리고 최적화·형상변형·신경망 학습에
실제로 쓸 수 있는지를 차례로 검증한다. 구체적인 기여는 다음 네 가지다.

\textbf{(1) 슬라이서-게이트 미분가능 지지 목적 $S_g$.} 손실을 생산 슬라이서 \emph{자신의}
임계각($60^\circ$)에서 매끄럽게 게이트한 지지높이 항 $S_g$ 가 실제 Cura(legacy CuraEngine 15.04 /
DP103, 3DWOX 가 정적 링크) 지지질량을 메쉬평균 $\mathbf{+0.80}$(g5test 헤드라인 18메쉬 전부
양)으로 예측해 복셀 추정기 TomoNV($+0.46$)를 크게 앞선다(\S\ref{sec:results}). 하드 게이트 대조군
$S_g^{\mathrm{hard}}$($S_g$ 의 날카로운 극한; 텐서·어텐션·완화 없음)는 오히려 약간 더
높고($+0.87$), $S_g$ 에 $L_{\mathrm{SFTF}}$ 를 더하면 떨어진다($+0.58$) --- 예측 가치는
슬라이서-게이트 물리에 있고, 완화는 그 물리를 최적화 가능하게 만드는 장치다.
역할 분리를 명시한다:
$L_{\mathrm{SFTF}}$ 는 지지량 예측기가 아니라 이전 SFTF 목적의 미분가능 재현(SFTF-정합)이고,
물리 예측은 게이트한 물리항($S$, $S_g$)의 몫이다.

\textbf{(2) 하드 라우팅의 소프트 어텐션 완화 프레임.} $J(\nvec)$ 에서 미분을 막는 \emph{유일한} 연산이
면 단위 하드 레이캐스팅(수신면/바닥으로의 하드 라우팅)임을 — \emph{고정 메쉬 위상, 비퇴화 면,
유일 최근접 수신면, 임계 여유(threshold margin)를 갖는 일반 위치(general position)} 가정 아래 —
식별하고, 이를 후보 수신면과 바닥 슬롯에 대한 \textbf{소프트 어텐션}으로 대체해 빌드방향 $\nvec$ 과
정점 $V$ \emph{양쪽}에 미분가능한 손실항 $L_{\mathrm{SFTF}}(V,\nvec)$ 를 유도하고, 온도 극한에서
$L_{\mathrm{SFTF}}\to J_w$ 임을 명제로 보인다(\S\ref{sec:method}). 이는 미분가능 렌더링의 soft
rasterizer~\citep{softras2019} 가 하드 $z$-버퍼/가시성을 완화한 것과 같은 정신을, 적층제조 지지비용의
하드 레이캐스팅에 적용한 것이다. $S_g$ 의 시그모이드 게이트도 같은 완화 원리의 산물이다.

\textbf{(3) 정점-기울기 자기지지 형상최적화의 다중 메쉬 정량화.} 재튜닝 없는 단일 레시피로
9개 메쉬를 변형해, 실제 지지재가 필요한 6개 메쉬 전부에서 실제 Cura support-only 질량을
$-96\%$--$-100\%$ 제거한다(합계 $14.2\to0.23$ g; 표~\ref{tab:shapeopt-multi}) --- 방향 샘플링이
불가능한 수만-자유도 설계공간에서 미분가능성만이 주는 성과다. 게이트를 계단함수 극한으로
조이면 최적화가 붕괴함을 절제로 보여(구에서 $25$배 악화), \emph{부드러운 게이트가 기울기의
원천}임을 입증한다. 순전파는 하드, 역전파만 시그모이드인 straight-through 게이트는
소프트 게이트의 최적화 성능을 유지한 채 게이트 축의 예측 편향을 없앤다. 텐서 대조는 이 제거가 텐서와 무관함을 확인한다: 목적에 텐서 항이 없고,
$L_{\mathrm{SFTF}}$ 를 더해도 달라지지 않으며, 텐서만으로는 구에서 실패한다.

\textbf{(4) 회전대칭 퇴화형 처리와 개념증명.} 구·원기둥처럼 단일 최적 방향이 정의되지 않는
형상에서 임의의 한 방향 대신 최적해 \emph{집합}(점·원·구면)의 대칭을 분류해 보고하고, PyTorch
참조구현으로 기울기 정확성과 빌드방향 최적화를 개념증명한다. (라벨 없는 분할상환(amortized)
GNN 실험은 의도적으로 기여 목록에 넣지 않는다: 방향 라벨 없이 손실만으로 학습해 TomoNV
지표에서는 성립하나 --- 보류 메쉬 백분위 $0.28$ 대 무작위 $0.41$, oracle $0.13$ --- 결정
지표인 실제 Cura 에서는 50k--100k면 메쉬를 포함한 leave-one-out 재실험에서도 이점이 없어, 개념증명으로만
보고한다(\S\ref{sec:results}).)

\section{관련 연구}\label{sec:related}
\paragraph{자기지지 형상·위상 최적화.} 오버행을 줄이는 한 갈래는 형상/위상 자체를 자기지지가 되도록
설계하는 것이다. 명시적 위상최적화(Moving Morphable Components)로 자기지지 구조를 얻거나~\citep{guo2017self},
밀도 기반에서 오버행 각 제약을 부과하거나~\citep{zhao2017self}, 자중하중까지 함께 다루며~\citep{kumar2022overhang},
밀도 기울기 적분으로 언더컷·오버행 각을 제어하기도 한다~\citep{qian2017undercut}. 나아가 적층제조 제약을
최적화 루프에 직접 넣는 \emph{AM 필터}도 제안되었다~\citep{langelaar2016selfsupp,langelaar2017filter}.
이들은 \emph{체적 밀도 장}을 최적화하며 빌드방향은 대개 고정한다. 본 연구는 표면 메쉬 위의 미분가능 손실로
빌드방향 $\nvec$ 과 정점 $V$ 를 \emph{같은} 목적함수에서 다루고(우리 형상 최적화는 개념증명 수준), 결과를
오버행 각 대리물이 아니라 \emph{실제 슬라이서} 지지질량으로 검증한다는 점이 다르다.

\paragraph{빌드방향 최적화·지지 구조 생성.} 빌드방향은 지지량·표면품질·비용을 좌우하므로 오래된 최적화
대상이며, 지지부피·표면 접근성·지각적 현저성 등을 기준으로 \emph{이산 방향 탐색}이 이뤄져 왔고
\citep{ezair2015orientation,zhang2015perceptual,mirzendehdel2021build}, 최근 리뷰가 그 목적함수와 탐색
전략을 정리한다~\citep{diangelo2020review}. 이와 상보적으로, 방향은 고정한 채 지지 자체를 경제적으로 생성해
재료를 줄이는 갈래도 있다~\citep{vanek2014clever,dumas2014scaffold,jiang2018review}. 이전 연구의
SFTF~\citep{sftf_engine} 는 방향 탐색 계열로, 면별 레이캐스팅으로 방향을 채점한다. 이들은 모두 많은 방향을
샘플링해 저지지 후보를 고르며, 목적함수가 미분가능하지 않아 방향·형상에 대한 경사하강을 직접 구동할 수 없다.

\paragraph{미분가능·신경망 적층제조.} 신경망으로 빌드방향·부품분할·위상을 동시 최적화하거나~\citep{chen2023concurrent},
다축 프린팅의 곡면 슬라이싱을 미분가능 신경장으로 학습하며~\citep{neuralslicer2024}, 이런 예측기의 표현으로
메쉬 고유 신경망이 쓰인다~\citep{hanocka2019meshcnn}. 이들은 각자 \emph{새로운} 미분가능 대리(surrogate)를
설계한다. 본 연구는 \emph{기존 SFTF 지지비용}을 최소 변형으로 미분가능화하여 그 물리 의미를 보존하고, 그
손실이 메쉬 예측기의 라벨 없는 물리 항으로도 쓰일 수 있음을 보인다.

\paragraph{이산 연산의 소프트 완화.} 하드·비미분 연산을 소프트 확률 연산으로 완화해 기울기를 흐르게 하는
발상은 미분가능 렌더링에서 정립되었다 --- soft rasterizer 는 하드 래스터화와 $z$-버퍼 가시성을 확률적
집합(soft aggregation)으로 대체하고~\citep{softras2019,kato2018neural}, 하드웨어 지향·에지 샘플링 정식화는
이를 실무 파이프라인과 불연속 처리로 확장하며~\citep{laine2020modular,loubet2019reparam}, 리뷰가 그 설계
공간을 정리한다~\citep{kato2020survey}. 본 연구의 소프트 수신면 배정은 같은 원리를 SFTF 의 하드 레이캐스팅
(수신면 $\arg\min$ + 면/바닥 이진 판정)에 적용한 것으로, 우리가 아는 한 적층제조 지지비용의 하드 수신면
배정에 이 완화를 직접 적용한 초기 사례다.

\clearpage
\section{방법}\label{sec:method}

\subsection{파장론 비유법 (wavelength analogy)}\label{sec:wavelength}
구체적인 수식에 들어가기 전에, 이후의 완화가 무엇을 하는지 한 장의 그림으로 먼저 설명한다.
TomoNV/SFTF 계열은 지지구조의 부피를 \emph{가상의 태양}이 만드는 물체의
\emph{그림자 부피}에 비유한다(그림~\ref{fig:wavelength}(a)). 이전 연구의 SFTF 는 이 그림자를
날카로운 레이캐스팅으로 계산한다. 본 연구는 그 그림자를 조금 번지게 만들어 기울기가 흐르게
한다. 따라서 핵심 질문은 간단하다: 같은 태양빛을 \emph{입자}로 볼 것인가, \emph{파동}으로
볼 것인가?

\begin{figure}[H]
\centering
\begin{minipage}[t]{0.66\linewidth}
  \centering
  \includegraphics[width=\linewidth]{stft_wave_analogy1.png}
\end{minipage}\hfill
\begin{minipage}[t]{0.31\linewidth}
  \centering
  \begin{tikzpicture}
    \begin{axis}[
        width=0.78\linewidth, height=4.2cm, scale only axis,
        domain=-1:1, samples=121,
        xlabel={\scriptsize $-\mvec_i\cdot\nvec$}, ylabel={\scriptsize $\tilde O_i$},
        xtick={-1,0,1}, ytick={0,1}, tick label style={font=\tiny},
        every axis x label/.style={at={(axis description cs:0.5,-0.08)},anchor=north},
        every axis y label/.style={at={(axis description cs:-0.06,0.5)},rotate=90,anchor=south},
        legend style={font=\tiny, at={(0.03,0.97)}, anchor=north west, draw=none, fill=none},
        legend cell align=left, enlarge x limits=false, clip=false]
      \addplot[black, thick] {max(0,x)}; \addlegendentry{$\max(0,\cdot)$ (입자)}
      \addplot[orange!80!black] {(1/8)*ln(1+exp(8*x))};  \addlegendentry{$\beta{=}8$}
      \addplot[red!75!black, densely dashed] {(1/2)*ln(1+exp(2*x))}; \addlegendentry{$\beta{=}2$ (긴 파장)}
    \end{axis}
  \end{tikzpicture}
  \vspace{-0.5em}

  {\scriptsize\bfseries (c) $\beta$ = 역파장}
\end{minipage}
\caption{파장론 비유. \textbf{(a)} 입자 그림에서는 그림자 경계가 칼같고, 이는 하드 SFTF의
  레이캐스팅에 해당한다. \textbf{(b)} 파동 그림에서는 회절로 경계가 번진다.
  \textbf{(c)} $\beta$ 는 소프트 오버행의 날카로움 손잡이, 즉 유효 역파장처럼 작동한다.}
\label{fig:wavelength}
\end{figure}

\subsubsection{이전 연구의 SFTF 이론 : 입자론적 접근법}
태양빛을 직진하는 \textbf{입자}\footnote{기하광학(ray optics) 근사. 빛을 직진하는 알갱이로
보아 회절·간섭을 무시한다.}로 보면 빛은 휘지 않고 곧게 나아가므로, 장애물의 모서리에서
그림자가 \emph{칼같이} 나뉜다. \emph{이상적인 점광원·평행광 기하광학에서는}\footnote{실제 태양은
각크기가 있어 회절이 없어도 \emph{반그림자}(penumbra)가 생긴다. 여기서는 비유를 또렷이 하기 위해
광원을 한 점(또는 완전 평행광)으로 이상화한 극단을 가정한다.} 정오의 천장 아래 선 사람 $A$ 가 받는
빛의 양은 모서리를 지나는 순간 1에서 0으로 \emph{불연속}하게 떨어진다. SFTF에서 오버행 강도
$\max(0,-\mvec_i\cdot\nvec)$ 와, 각 오버행 면을 가장 가까운 수신면 \emph{하나}로만 보내는
하드 레이캐스팅이 바로 이 입자적 그림자에 해당한다. 그래서 경계에서 함수는 기울기가
꺾이거나(꺾임, kink) 값이 튀어(점프) 미분이 막힌다. 이는 딥러닝에서 ReLU가 $0$ 근처에서
기울기가 갑자기 바뀌는 것과 같은 종류의 비매끄러움이다. 다만 ReLU의 꺾임은 부분기울기로
다룰 수 있는 반면, 하드 레이캐스팅의 수신면 전환은 값 자체가 바뀌는 점프까지 만들 수 있다.

이전 연구의 SFTF~\citep{sftf_engine}는 삼각형 면 $i$ 의 무게중심 $\cvec_i$, 단위 법선 $\mvec_i$,
면적 $A_i$ 에서 출발한다. 빌드방향 $\nvec\in S^2$ 에 대해 바닥 높이와 면별 기본량은
\begin{align}
z_{\mathrm{plate}}(\nvec) &= \min_{\bm v\in V}\ \bm v\cdot\nvec, &
O_i(\nvec) &= \max\!\big(0,\,-\mvec_i\cdot\nvec\big), &
\eta_i(\nvec) &= \cvec_i\cdot\nvec - z_{\mathrm{plate}}(\nvec).
\label{eq:base}
\end{align}
$O_i$ 는 오버행 강도\footnote{면 법선이 빌드방향 반대쪽을 향할수록 커지는 양. 값이 0이면
지지가 필요 없는 면이다.}다. 각 오버행 면에서 $-\nvec$ 방향으로 레이를 쏘아 수신면 $t_i$
를 찾는다. 유효 수신 조건은 $t\neq i$, 레이거리 $>\varepsilon$, 지지높이
$h_{it}=(\cvec_i-\cvec_t)\cdot\nvec>\varepsilon$, 수신면 정렬 $\mvec_t\cdot\nvec>\tau_r\ (\tau_r{=}0.05)$
이며, 여러 후보 중 \emph{가장 가까운}(최소 $h$) 면이 선택된다. 유효 수신이 없으면 면은
바닥으로 떨어진다. 이로부터 이전 연구의 SFTF는 세 지지비용 항~\citep{sftf_engine}을 만든다.
식~\eqref{eq:P}는 오버행 면과 그것을 받치는 수신면의 면적 쌍을 곱해 면--면 지지 부담을
재는 항이고, 식~\eqref{eq:B}는 수신면이 없어 바닥까지 지지해야 하는 경우의 비용을 높이까지
반영해 재는 항이다. 식~\eqref{eq:F}는 소스면과 수신면 법선의 흐름텐서를 모아 방향성 지지
불균형을 평가한다.
\begin{align}
P(\nvec) &= \!\!\sum_{i:\,\text{면지지}}\!\! O_i\,A_i\,A_{t_i},
\label{eq:P}\\
B(\nvec) &= \!\!\sum_{i:\,\text{바닥지지}}\!\! O_i\,A_i\,\big(1+\alpha\,\eta_i\big),
\qquad \alpha=\tfrac{1}{D},
\label{eq:B}\\
\bm F(\nvec) &= \!\!\sum_{i:\,\text{면지지}}\!\!
\frac{O_i A_i A_{t_i}}{1+\alpha\,h_{it_i}}\;\mvec_i\otimes\mvec_{t_i},
\qquad
R(\nvec)=\max\!\big(0,\,-\nvec^{\!\top}\!\operatorname{sym}(\bm F)\,\nvec\big),
\label{eq:F}
\end{align}
여기서 $D$ 는 메쉬 바운딩박스 대각, $\operatorname{sym}(\bm F)=\tfrac12(\bm F+\bm F^{\!\top})$.
출판된 SFTF의 기본 지지비용~\citep{sftf_engine}은
\begin{equation}
J_{\mathrm{SFTF}}(\nvec)=\tilde R_{\mathrm{aug}}(\nvec)+P(\nvec)
=R(\nvec)+B(\nvec)+P(\nvec),\qquad
\nvec^\ast=\arg\min_{\nvec\in S^2} J_{\mathrm{SFTF}}(\nvec).
\label{eq:J}
\end{equation}
여기서 $\tilde R_{\mathrm{aug}}=R+B$는 빌드플레이트를 법선 $n$의 가상 ground receiver로
추가한 증강 텐서의 Rayleigh 기여이다. 본 논문은 미분가능 완화와 물리 재가중을 다루기 위해
\begin{equation}
J_w(\nvec)=w_R\,R(\nvec)+w_P\,P(\nvec)+w_B\,B(\nvec)
\label{eq:Jw}
\end{equation}
도 함께 사용하며, 기본 가중치 $w_R{=}w_P{=}w_B{=}1$이면 $J_w=J_{\mathrm{SFTF}}$이다. 따라서
식 \eqref{eq:base}--\eqref{eq:Jw}는 이전 연구~\citep{sftf_engine}의 이산 지지비용을 본 논문
기호로 정리한 것이다.
\eqref{eq:P}--\eqref{eq:F} 에서 미분을 막는 것은 오직 \emph{수신면 선택}($\arg\min$ 형태의
하드 레이캐스팅)과 그에 딸린 \emph{면/바닥 이진 판정}이다. $\max(0,\cdot)$, $\min$ 은 거의
모든 점에서 미분가능(부분기울기)하므로, 이 \emph{유일성} 주장은 다음 일반 위치 가정 아래에서
성립한다.

\begin{assumption}[일반 위치]\label{asm:gp}
주어진 $(V,\nvec)$ 에서 (i) 메쉬 위상(면 연결관계)은 고정이고, (ii) 모든 면이 비퇴화이며
($A_i>0$), (iii) 각 오버행 면의 레이가 맞는 수신면이 \emph{유일}하고(최근접 후보가 한 면으로
명확히 결정), (iv) 모든 하드 판정이 \emph{임계 여유}(threshold margin)를 갖는다 --- 즉
$\lvert\mvec_i\!\cdot\!\nvec\rvert$, $h_{it}-\varepsilon$, $\mvec_t\!\cdot\!\nvec-\tau_r$ 가 0 에서
떨어져 있다. 나아가 소프트 라우팅의 극한을 논할 때는 (v) 각 오버행 면에서 후보집합 위
\emph{어피니티}\footnote{affinity. 아래 \eqref{eq:pi} 에서 소프트 어텐션이 각 후보 수신면에
매기는 점수. 무게중심 사이의 가로거리와 높이차로 정해진다.} 최대점이 레이캐스트 수신면
$t_i$(유효 수신면이 없으면 바닥)와 \emph{일치}한다고 가정한다.
\end{assumption}

\noindent (i)--(iv) 를 어기는 점(수신면 동률, 가시성 불연속, 퇴화 면, 임계각 경계)은
$(V,\nvec)$ 공간에서 \emph{측도 0}의 집합을 이루며, 그 위에서 $J$ 는 점프(불연속)를 가질 수
있다. 그 여집합(일반 위치)에서는 $J$ 가 \emph{국소적으로} 매끄럽고, 미분을 막는 연산은 위의 하드
라우팅뿐이다. 아래 완화는 이 하드 라우팅을 매끄럽게 대체하여 그러한 경계까지 \emph{연속}으로
잇는다. 조건 (v) 는 성격이 다르므로 구분해 둔다. 이는 (iii) 과 별개의 조건이다 --- (iii) 은
\emph{레이가 맞는} 면이 하나임을 말할 뿐이고, (v) 는 \emph{어피니티가 고르는} 면이 바로 그
면이어야 함을 요구한다. 어피니티는 레이--삼각형 교차가 아니라 무게중심 사이의 거리로 정해지므로
두 순서는 어긋날 수 있고, 그렇게 어긋나는 배치는 (i)--(iv) 와 달리 측도 0 이 아니라
\emph{열린 집합}을 이룬다(작은 섭동으로 없앨 수 없다). 절~\ref{sec:centroid-limit} 에서 최소
반례와 그 실질적 영향 범위를 밝힌다.

\subsubsection{이번 연구: 파동론적 접근법}
본 연구는 같은 태양빛을 이번에는 \textbf{파동}으로 본다(그림~\ref{fig:wavelength}(b)).
파동은 장애물 모서리에서 기하학적 그림자 안쪽으로 휘어 드는
\textbf{회절}\footnote{diffraction. 파동이 장애물·구멍의 가장자리에서 진행 방향을 바꾸어
기하학적 그림자 영역 안으로 퍼지는 현상.}을 일으켜, 그림자 경계가 칼날이 아니라 밝기가
점차 변하는 \textbf{반그림자}\footnote{penumbra. 완전한 빛과 완전한 그림자 사이에서 밝기가
연속적으로 변하는 전이 띠.}로 번진다. 회절의 세기는 빛의 \textbf{파장} $\lambda$ 가 정하며,
모서리에서의 퍼짐각은 대략 $\theta\sim\lambda/d$ 이다($d$: 장애물 크기). 즉 \emph{파장이
길수록(=주파수가 낮을수록) 더 크게 회절}하여 경계가 더 부드러워지고, 반대로 \emph{파장이
짧을수록(=주파수가 높을수록) 덜 회절}하여 경계가 날카로워진다. 파장을 0으로 보내는
\textbf{단파장 극한}\footnote{short-wavelength (eikonal) limit. 파동광학이 기하광학으로
환원되는 극한. 파장이 형상 크기에 비해 무시할 만큼 작아지면 회절이 사라지고 빛은 다시
직진하는 입자처럼 행동한다.}에서는 회절이 사라져, 파동광학이 위 입자적 기하광학으로
\emph{점근적으로}(asymptotic/eikonal limit) 환원된다 --- 비유상으로 ``기하광학 극한''으로
되돌아가는 셈이다. 이 관점에서는 3.1.1에서 ReLU의 꺾임에 해당하던
$\max(0,\cdot)$ 꼴의 오버행 항이 이번 연구에서는 매끄러운 softplus 함수로 대응되어 바뀐다.

\paragraph{수식에서는 온도들이 유효 파장 역할을 한다.}
이제 이 비유를 실제 수식의 손잡이로 옮긴다. 그 손잡이는 여러 \emph{온도(temperature)}
파라미터다. 그중 $\beta$ 는
소프트 오버행 $\tilde O_i=\softplus_\beta(-\mvec_i\cdot\nvec)$ 의 \emph{모서리 날카로움}에 직접
대응한다. 다만 수신면 배정 $\pi_{ij}$ 의 \emph{퍼짐}(blur width)은 $\beta$ 혼자가 아니라
횡 정렬·아래 게이트·수신면 상향·최근접 선호·바닥 슬롯을 정하는 온도들
$(\sigma_\ell,\tau_b,\epsilon_r,\beta_n^{-1},a_0)$ 이 \emph{함께} 정한다(아래 식~\eqref{eq:pi}).
따라서 엄밀히는 \emph{이 온도들의 묶음}이 하나의 \emph{유효 파장/blur width}
$\lambda_{\mathrm{eff}}$ 처럼 작동한다고 보는 것이 정확하며, $\beta$ 는 그 손잡이의 대표격이다
($\lambda_{\mathrm{eff}}$ 가 작을수록 $\beta\!\to\!\infty$, $\sigma_\ell,\tau_b,\epsilon_r\!\to\!0$,
$\beta_n\!\to\!\infty$, $a_0\!\to\!0^+$ 에 대응):
\begin{itemize}
\item \textbf{짧은 유효 파장(높은 주파수):} 회절이 약해 그림자가 날카롭고,
$\softplus_\beta(\cdot)\to\max(0,\cdot)$ 와 한 면으로 집중되는 $\pi_{ij}$ 로 이전 연구의 SFTF
(입자/기하광학)를 회복한다.
\item \textbf{긴 유효 파장(낮은 주파수):} 회절이 강해 그림자가 번지고, 손실이
매끄러워져 자동미분과 경사하강이 가능해진다(그림~\ref{fig:wavelength}(c)).
\end{itemize}

\subsection{개선된 손실 함수}\label{sec:improved-loss}
위 비유를 실제 계산식으로 옮기려면 두 가지를 바꾸면 된다. 첫째, ReLU처럼 꺾이는 오버행
항은 softplus로 둥글린다. 둘째, 레이캐스팅이 수신면 하나를 고르는 하드 선택은 여러 후보에
확률을 나누는 소프트 선택으로 바꾼다. 이때 온도들을 함께 조이면 소프트 비용이 SFTF의 하드
비용으로 돌아가며, 파동 비유로 말하면 이것이 바로 \emph{단파장 극한}이다. 받침면 선택의
소프트화도 같은 그림으로 읽힌다: \emph{그림으로 읽으면} 입자는 빛이 수신면 하나만 때리지만
파동은 모서리 회절로 \emph{여러} 수신면에 퍼져 닿는 모습이고, \emph{수학적으로는} 이 퍼짐을
확률적 soft visibility $\pi_{ij}$ 로 모델링한 소프트 라우팅이다(파동방정식의 해가 아니라
soft attention kernel). 또한 온도들을 점차 조이는 담금질(annealing)은 곧 \emph{유효 파장을
점차 줄이는} 과정이다 --- 처음에는 긴 파장으로(회절이 큰) 넓고 부드러운 비용 지형에서 좋은
골짜기를 찾고, 점차 파장을 줄여 이전 연구의 SFTF의 날카로운 비용에 정렬시킨다.

\paragraph{(a) 기하량: 정점 $V$ 의 매끄러운 함수.}
첫 단계의 목적은 메쉬에서 이후 손실항이 참조할 기본 물리량을 모두 미분가능한 형태로
정의하는 것이다. 면 $i=(a,b,c)$ 에 대해
$\cvec_i=\tfrac{\bm v_a+\bm v_b+\bm v_c}{3}$,
$\bm N_i=\tfrac12(\bm v_b-\bm v_a)\times(\bm v_c-\bm v_a)$,
$A_i=\lVert\bm N_i\rVert$, $\mvec_i=\bm N_i/\lVert\bm N_i\rVert$ 는 (퇴화면을 제외하면)
$V$ 에 대해 매끄럽다. 빌드방향은 $\nvec(\theta,\phi)=(\sin\theta\cos\phi,\sin\theta\sin\phi,\cos\theta)$
로 두면 $S^2$ 제약이 자동 충족된다.

\paragraph{(b) 소프트 오버행.}
두 번째 단계의 목적은 SFTF의 ReLU형 오버행 판정을 매끄러운 함수로 바꾸어 오버행 경계에서도
기울기가 흐르게 하는 것이다.
$\tilde O_i=\softplus_\beta(-\mvec_i\cdot\nvec)\xrightarrow[\beta\to\infty]{}\max(0,-\mvec_i\cdot\nvec)$.
임계각 $\theta_c$ 를 쓸 경우 게이트 $g_i=\sigma(\kappa(-\mvec_i\cdot\nvec-\cos\theta_c))$ 를 곱한다
($\sigma$: 로지스틱). 즉 식~\eqref{eq:base}의 SFTF의 오버행 강도 $O_i$는 딱 꺾이는 ReLU형
함수이고, 여기서는 같은 극한을 갖는 $\tilde O_i$로 대체해 기울기가 끊기지 않게 한다.

\paragraph{(c) 소프트 수신면 배정: 핵심.}
세 번째 단계의 목적은 SFTF처럼 수신면 하나를 갑자기 고르지 않고, 가능한 수신면과 바닥에
연속적인 책임도를 나누어 주는 것이다. 소스 면 $i$ 의 후보 수신 집합 $\mathcal C(i)$ (전체 면,
또는 아래쪽 $k$-최근접). 각 후보 $j$ 에 대해 $\bm\delta=\cvec_j-\cvec_i$ 로 두고
$h_{ij}=-(\bm\delta\cdot\nvec)$, $d_{ij}^2=\lVert\bm\delta\rVert^2-(\bm\delta\cdot\nvec)^2$.
SFTF의 하드 조건을 곱셈형 소프트 게이트로 완화한다:
\begin{equation}
a_{ij}=
\underbrace{\sigma\!\Big(\tfrac{h_{ij}}{\tau_b D}\Big)}_{\text{아래 게이트}}\;
\underbrace{\exp\!\Big(-\tfrac{d_{ij}^2}{2(\sigma_\ell D)^2}\Big)}_{\text{횡 정렬(레이)}}\;
\underbrace{\sigma\!\Big(\tfrac{\mvec_j\cdot\nvec-\tau_r}{\epsilon_r}\Big)}_{\text{수신면 상향}}\;
\underbrace{\exp\!\big(-\tfrac{\beta_n}{D}\,\relu(h_{ij})\big)}_{\text{최근접 선호}},
\quad a_{ii}=0.
\label{eq:aij}
\end{equation}
식~\eqref{eq:aij}은 이전 연구의 SFTF의 수신면 조건~\citep{sftf_engine}을 네 개의 부드러운 점수로
바꾼 것이다. 첫 항은 후보가 소스보다 아래에 있는지, 둘째 항은 레이 방향에서 옆으로 얼마나
벗어났는지, 셋째 항은 수신면이 위쪽을 향하는지, 넷째 항은 더 가까운 후보를 선호하는지를
나타낸다. 따라서 식~\eqref{eq:base}--\eqref{eq:aij}은 이전 연구의 SFTF~\citep{sftf_engine}의 하드
레이캐스팅을 본 연구의 소프트 게이트로 연결하는 구간이다.
상수 \emph{바닥 슬롯}\footnote{레이가 어떤 면에도 닿지 않고 바닥(빌드 플레이트)으로 빠지는
경우를 한 칸의 가상 후보로 둔 것.} $a_0$ 를 더해 정규화하면 소스별 범주분포가 된다:
\begin{equation}
\pi_{ij}=\frac{a_{ij}}{\sum_{k\in\mathcal C(i)}a_{ik}+a_0},\qquad
\pi_i^{\mathrm{bed}}=\frac{a_0}{\sum_{k\in\mathcal C(i)}a_{ik}+a_0},\qquad
\sum_j\pi_{ij}+\pi_i^{\mathrm{bed}}=1.
\label{eq:pi}
\end{equation}
식~\eqref{eq:pi}는 식~\eqref{eq:aij}의 점수를 합이 1인 비율로 바꾸는 단계다. SFTF에서는
오버행 면 $i$가 수신면 $t_i$ 하나로만 보내졌지만, 여기서는 후보 $j$들과 바닥 슬롯이 각각
$\pi_{ij}$, $\pi_i^{\mathrm{bed}}$만큼 지지 책임을 나누어 가진다.
게이트가 날카로워지고 $\beta_n\to\infty$ 면 $\pi_{i\cdot}$ 는 유효 최근접 수신면 하나로
집중되고, 유효 수신이 없으면 $\pi_i^{\mathrm{bed}}\to1$ 이 되어 SFTF의 하드 레이캐스팅을
회복한다(그림~\ref{fig:soft}).

\begin{figure}[H]
\centering
\input{pics/ftree4x_unified_tikz.tex}
\resizebox{\linewidth}{!}{%
\begin{tikzpicture}[line join=round,line cap=round]
  % ============================ (a) 입자: 하드 레이캐스팅 ============================
  \begin{scope}
    \node[panelLabel] at (-2.35,6.95) {(a) particle\,$\cdot$\,hard raycasting};
    \ftreeSun{-2.5}{6.35}
    \draw[sunray] (-2.32,6.20) -- (-0.95,4.32);
    \draw[sunray] (-2.18,6.48) -- (0.20,6.35);
    \draw[sunray] (-2.42,6.04) -- (-1.25,5.32);
    \ftreeUPlate
    \ftreeUMesh
    \filldraw[recface] \ftreeURec;
    \filldraw[srcface] \ftreeUSrcFace;
    \draw[hardray] (-0.872,3.936) -- (-0.872,3.066) node[midway,right=14pt,yshift=-7pt,font=\scriptsize]{$-\nvec$};
    \draw[normSrc] (-0.872,4.026) -- (-0.872,3.366) node[right=1pt,font=\scriptsize]{$\mvec_i$};
    \draw[normRec] (-0.872,2.826) -- (-0.872,3.486) node[left=1pt,font=\scriptsize]{$\mvec_j$};
    \fill[srcDot] (-0.872,4.026) circle (1.25pt);
    \fill[recDot] (-0.872,2.826) circle (1.25pt);
    \node[ohred!80!black,font=\scriptsize] at (-1.32,3.97) {$i$};
    \node[rcblue!82!black,font=\scriptsize] at (-1.95,2.74) {$j$};
    \draw[measure] (0.5,4.026) -- (0.5,2.826) node[midway,right=2pt,font=\scriptsize]{$h_{ij}$};
    \node[termLabel] at (1.45,5.95) {$\mvec_i\!\otimes\!\mvec_j$};
    \draw[axisn] (-3.42,3.687) -- (-3.42,5.487) node[above,inner sep=1pt,font=\scriptsize]{$\nvec$};
  \end{scope}
  % ============================ (b) 파동: 소프트 라우팅 ============================
  \begin{scope}[xshift=8.4cm]
    \node[panelLabel] at (-2.35,6.95) {(b) wave\,$\cdot$\,soft routing};
    \ftreeSun{-2.5}{6.35}
    \draw[sunwave] (-2.32,6.20) -- (-0.95,4.32);
    \draw[sunwave] (-2.18,6.48) -- (0.20,6.35);
    \draw[sunwave] (-2.42,6.04) -- (-1.25,5.32);
    \ftreeUPlate
    \ftreeUMesh
    \fill[rcblue!30,opacity=0.28] (-1.20,2.74) ellipse (1.55 and 0.40);
    \filldraw[recfacew] \ftreeURecTwo;
    \filldraw[recface] \ftreeURec;
    \filldraw[srcface] \ftreeUSrcFace;
    \draw[normSrc] (-0.872,4.026) -- (-0.872,3.366) node[right=1pt,font=\scriptsize]{$\mvec_i$};
    \fill[srcDot] (-0.872,4.026) circle (1.25pt);
    \node[ohred!80!black,font=\scriptsize] at (-1.32,3.97) {$i$};
    \draw[softray,line width=1.5pt] (-0.872,3.90) .. controls (-0.80,3.40) and (-0.76,3.10) .. (-0.78,2.92)
         node[pos=0.48,right=0.5pt,font=\scriptsize]{$\pi_{ij_1}$};
    \draw[softray,line width=1.0pt] (-0.95,3.92) .. controls (-1.45,3.55) and (-1.75,3.08) .. (-1.70,2.84)
         node[pos=0.5,left=0.5pt,font=\scriptsize]{$\pi_{ij_2}$};
    \draw[softray,line width=0.6pt] (-0.80,3.90) .. controls (0.05,2.55) and (-0.40,1.15) .. (-0.78,0.50)
         node[pos=0.86,right=1pt,font=\scriptsize]{$\pi_i^{\mathrm{bed}}$};
    \fill[recDot] (-0.78,2.92) circle (1.1pt);
    \fill[recDot] (-1.70,2.84) circle (1.1pt);
    \fill[rcblue!82!black] (-0.78,0.47) circle (1.3pt);
    \node[rcblue!82!black,font=\scriptsize] at (-0.50,2.70) {$j_1$};
    \node[rcblue!82!black,font=\scriptsize] at (-2.10,2.66) {$j_2$};
    \node[termLabel] at (1.65,5.95) {$\displaystyle\sum_j \pi_{ij}\,\mvec_i\!\otimes\!\mvec_j$};
    \draw[axisn] (-3.42,3.687) -- (-3.42,5.487) node[above,inner sep=1pt,font=\scriptsize]{$\nvec$};
  \end{scope}
\end{tikzpicture}}
\caption{FTree4x 형상에서 본 지지 흐름의 \emph{입자/파동} 비교(그림~\ref{fig:wavelength}의 빛
비유를 실제 메쉬 위에 옮긴 것). 위쪽 \emph{가상의 태양}이 보내는 빛이 곧 지지 흐름이다.
\textbf{(a) 입자(기하광학)$\,\cdot\,$하드 레이캐스팅:} 오버행 소스면 $i$(빨강, 법선 $\mvec_i$)에서
$-\nvec$ 방향으로 \emph{단 하나의 직선 레이}를 쏘아 최근접 수신면 $j$(파랑, 법선 $\mvec_j$)
하나로만 보낸다. 흐름텐서는 한 항 $\mvec_i\!\otimes\!\mvec_j$, 지지높이는 $h_{ij}$.
\textbf{(b) 파동$\,\cdot\,$소프트 라우팅:} 같은 소스면의 흐름이 모서리 회절처럼 여러 후보
$j_1,j_2$와 바닥 슬롯으로 \emph{번져}, 각 경로가 책임도 $\pi_{ij}$, $\pi_i^{\mathrm{bed}}$ 를
나눠 갖는다(물결 화살표 굵기 $\propto\pi$). 흐름텐서는 기대값
$\sum_j\pi_{ij}\,\mvec_i\!\otimes\!\mvec_j$ 로 바뀐다.}
\label{fig:soft}
\end{figure}

\paragraph{(d) 소프트 지지비용.}
마지막 단계의 목적은 위에서 얻은 소프트 오버행과 소프트 수신 확률을 이전 연구의 SFTF의 세 지지비용
항에 대입해, 최종적으로 자동미분 가능한 손실함수를 만드는 것이다. 바닥 높이는 soft-min 으로 두고
($z_{\mathrm{plate}}(\nvec)=-\tfrac{D}{\gamma}\log\sum_{\bm v}\exp(-\tfrac{\gamma}{D}\,\bm v\cdot\nvec)$),
식~\eqref{eq:P}--\eqref{eq:F} 의 단일 수신면 $t_i$ 를 기대값 $\sum_j\pi_{ij}(\cdot)$ 로 대체하면
\begin{align}
\tilde P &= \sum_i \tilde O_i\,A_i\sum_{j}\pi_{ij}A_j, \label{eq:Pt}\\
\tilde B &= \sum_i \tilde O_i\,A_i\;\pi_i^{\mathrm{bed}}\,\big(1+\alpha\,\relu(\eta_i)\big),\label{eq:Bt}\\
\tilde{\bm F}_{\mathrm{face}} &= \sum_i\sum_{j}\pi_{ij}\,
\frac{\tilde O_i A_i A_j}{1+\alpha\,\relu(h_{ij})}\;\mvec_i\otimes\mvec_j,
\qquad
\tilde R_{\mathrm{face}}=\softplus_\beta\!\big(-\nvec^{\!\top}\!\operatorname{sym}(\tilde{\bm F}_{\mathrm{face}})\,\nvec\big).\label{eq:Ft}
\end{align}
식~\eqref{eq:Pt}은 SFTF의 면--면 쌍 지지항 $P$를 소프트화한 것이다. 원래는 선택된 수신면
$t_i$의 면적 $A_{t_i}$만 곱했지만, 이제는 모든 후보 면적 $A_j$를 확률 $\pi_{ij}$로 평균한다.
식~\eqref{eq:Bt}은 바닥 지지항 $B$의 소프트 버전으로, 수신면이 없을 확률
$\pi_i^{\mathrm{bed}}$가 클수록 바닥 지지 비용이 커진다. 식~\eqref{eq:Ft}은 흐름텐서 항이다.
SFTF의 $\mvec_i\otimes\mvec_{t_i}$ 대신 후보 법선들의 기대값
$\sum_j\pi_{ij}\mvec_i\otimes\mvec_j$를 쓰고, 마지막 벌점도 $\max(0,\cdot)$ 대신 softplus로
바꾸어 기울기가 흐르게 한다. 즉 식~\eqref{eq:Pt}--\eqref{eq:Ft}은 SFTF의 세 비용항
$P,B,R$을 각각 미분가능한 $\tilde P,\tilde B,\tilde R_{\mathrm{face}}$로 바꾼 것이다.
이로 인해 이번 연구에서 개선한 손실함수는 다음 식~\eqref{eq:loss}와 같다. 이 손실값은
작을수록 필요한 지지가 적다는 뜻이며, 따라서 최적화에서는 이를 최소화 대상으로 둔다.
\begin{equation}
\boxed{\;L_{\mathrm{SFTF}}(V,\nvec)=w_R\,\tilde R_{\mathrm{face}}+w_P\,\tilde P+w_B\,\tilde B\;}
\label{eq:loss}
\end{equation}

\subsection{일관성 (soft$\to$hard)}\label{sec:consistency}
\begin{proposition}[소프트$\to$하드 수렴]\label{prop:soft2hard}
가정~\ref{asm:gp} 을 만족하는 점 $(V,\nvec)$ 에서, 온도를
$\sigma_\ell\to0,\ \tau_b\to0,\ \epsilon_r\to0,\ \beta_n\to\infty,\ a_0\to0^+,\ \beta\to\infty,\ \gamma\to\infty$
로 보내면
$\pi_{ij}\to\mathbb 1[j=t_i]$, $\pi_i^{\mathrm{bed}}\to\mathbb 1[\text{무수신}]$,
$\tilde O_i\to O_i$, $\tilde R_{\mathrm{face}}\to R$, $z_{\mathrm{plate}}^{\mathrm{soft}}\to z_{\mathrm{plate}}$ 이며,
따라서 $L_{\mathrm{SFTF}}(V,\nvec)\to J_w(\nvec)$ \eqref{eq:Jw} 이다.
\end{proposition}
\begin{proof}[증명 (개략)]
임계 여유(가정~\ref{asm:gp}(iv))에 의해 각 하드 게이트 인자는 그 인수가 0 에서 떨어져 있다.
로지스틱 $\sigma(\cdot/\epsilon)$ 는 $\epsilon\to0$ 에서 부호에 따라 $\{0,1\}$ 로, 최근접 선호
$e^{-(\beta_n/D)\relu(h)}$ 는 $\beta_n\to\infty$ 에서 유일 최소 $h$(가정~\ref{asm:gp}(iii))만 살아남아
지표함수로 수렴한다. softplus$_\beta\to\max(0,\cdot)$, soft-min$_\gamma\to\min$ 도 표준 결과다.
정규화 \eqref{eq:pi} 에서 $a_0\to0^+$ 이면 유효 수신이 있을 때 $\pi_i^{\mathrm{bed}}\to0$, 없을 때
$\to1$ 이다. 항별로 대입하면 \eqref{eq:Pt}--\eqref{eq:Ft} 가 \eqref{eq:P}--\eqref{eq:F} 로,
$L_{\mathrm{SFTF}}\to J_w$ 로 간다. 기본 가중치에서는 $J_w=J_{\mathrm{SFTF}}$이다. \end{proof}
\noindent 즉 \eqref{eq:loss} 는 하드 SFTF 비용의 \emph{매끄러운 완화}이며(측도-0 경계까지 연속으로 확장),
이를 \S\ref{sec:results} 에서 수치로 확인한다(유한차분 기울기 상대오차 $3\times10^{-10}$).
다만 수렴 주장의 범위를 분명히 해 둔다. softplus 오버행·시그모이드 게이트·soft-min 바닥높이는
\emph{무조건} 수렴하지만, 수신면 배정 $\pi_{ij}\to\mathbb 1[j=t_i]$ 는 가정~\ref{asm:gp}(v),
즉 어피니티 최대점이 레이캐스트 수신면과 일치할 때에만 성립한다. 따라서
$L_{\mathrm{SFTF}}\to J_w$ 는 \emph{조건부} 진술이며, 본 논문이 쓰는 메쉬에서는 이 조건이
성립하지만 일반 위치에서 자동으로 보장되지는 않는다(절~\ref{sec:centroid-limit}).

\paragraph{게이트 함수형과 straight-through(STE) 변형.}
본문의 임계각 게이트는 시그모이드 $\sigma((x-t)k)$ 를 기본으로 하지만($x=-\mvec\cdot\nvec$,
$t=\sin\theta_c$, $k$: sharpness), 구현은 게이트 함수형을 교체 가능하게
둔다(\texttt{SFTFConfig.gate\_mode}): 시그모이드, 구간 $[t\pm d]$ 밖에서 정확히 $0/1$ 인
$C^1$ smoothstep, 그리고 \textbf{straight-through 추정기}(STE)~\citep{bengio2013ste} 다.
STE 는 한 줄
$g_{\mathrm{ste}}=g_{\mathrm{soft}}+\mathrm{stopgrad}(g_{\mathrm{hard}}-g_{\mathrm{soft}})$
로 구현되며, 순전파(값)는 하드 지시함수 $g_{\mathrm{hard}}=\mathbf 1[x>t]$, 역전파(기울기)는
시그모이드 $g_{\mathrm{soft}}$ 의 것을 쓴다 --- 가중치를 $\pm1$ 로 이진화하는 양자화
신경망(binary neural network) 학습에서 표준으로 쓰이는 기법이다. 성격을 분명히 해 둔다:
STE 의 역전파는 순전파 함수의 진짜 도함수가 아니라 \emph{대리 기울기}(surrogate
gradient)다. 지시함수의 도함수는 거의 어디서나 $0$ 이므로, STE 는 의도적으로 편향된
기울기를 공급해 최적화를 굴린다. 따라서 명제~\ref{prop:soft2hard} 와
\S\ref{sec:results} 의 유한차분 대 해석적 기울기 일치 검증은 매끄러운
(시그모이드·smoothstep) 게이트 구성에만 적용되고, STE 구성에는 성립하지 않으며 성립을
의도하지도 않는다 --- STE 의 타당성은 기울기 일치가 아니라 최적화 \emph{결과}로
검증한다(\S\ref{sec:results} 의 게이트 처방 문단). 추가로 두 컴팩트 지지(compact-support)
변형을 둔다. $C^2$ \emph{smootherstep}(5차식 $6u^5-15u^4+10u^3$, $u\!=\!\mathrm{clamp}((x-(t-d))/2d,0,1)$;
밴드 양끝에서 1차\emph{와} 2차 도함수가 모두 $0$)은 $C^1$ smoothstep 의 매끄러운-순전파
대응물이다. 그리고 \emph{컴팩트-역전파} STE(\texttt{ste\_smooth})는 순전파는 하드로 두되
역전파 대리 기울기를 시그모이드 대신 smootherstep 도함수로 바꿔 밴드 $[t\pm d]$ 안에서만
$0$ 이 아니게 한다. 결과절의 게이트 처방 문단에서 보이듯, 이 컴팩트 대리 기울기는 방향이
이미 밴드 안일 때 하드 하강방향과 더 잘 정렬되지만 밴드 밖에서는 정확히 $0$ 이라
cold-start 에서 정체할 수 있다 --- 넓은 시그모이드-역전파 STE 가 견고한 기본이다.

\subsection{기울기와 최적화}
$\nvec(\theta,\phi)$ 파라미터화에서는 자동미분이 $\partial L/\partial(\theta,\phi)$ 를 직접
준다. $\nvec=\bm u/\lVert\bm u\rVert$ 로 직접 두는 경우 단위구 접선공간으로 사영한다:
$\bm g_\perp=(\bm I-\nvec\nvec^{\!\top})\nabla_{\nvec}L$, $\nvec\leftarrow(\nvec-\rho\bm g_\perp)/\lVert\cdot\rVert$.
$A_i,\mvec_i,\cvec_i,h_{ij},\eta_i$ 가 모두 $V$ 의 매끄러운 함수이므로 $\partial L/\partial V$ 도
연쇄법칙으로 흐른다. 온도는 $D$ 상대 단위로 담금질한다(권장 일정:
$\sigma_\ell:0.05\!\to\!0.01$, $a_0:0.05\!\to\!0.01$, $\beta_n:6\!\to\!24$, $\beta:16\!\to\!64$,
$\tau_b{=}10^{-3}$, $\tau_r{=}0.05$, $\epsilon_r{=}0.05$, $\gamma{=}64$). 초반에는 부드럽게
시작해 점차 날카롭게 만들어 하드 목적 \eqref{eq:J} 에 정렬시킨다.

\begin{algorithm}[t]
\caption{미분가능 SFTF 손실 $L_{\mathrm{SFTF}}(V,\nvec)$}
\label{alg:loss}
\begin{algorithmic}[1]
\Require 정점 $V$, 면 $F$, 빌드방향 $\nvec$, 설정 $\Theta$(가중치·온도), (선택) $k$
\State $\cvec,\mvec,A,D \gets \textsc{FaceGeometry}(V,F)$;\quad $\alpha\gets 1/D$;\quad $\nvec\gets\nvec/\lVert\nvec\rVert$
\State $\tilde O_i \gets \softplus_\beta(-\mvec_i\!\cdot\!\nvec)$ \Comment{(선택) 임계각 게이트 곱}
\State $\mathcal C(i)\gets$ 전체 면 또는 아래쪽 $k$-최근접
\For{각 소스 $i$, 후보 $j\in\mathcal C(i)$}
  \State $h_{ij}\gets(\cvec_i-\cvec_j)\!\cdot\!\nvec$;\quad
         $d_{ij}^2\gets\lVert\cvec_j-\cvec_i\rVert^2-((\cvec_j-\cvec_i)\!\cdot\!\nvec)^2$
  \State $a_{ij}\gets \sigma(\tfrac{h_{ij}}{\tau_bD})\,
          e^{-d_{ij}^2/2(\sigma_\ell D)^2}\,
          \sigma(\tfrac{\mvec_j\cdot\nvec-\tau_r}{\epsilon_r})\,
          e^{-(\beta_n/D)\relu(h_{ij})}$,\quad $a_{ii}{=}0$
\EndFor
\State $\pi_{ij}\gets a_{ij}/(\textstyle\sum_k a_{ik}+a_0)$;\quad
       $\pi_i^{\mathrm{bed}}\gets a_0/(\textstyle\sum_k a_{ik}+a_0)$ \Comment{식 \eqref{eq:pi}}
\State $z_{\mathrm{plate}}\gets \text{soft-min}_{\bm v}(\bm v\!\cdot\!\nvec)$;\quad
       $\eta_i\gets \relu(\cvec_i\!\cdot\!\nvec-z_{\mathrm{plate}})$
\State $\tilde P\gets\sum_i\tilde O_iA_i\sum_j\pi_{ij}A_j$;\quad
       $\tilde B\gets\sum_i\tilde O_iA_i\,\pi_i^{\mathrm{bed}}(1+\alpha\eta_i)$
\State $\tilde{\bm F}_{\mathrm{face}}\gets\sum_{i,j}\pi_{ij}\tfrac{\tilde O_iA_iA_j}{1+\alpha\relu(h_{ij})}\mvec_i\mvec_j^{\!\top}$;\quad
       $\tilde R_{\mathrm{face}}\gets\softplus_\beta(-\nvec^{\!\top}\!\operatorname{sym}(\tilde{\bm F}_{\mathrm{face}})\nvec)$
\State \Return $w_R\tilde R_{\mathrm{face}}+w_P\tilde P+w_B\tilde B$ \Comment{자동미분으로 $\partial L/\partial\nvec,\ \partial L/\partial V$}
\end{algorithmic}
\end{algorithm}

\subsection{물리 지지부피 확장 $S$}\label{sec:supvol}
$L_{\mathrm{SFTF}}$ 는 이전 연구의 SFTF 목적을 충실히 완화하지만, \emph{SFTF 비용 자체}가 물리 지지\emph{부피}의
느슨한 프록시다(\S\ref{sec:results} 에서 정량화). 특히 면-면 흐름텐서 $\tilde{\bm F}_{\mathrm{face}}$ \eqref{eq:Ft} 는 지지높이를
$1/(1+\alpha h)$ 로 \emph{감쇠}시키는데, 이는 지지재가 \emph{많을수록}(기둥이 높을수록) 비용이 커야 하는
물리와 거꾸로다. 그래서 같은 소프트 라우팅($\pi_{ij},\pi_i^{\mathrm{bed}}$) 위에 물리적으로 동기화된
미분가능 \emph{지지부피} 항을 정의한다:
\begin{equation}
S(V,\nvec)=\sum_i \tilde O_i\,A_i\Big(\pi_i^{\mathrm{bed}}\,\relu(\eta_i)+\sum_j \pi_{ij}\,\relu(h_{ij})\Big),
\label{eq:supvol}
\end{equation}
즉 \emph{오버행 면적 $\times$ 기대 낙하높이}로 지지 기둥 부피에 비례하며, $\tilde O_i,A_i,\pi,\eta,h$ 가
모두 미분가능하므로 $S$ 도 $V,\nvec$ 에 미분가능하다. 기본 물리항은 $L_{\mathrm{SFTF}}+\lambda_S\,S$ 이며,
실제 생산 슬라이서와 맞출 때는 같은 항을 슬라이서 임계각에서 게이트한다. 실제 \emph{슬라이서}는
(수직 기준) 임계각($60^\circ$)보다 더 누운 면만 지지하므로, 평가용으로는 오버행을 그 임계각에서
게이트하고 낙하높이를 \emph{바닥판까지}로 둔 변형
$S_g=\sum_i \mathrm{gate}_{60}(\tilde O_i)\,A_i\,\eta_i$ 도 함께 쓴다. $S,S_g$ 의 물리 충실도(TomoNV 추정기
및 \emph{실제 Cura} 지지질량과의 일치)는 \S\ref{sec:results} 에서 정량화한다.

\section{결과}\label{sec:results}
참조구현과 데모 스크립트로 다음을 검증한다. 결과 절은 세 단계로 읽으면 된다.
첫째, 완화가 수학적으로 제대로 작동하는지 확인한다: 기울기가 맞고, 온도를 조이면 이전 연구의 SFTF 로
돌아가며, 경사하강이 격자 전수탐색과 같은 분지에 도달해야 한다. 둘째, 그 손실이 물리 지지량과
얼마나 맞는지 따진다: 이전 연구의 SFTF 자체의 한계를 확인한 뒤, 물리 지지부피 항 $S$ 로 보완한다.
셋째, 이 손실을 실제 활용 시나리오에 넣어 본다: 형상 최적화, 신경망 예측, 그리고 실제 생산
슬라이서 검증이다.

\begin{table}[t]
  \centering
  \caption{결과 절의 실험 조건 요약. 각 실험은 서로 다른 질문을 검증하므로 메쉬 수와 방향 수가 다르다.}
  \label{tab:exp-summary}
  \scriptsize
  \begin{tabular}{>{\raggedright\arraybackslash}p{0.18\linewidth}
                  >{\raggedright\arraybackslash}p{0.18\linewidth}
                  >{\raggedright\arraybackslash}p{0.23\linewidth}
                  >{\raggedright\arraybackslash}p{0.23\linewidth}}
    \toprule
    목적 & 기준 & 데이터/방향 & 보고 지표 \\
    \midrule
    하드 SFTF 재현 & 하드 $J_{\mathrm{SFTF}}$ & 합성 형상 및 Bunny & 수렴오차, 기울기 상대오차 \\
    단일 메쉬 물리 비교 & TomoNV 복셀 추정기 & Bunny, 49--64 방향 & Spearman/Pearson, 최소방향 차이 \\
    가중치 재조정 & TomoNV 복셀 추정기 & 160 방향, 5-겹 CV & held-out 순위상관 \\
    물리항 $S$ 일반화 & TomoNV 복셀 추정기 & 11 메쉬, 48 방향 & 메쉬 단위 leave-one-out Spearman \\
    라벨 없는 GNN & TomoNV 복셀 추정기 & 9 메쉬 leave-one-out & 지지질량 백분위 \\
    생산 슬라이서 검증 & CuraEngine 지지질량 & g5test 헤드라인 18(전체 21) 메쉬, 48 방향 & Spearman, 최적화 백분위 \\
    \bottomrule
  \end{tabular}
\end{table}

\paragraph{기울기 정확성.} 먼저 완화가 계산 가능한 손실인지 확인한다. 합성 형상에서
순전파/역전파가 유한하고, $\partial L/\partial\nvec$ 의 해석적 기울기가 중심차분 유한차분과
접선 성분 상대오차 $3.1\times10^{-10}$ 로 일치한다. $\partial L/\partial V$ 역시 정상적으로
흐른다(스모크 테스트 통과). 이 유한차분 일치 검증은 매끄러운(시그모이드·smoothstep)
게이트 구성에 대한 것이다 --- STE 게이트는 정의상 순전파의 진짜 도함수가 아닌 대리
기울기를 쓰므로 이 검증의 대상이 아니며, 그 타당성은 최적화 결과로 따로
검증한다(\S\ref{sec:consistency}). torch 미설치 환경에서는 동일 수식의 numpy 미러로 soft$\to$hard
집중(어텐션 엔트로피 $0.895\!\to\!0.029$)과 sharp 극한에서 $\arg\max_j\pi_{ij}$ 가 하드
최근접 수신면과 일치함을 확인했다.

그림~\ref{fig:relaxation} 은 이 검증을 두 축으로 요약한다. 하나는 해석적 기울기와 중심차분의
일치이고, 다른 하나는 온도를 sharpen 할 때 $L_{\mathrm{SFTF}}\to J_{\mathrm{SFTF}}$ 로 점별
수렴한다는 사실이다. 여기서 비교 기준은 TOMO가 아니라 \emph{미분 불가능한 이전 연구의 SFTF} 자체다.
\textbf{파동론으로 보면}(\S\ref{sec:wavelength}) 이 수렴은 \emph{단파장 극한} 그 자체다:
회절 폭에 해당하는 수신 온도 $\sigma_\ell$ 을 좁힐수록(=파장을 줄일수록) 그림자 번짐이
사라져, 파동광학적 소프트 비용이 입자광학적 SFTF의 하드 점수 $J_{\mathrm{SFTF}}$ 로 되돌아간다.
방향당 평균 상대오차 $0.88\!\to\!0.10$ 이 그 환원의 정량 증거다.

\begin{figure}[t]
  \centering
  \includegraphics[width=0.95\linewidth]{diff_sftf_relaxation.png}
  \caption{미분가능 완화의 정확성. \textbf{(좌)} 수신 온도 $\sigma_\ell$ 를 sharpen 하면 소프트 손실
  $L_{\mathrm{SFTF}}(\nvec)$ 가 SFTF의 하드 점수 $J_{\mathrm{SFTF}}(\nvec)$ 로 \emph{점별 수렴}한다
  --- 날카로워진 어텐션이 레이캐스트 수신면을 고르는 한 그렇다(절~\ref{sec:centroid-limit})
  (방향당 평균 상대오차 $0.88\!\to\!0.10$, Stanford Bunny). \textbf{(우)} 해석적 기울기
  $\partial L/\partial(\theta,\phi)$ 가 중심차분과 $y{=}x$ 위에서 일치한다(무작위 60방향, 상대오차
  $1.2\times10^{-6}$, float64). 즉 본 완화는 SFTF의 물리적 의미를 보존하면서 미분만 가능하게 한 것이다.}
  \label{fig:relaxation}
\end{figure}

\paragraph{빌드방향 최적화와 자기일관성.} 합성 L-브래킷에서 다중 시드 경사하강
($\arg\min$ 대체)으로 얻은 $\nvec^\ast$ 가 빌드방향 비용 랜드스케이프의 격자 전수탐색
최소와 $2.9^\circ$ 이내로 정합한다(그림~\ref{fig:landscape}, $\Delta L\approx10^{-4}$)\footnote{파동론(\S\ref{sec:wavelength})으로
보면 이 매끄러운 랜드스케이프는 \emph{긴 파장}으로 본 지형이다: 회절이 커 날카로운 능선이
번져 사라지고 넓은 분지만 남으므로 경사하강이 골짜기로 흘러들 수 있다. 담금질($\beta$ 증가)은
이 파장을 점차 줄여 SFTF의 날카로운 지형으로 되돌리는 과정이다.}. 즉
경사 기반 해가 전역 격자 최소의 분지(basin)에 안착한다. 그림~\ref{fig:oriented} 은
$\nvec^\ast\!\to\!+z$ 로 정렬한 메쉬를 면별 오버행 강도로 음영해 보인 것이다.

\begin{figure}[t]
  \centering
  \includegraphics[width=0.78\linewidth]{demo_sftf_landscape.png}
  \caption{빌드방향 지지비용 $L_{\mathrm{SFTF}}(\nvec)$ 의 (yaw,\,pitch) 랜드스케이프.
  경사하강 해 $\nvec^\ast$ 와 격자 전수탐색 최소가 같은 분지에 위치한다.}
  \label{fig:landscape}
\end{figure}

\begin{figure}[t]
  \centering
  \includegraphics[width=0.62\linewidth]{demo_sftf_oriented.png}
  \caption{최적 빌드방향으로 정렬한 메쉬($\nvec^\ast\!\to\!+z$). 색은 면별 오버행 강도다.}
  \label{fig:oriented}
\end{figure}


\paragraph{고차원 설계공간: 경사 대 샘플링.} 미분가능성의 본질적 이득은 \emph{차원}에서 드러난다.
빌드방향 $\nvec\in S^2$ 는 2차원이라 격자/샘플 탐색으로도 충분하지만, 형상 $V$(꼭짓점 수천 자유도)나
신경망 가중치처럼 고차원 설계공간에서는 샘플링이 무력하다. 예시로, 면별 소프트 배정(파트 멤버십,
$\sim$4{,}600 자유도)으로 표현한 설계공간에서 $L_{\mathrm{SFTF}}$ 를 경사하강으로 최소화하면
(그림~\ref{fig:highdim}), 수십 회 평가만에 실제 지지(45$^\circ$ footprint)가 0 근처로 떨어지는 반면,
비미분 점수가 허용하는 유일한 수단인 무작위 샘플링은 수백 표본에도 정체한다.
\textbf{파동론으로 보면}(\S\ref{sec:wavelength}) 이 이득의 근원은 회절이다: 입자라면 빛이
수신면 하나만 때려 한 면씩만 갱신되지만, 파동은 모서리 회절로 \emph{여러 수신면에 동시에}
닿아 모든 면의 소프트 배정에 한꺼번에 기울기를 흘려보낸다. 즉 고차원 갱신은 ``파동이 여러
receiver 를 동시에 비추는'' 효과다.

\begin{figure}[t]
  \centering
  \includegraphics[width=0.72\linewidth]{diff_sftf_highdim.png}
  \caption{미분가능성이 여는 고차원 최적화. $\sim$4{,}600 자유도 설계공간(면별 소프트 배정)에서
  $L_{\mathrm{SFTF}}$ 경사하강(파랑)은 수십 평가만에 실제 지지를 0 근처로 낮춘다. 비미분 점수가
  허용하는 무작위 샘플링(주황)은 수백 표본에도 정체한다. 격자/샘플 탐색은 저차원 빌드방향엔
  충분하나 고차원 설계공간에서는 기울기만이 작동한다.}
  \label{fig:highdim}
\end{figure}

\paragraph{TomoNV 기준 물리 지지질량 비교.} 여기까지는 ``이전 연구의 SFTF 를 잘 완화했는가''의 검증이다.
다음 질문은 더 엄격하다: 이전 연구의 SFTF 자체가 실제 지지질량을 얼마나 잘 나타내는가?
이를 보기 위해 미분가능 프록시 $L_{\mathrm{SFTF}}(\nvec)$ 와 솔리드
기반 복셀 지지량 추정기 TomoNV~\citep{msst,tomonv} 의 지지질량 $\mathrm{mss}(\nvec)$ [g] 을
\textbf{watertight 솔리드}(Stanford Bunny, 69{,}664면; \texttt{merge\_vertices}+\texttt{fill\_holes}
로 복구, 부피 $8.3\times10^4$ mm$^3$)의 49개 빌드방향에서 비교했다. TomoNV 를 적용하기 좋은
닫힌 솔리드임에도 순위상관은 제한적이다(Spearman $+0.17$, Pearson $+0.25$; 그림~\ref{fig:vstomo}).
이는 프록시 면 수와 방향 수를 늘려도 유지되어 \emph{서브샘플 아티팩트가 아니며}, 프록시 최소 방향과
TomoNV 최소 방향도 $50^\circ$ 이상 어긋난다. 종합하면, 본 완화는 이전 연구의 SFTF 목적을 충실히
재현하지만(일관성·기울기·자기일관성), \emph{이전 연구의 SFTF 비용 자체가 복셀 기준 물리 지지부피의
느슨한 프록시}임을 보여준다. 따라서 손실항의 가치는 미분가능한 SFTF-정합 최적화 목표라는 데 있으며,
아래의 물리 지지부피 항 $S$ 와 CuraEngine 검증은 바로 이 간극을 보완하기 위한 단계다.

\begin{figure}[t]
  \centering
  \includegraphics[width=0.62\linewidth]{demo_sftf_vs_tomo.png}
  \caption{미분가능 프록시 $L_{\mathrm{SFTF}}$ 대 TomoNV 물리 지지질량 $\mathrm{mss}$ [g]
  (49개 빌드방향, watertight Stanford Bunny). 닫힌 솔리드에서도 상관은 제한적이다(본문 참조).}
  \label{fig:vstomo}
\end{figure}

\paragraph{빌드방향 비용 랜드스케이프: 하드 vs 미분가능 vs 물리.} 위 산점도 교차검증을
\emph{한 장의 등고선 지도}로 확장하면 세 비용이 빌드방향 구면 위에서 어떻게 분포하는지 직접
비교할 수 있다(그림~\ref{fig:contourcompare}). 실용적인 밀집 메쉬(Stanford Bunny, 69{,}662면)에
대해 이전 SFTF 논문과 동일한 $(\mathrm{yaw},\mathrm{pitch})$ 매개화\footnote{$\nvec=[-\sin p,\ \cos p\sin y,\ \cos p\cos y]$,
두 각 모두 $[0^\circ,360^\circ)$. 색은 이전 SFTF 논문과 같은 \texttt{RdBu\_r}(적=고비용, 청=저비용).
두 각이 모두 $0$--$360^\circ$ 라 구면을 이중으로 덮으므로 같은 방향이 지도상 여러 곳에 나타날 수 있다.}
위에 네 비용을 \emph{왼쪽부터} 나란히 그렸다(그림~\ref{fig:contourcompare} 의 패널 표시 (a)--(d) 에 대응):
\textbf{(a)~A} 하드 SFTF $J_{\mathrm{SFTF}}$(미분가능 손실을 sharp
극한으로 보낸 것으로, 미분 불가능한 SFTF의 하드 목적에 해당, 컬러바 $J_{\mathrm{SFTF}}$), \textbf{(b)~B$'$} 미분가능 $L_{\mathrm{SFTF}}$
를 부분적으로 sharpen($f{=}0.7$)한 것(컬러바 $L_{\mathrm{sharp}}$), \textbf{(c)~B} 완전 소프트 $L_{\mathrm{SFTF}}$(실제 작동점,
컬러바 $L_{\mathrm{SFTF}}$), \textbf{(d)~C} 물리 TomoNV 지지질량 $\mathrm{mss}$ [g]. A$\to$B$'\to$B 로 갈수록 온도가 풀리며, 같은
고비용(적색) 분지를 공유한 채 점점 평탄해진다. 정량적으로도 sharpen 한 B$'$ 는 A 와 거의 일치하고
(Spearman $+0.97$), 완전 소프트 B 도 $+0.76$ 으로, B 가 A 의 \emph{매끄러운 대체물}이며 온도를
조이면 SFTF의 하드 비용으로 \emph{수렴}함이 한 장에 드러난다(\S\ref{sec:results} fig:relaxation 의 점별 수렴을
랜드스케이프로 재확인). 반면 C 와 B 의 상관은 $+0.44$ 에 그쳐 앞 절의 정직한 결론---이전 연구의 SFTF 비용은
물리 지지부피의 느슨한 프록시---을 다시 보여준다.
\textbf{파동론으로 보면}(\S\ref{sec:wavelength}) A$\to$B$'\to$B 는 \emph{유효 파장을 점점 늘리는}
한 장의 sweep 이다 --- 즉 \S\ref{sec:wavelength} 의 담금질(파장을 \emph{줄이는} 과정)의
\emph{역방향}으로, hard 에서 soft 로 풀어 가는 sweep 이다: A 는 입자(날카로운 그림자), B$'$ 는
짧은 파장(살짝 번짐, $+0.97$), B 는 긴 파장(크게 번졌지만 같은 분지 유지, $+0.76$). 파장이
길수록 회절이 커져 비용장이 평탄해지되 골짜기 위치는 보존됨이 한눈에 드러난다.

\paragraph{두 마커의 의미.} 각 패널에는 두 종류의 최적 빌드방향이 겹쳐 있다. \emph{panel argmin}
(검은 $\times$)은 \textbf{그 패널이 그리는 비용의 격자 전수탐색 최소}로, 패널마다 독립적으로 계산된다
(A 는 $J$, B$'$/B 는 해당 $L$, C 는 $\mathrm{mss}$ 의 최소). 즉 ``그 비용함수가 말하는 이론상 최적
방향''이다. \emph{gradient $\nvec^\ast$}(초록 $\star$)은 \textbf{미분가능 손실 $L$(완전 소프트) 하나에만}
다중 시드 경사하강으로 얻은 해이며, 네 패널에 \emph{같은 방향}으로 겹쳐 그렸다. 읽는 법은 세 가지다.
(i) B 에서 $\star$ 가 $\times$ 의 분지에 안착하면 ``기울기만으로 전수탐색 최적을 재현''하는
\emph{자기일관성}이다(그림~\ref{fig:landscape} 의 정량 주장과 동일). (ii) A 위의 $\star$ 는
미분가능화가 SFTF의 하드 목적을 보존하는지를, (iii) C 위의 $\star$ 는 $L$-최적 방향이 실제 지지를 줄이는지를
(여기서는 저지지 청색 영역에 들지만 C 의 자체 최적과는 어긋남) 보여준다. 한편 패널마다 비용의
\emph{종류와 척도가 다르므로}(A/B$'$/B 는 단위 정규화 메쉬의 차원 없는 SFTF 점수, C 는 물리 질량 [g])
\textbf{절대값이 아니라 분포의 모양과 순위만} 비교해야 하며, 그래서 컬러바도 패널별로 독립이다. 또
$\times$ 는 단일 격자 셀이라 거의 같은 높이의 분지가 둘이면 다른 분지로 튈 수 있어, 그 \emph{위치}는
필드 전체의 순위상관보다 덜 안정적임에 유의한다.

\begin{figure}[t]
  \centering
  \includegraphics[width=\linewidth]{contour_compare_bunny.png}
  \caption{Bunny 빌드방향 지지비용 랜드스케이프: 하드 SFTF $\to$ 미분가능 SFTF(소프트$\to$샤프)
  대 물리 TomoNV. 왼쪽부터 패널 \textbf{(a)} 하드 SFTF $J$, \textbf{(b)} sharpen $L$, \textbf{(c)}
  소프트 $L$, \textbf{(d)} 물리 TomoNV $\mathrm{mss}$. 각 패널의 정의·순위상관과 두 표식(검은 $\times$,
  초록 $\star$)의 의미는 본문 참조.}
  \label{fig:contourcompare}
\end{figure}

\paragraph{물리 충실도를 위한 가중치 재조정.} 세 항 $(\tilde R_{\mathrm{face}},\tilde P,\tilde B)$ 의 방향별 값과
TomoNV 지지질량을 회귀하여 가중치 $w_R,w_P,w_B$ 를 다시 맞췄다(96방향, 5-겹 교차검증). 원척도
최소제곱(OLS/NNLS)은 학습 상관을 Spearman $+0.59$ 까지 올리지만 held-out 에서 $-0.02$ 로 붕괴해
\emph{과적합}이다. 반면 \textbf{순위공간 재가중}(rank-OLS)은 held-out 에서 일반화하여 순위상관을
baseline $+0.21$ 에서 $\mathbf{+0.40}$ 으로(Pearson $+0.39$) 끌어올린다(그림~\ref{fig:tuned});
가중치는 $(w_R,w_P,w_B)\propto(+0.49,-0.36,+0.16)$ 이다. 즉
흐름텐서 항 $R$ 과 바닥 항 $B$ 를 키우고 쌍지지 항 $P$ 를 거의 끄는 것이 물리
지지질량과 더 잘 맞는다. 다만 $+0.40$ 은 여전히 중간 수준으로, 재조정이 순위 일치를 높이지만
SFTF 세 항만으로 물리 지지질량을 정밀히 예측하지는 못한다. 비선형 특징이나 물리 기반 항의 추가가
후속 과제다.

\begin{figure}[t]
  \centering
  \includegraphics[width=0.92\linewidth]{demo_sftf_tuned.png}
  \caption{가중치 재조정 전후. 좌: baseline $w{=}(1,1,1)$ (Spearman $+0.21$). 우: 순위공간 재가중
  (5-겹 교차검증 held-out Spearman $+0.40$). 점은 빌드방향, 색은 TomoNV 지지질량.}
  \label{fig:tuned}
\end{figure}

\paragraph{물리 지지부피 항 $S$ 의 일반화(TomoNV).} 가중치 재조정은 원래 있는 세 항의 비율만
바꾸므로, 이전 연구의 SFTF 에 없는 물리량을 새로 설명하지는 못한다. 그래서 다음 단계에서는
\S\ref{sec:supvol} 에서 정의한 물리 지지부피 항 $S$ \eqref{eq:supvol} 를 더한다.
11개 watertight 메쉬(프리미티브·브래킷·Bunny, 48방향)에서 \textbf{메쉬 단위 leave-one-out}
일반화(보류 메쉬의 방향 순위 Spearman)를 측정하면, 학습 없이 $S$ 만으로 평균 $+0.61$ 로 하드 SFTF 기반
$L_{\mathrm{SFTF}}$($+0.17$)보다 세 배 이상 높고(회전대칭 퇴화형 구 제외 시 $+0.69$), 8개 특징을 쓴
Ridge$\cdot$Gradient Boosting$\cdot$MLP($+0.33\!\sim\!+0.56$)도 대체로 능가한다(그림~\ref{fig:learned}).
여기서 Spearman 은 절대 지지질량[g]의 오차가 아니라, 각 보류 메쉬 안에서 48개 빌드방향을
``적게 지지되는 방향부터 많이 지지되는 방향까지'' 얼마나 같은 순서로 줄 세우는지를 뜻한다.
따라서 이 그림의 물리적 의미는 단순하다: 지지재 양의 방향별 변화는 대체로 \emph{오버행 면적}
$\times$ \emph{수신면/바닥까지의 낙하 높이}라는 지지부피 근사로 설명되며, 이 물리량은 학습된
비선형 회귀기보다 보지 않은 형상에 더 잘 일반화된다. 그림의 점들은 각 보류 메쉬의 개별 Spearman
으로, 퍼짐은 통계적 신뢰구간이 아니라 형상별 난이도 차이(메쉬 간 이질성)를 나타낸다.
즉 충실도 향상은 \emph{모델 복잡도가 아니라 올바른 물리 특징}에서 온다. 이로써 게이트 전의 매끄러운
물리항으로는 $L_{\mathrm{SFTF}}+\lambda_S\,S$ 가 정당화되고, 실제 슬라이서 정합에는 아래의
$S_g$ 변형을 쓴다.

\begin{figure}[t]
  \centering
  \includegraphics[width=0.9\linewidth]{demo_sftf_learned.png}
  \caption{TomoNV 지지질량에 대한 \emph{메쉬 단위 leave-one-out} 일반화(11 메쉬, 48방향). 물리기반
  미분가능 지지부피 $S$ \eqref{eq:supvol} 가 학습 없이 기본 $L_{\mathrm{SFTF}}$ 와 학습된
  Ridge/GBR/MLP 를 모두 능가한다. 막대는 보류 메쉬 평균 Spearman, 흰 점은 각 보류 메쉬의
  Spearman 이다. 점의 퍼짐은 신뢰구간이 아니라 메쉬별 일반화 난이도 차이를 나타낸다.}
  \label{fig:learned}
\end{figure}

\paragraph{TomoNV 기준 엔드투엔드 점검.} 중간 점검으로 $S$ 를 손실에 켜고($w_S{=}1$) 빌드방향을 실제로
최적화했을 때 TomoNV 추정 지지질량이 줄어드는지 확인했다. 11개 메쉬에서 경사하강으로 얻은
$\nvec^\ast$ 의 TomoNV $\mathrm{mss}$ 를 48방향 분포의 백분위로 환산하면($0$=최적), SFTF 손실은 평균 $0.20$,
$L_{\mathrm{SFTF}}+S$ 도 $0.20$ 으로 사실상 동급이다 --- 두 손실 모두 6/11 메쉬에서 백분위
$0.02$ 이하의 최적 분지에 도달하므로, $S$ 를 더해도 엔드투엔드 결과를 해치지 않되 이 지표만으로는
추가 이득도 크지 않다(순위 일반화의 이득은 위 LOMO 비교가 보여준다). 반면 $S$ \emph{단독}
($w_R{=}w_P{=}w_B{=}0$)은 평균이 분명히 높아($0.30$), $R,P,B$ 를 유지한 $L_{\mathrm{SFTF}}+\lambda_S S$
가 견고한 선택임을 확인한다.

\paragraph{형상 최적화(개념증명): 자기지지 형상 유도.} 자기지지 형상 설계 자체는 위상최적화에서 폭넓게
연구되었다~\citep{guo2017self,zhao2017self,kumar2022overhang}. 따라서 여기서의 새로움은 \emph{자기지지
형상}이 아니라, 그것을 \textbf{SFTF 에서 유도한 미분가능 메쉬 손실의 정점 기울기}로 유도하고 그 결과를
\textbf{복셀 추정 지지질량(TomoCPU/TomoNV)으로 점검}했다는 점이다(개념증명). $\partial L/\partial V$ 가 흐른다는 점을
이용해, 빌드방향을 $\nvec{=}+z$ 로 고정하고 정점 $V$ 를 직접 최적화했다. 손실은 $L_{\mathrm{SFTF}}$(임계각
$\theta_c{=}60^\circ$ 게이트, $+S$)에 형상 정규화(라플라시안 평활 $+$ 부피보존 $+$ 데이터항)를 더한
것이다. 구(icosphere)는 \textbf{바닥이 가팔라진 자기지지 형상}(teardrop)으로 변형되어 $60^\circ$
기준 오버행 면적이 $0$ 이 되고($-100\%$) $L_{\mathrm{SFTF}}$ 지지항이 $-63\%$ 감소했으며, \emph{무엇보다}
TomoCPU 추정 지지질량이 $1.82\to0.07$ g 으로 $-96\%$ 줄었다(그림~\ref{fig:shapeopt}). 즉 손실항의
정점 기울기가 물리적으로 유의미한 자기지지 형상을 유도한다.
\textbf{파동론으로 보면}(\S\ref{sec:wavelength}) 형상 최적화가 가능한 이유 자체가 회절이다:
그림자 경계가 입자처럼 칼같으면 정점을 움직여도 경계에서 기울기가 0/정의불가지만, 파동처럼
번진 경계는 $\partial L/\partial V$ 가 살아 있어 형상을 ``밀어'' 변형시킬 수 있다. 따라서 정점
기반 자기지지 설계는 본질적으로 파동(소프트) 영역에서만 작동한다.

\begin{figure}[t]
  \centering
  \includegraphics[width=\linewidth]{demo_sftf_shapeopt_tomocpu_support.png}
  \caption{$\partial L/\partial V$ 를 이용한 자기지지 형상 최적화($\nvec{=}+z$, $\theta_c{=}60^\circ$).
  \textbf{(a)} 변형 전 구에는 하부에 넓은 TomoCPU 지지구조가 형성된다.
  \textbf{(b)} 최적화 후에는 바닥이 자기지지 teardrop 형태로 가팔라지며, TomoCPU 지지질량이
  $1.82\to0.07$ g($-96\%$)로 감소한다.}
  \label{fig:shapeopt}
\end{figure}

\paragraph{고해상도·임의 메쉬로의 확장.} 식 \eqref{eq:supvol} 의 면-면 라우팅은 $O(F^2)$ 라 수만 면
규모에서는 비싸다. 자기지지 변형을 구동하는 신호는 본질적으로 per-face 오버행과 \emph{바닥 지지높이}
($O(F)$)이므로, $S$ 의 바닥 항만 쓰는 확장 가능한 목적함수로 충분하다. 다만 고해상도에서 단순 오버행
최소화는 표면을 잘게 \emph{주름지게}(wrinkle) 만들어 $60^\circ$ 게이트만 회피하며 면적을 폭증시키는
퇴화해에 빠진다(이때 TomoNV 추정값은 오히려 증가). 이를 \textbf{표면적 보존 정규화}로 막으면, 고해상도
구(subdiv5, 20{,}480면)는 오버행이 $-99\%$, TomoNV 추정 지지질량이 $-36\%$ 로 깔끔히 수렴한다.
\emph{임의 메쉬}에서도 같은 정점 기울기가 작동한다: 토러스는 관 단면이 원에서 \textbf{teardrop}
방향으로 변형되어 TomoCPU 지지질량이 $2.49\to0.63$ g($-75\%$)로 감소한다(그림~\ref{fig:shapeopt_torus}).
같은 토러스를 표면적 보존 \emph{없이} 최적화하면 지지질량이 오히려 $2.49\to3.94$ g 으로 \emph{증가}해
위의 주름 퇴화 경고를 그대로 재현한다 --- 확장 가능한 목적에서는 표면적 보존이 선택이 아니라 필수다.

\begin{figure}[t]
  \centering
  \includegraphics[width=\linewidth]{demo_sftf_shapeopt_torus_tomocpu_support.png}
  \caption{임의 메쉬(토러스)의 자기지지 형상 최적화($\nvec{=}+z$, $\theta_c{=}60^\circ$, 확장 가능한
  $O(F)$ 목적 $+$ 표면적 보존). \textbf{(a)} 변형 전 토러스에는 하부 링을 따라 넓은 TomoCPU
  지지구조가 생긴다. \textbf{(b)} 최적화 후 관 단면이 teardrop 으로 가팔라져 지지구조가 줄고,
  TomoCPU 지지질량이 $2.49\to0.63$ g($-75\%$)로 감소한다(표면적 보존이 없으면 주름 퇴화로 오히려 증가).}
  \label{fig:shapeopt_torus}
\end{figure}

\paragraph{다중 메쉬 정량화: 실제 슬라이서 지지재 제거.} 형상최적화가 1--2개 데모에
그치지 않음을 보이기 위해, \emph{같은} 레시피($O(F)$ 목적 $+$ 표면적 보존, $\theta_c{=}60^\circ$,
400스텝, 메쉬별 재튜닝 없음)를 9개 메쉬에 일괄 적용하고, 변형 전후 형상을 \textbf{실제 생산
슬라이서}(legacy CuraEngine 15.04 / DP103)로 $\nvec{=}+z$ 에서 슬라이스해 support-only 질량을
측정했다(표~\ref{tab:shapeopt-multi}). $z$-up 에서 실제 지지재가 필요한 \textbf{6개 메쉬 전부}에서
Cura 지지질량이 $-96\%$--$-100\%$ 제거된다(합계 $14.2\to0.23$ g). 수천--수만 자유도의 정점
설계공간은 방향 샘플링이 원리적으로 불가능한 영역이므로, 이 결과는 \emph{미분가능성이 아니면
얻을 수 없는} 고유한 성과다. 저해상도(28면) U-브래킷에서 TomoNV 추정값이 증가($0.24\to0.39$ g)
하는 예외는 정직하게 표기한다 --- 복셀 추정기의 저해상도 노이즈로, 실제 Cura 기준으로는
지지재가 처음부터 끝까지 $0$ 이다. 다만 이 표의 제거율은 CuraEngine 에 특이적이며 슬라이서를
바꾸면 유지되지 않는다. 절~\ref{sec:shapeopt-transfer-limit} 에서 같은 형상을 PrusaSlicer 로
재슬라이스해, 정점 기울기가 무엇을 달성했고 무엇을 달성하지 못했는지 한정한다.

\begin{table}[t]
  \centering
  \caption{정점-기울기 자기지지 형상최적화의 다중 메쉬 정량화($\nvec{=}+z$,
  $\theta_c{=}60^\circ$, 확장 가능한 $O(F)$ 목적 $+$ 표면적 보존, 400스텝 --- \emph{메쉬별 재튜닝
  없음}). 오버행 면적은 단위대각 정규화 값, TomoNV 는 복셀 추정 지지질량, Cura 는 legacy
  CuraEngine 15.04 / DP103 의 \textbf{실제 support-only 질량}이다. 행은 $z$-up 에서 실제
  지지재가 필요한 6개(위; $-96\%$--$-100\%$ 제거)와 지지재가 처음부터 $0$ 인 대조군
  3개(아래)로 분리했다. 오른쪽 두 열은 텐서 기여 대조군(재최적화 후 최종 Cura 질량):
  목적에 텐서 손실을 더해도(+텐서) 결과가 실질적으로 달라지지 않는 반면, 텐서만으로는
  구가 실패($0.88\to\mathbf{0.99}$ g)하고 원환·Bunny 도 악화된다.}
  \label{tab:shapeopt-multi}
  \small
  \begin{tabular}{lrrrrrr}
    \toprule
    메쉬 & 면수 & 오버행@$60^\circ$ 전$\to$후 & TomoNV [g] 전$\to$후 & Cura [g] 전$\to$후 &
    \multicolumn{2}{c}{재최적화 후 Cura [g]} \\
     & & & & (본 목적) & +텐서 & 텐서만 \\
    \midrule
    icosphere        & $1{,}280$  & $0.073\to0.000$ & $1.82\to0.04$ & $0.66\to\mathbf{0.00}$ & $0.00$ & $0.01$ \\
    구 (sphere)      & $2{,}976$  & $0.062\to0.001$ & $1.80\to0.30$ & $0.88\to\mathbf{0.00}$ & $0.00$ & $\mathbf{0.99}$ \\
    원환 (torus)     & $2{,}304$  & $0.149\to0.000$ & $2.49\to0.62$ & $0.26\to\mathbf{0.00}$ & $0.00$ & $0.03$ \\
    후크 (hook)      & $1{,}560$  & $0.032\to0.000$ & $2.03\to0.46$ & $3.57\to\mathbf{0.00}$ & $0.00$ & $0.00$ \\
    파이프엘보       & $2{,}400$  & $0.113\to0.000$ & $6.27\to1.43$ & $6.39\to\mathbf{0.14}$ & $0.11$ & $0.16$ \\
    Bunny            & $69{,}662$ & $0.106\to0.000$ & $3.21\to1.66$ & $2.47\to\mathbf{0.09}$ & $0.03$ & $0.26$ \\
    \midrule
    원뿔 (cone; 지지 불필요 대조군)   & $96$ & $0.220\to0.000$ & $0.30\to0.13$ & $0.00\to0.00$ & $0.00$ & $0.00$ \\
    U-브래킷 (지지 불필요 대조군)     & $28$ & $0.228\to0.000$ & $0.24\to0.39$ & $0.00\to0.00$ & $0.00$ & $0.00$ \\
    C-클램프 (지지 불필요 대조군)     & $28$ & $0.350\to0.000$ & $0.24\to0.24$ & $0.00\to0.00$ & $0.00$ & $0.00$ \\
    \bottomrule
  \end{tabular}
\end{table}

\paragraph{텐서 기여 대조: 형상최적화도 텐서가 견인하지 않는다.}
표~\ref{tab:shapeopt-multi} 의 레시피 자체가 텐서에 대한 진술이다: 확장 가능한 $O(F)$
목적은 게이트된 오버행면적$\times$높이 합 --- $S_g$ 의 형상 쪽 대응물 --- 이며 텐서 항을
포함하지 않는다. 표의 대조 두 열이 텐서가 무엇을 더하는지 정량화한다. 9개 메쉬 전부를
텐서 손실 $L_{\mathrm{SFTF}}$ 를 등가중으로 \emph{더해} 재최적화해도 실질적 변화가 없다:
지지 필요 6개 메쉬 모두 $96$--$100\%$ 제거 대역을 유지한다(총 잔량 $0.23$ 대 $0.14$ g).
반면 텐서 손실 \emph{만으로} 재최적화하면 불충분하다: 구는 아예 실패하고($0.88\to0.99$ g),
원환·Bunny 는 $88$--$90\%$ 제거로 떨어진다(총 잔량 $1.45$ g). 표~\ref{tab:cura} 의 예측
대조와 합치면 역할 분담이 데이터로 완결된다: SFTF 텐서는 예측 헤드라인도 형상최적화
헤드라인도 견인하지 않으며 --- 둘 다 게이트된 지지높이 물리가 견인한다 --- 텐서의 역할은
이전 SFTF 목적의 미분가능한 충실 재현이다. (텐서 단독 실행도 매끄러운 오버행 게이트는
공유하므로, 그 부분적 성공은 아래 절제실험과 일관된다: 쓸 만한 정점 기울기를 공급하는
것은 텐서 구조가 아니라 게이트의 부드러움이다.)

\paragraph{게이트 절제: 부드러움이 기울기의 원천이다.} ``잘 맞는 항($S_g$)은 미분가능하게
만들 것도 없는 단순한 항''이라는 반론을 절제실험으로 반박한다. 시그모이드 게이트의 sharpness
$k$ 를 $8\to24\to96\to384\to6144$(계단함수 극한)로 조이며 같은 형상최적화를 반복하면,
$k{=}8$--$24$ 에서는 오버행이 완전히 사라지고 TomoNV 질량이 최저(구 $0.04$ g)로 안정 수렴하지만,
$k{\ge}96$ 부터는 오버행이 잔존하고 결과가 불안정해져 구에서 최대 $25$배 나쁜 $0.90$ g 에
이른다(토러스도 동일 경향). 하드 게이트는 임계 근방 밖에서 기울기가 소멸해 정점 신호가
잡음화되기 때문이다. 즉 $S_g$ 의 가치는 ``오버행$\times$낙하높이''라는 항 자체가 아니라 그것을
\emph{매끄럽게 게이트해 기울기를 살린 것} --- 정확히 본 논문의 완화 기계장치 --- 에 있다.
파동론(\S\ref{sec:wavelength})으로 보면 게이트를 조이는 것은 파장을 $0$ 으로 보내는 입자
극한이며, 회절(기울기)이 함께 사라진다.

\paragraph{게이트 처방: straight-through 로 예측과 최적화를 한 목적으로.}
위 절제와 표~\ref{tab:cura} 의 하드 게이트 우위를 합치면 실용적 딜레마가 남는다:
\emph{예측}(순위 충실도)은 날카로운 게이트가, \emph{최적화}(기울기)는 부드러운 게이트가
유리하다. 이를 해소하는 처방이 \S\ref{sec:consistency} 에서 정의한
\textbf{straight-through 추정기}(STE) 게이트다 --- 순전파는 하드 지시함수
$\mathbf{1}[-\mvec\cdot\nvec>\sin\theta_c]$, 역전파만 시그모이드의 \emph{대리
기울기}(surrogate gradient)다~\citep{bengio2013ste}. 게이트 변형만
바꿔 표~\ref{tab:shapeopt-multi} 와 같은 9메쉬 배치 프로토콜을 재실행하면, 지지 필요
6개 메쉬의 실제 Cura 잔량 합계가 시그모이드 $k{=}24$(본문 레시피) $0.23$ g(제거율
$98.4\%$) 대 STE $0.28$ g($98.0\%$)으로 사실상 동급인 반면, 순수 하드 게이트는
$7.26$ g($49\%$)으로 붕괴하고 지지 $0$ 이던 대조군 두 개까지 악화시킨다. 임계 밖에서
정확히 $0/1$ 인 정적 smoothstep 게이트($\pm0.02$--$0.05$)는 그 중간($0.59$--$0.68$ g,
$95$--$96\%$)이다. STE 는 순전파가 하드 게이트와 동일하므로 게이트 축의 예측
편향(시그모이드의 각도 번짐과 0-서포트 누설)이 구성상 사라지고 --- $A_i\eta_i$ 골격에서는
하드 게이트와 점수가 동일하다 --- 역전파는 시그모이드와 동일하므로 최적화는 소프트
수준이다. 다만 풀 $S_g$ 예측기에 끼우면 남은 완화 성분(softplus 오버행 크기 가중·soft-min
바닥높이)이 격차를 마저 지므로 하드 대조군에는 못 미친다(표~\ref{tab:cura} 의
$S_g^{\mathrm{ste}}$ 열 $+0.78$; 격차의 성분별 진단은 아래 Cura 검증 문단). 요약하면:
\emph{평가·순위}에는 완화가 전혀 필요 없으므로 $S_g^{\mathrm{hard}}$(또는 좁은 smoothstep
골격)를 쓰고, \emph{미분가능 목적 안의 게이트}는 STE 가 --- 최적화 성능 손실 없이 게이트
축의 예측 편향을 없애므로 --- 처방이다.

STE 의 역전파에는 한 가지 선택지가 더 있으며, 이는 순전한 개선이 아니라 진짜
trade-off 다. STE 의 순전파가 하드 지시함수이므로 어떤 대리 기울기를 쓰든 순위는
동일하고, 대리 기울기는 최적화의 궤적만 바꾼다. 시그모이드 대리 기울기를 컴팩트한 $C^2$
smootherstep 도함수(\texttt{ste\_smooth})로 바꾸면 기계부품에서 대리 기울기와 하드
유한차분 기준 방향 사이의 스텝별 정렬(코사인)이 올라가지만(시그모이드 역전파의 평균
$0.35$ 대비 $0.52$; 실린더·원뿔·U-브래킷·파이프엘보와 Thingi10k 부품 기준), 컴팩트
대리 기울기는 밴드 $[t\pm d]$ 밖에서 정확히 $0$ 이라 임계각에서 먼 시작 방향에서는
정체한다: 단일 시작·20스텝의 빡빡한 예산에서는 시그모이드-역전파 STE 보다 \emph{나쁜}
방향에 도달하고(정규화 하드 지지 $0.272$ 대 $0.247$), 반대로 넉넉한 다중시작 예산에서는
차이가 사라진다(모든 게이트 변형이 전역 최적에 도달). 즉 컴팩트 역전파는 활성 영역에서는
더 날카롭지만 그 밖에서는 눈이 먼 양날의 검이므로, cold-start 방향 탐색의 견고한 기본은
\emph{시그모이드-역전파} STE 다. 컴팩트 변형은 해 근방에서, 또는 밴드폭 $d$ 를
넓게 시작해 좁혀 가는 broad-to-compact annealing 과 함께 쓸 때에만 유리하다.

\paragraph{형상최적화 데모의 한계.} 본 논문의 형상최적화는 어디까지나 \emph{기하 전용}
개념증명임을 분명히 한다. 손실이 보는 것은 지지재 관점의 기하량(오버행 강도·낙하높이·표면적
보존)뿐이며, 응력·강성 같은 구조 응답, 최소 벽두께, 조립 공차 등 제조성·기능성
제약\footnote{실제 부품 설계에서는 하중을 견디는 강도, 프린터가 성형 가능한 최소 두께,
끼워맞춤 공차 등이 형상을 제약한다. 본 데모의 손실에는 이들이 전혀 들어 있지 않다.}은 전혀
포함하지 않는다. 따라서 표~\ref{tab:shapeopt-multi} 의 결과 형상은 ``정점 기울기가 실제
지지재를 제거하는 방향으로 형상을 움직일 수 있다''는 증거이지, 그대로 쓸 수 있는 부품
설계안이 아니다. density 기반 위상최적화의 자기지지 제약
문헌~\citep{langelaar2016selfsupp,guo2017self,qian2017undercut}처럼 구조 제약과 결합하는 것
--- 본 손실을 기존 위상최적화의 \emph{추가 항}으로 쓰는 것 --- 이 자연스러운 후속 과제다.

\paragraph{신경망(개념증명): 라벨 없는 분할상환 추론 \emph{가능성}.} 신경망으로 빌드방향을 직접 학습하는
연구가 이미 있으나, 보통 자체 미분가능 대리나 라벨을 쓴다~\citep{chen2023concurrent}. 여기서는 강한 학습
주장을 하려는 것이 아니라, \emph{우리 손실의 미분가능성만으로} 라벨 없는 분할상환(amortized) 추론이
가능함을 작은 규모에서 \emph{보이는} 것이 목적이다. 메쉬 면-그래프(노드$=$면, 엣지$=$면 인접)를 입력받는
메시지패싱 GNN이 면별 가중치 $a_i\ge0$ 를 내고,
빌드방향을 면 anti-법선의 가중합 $\nvec=\mathrm{norm}(\sum_i a_i(-\mvec_i))$ 으로 예측한다(이 구성은
회전에 자연스럽고 \emph{상수 붕괴}를 막는다). 학습 신호는 \emph{오직} 예측 방향의 $L_{\mathrm{SFTF}}$
(정답 방향 라벨 불필요)이며, 기울기가 $\nvec$ 를 통해 GNN 가중치로 흐른다. 9개 메쉬에서 메쉬 단위
leave-one-out 으로 평가하면(보류 메쉬에 대한 \emph{한 번의 forward} 예측) TomoNV 추정 지지질량
백분위가 평균 $0.28$ 로 무작위($0.41$)를 크게 앞서고 메쉬별 경사하강 oracle($0.13$)의 중간에 이른다
(그림~\ref{fig:gnn}). 6/9 메쉬에서 무작위를 이기며 일부(원기둥·원뿔·파이프엘보)에서는 실패한다 — 즉 \emph{분할상환
(amortized) 추론}이 가능함을 보이되, 작은 데이터셋·단순 모델 탓에 메쉬별 최적화를 대체하지는 않는다.
회전등변 GNN과 대규모 데이터가 후속 과제다. 정직하게 덧붙이면, 같은 실험을 \emph{실제 Cura} 지지질량
백분위로 옮기고 손실을 게이트 조합($L_{\mathrm{SFTF}}+S_g$)으로 학습해도 소형 세트에서는 이점이
확인되지 않는다(GNN $0.60$ 대 무작위 $0.40$). 이 실패가 거의 자기지지인 소형 프리미티브 위주의
테스트베드 때문인지 확인하기 위해, GPU 구현으로 50k--100k면 지지요구 유기 스캔 5종을 포함한
15메쉬 leave-one-out을 다시 수행했다. 이를 5개 독립 시드로 반복하고 무작위 기준도 메쉬·시드당
1,000방향으로 안정화하면, GNN 백분위는 무증강 $0.538$ 대 무작위 $0.469$이고(75개 mesh--seed
쌍 중 29승), 무작위 SO(3) 증강에서는 오히려 $0.642$ 대 $0.469$(14/75승)로 나빠진다. 메쉬를
군집으로 재표집한 GNN--무작위 평균차의 $95\%$ 구간은 무증강 $+0.069$
$[-0.030,+0.172]$(15개 메쉬 평균차 Wilcoxon $p=0.277$), 증강 $+0.173$
$[+0.101,+0.249]$($p=6.1\times10^{-4}$)이다. 따라서 \emph{대형 메쉬 제외만으로} 기존 실패를
설명할 수 없고, 단일 시드에서 보인 증강 개선도 재현되지 않는다. 다만 폴드당 훈련 메쉬가 여전히
14개이고 회전등변 모델을 직접 비교하지 않았으므로 데이터 규모 일반을 기각하거나 비등변 구조를
원인으로 확정하지는 않는다. 결과는 직접 등변성 오차와 모델 귀납편향을 통제 비교할 필요를 지목한다.
TomoNV 기반 결과는 개념증명으로 유지하되, 분할상환 추론은 본 논문의 기여 목록에는 넣지 않는다.

\begin{figure}[t]
  \centering
  \includegraphics[width=\linewidth]{demo_sftf_gnn.png}
  \caption{라벨 없는 자기지도 GNN 빌드방향 예측(메쉬 단위 leave-one-out, 9 메쉬). 좌: 보류 메쉬별
  TomoNV 추정 지지질량 백분위(낮을수록 좋음). 우: 평균. 한 번의 forward 로 예측한 GNN($0.28$)이
  무작위($0.41$)를 크게 앞서고 메쉬별 경사하강 oracle($0.13$)에 근접한다(라벨 없이 $L_{\mathrm{SFTF}}$
  만으로 학습).}
  \label{fig:gnn}
\end{figure}

\paragraph{실제 생산 슬라이서로의 검증.} 위의 물리 비교는 주로 TomoNV 를 복셀 기반 중간 기준으로
삼았지만, TomoNV 자체도 생산 슬라이서가 아니라 \emph{추정기}다. 결정적 시험은 미분가능 손실이
\emph{실제 슬라이서}가 깔아내는
지지재 양을 추종하는가이다. 메쉬 정체성은 기반 SFTF 연구~\citep{sftf_engine}·자매 논문(SFTFCluster)과
\emph{동일한} g5test 5그룹 벤치마크(A 기본도형·B 단순기능부품·C 유기 스캔·D Thingi10k 세트1·E
Thingi10k 세트2 대형; 부록 표~\ref{tab:coverage-g5})를 그대로 채택한다. 슬라이서 검증에는 이 중
헤드라인 18메쉬(코어 프리미티브·브래킷 8종 + 유기 대형 스캔 7종 + Thingi10k 기계부품 3종)에,
순위검증이 ill-posed한 퇴화·내부공동 형상 3종(정육면체·구·속빈상자)을 투명성을 위해 더한 21메쉬를
쓴다(E군은 all-pairs 예측기의 $O(F^2)$ 한계로 데시메이션 경유만, 부록~\ref{app:mesh-mg}).
대표로 8개 watertight 코어 메쉬(원기둥·원뿔·원환·U-브래킷·후크·C-클램프·파이프엘보·
Stanford Bunny)를, 3DWOX Desktop 이 \emph{정적으로 링크}한 바로 그 세대의 슬라이서인
\textbf{legacy CuraEngine 15.04} 의 헤드리스 모드로, 공식 \textbf{Sindoh DP103 PLA} 프로파일
(선형(lines) 서포트, $60^\circ$ 오버행 임계, 서포트 밀도 $20\%$, 선형 인필 $15\%$, 라프트 없음)
로 슬라이싱했다. 빌드방향이 $+z$ 가 되도록 회전시키고, TomoNV 와 \emph{같은} 48개
Fibonacci 방향에서 \emph{서포트 전용} 필라멘트 질량(G-code 의
\texttt{;TYPE:SUPPORT}/\texttt{SUPPORT-INTERFACE} 압출량\footnote{압출량은 절대 $E$ 좌표의
\emph{high-water-mark}(직전 최고치를 넘어서는 증분만)로 합산해 리트랙션 복귀(re-prime)의
이중계산을 제거한 뒤, 필라멘트 길이[mm]에 단면적 $\pi(1.75/2)^2$\,mm$^2$ 과 PLA 밀도
$1.21$\,g/cm$^3$ 를 곱해 그램으로 환산한다. 단순 양(+)의 $E$ 증분 합산은 리트랙션마다
복귀분을 새 필라멘트로 이중계산해 서포트가 많은 방향을 비균일하게 부풀리고 방향 간 순위를
왜곡한다.})만 합산해 측정했다. 메쉬별 Spearman 과 메쉬 간 평균의 부트스트랩 $95\%$ 신뢰구간을
표~\ref{tab:cura} 에 정리했다.

이 검증은 이전 3DWOX/DP103 수기 측정 실험(Stanford Bunny, $30^\circ$ yaw--pitch 격자,
bed adhesion \texttt{None})과 \emph{같은 슬라이싱 엔진}을 쓴다 --- legacy CuraEngine 은
DP103 프로파일에서 3DWOX 의 토패스와 \texttt{;TOTAL\_MASS} 를 $0.1$\,g 이내로,
수기 측정 무게 격자를 Spearman ${\approx}0.99$ 로 재현한다. 따라서 본 절은 \emph{다른} 슬라이서로
보는 보조 스트레스 테스트가 아니라, 실제 생산 도구체인(3DWOX/DP103)에 대한 직접 검증이다.
다만 두 가지 단서가 있다: (i) 프로파일이 DP103 기본값이라 깔리는 지지재 자체가 적고
(예: Bunny 의 서포트 질량이 방향에 따라 $2$--$15$\,g), (ii) 일부 합성 형상은 48개 방향 중
다수에서 거의 자기지지여서(서포트 ${\approx}0$) \emph{게이트 없는} 예측기로는 방향 간 순위 신호가
빈약하다 --- 그러나 아래에서 보듯 슬라이서 임계각에서 게이트하면 이를 극복한다.

\begin{table}[t]
  \centering
  \caption{legacy CuraEngine 15.04 / Sindoh DP103 PLA(lines, $60^\circ$, support-only)
  지지질량과 각 예측기의 \textbf{메쉬별} Spearman 순위상관(g5test 5그룹 벤치마크, 48 빌드방향).
  위 8개는 코어 프리미티브·브래킷, 가운데 10개는 유기 대형 스캔(마네킹·드래곤 100k·Happy·
  Lucy·Nefertiti·간·신장)과 Thingi10k 기계부품 3종이며, 이 \textbf{18개가 순위검증이 잘 정의되는
  헤드라인 집합}이다. 맨 아래 별도 블록의 3개(정육면체·구·속빈상자)는 순위 자체가 \emph{ill-posed}
  이거나(구: 회전대칭이라 방향과 무관하게 지지량이 $0.6$--$0.7$\,g로 \emph{평탄}) 내부 공동이 지지를
  좌우해(속빈상자) 표면 기반 예측기가 원리적으로 무력한 형상으로, TomoNV 를 포함한 \emph{모든} 열이
  동반 실패한다 --- 전체 21메쉬 평균을 투명하게 함께 싣되 헤드라인은 18개 기준이다. 맨 아래 두
  평균 행은 각각 헤드라인 18 / 전체 21 의 메쉬 간 평균과 부트스트랩($10^4$ 재표집) $95\%$
  신뢰구간이다. 슬라이서의 $60^\circ$ 임계각에서 게이트한 바닥높이 항 $S_g$ 가 실제 Cura
  지지질량을 헤드라인 평균 $\mathbf{+0.80}$(CI $[{+}.74,{+}.84]$ 가 $0$ 을 배제)으로 예측해,
  복셀 추정기 TomoNV($+0.46$)와 게이트 없는 $L_{\mathrm{SFTF}}$/$S$($+0.26$--$+0.39$)를 크게
  앞선다. \emph{핵심은 슬라이서 자신의 임계각에서 게이트하는 것}이다: 게이트 없는 항은 거의
  자기지지인 형상(원기둥·원뿔·브래킷)에서 무너지지만, 게이트하면 그 형상들까지 살아난다. 오른쪽
  세 대조 열: 게이트 항에 텐서 손실을 더한 $L_{\mathrm{SFTF}}{+}S_g$(순위공간 등가중 합)는
  $+0.58$ 로 오히려 \emph{내려가고}, 풀 $S_g$ 에서 \emph{게이트만} straight-through(순전파 하드,
  역전파 시그모이드)로 바꾼 $S_g^{\mathrm{ste}}$ 는 $+0.78$ 로 $S_g$ 와 동급에 머물며, $S_g$ 의
  \emph{모든} 매끄러운 성분을 날카로운 극한으로 바꾼 --- 텐서·어텐션·완화가 전혀 없는 --- 하드
  게이트 대조군 $S_g^{\mathrm{hard}}$ 는 $+0.87$ 로 약간 더 \emph{높다}. $S_g^{\mathrm{ste}}$ 와
  $S_g^{\mathrm{hard}}$ 의 차($-0.09$)가 곧 게이트 이외의 완화 성분(softplus 오버행 크기 가중·
  soft-min 바닥높이)의 몫이다.}
  \label{tab:cura}
  \small
  \begin{tabular}{lrrrrrrrr}
    \toprule
    메쉬 & Cura 질량[g] & TomoNV & $L_{\mathrm{SFTF}}$ & $L_{\mathrm{SFTF}}{+}S$ & $L_{\mathrm{SFTF}}{+}S_g$ & $S_g$ & $S_g^{\mathrm{ste}}$ & $S_g^{\mathrm{hard}}$ \\
    \midrule
    원기둥 (cylinder)   & $0.0$--$10.2$   & $-0.20$ & $-0.63$ & $-0.59$ & $+0.44$ & $+0.87$ & $+0.92$ & $+0.98$ \\
    원뿔 (cone)         & $0.0$--$10.1$   & $-0.42$ & $+0.03$ & $-0.18$ & $+0.51$ & $+0.86$ & $+0.96$ & $+0.98$ \\
    원환 (torus)        & $2.6$--$6.5$    & $+0.86$ & $+0.37$ & $+0.74$ & $+0.79$ & $+0.86$ & $+0.76$ & $+0.82$ \\
    U-브래킷            & $0.0$--$55.7$   & $-0.45$ & $+0.32$ & $+0.31$ & $+0.52$ & $+0.66$ & $+0.48$ & $+0.48$ \\
    후크 (hook)         & $0.1$--$7.1$    & $+0.78$ & $+0.31$ & $+0.58$ & $+0.66$ & $+0.84$ & $+0.83$ & $+0.91$ \\
    C-클램프            & $0.0$--$29.5$   & $-0.40$ & $+0.23$ & $+0.13$ & $+0.52$ & $+0.77$ & $+0.76$ & $+0.76$ \\
    파이프엘보          & $0.0$--$13.8$   & $+0.95$ & $+0.22$ & $+0.53$ & $+0.61$ & $+0.97$ & $+0.98$ & $+0.99$ \\
    Bunny               & $2.0$--$14.8$   & $+0.89$ & $+0.14$ & $+0.50$ & $+0.50$ & $+0.85$ & $+0.84$ & $+0.94$ \\
    \midrule
    마네킹 (manikin)    & $1.2$--$6.2$    & $+0.82$ & $+0.54$ & $+0.67$ & $+0.70$ & $+0.82$ & $+0.82$ & $+0.91$ \\
    드래곤 (dragon 100k)& $4.3$--$19.2$   & $+0.75$ & $+0.56$ & $+0.64$ & $+0.65$ & $+0.60$ & $+0.58$ & $+0.64$ \\
    Happy Buddha 50k    & $3.8$--$18.7$   & $+0.64$ & $+0.53$ & $+0.69$ & $+0.64$ & $+0.67$ & $+0.55$ & $+0.73$ \\
    Lucy 50k            & $2.3$--$16.9$   & $+0.87$ & $+0.56$ & $+0.76$ & $+0.72$ & $+0.90$ & $+0.87$ & $+0.96$ \\
    Nefertiti 100k      & $1.4$--$12.4$   & $+0.86$ & $-0.02$ & $+0.35$ & $+0.56$ & $+0.90$ & $+0.86$ & $+0.98$ \\
    간 (liver 19k)      & $0.4$--$16.0$   & $+0.90$ & $+0.27$ & $+0.47$ & $+0.58$ & $+0.82$ & $+0.78$ & $+0.97$ \\
    신장 (kidney 12k)   & $0.2$--$5.7$    & $+0.91$ & $+0.58$ & $+0.65$ & $+0.71$ & $+0.80$ & $+0.79$ & $+0.95$ \\
    Thingi-D1 (37009)   & $0.1$--$11.7$   & $+0.01$ & $+0.67$ & $+0.73$ & $+0.72$ & $+0.77$ & $+0.75$ & $+0.86$ \\
    Thingi-D5 (37095)   & $0.0$--$27.2$   & $-0.35$ & $+0.01$ & $+0.00$ & $+0.26$ & $+0.84$ & $+0.94$ & $+0.94$ \\
    Thingi-D9 (37415)   & $4.3$--$14.6$   & $+0.87$ & $+0.06$ & $+0.13$ & $+0.29$ & $+0.53$ & $+0.51$ & $+0.80$ \\
    \midrule
    \textbf{헤드라인 평균(18)} &          & $+0.46$ & $+0.26$ & $+0.39$ & $+0.58$ & $\mathbf{+0.80}$ & $+0.78$ & $+0.87$ \\
    \;\;95\% CI         &                 & $[{+}.20,{+}.70]$ & $[{+}.12,{+}.39]$ & $[{+}.22,{+}.55]$ & $[{+}.51,{+}.64]$ & $[\mathbf{{+}.74,{+}.84}]$ & $[{+}.71,{+}.84]$ & $[{+}.80,{+}.92]$ \\
    \midrule
    \multicolumn{9}{l}{\footnotesize\emph{순위검증이 ill-posed한 퇴화·내부공동 형상(헤드라인 제외; 대칭 연구·한계절 참조)}}\\
    정육면체 (cube)     & $0.0$--$52.3$   & $+0.22$ & $+0.48$ & $+0.48$ & $+0.32$ & $-0.11$ & $-0.15$ & $-0.15$ \\
    구 (sphere; 평탄)   & $0.6$--$0.7$    & $-0.00$ & $-0.14$ & $-0.14$ & $-0.14$ & $-0.14$ & $-0.13$ & $+0.04$ \\
    속빈상자 (hollow box)& $0.0$--$50.0$  & $+0.17$ & $+0.09$ & $+0.11$ & $+0.09$ & $+0.02$ & $-0.00$ & $-0.00$ \\
    \midrule
    전체 평균(21)       &                 & $+0.41$ & $+0.25$ & $+0.36$ & $+0.51$ & $+0.67$ & $+0.65$ & $+0.74$ \\
    \;\;95\% CI         &                 & $[{+}.18,{+}.63]$ & $[{+}.11,{+}.37]$ & $[{+}.20,{+}.50]$ & $[{+}.40,{+}.60]$ & $[{+}.52,{+}.80]$ & $[{+}.50,{+}.78]$ & $[{+}.58,{+}.87]$ \\
    \bottomrule
  \end{tabular}
\end{table}

미분가능 \emph{게이트} 지지항이 실제 슬라이서 지지질량을 매우 잘 추종한다. 오버행을 임계각에서
게이트하고 각 진짜 오버행을 \emph{바닥판까지 낙하 높이} $\eta_i$ 로 점수화한 변형\footnote{$S_g=\sum_i
\mathrm{gate}_{60}(\tilde O_i)\,A_i\,\eta_i$. $\mathrm{gate}_{60}$ 은 면이 \emph{수직 기준}으로 DP103
임계($60^\circ$)보다 더 누운 \emph{진짜} 오버행($-(\mvec\cdot\nvec)>\sin60^\circ$)에만 1, 그 외엔 0에
가까운 매끄러운 시그모이드 문(門)으로 자기지지 면을 제외하고, $\eta_i$ 는 면 중심에서 빌드플레이트까지의
높이다. 이 게이트 규약은 TomoNV DLL·Cura \texttt{support\_angle} 과 동일하다(\S\ref{sec:method}).}
$S_g$ 는 실제 Cura 지지질량을 메쉬별 평균 Spearman $\mathbf{+0.80}$ 로 예측하며 \emph{헤드라인
18개 메쉬 전부에서 양}($95\%$ CI $[{+}0.74,{+}0.84]$ 가 $0$ 을 배제)이다. 이는 복셀 추정기
TomoNV($+0.46$)\footnote{TomoNV 열은 지지부피 엔진의 정수 오버플로 결함을 수정한 빌드로 전부
재계산했다. 수정 전 대형 유기 스캔(마네킹·드래곤·Happy·Lucy·Bunny)의 TomoNV 상관이 실제보다
낮게 나와 이 열 평균이 낮게 보고됐으나, 소형·기계부품 행과 $S_g$ 열·Cura 기준은 영향받지
않는다.}를 크게 앞서고, 게이트 없는 $L_{\mathrm{SFTF}}$($+0.26$)·$L_{\mathrm{SFTF}}+S$($+0.39$)
보다도 훨씬 높다. 특히 확장 10개 --- 유기 대형 스캔(마네킹·드래곤 100k면·Happy Buddha·Lucy·
\textbf{Nefertiti·간·신장})과 Thingi10k 기계부품 3종 --- 에서도 $S_g$ 는 전부 양이며, 이번에
추가한 유기 스캔 3종(Nefertiti $+0.90$, 간 $+0.82$, 신장 $+0.80$)이 헤드라인을 오히려 강화해
프리미티브에 국한된 결과가 아님을 보인다. 이 정량 순위의 \emph{정성적} 동반 그림을
그림~\ref{fig:g5landscape} 에 벤치마크 전체로 펼쳐 두었다: 세 방법의 (yaw,\,pitch) 지지비용
랜드스케이프를 메쉬마다 나란히 놓으면, 하드 SFTF 와 미분가능 SFTFsoft 의 지형이 거의 겹치는
(일치성 주장) 반면 물리 예측기 TomoNV 는 종종 다른 골짜기를 가리키는 것이 한눈에 드러난다.

\begin{figure}[p]
  \centering
  \includegraphics[width=\textwidth]{g5test_methods_landscape_grouped.png}
  \caption{g5test 5그룹 벤치마크 전체(38메쉬)에 걸친 세 빌드방향 예측기의 \emph{정성적}
  비교. 각 메쉬 행은 왼쪽부터 \textbf{[원본 형상 $\mid$ TomoNV 물리 지지질량 $\mid$
  하드 SFTF 비용 $J$ $\mid$ 미분가능 SFTFsoft 손실 $L$]} 이다. 오른쪽 세 패널은 각
  방법이 매기는 지지비용을 (yaw,\,pitch)$\in[0,360)^2$ 격자 위에 RdBu\_r 로 그린
  랜드스케이프로(붉을수록 고비용), 세 방법의 단위가 서로 달라(TomoNV 는 그램[g],
  SFTF 계열은 무차원 점수) \emph{각 패널을 자체 정규화}(패널별 min--max)했다 --- 따라서
  절대값이 아니라 지형의 \emph{모양}(어느 방향을 좋다/나쁘다 보는지)을 비교한다.
  $\times\,1$--$5$ 는 각 방법이 예측한 \emph{상위 5순위} 배향으로, 서로 다른 골짜기
  (basin)에 놓이도록 (yaw,\,pitch) 주기격자 위에서 비최소 억제(toroidal NMS)로 골라
  순위 번호를 붙였다: 전역 최소를 먼저 고른 뒤 그 주변 이웃(반경 ${\approx}$격자변$/6$,
  yaw$\cdot$pitch 두 축이 모두 $360^\circ$ 주기라 거리는 경계를 넘어 감긴다)을 억제하고
  다음 최소를 고르기를 반복한다 --- 단순히 최저값 $5$칸을 찍으면 전역 최소 주변에
  뭉치므로, 이렇게 해야 실제로 구별되는 후보 배향 $5$개가 나온다($\times\,1$ 이 전역
  최소=제1순위). 표~\ref{tab:cura}
  의 Spearman 이 수치로 말하는 것 --- 하드 $J$ 와 소프트 $L$ 의 강한 일치, 물리(TomoNV)
  충실도의 가변성 --- 이 지형으로도 보인다. 회전대칭 퇴화 형상(A2 구)이나 법선이 전
  각도에 퍼진 대형 스캔(E 그룹 일부)은 랜드스케이프가 거의 평탄해 자체 정규화가 미세
  변동을 잡음처럼 증폭하므로(본문의 ill-posed 논의 참조) 그 행들은 지형 대비가 약하게
  보이는 것이 정상이다. 이 그림은 예측 정확도의 \emph{정성} 보조 자료이며, 정량 결론은
  표~\ref{tab:cura} 가 담는다.}
  \label{fig:g5landscape}
\end{figure}

\textbf{순위검증이 ill-posed한 형상(정육면체·구·속빈상자)은 헤드라인에서 뺐다.} g5test 5그룹을
채우며 추가한 이 셋은 표에 투명하게 실었으나(전체 21메쉬 평균 $S_g$ $+0.67$), 헤드라인 18개에는
넣지 않는다. 이유는 \emph{순위 검증 자체가 성립하지 않는} 형상이기 때문이다: 구는 회전대칭이라
어느 방향으로 눕혀도 지지량이 $0.6$--$0.7$\,g 로 사실상 \emph{평탄}(슬라이서 양자화 폭 이내)해서
방향 간 순위를 매길 대상이 없고 --- 그래서 $S_g$($-0.14$)뿐 아니라 TomoNV($-0.00$)까지 모든 열이
잡음 수준이다. 정육면체는 12면 근퇴화 형상이고, 속빈상자는 내부 공동이 지지를 좌우해 \emph{표면}
법선만 보는 예측기(TomoNV 포함, 각각 $+0.22$·$+0.17$)가 원리적으로 무력하다. 이들은 게이트나
가중치를 재튜닝해 억지로 끌어올리지 않고 정직하게 표기하며(재튜닝은 본 논문 전반의 금지 원칙),
구·정육면체의 회전대칭 퇴화는 \S\ref{sec:results} 의 대칭 처리에서, 내부공동 한계는 형상최적화
한계절에서 다룬다.

표~\ref{tab:cura} 의 오른쪽 세 대조 열은 이 정확도의 원천이 무엇인지 --- 특히 SFTF
텐서와 완화 기계장치가 예측에 기여하는지 --- 를 격리한다. 먼저 게이트 항에 텐서 손실을
더하면($L_{\mathrm{SFTF}}{+}S_g$, 순위공간 등가중 합) 헤드라인 18메쉬 평균 상관이
$+0.80\to+0.58$ 로 오히려 \emph{내려간다}(메쉬별 상관쌍에 대한 Wilcoxon 부호순위
검정\footnote{짝지은 두 표본(여기서는 같은 메쉬 집합에서 잰 두 예측기의 메쉬별 상관)의
차이 중앙값이 0인지 확인하는 비모수 검정. 정규성 가정 없이 소표본에서 쓸 수 있다.}
$p=2\times10^{-5}$): 텐서 항은 실제 지지질량 순위를 벼리지 못하고 게이트 신호를
희석한다. 다음으로 하드 게이트 대조군 $S_g^{\mathrm{hard}}$\footnote{$S_g$ 의 모든
매끄러운 성분을 날카로운 극한으로 바꾼 것: softplus 오버행과 시그모이드 게이트는 정확한
지시함수 $-\mvec_i\cdot\nvec>\sin60^\circ$ 로, soft-min 바닥높이는 정확한 최소값으로.
즉 $S_g^{\mathrm{hard}}=\sum_i \mathbf{1}[-\mvec_i\cdot\nvec>\sin60^\circ]\,A_i\,\eta_i$.}
는 텐서도 수신면 어텐션도 어떤 완화도 쓰지 않는 순수 배열 연산 몇 줄인데, Cura 를 $S_g$
보다 오히려 약간 \emph{더 잘} 예측한다($+0.87$ 대 $+0.80$; 메쉬별 짝지은 차 $-0.07$,
Wilcoxon $p=0.003$). 따라서 예측 헤드라인은 게이트된 오버행 면적$\times$바닥까지
높이라는 \emph{슬라이서-게이트 물리}가 전부 견인하며, 미분가능성 자체는 평균 순위
충실도를 약 $0.07$ 만큼 오히려 깎는다. $S_g$ 와 $S_g^{\mathrm{hard}}$ 에는 적합(fit)
파라미터가 하나도 없으므로($\theta_c$ 는 대상 프로파일에서 읽는 값), 이 비교에는 학습이
없고 held-out 분리도 필요 없다. 완화가 사는 것은 정확도가 아니라 \emph{기울기}다:
$S_g^{\mathrm{hard}}$ 는 계단 게이트 합이라 이후의 빌드방향·형상 최적화를 구동할 수
없고, 아래 게이트 절제실험은 정확히 그 하드 극한에서 최적화가 붕괴함을 보인다. 즉
매끄러운 기계장치와 $L_{\mathrm{SFTF}}$ 자체의 역할은 예측이 아니라 최적화, 그리고 이전
SFTF 목적에의 충실도다.

\textbf{격차의 성분별 진단과 $S_g^{\mathrm{ste}}$ 열.} 하드 게이트가 앞서는 $0.07$ 의
격차를 성분별로 분해할 수 있다. 게이트 축부터 격리하면 두 기제가 보인다.
(i) \emph{번짐}: sharpness $24$ 의 시그모이드는 cos-공간($-\mvec\cdot\nvec$)에서
$10$--$90\%$ 전이폭이 ${\approx}0.18$ 이고, $\theta_c{=}60^\circ$ 에서는
$d\sin\theta/d\theta{=}\cos60^\circ{=}0.5$ 로 나뉘어 각도로 약 $21^\circ$ 의 애매 구간이
된다. 큰 평면 몇 개가 형상의 전부인 기계부품은 그 평면들이 통째로 임계각 근처에 걸리는
방향이 많아 이 부분 점수가 순위를 좌우하지만, 법선이 전 각도에 퍼진 유기 스캔은 평균
속에 상쇄된다. (ii) \emph{누설}: 시그모이드는 어디서도 정확히 $0$ 이 아니므로, 서포트가
정확히 $0$ g 인 다수의 방향(거의 자기지지 형상에서 48개 중 $15$--$22$개)에 가짜 부분
점수가 얹혀 동률 순위가 잡음화된다. 실제로 $S_g^{\mathrm{hard}}$ 골격
$\sum_i g(-\mvec_i\cdot\nvec)\,A_i\,\eta_i$ 에서 게이트 $g$ 만 바꿔 스윕하면(같은 캐시된
Cura 랜드스케이프), 유기 스캔은 어떤 게이트든 $+0.88$--$+0.89$ 로 평평한 반면
$L_{\mathrm{SFTF}}$ 실패 4종(원기둥·원뿔·D5·D9)은 시그모이드 $+0.82$ 대 하드 $+0.93$
이고, 임계 밖에서 정확히 $0/1$ 인 $C^1$ smoothstep 게이트($\pm0.02$--$0.05$)는 두 기제를
모두 제거해 실패 4종을 하드 수준($+0.90$--$+0.93$)으로 $3$--$8^\circ$ 의 기울기
대역과 함께 회복한다. 그러나 게이트가 격차의 전부는 아니다. 표~\ref{tab:cura} 의
$S_g^{\mathrm{ste}}$ 열은 \emph{풀} $S_g$ 에서 \emph{게이트만} straight-through
게이트(\S\ref{sec:consistency}; 순전파 하드, 역전파 시그모이드)로 바꾼 것 --- 즉
``게이트만 하드''(gate-only-hard) 변형 --- 인데, 헤드라인 평균 $+0.78$ 로 $S_g$($+0.80$;
짝지은 차 $-0.02$, Wilcoxon $p{=}0.09$)와 통계적으로 동급에 머물고 $S_g^{\mathrm{hard}}$($+0.87$;
짝지은 차 $-0.09$, $p{=}8\times10^{-6}$)에는 못 미친다. $S_g^{\mathrm{ste}}$ 와
$S_g^{\mathrm{hard}}$ 는 게이트가 같으므로(순전파 기준 둘 다 하드 지시함수), 이 $-0.09$
는 온전히 \emph{게이트 이외의} 완화 성분 --- softplus 오버행 크기 가중과 soft-min
바닥높이 --- 의 몫이다. 방향을 확정하는 추가 대조로, 하드 게이트에 \emph{정확한} 오버행
크기 인자와 정확한 바닥높이를 쓴 골격
$\sum_i \mathbf{1}[\cdot]\,\max(0,-\mvec_i\cdot\nvec)\,A_i\,\eta_i$ 는 $+0.87$ 로
$S_g^{\mathrm{hard}}$ 와 같다 --- 오버행 크기 인자 자체는 무해하며, 해로운 것은 그
\emph{완화}(softplus 의 잔여 바이어스와 soft-min 이 $\eta$ 에 더하는 방향 의존
오프셋)다. 처방은 역할별로 갈린다: \emph{평가·순위}에는 완화가 전혀 필요 없으므로
$S_g^{\mathrm{hard}}$ 를 쓰고, \emph{미분가능 목적 안의 게이트}는 STE 가 최적화 성능
손실 없이 게이트 축의 편향을 없앤다(형상최적화 절의 게이트 처방 문단).

\textbf{핵심은 슬라이서 자신의 임계각($60^\circ$)에서 게이트}하는 것이다. 게이트 없는 항은 거의
자기지지인 형상(원기둥·원뿔·U-브래킷·C-클램프; 48방향 중 $15$--$22$개가 서포트 ${\approx}0$)에서
순위가 동률·잡음에 지배돼 무너지지만 --- 이 형상들에서는 \emph{보정 기준이던} TomoNV 까지 음의
상관을 보인다(원기둥 $-0.20$, U-브래킷 $-0.45$) --- 슬라이서의 $60^\circ$ 컷오프로 게이트하면 바로 그
형상들이 $+0.66$--$+0.87$ 로 살아난다. 게이트 절제실험이 이를 분리해 보여준다: 게이트는 Cura
일치도를 메쉬평균 $+0.45$--$+0.74$ 만큼 \emph{올리지만}, 같은 게이트가 TomoNV 와의 일치도는 오히려
$-0.37$--$-0.60$ 만큼 \emph{낮춘다}. 모순이 아니다 --- $60^\circ$ 자기지지 컷오프는 실제 슬라이서가
토패스로 적용하는 바로 그 규칙이라, 게이트한 항은 \emph{실제 슬라이서}에 정합하고, 게이트 없는
매끄러운 항은 복셀 \emph{추정기}(TomoNV)에 정합한다(게이트 없는 $S$ 는 TomoNV 일반화에서 $+0.61$,
\S\ref{sec:results}). 즉 미분가능 손실을 슬라이서 임계각에서 게이트하면, 훨씬 무거운 복셀 추정기보다
\emph{실제} 생산 슬라이서를 더 잘 예측한다.

\textbf{프로파일 간 이식성(단일 프로파일 일반화).} 게이트 각 $\theta_c$ 는 맞춰 넣은 상수가 아니라
\emph{대상 슬라이서 프로파일에서 읽어 오는} 파라미터다(DP103 은 $60^\circ$). 따라서 다른 프로파일로의
이식은 손실을 재튜닝하는 것이 아니라 \emph{그 프로파일의 오버행 임계각으로 다시 게이트}하는 것으로
끝난다. 대상 프로파일의 각도를 그대로 채택하는 이 규약은 저자의 SFTF 원고 시리즈 전체가
공유하며, generic FDM 프로파일을 대상으로 하는 자매 논문 SFTFCluster 는 같은 규약에 따라
$45^\circ$ 에서 게이트한다. 이 선택에 결과가 취약하지 않음을 보이기 위해, Cura 기준 랜드스케이프는 DP103 $60^\circ$ 로
고정한 채 $S_g$ 의 게이트 각만 $\theta_c\in\{45,50,55,60\}^\circ$ 로 바꿔 재게이트했다
(그림~\ref{fig:thetac}). 메쉬별 평균 Spearman 은 $55^\circ$·$60^\circ$ 에서 $+0.79$ 로 같고,
$50^\circ$ 에서 $+0.77$, $15^\circ$ 나 어긋난 $45^\circ$ 에서도 $+0.71$ 로 --- 모든 경우 복셀 추정기
TomoNV($+0.38$)와 게이트 없는 변형($+0.26$--$+0.40$)을 여전히 크게 앞선다. 완만한 열화는 순위 신호가
임계각 바로 위에 걸린 \emph{거의 자기지지}인 프리미티브에 집중된다($\theta_c$ 를 $60^\circ\to45^\circ$ 로
낮출 때 원기둥 $+0.87\to+0.21$, C-클램프 $+0.77\to+0.49$). 반면 유기 대형 스캔은 거의 평평하거나
오히려 살짝 오른다(Lucy $+0.90\to+0.94$, Bunny $+0.85\to+0.89$). 요컨대 새 슬라이서 프로파일 적용은
그 프로파일의 오버행 각을 읽어 오기만 하면 되고, 그 각의 어느 정도 오차에도 예측기는 견딘다.

\begin{figure}[t]
  \centering
  \includegraphics[width=0.66\linewidth]{demo_sftf_thetac_sensitivity.png}
  \caption{$S_g$ 의 게이트 각 민감도(15 메쉬, 48 방향; 실제 Cura 기준은 DP103 $60^\circ$ 프로파일로
  고정). 회색 선은 메쉬별 Spearman, 초록 선은 평균(부트스트랩 $95\%$ 신뢰구간 띠), 점선은 DP103
  임계각이다. $\theta_c$ 를 $\pm5^\circ$ 바꿔도 평균 일치도는 사실상 그대로이며, $15^\circ$ 어긋난
  경우에도 TomoNV·게이트 없는 기준선보다 훨씬 높게 유지된다.}
  \label{fig:thetac}
\end{figure}

\textbf{현대 슬라이서로의 이식.} 게이트 각 재조정(위)에 더해, 예측이 \emph{다른 세대의}
슬라이서로도 전이되는지 직접 확인했다. 네 메쉬(원환·후크·파이프엘보·Thingi D9)를 \emph{같은}
48개 Fibonacci 방향에서 현행 \textbf{UltiMaker CuraEngine 5.13}(기본 $0.4$\,mm PLA, 선형 서포트,
$60^\circ$ 오버행)으로 다시 슬라이싱해 서포트 질량을 측정했다. $S_g$ 는 이 현대 슬라이서의 방향별
서포트 순위를 메쉬평균 Spearman $\mathbf{+0.68}$ 로 예측하며(원환·후크·파이프엘보 $+0.77$--$+0.84$,
기계부품 D9 는 레거시에서와 같은 이유로 $+0.33$ 로 약함), 무엇보다 \emph{레거시(15.04)와 현대(5.13)
두 엔진이 방향 순위를 메쉬평균 $\mathbf{+0.90}$ 으로 거의 동일하게} 매긴다. 즉 본문의 DP103/15.04
검증은 특정 레거시 엔진의 인공물이 아니라 세대를 가로질러 유지되는 물리이며, 새 프로파일·엔진에는
그 프로파일의 오버행 각으로 재게이트하면 된다는 이식성 논증을 실측으로 뒷받침한다.

\textbf{메쉬 해상도와 coarse-to-fine 평가(중요).} 지지부피 항 $S$ 는 면별 오버행을 적분하므로,
입력 메쉬를 데시메이션하면 합산 대상인 미세 오버행이 뭉개져 변별력이 떨어진다. 실제로 Bunny 의
$S$ 상관은 프록시 면 수를 $6$k$\to$$50$k 로 높이면 $+0.58\to+0.83$ 로 오른다
(부록~\ref{app:mesh-mg}). 본 결과는 SFTF 손실이 단순한 mesh-independent scalar 가 아니라,
표면 이산화가 보존하는 overhang/height 분포에 의존하는 적분량임을 보여준다. 따라서 decimated
mesh 는 최종 물리 평가를 대체하기보다 coarse-to-fine 후보 축소에 사용하는 것이 적절하다. Bunny
$15$k--$30$k--$69$k case study 에서 $15$k top-$4$ $\to$ $30$k top-$2$ $\to$ $69$k top-$2$ 스케줄은
full-mesh 최적 방향을 유지하면서 $24$방향 sweep 비용을 약 $6.0\times$ 줄였지만, $15$k 단독
최적 방향은 full 최적 방향과 $43.7^\circ$ 어긋났다. 따라서 SFTF--슬라이서 일치도는
데시메이션하지 않은(또는 $\ge\!30$k 면) 메쉬에서 평가하고 면 수를 명시한다. 면-면 라우팅의
$O(F^2)$ 메모리는 후보 탐색을 행 블록으로 청크해($\sim\!60$\,GB$\to\sim\!2$\,GB) 회피했다.

\textbf{end-to-end 최적화.} 게이트는 \emph{랭킹}뿐 아니라 \emph{최적화}에도 도움이 된다. 빌드방향을
각 손실로 최적화한 뒤 실제 Cura 지지질량 백분위(코어 8 메쉬 평균, $0{=}$ 최적)를 보면,
$L_{\mathrm{SFTF}}+S_g$ 가 $0.232$ 로 가장 좋아 기본 $L_{\mathrm{SFTF}}$($0.242$)와 게이트 없는
$+S$($0.240$)를 모두 앞선다. 즉 슬라이서 임계각에서 게이트한 물리항은 실제 Cura 지지재가 적은 방향으로
더 잘 이끈다. 종합하면, 미분가능 SFTF 손실을 생산 슬라이서의 임계각에서 게이트하면 \emph{상관}($+0.80$)과
\emph{최적화}($0.232$) 양쪽에서 복셀 추정기를 능가하는, 본 논문에서 가장 강한 물리 검증이 된다.

\begin{figure}[t]
  \centering
  \includegraphics[width=0.49\linewidth]{demo_sftf_vs_slicer.png}\hfill
  \includegraphics[width=0.49\linewidth]{demo_sftf_slicer_opt.png}
  \caption{legacy CuraEngine 15.04 / DP103 PLA support-only 검증(그림은 코어 8 메쉬, 48 빌드방향,
  $60^\circ$; g5test 확장(헤드라인 18메쉬/전체 21)은 표~\ref{tab:cura}).
  좌: 실제 Cura 지지질량과의 메쉬별 평균 Spearman 상관. 슬라이서의 $60^\circ$ 임계각에서 게이트한
  바닥높이 항 $S_g$ 가 $\mathbf{+0.83}$(코어 8 메쉬 전부 양, CI $[{+}.77,{+}.89]$)으로 복셀 추정기 TomoNV
  ($+0.22$)와 게이트 없는 $L_{\mathrm{SFTF}}$($+0.12$)·$L_{\mathrm{SFTF}}+S$($+0.25$)를 크게 앞선다.
  게이트가 없으면 거의 자기지지인 형상(원기둥·원뿔·브래킷, 서포트 ${\approx}0$)에서 TomoNV 까지
  무너지지만, 슬라이서 임계각에서 게이트하면 그 형상들까지 살아난다. 우: 경사하강으로 최적화한
  빌드방향의 실제 Cura 지지질량 백분위(낮을수록 좋음). $L_{\mathrm{SFTF}}+S_g$($0.232$)가 기본
  $L_{\mathrm{SFTF}}$($0.242$)와 게이트 없는 $+S$($0.240$)를 앞서, 게이트한 물리항이 \emph{상관}과
  \emph{최적화} 양쪽에서 최선임을 보인다.}
  \label{fig:slicer}
\end{figure}

\textbf{동일 예산 배향 탐색: 샘플링 대 기울기 정련.} 빌드방향 탐색 자체는 2차원 문제이므로,
``기울기가 이 문제 \emph{안에서도} 이득인가, 아니면 아래에서 다룰 고차원(형상최적화)에서만
이득인가''를 직접 실험으로 확인했다. 총 평가 예산\footnote{목적함수를 한 번 계산하는 것을
평가 1회로 센다. 기울기 스텝은 역전파 비용까지 치면 실제로는 약 2배 비싸지만 여기서는
후하게 1회로 계산했다 --- 즉 이 계산법에서 샘플링이 이기면 그 결론은 보수적으로도 성립한다.}
$B\in\{8,16,48\}$ 를 고정하고, (a) Fibonacci 방향 $B$개를 순수 샘플링하는 전략과
(b) $B/2$개만 샘플링한 뒤 최고점에서 Adam 기울기 정련을 $B/2$ 스텝 수행하는 혼합 전략을
같은 $L_{\mathrm{SFTF}}+S_g$ 목적으로 비교하고, 각 전략이 고른 최종 방향을 실제 Cura 로
슬라이스했다(그림~\ref{fig:equalbudget}). 평균 백분위로는 두 전략이 사실상 동률이고
메쉬별 승패도 엇갈린다($B{=}8/16/48$ 에서 샘플링/혼합 $0.41/0.33$, $0.32/0.39$,
$0.31/0.32$) --- 본문의 주장대로 2차원 배향 landscape 는 샘플링만으로 충분히 다룰 수 있다.
그러나 실제 그램 수로 보면 혼합 전략이 모든 예산에서 샘플링과 같거나 낫고, $B{=}48$ 에서는
48방향 oracle 대비 초과 지지질량을 절반 이하로 줄인다($3.16\to1.40$\,g). 이득의 근원은
지지량 $0$ 인 자세의 골짜기가 매우 좁아 고정 샘플 격자가 골짜기를 건너뛰는 준퇴화 형상
(원기둥·U-브래킷·C-클램프)이다 --- 마지막 $10$--$15^\circ$ 의 국소 정련이 골짜기 안으로
걸어 들어간다. 반대로 대리 손실의 최소점이 Cura 의 최소점과 어긋난 메쉬(원뿔·후크)에서는
정련이 오히려 조금 나빠질 수 있다. 요컨대 배향 탐색만이라면 기울기가 \emph{필수}는 아니지만
같은 예산에서 손해도 아니며, 미분가능성의 결정적 가치는 샘플링이 닿을 수 없는
표~\ref{tab:shapeopt-multi} 의 정점공간 형상최적화에 있다.

\begin{figure}[t]
  \centering
  \includegraphics[width=0.88\linewidth]{demo_equal_budget.png}
  \caption{동일 예산 배향 탐색(코어 8 메쉬, 목적 $L_{\mathrm{SFTF}}+S_g$). 같은 평가 횟수
  $B$ 에서 순수 Fibonacci 샘플링과 ``$B/2$ 샘플 + 최고점에서 $B/2$ 기울기 정련''을 비교하고,
  각 전략의 최종 방향을 legacy CuraEngine 15.04 / DP103 으로 슬라이스했다. 좌: 48방향 실제
  지지질량 landscape 백분위($0{=}$최적) --- 사실상 동률. 우: 48방향 oracle 대비 초과
  지지질량 --- 기울기 정련이 모든 예산에서 같거나 낫고 $B{=}48$ 에서 초과분을 절반 이하로
  줄인다.}
  \label{fig:equalbudget}
\end{figure}

\section{교차 슬라이서 전이: PrusaSlicer}\label{sec:crossslicer}

Cura 검증은 한 가지 질문을 남긴다. 우리가 본 것은 \emph{CuraEngine 의} 성질인가, 아니면
\emph{인쇄 공정의} 성질인가? 앞 문단의 Cura~5.13 이식이 같은 계보의 다른 세대를 확인했다면,
이번에는 아예 \textbf{코드베이스도 서포트 생성기도 다른} 슬라이서로 예측 실험을 통째로
반복한다: PrusaSlicer~2.9.6(콘솔). 프로파일은 고정본이고, 수평 기준 오버행 임계각 $30^\circ$ 가
본문과 같은 $\theta_c=90^\circ-30^\circ=60^\circ$ 관례를 재현한다. 새 슬라이서에 맞춰 조정한 것은
하나도 없다: $\theta_c$ 는 이번에도 \emph{선언된 프로파일에서 읽어 오고}, 두 예측자는 모두
맞춤 계수가 없으며(fit-free), 같은 48개 Fibonacci 방향과 같은 메쉬를 그대로 쓴다. 지지질량은
Cura 경로와 동일한 high-water-mark 방식으로 방출된 G-code 에서 집계한다.

21개 메쉬 전체에서 하드 게이트 대조군 $S_g^{\mathrm{hard}}$ 는 실제 PrusaSlicer 지지질량에
대해 메쉬평균 Spearman $\mathbf{+0.73}$(부트스트랩 $95\%$ CI $[+0.62,+0.82]$), $S_g$ 는
$+0.62$($[+0.50,+0.73]$)를 얻고, 21개 중 20개에서 양이다. 유일한 예외인 구(sphere)는 회전대칭
때문에 지지 landscape 가 거의 평탄해, 그에 대한 순위상관은 예측이 아니라 격자화 잡음을
재는 셈이 된다. 두 가지 관찰이 무엇이 전이되는지 한정한다. 첫째, \emph{두 슬라이서끼리의
합의} 자체 --- 같은 방향들에 대한 $\mathrm{Spearman}$(Cura, Prusa) --- 가 평균 $+0.70$ 이다.
즉 맞춤 없는 게이트는 \emph{한 번도 본 적 없는} 슬라이서를, 다른 슬라이서가 그 슬라이서를
맞히는 만큼 맞힌다. 이 값이 이 비교의 자연스러운 상한선이다. 정육면체와 속 빈 상자에서는
두 슬라이서가 서로 사실상 불일치하는데도($+0.05$, $-0.03$) 게이트는 PrusaSlicer 를 여전히
잘 따라간다($+0.83$, $+0.85$) --- 예측자가 CuraEngine 의 고유한 습성에 맞춰진 것이 아님을
보여준다. 둘째, Cura 에서 발견한 순서 $S_g^{\mathrm{hard}}>S_g$ 가 PrusaSlicer 에서도 같은
크기로 재현된다(평균 격차 $0.11$; 21개 짝지은 메쉬별 상관에 대한 Wilcoxon 부호순위
$p=1.6\times10^{-4}$). 소프트 오버행·소프트 바닥 항이 순위를 가장 많이 희석하는 D9 사례도
포함해서 그렇다. 하드 게이트 대조군의 결론은 그대로 전이된다: 예측은 두 슬라이서 모두에서
게이트 물리가 견인하며, 미분가능성은 다시 한 번 작고 일관된 만큼의 순위 충실도를 대가로
치른다.

\begin{table}[H]
  \centering
  \caption{PrusaSlicer~2.9.6 로의 교차 슬라이서 전이(고정 프로파일, $\theta_c=60^\circ$ 를
  프로파일에서 읽음; 48방향; G-code 기반 support-only 질량). 맞춤 없는 예측자들의 실제
  PrusaSlicer 지지질량에 대한 메쉬별 Spearman 과, 자연스러운 상한선인 두 슬라이서 사이의
  합의 $\mathrm{Spearman}$(Cura, Prusa). 구(sphere) 행은 퇴화 대조군이다: 거의 평탄한
  landscape 에는 순위 매길 신호가 없다. 실패한 슬라이스($1{,}008$ 중 9개 --- 모서리로 선
  방향에서 첫 레이어가 비는 경우이며 그중 5개가 원뿔)는 메쉬별로 제외했고, ``유효 방향''
  열이 남은 방향 수다.}
  \label{tab:crossslicer}
  \small
  \begin{tabular}{lrrrr}
    \toprule
    메쉬 & $S_g^{\mathrm{hard}}$ & $S_g$ & Cura$\sim$Prusa & 유효 방향 \\
    \midrule
    정육면체 (cube)     & $+0.83$ & $+0.75$ & $+0.05$ & 47/48 \\
    구 (sphere)         & $-0.04$ & $-0.10$ & $+0.59$ & 48/48 \\
    원기둥 (cylinder)   & $+0.94$ & $+0.85$ & $+0.96$ & 48/48 \\
    원뿔 (cone)         & $+0.91$ & $+0.83$ & $+0.95$ & 43/48 \\
    원환 (torus)        & $+0.74$ & $+0.89$ & $+0.83$ & 48/48 \\
    U-브래킷            & $+0.83$ & $+0.75$ & $+0.56$ & 47/48 \\
    후크 (hook)         & $+0.90$ & $+0.83$ & $+0.92$ & 48/48 \\
    C-클램프            & $+0.87$ & $+0.77$ & $+0.70$ & 47/48 \\
    파이프엘보          & $+0.97$ & $+0.95$ & $+0.98$ & 48/48 \\
    속 빈 상자          & $+0.85$ & $+0.71$ & $-0.03$ & 47/48 \\
    Bunny\_69k          & $+0.76$ & $+0.65$ & $+0.80$ & 48/48 \\
    manikin             & $+0.68$ & $+0.51$ & $+0.75$ & 48/48 \\
    dragon\_100k        & $+0.61$ & $+0.48$ & $+0.63$ & 48/48 \\
    happy\_50k          & $+0.51$ & $+0.35$ & $+0.68$ & 48/48 \\
    lucy\_50k           & $+0.32$ & $+0.17$ & $+0.45$ & 48/48 \\
    nefertiti\_100k     & $+0.61$ & $+0.47$ & $+0.67$ & 48/48 \\
    liver\_19k          & $+0.88$ & $+0.66$ & $+0.90$ & 48/48 \\
    kidney\_12k         & $+0.96$ & $+0.86$ & $+0.94$ & 48/48 \\
    D1\_37009           & $+0.79$ & $+0.73$ & $+0.85$ & 48/48 \\
    D5\_37095           & $+0.82$ & $+0.71$ & $+0.82$ & 48/48 \\
    D9\_37415           & $+0.56$ & $+0.24$ & $+0.74$ & 48/48 \\
    \midrule
    평균 (21)           & $+0.73$ & $+0.62$ & $+0.70$ & \\
    평균 (구 제외)      & $+0.77$ & $+0.66$ & $+0.71$ & \\
    \bottomrule
  \end{tabular}
\end{table}

\section{손실항의 활용}
\textbf{(1) 빌드방향 최적화.} $V$ 고정, $\nvec$ 만 최적화. SFTF의 512방향 구면샘플 + 콘
정련을 \emph{여러 시드의 경사하강 + 담금질}로 대체한다.
\textbf{(2) 생성/위상 형상 최적화.} $L=L_{\text{형상}}+\lambda\,L_{\mathrm{SFTF}}(V,\nvec^\ast)$
로 두고 $V$(또는 형상 생성기 파라미터)로 역전파하여 \emph{자기지지} 경향의 형상을 유도한다
(그림~\ref{fig:shapeopt} 의 구$\to$teardrop 변형으로 검증).
\textbf{(3) 신경망 학습.} 메쉬 그래프(면=노드, 면 인접=엣지)를 입력받아 방향을 예측하는
GNN을 \emph{예측 방향의 $L_{\mathrm{SFTF}}$ 최소화}로 라벨 없이(self-supervised) 학습할 수 있다
(그림~\ref{fig:gnn} 에서 메쉬 단위 leave-one-out 으로 검증).

\paragraph{회전대칭 퇴화형 처리.} 단일 최적 방향 $\nvec^\ast$ 는 방향 손실 landscape $L(\nvec)$ 의
최소점이 \emph{고립}되어 있을 때만 의미가 있다.\footnote{즉 그 방향에서 조금만 벗어나도 손실이
오르는 뚜렷한 골짜기가 있어야 한다. 골짜기가 없으면(평평하거나 띠 모양) 경사하강은 아무 방향에나
멈춘다.} 구(sphere)는 \emph{모든} 방향이 같으므로 최적해가 구면 $S^2$ 전체이고, 축대칭 부품(원기둥·
원뿔·원환)은 대칭축 둘레로 한 \emph{원}(circle)이 모두 같다(1-매개변수 족). 이런 형상에서도 경사하강은
\emph{어떤} $\nvec^\ast$ 를 내놓지만 그것은 난수 씨앗이 만든 임의의 값일 뿐이며 — 씨앗마다 구면 전체에
($160^\circ$ 이상) 흩어진다. 우리는 $L$ 의 대칭을 직접 분류해 이를 해결한다: 피보나치 방향들에서 $L$ 을
표본화해, landscape 가 거의 평평하면(상대 산포 $\mathrm{CV}<0.02$) \emph{등방}(isotropic)으로 부르고,
그렇지 않으면 $L$ 의 2차 방향 이방성에서 후보 축을 제안한 뒤 $L$ 이 그 축에 대한 극각에만 의존할
때에만(축각 코사인 $\cos\angle(\nvec,\mathrm{axis})$ 에 대한 저차 적합이 분산의 $0.85$ 이상을 설명) \emph{축대칭}
으로 받아들인다(이 극각붕괴 검정은 약한 이방성의 generic 형상이 흉내낼 수 있는 단순 고윳값 간격보다
훨씬 안정적이다). g5 집합에서 이는 구를 등방($\mathrm{CV}=0.009$), 원기둥·원뿔·원환을 축대칭(축을
$2^\circ$ 이내로 복원, $R^2_{\mathrm{axis}}=0.90$--$1.00$)으로, 그리고 약한 이방성의 스탠퍼드 버니
($R^2_{\mathrm{axis}}=0.54$)를 포함한 모든 방향성 부품을 generic 으로 분류한다(그림~\ref{fig:symmetry}).
그러면 최적화기는 임의의 한 방향 대신 최적해 \emph{집합}(점·원·구면)의 대칭을 보고한다. 나아가 축대칭
부품에 대해서는 손실이 의존하는 \emph{단 하나의} 극각에 대해 손실을 최소화해 그 원을 특정한다(그림~\ref{fig:tilt})
— 방향 탐색이 1차원으로 줄어든다. 원기둥에서는 이것이 \emph{축을 따라 세우는} tilt($\mathrm{tilt}^\ast{=}0^\circ$)
를, 원환에서는 적도쪽 $90^\circ$ 를 돌려주며, 최적점에서의 방위각 방향 손실 산포(여기서 ${<}10^{-3}$)는
축대칭 환원이 타당했는지에 대한 점검 역할을 겸한다. 끝으로 이 극각붕괴 점수는 generic 으로 남는
형상에도 유용한 \emph{연속적} 근사 축대칭도다: 후크·C-클램프·사각관은 뚜렷한 유사축(pseudo-axis)에 대해
$R^2_{\mathrm{axis}}=0.66$--$0.77$ 을 받는데 — 손실 변동의 대부분이 그 축에 대한 극각으로 설명되므로
최적해가 얕은 근원형(near-circular) 골짜기가 되고 따라서 $\nvec^\ast$ 의 \emph{방위각}이 약하게만 구속된다
— 반면 정육면체($0.04$)와 파이프-엘보($0.30$)는 날카롭게 고립된 최적해를 가진다. 이 정도를 함께 보고하면
generic 의 $\nvec^\ast$ 를 얼마나 신뢰할지 알 수 있다.

\begin{figure}[t]
  \centering
  \includegraphics[width=0.66\linewidth]{demo_sftf_symmetry.png}
  \caption{방향 손실 landscape 로부터 회전대칭 퇴화형 검출. 각 점은 한 빌드방향에서의 미분가능 SFTF
  지지손실로, \emph{검출된} 대칭축과 이루는 각의 코사인에 대해(평균 대비 상대편차로) 그렸다. 축대칭
  원기둥(초록)은 하나의 곡선으로 모이고($R^2_{\mathrm{axis}}=0.95$), 구(회색)는 거의 평평한 띠이며
  ($\mathrm{CV}=0.009$: 모든 방향이 동등), generic 형상(버니, 빨강)은 흩어진다($R^2_{\mathrm{axis}}=0.54$).
  분류기는 퇴화형에서 경사하강이 내놓는 임의의 $\nvec^\ast$ 대신 최적해 집합(구·원·고립점)의 대칭을
  반환한다.}
  \label{fig:symmetry}
\end{figure}

\begin{figure}[t]
  \centering
  \includegraphics[width=0.66\linewidth]{demo_sftf_tilt.png}
  \caption{축대칭 형상의 최적 \emph{tilt} 보고. 대칭축이 검출되면 방향 탐색은 손실이 의존하는 단 하나의
  극각으로 환원된다: 각 곡선은 빌드방향과 축이 이루는 tilt 에 대한 (방위각 평균) SFTF 손실이고, 별표는
  최소 tilt 를 나타낸다(최적해는 그 tilt 의 방향들이 이루는 원 전체다). 원기둥은 \emph{축을 따라}
  세우는 것이($\mathrm{tilt}^\ast{=}0^\circ$), 원환·원뿔은 적도 부근($90^\circ$/$94^\circ$)이 최적이다.
  탐색을 이 1차원 곡선으로 줄이면 전체 구면 스캔을 대체하고 임의의 한 방향 대신 최적해 집합 전체를
  돌려준다.}
  \label{fig:tilt}
\end{figure}

\section{한계: 형상최적화 결과는 슬라이서에 특이적이다}\label{sec:shapeopt-transfer-limit}

한 문장으로 요약하면 이렇다. 표~\ref{tab:shapeopt-multi} 의 ``지지재 $-96\%$--$-100\%$ 제거''는
\emph{Cura 가 청구하는} 지지재를 제거한 것이고, 슬라이서를 바꾸면 그 성과가 거의 사라진다.

표~\ref{tab:shapeopt-multi} 는 지지질량을 슬라이서 \emph{하나}로만 측정했다.
절~\ref{sec:crossslicer} 은 게이트 물리가 CuraEngine 의 특성이 아니라 공정의 특성이라고
논증했다 --- \emph{예측}이, 예측자가 한 번도 본 적 없는 슬라이서로 전이된다는 근거로. 그렇다면
\emph{최적화된 형상} 역시 바로 그 슬라이서에서 지지재 없이 인쇄되는지가 자연스러운 검증이 된다.
그래서 같은 전후 메쉬를
PrusaSlicer~2.9.6(콘솔)으로 다시 슬라이스했다. 프로파일은 고정본이며 수평 기준 오버행 임계각
$30^\circ$ 가 본문과 같은 $\theta_c{=}60^\circ$ 관례를 재현한다\footnote{Prusa 의 임계각 $T$ 는
\emph{수평면} 기준 슬로프이고 본문의 게이트각 $\theta_c$ 는 \emph{수직} 기준이므로
$\theta_c=90^\circ-T$ 이다. 따라서 $T{=}30^\circ$ 가 곧 $\theta_c{=}60^\circ$ 로, DP103/Cura 와
같은 관례다.}. 새 슬라이서에 맞춰 조정한 것은 아무것도 없다. 결과는 전이되지 않으며,
그 이유가 시사적이므로 온전히 밝힌다(표~\ref{tab:shapeopt-prusa}).

결과는 둘로 나뉜다. 하나는 \textbf{확증}이다. PrusaSlicer 는 \emph{대조군} 지정을 독립적으로
재현해, 원뿔·U-브래킷·C-클램프의 최적화 \emph{전} 지지질량을 정확히 $0.00$ g 으로 청구한다.
이 세 행은 두 슬라이서 모두에서 $z$-up 에 지지재가 실제로 불필요한 부품이 맞고,
표~\ref{tab:shapeopt-multi} 의 U-브래킷 이상치($0.24\to0.39$ g)가 실제 비용이 아니라 TomoNV
복셀 추정기의 노이즈였음도 확인된다. 다른 하나는 \textbf{실패}다. 지지재가 필요한 6개 메쉬 중
둘(icosphere·원환)은 최적화 후 형상이 아예 슬라이스되지 않는다 --- PrusaSlicer 가 ``첫 레이어가
비어 있다''\footnote{첫 레이어(first layer)는 바닥판 위에 최초로 압출되는 한 층이다. 부품이 바닥에
점으로만 닿으면 이 층의 단면적이 $0$ 이 되어 인쇄를 시작할 수 없다.}며 중단한다. 슬라이스되는
나머지 4개에서 지지질량 합계는 $37.9\to36.9$ g, 즉 $-2.7\%$ 에 그친다 --- 같은 변형에 대해
CuraEngine 이 보고하는 $-98.4\%$ 와 대비된다. Bunny 는 개선에 실패하는 정도가 아니라 실제
지지질량이 $+59\%$ \emph{증가}한다($14.3\to22.7$ g). 공중 오버행 면적은 $-96\%$ 줄었는데도
($1523\to66$ mm\textsuperscript{2}) 그렇다. 최적화된 무지지 대조군 둘도 PrusaSlicer 에서는
지지재가 새로 생긴다($0.00\to1.29$ g, $0.00\to2.21$ g). Cura 는 여전히 $0$ 으로 본다.

원인은 \emph{목적함수가 청구하는 것}과 \emph{슬라이서가 청구하는 것}의 불일치이고, 빈 첫 레이어가
그 증상을 가장 선명하게 드러낸다. 본 목적함수는 \textbf{면 각도} 기준이다: 어떤 면이 임계각
$\theta_c$ 만 넘기면 그 \emph{아래에 무엇이 있든} 비용이 $0$ 이다. 뭉툭한 형상에서 이 기준을
만족시키는 가장 싼 방법은 밑면을 뾰족하게 깎아 바닥판에 점으로 만나게 하는 것이다 ---
그림~\ref{fig:shapeopt} 의 고전적인 물방울(teardrop) 형상이 정확히 이 수(手)이고, icosphere 의
오버행이 $0$ 에 도달하는 이유도 이것이다. 그러나 수학적인 점은 첫 레이어가 될 수 없다.
G-code 를 직접 열어 보면 같은 사실이 정량적으로 확인된다: PrusaSlicer 가 원환에 생성하는 지지재
압출은 \emph{전부 부품 바닥}에 있다(최적화 전 $z=0.20$--$1.20$ mm, 후 $0.20$--$4.40$ mm).
PrusaSlicer 는 오버행 면을 받치는 것이 아니라, 바닥에 간신히 닿은 부품 \emph{아래의 쐐기꼴 공극을
메우는} 중이다. 그리고 밑면을 가파르게 깎을수록 그 공극은 \emph{더 높아진다}. 목적함수는 실제
비용을 올리는 바로 그 변형에 보상을 준다.

이는 높이 가중치의 아티팩트가 아니라 면 기반 정식화에 내재한 문제다. 가중치 $(1+\eta/D)$ 는
바닥판에 \emph{닿아 있는} 면에도 --- 이미 바닥판이 받쳐 주는데도 --- 면적을 전액 청구하므로,
바닥값을 없애 $\eta/D$ 로 바꾸는 것이 자연스러운 수리안이다. 그러나 도움이 되지 않는다.
수리한 가중치에서 원환의 밑면은 수평 기준 $35^\circ$ 이내의 하향면이 하나도 남지 않는데
--- 모든 하향면이 $30^\circ$ 임계를 여유 있게 통과한다 --- 지지질량은 오히려 $2.895\to2.969$ g 으로
늘어난다. 두 가중치에서 모두 슬라이스되는 4개 메쉬에서도 수리안이 더 나쁘다(U-브래킷
$1.29\to3.35$, C-클램프 $2.21\to2.76$, 파이프엘보 $7.16\to8.75$, Bunny $22.75\to26.68$ g).
\emph{오버행 $0$} 과 \emph{지지재 $0$} 은 서로 다른 조건이고, 우리 기울기가 볼 수 있는 것은
전자뿐이다.

따라서 주장의 범위를 한정한다. 표~\ref{tab:shapeopt-multi} 가 확립하는 것은, 샘플링이 닿을 수 없는
수만 자유도의 설계공간에서 정점 기울기가 \emph{CuraEngine 15.04/DP103 이 청구하는} 지지재를
사실상 전부 제거할 수 있다는 사실이다. 그 수치들은 측정값이며 유효하다. 반면 확립하지 못하는 것
--- 그리고 우리가 철회하는 것 --- 은 그 결과 형상이 슬라이서 일반에 대해 자기지지이거나, 출력된
그대로 제조 가능하다는 주장이다. 예측 헤드라인은 영향받지 않는다: $S_g$ 와 $S_g^{\mathrm{hard}}$ 에는
형상최적화가 개입하지 않으며 순위는 PrusaSlicer 로 그대로 전이된다(절~\ref{sec:crossslicer}).
두 결과는 같은 경계의 양쪽에 있다 --- 프로파일에서 $\theta_c$ 를 읽어 오는 것은 전이되고,
면 기준을 파고드는 것은 전이되지 않는다. 수리 방향은 목적함수가 면 각도만이
아니라 \emph{부품 아래의 공기}를 청구하도록 만들고, 바닥 접촉이 점으로 붕괴하지 않도록 인쇄 가능한
접지면적을 제약하는 것이다. 둘 다 본 논문의 범위 밖이다.

\begin{table}[H]
  \centering
  \caption{표~\ref{tab:shapeopt-multi} 와 \emph{동일한} 전후 메쉬의 교차 슬라이서 재슬라이스
  (PrusaSlicer~2.9.6, 고정 프로파일, 수평 기준 임계각 $30^\circ\Rightarrow\theta_c{=}60^\circ$,
  $\nvec{=}+z$, G-code 기반 support-only 질량). ``---'' 는 PrusaSlicer 가 거부한 최적화 후 형상이다:
  변형이 밑면을 아래로 뾰족한 꼭짓점으로 만들어 첫 레이어가 비어 버린다. PrusaSlicer 는 무지지
  대조군 3개의 최적화 전 지지질량이 $0.00$ g 임을 독립적으로 확증한다. 슬라이스되는 지지 필요
  4개 메쉬에서 제거율은 $-2.7\%$($37.9\to36.9$ g)로, CuraEngine 의 $-98.4\%$ 와 대비된다.}
  \label{tab:shapeopt-prusa}
  \small
  \begin{tabular}{lrrr}
    \toprule
    메쉬 & Cura [g] 전$\to$후 & Prusa [g] 전$\to$후 & Prusa 증감 \\
    \midrule
    icosphere        & $0.66\to0.00$ & $3.45\to$ ---   & 슬라이스 불가 \\
    구 (sphere)      & $0.88\to0.00$ & $3.74\to1.60$   & $-57\%$ \\
    원환 (torus)     & $0.26\to0.00$ & $2.89\to$ ---   & 슬라이스 불가 \\
    후크 (hook)      & $3.57\to0.00$ & $8.01\to5.38$   & $-33\%$ \\
    파이프엘보       & $6.39\to0.14$ & $11.85\to7.16$  & $-40\%$ \\
    Bunny            & $2.47\to0.09$ & $14.32\to22.75$ & $\mathbf{+59\%}$ \\
    \midrule
    \multicolumn{4}{l}{\footnotesize\emph{무지지 대조군 (두 슬라이서 모두 최적화 전 $0.00$ g 으로 일치)}}\\
    원뿔 (cone)      & $0.00\to0.00$ & $0.00\to$ ---   & 슬라이스 불가 \\
    U-브래킷         & $0.00\to0.00$ & $0.00\to1.29$   & 지지재 발생 \\
    C-클램프         & $0.00\to0.00$ & $0.00\to2.21$   & 지지재 발생 \\
    \bottomrule
  \end{tabular}
\end{table}

\section{한계: 무게중심 수신 어텐션의 날카로운 극한}\label{sec:centroid-limit}

핵심을 먼저 말하면 이렇다. 소프트 어텐션을 날카롭게 조이면 어텐션은 \emph{어피니티가 가장 큰}
후보로 몰리는데, 그 후보가 \emph{레이가 실제로 맞는} 수신면이라는 보장이 없다. 그래서
명제~\ref{prop:soft2hard} 의 수렴은 가정~\ref{asm:gp}(v) 아래에서만 성립하며, 우리는 이를
일반 위치 문구 뒤에 묻어 두는 대신 명시적으로 밝힌다.

어긋남의 뿌리는 두 기준이 서로 다른 것을 재기 때문이다. 어피니티의 가로 인자
$\exp\!\bigl(-d_{ij}^2/2(\sigma_\ell D)^2\bigr)$ 는 후보 면의 \emph{무게중심}에서 빌드 레이까지의
거리를 재는 반면, 하드 배정은 레이--삼각형 \emph{교차}로 정해진다. 이 두 순서는 불일치할 수
있다: 아래로 향한 레이가 \emph{전혀 맞히지 않는} 면이, 정작 맞히는 면보다 무게중심 기준으로는
더 가까울 수 있다.

최소 반례가 이 실패 양상을 구체적으로 보여준다\footnote{이 반례는 재현 가능한 단위검정으로
고정해 두었다: \texttt{Tomo\_DiffSupport\_dev\char`\\tests\char`\\test\_centroid\_counterexample.py}.}.
높이 $1$ 의 원점에 소스 샘플을 두고 레이를 $-\nvec$ 방향으로 쏜다. 꼭짓점이
$(-2,-1,0)$, $(2,-1,0)$, $(0,3,0)$ 인 큰 수신 삼각형은 레이가 실제로 맞히지만, 그 무게중심
$(0,\tfrac13,0)$ 의 가로거리 제곱은 $d^2=\tfrac19$ 이다. 반면 높이 $0.5$ 에 놓인 작은 방해면
--- 꼭짓점 $(\tfrac1{50},-\tfrac1{100},\tfrac12)$, $(\tfrac2{25},-\tfrac1{100},\tfrac12)$,
$(\tfrac1{20},\tfrac1{50},\tfrac12)$ --- 은 레이가 \emph{빗나가는데도} 무게중심 $(0.05,0,0.5)$ 의
가로거리 제곱이 $d^2=\tfrac1{400}$ 로 훨씬 작다. 방해면 쪽으로 기우는 로그-어피니티 여유
$\bigl(\tfrac19-\tfrac1{400}\bigr)/\bigl(2\sigma_\ell^2D^2\bigr)$ 는 \emph{모든} $\sigma_\ell$ 에
대해 양이고 $\sigma_\ell\rightarrow0$ 에서 \emph{발산}한다. 즉 날카롭게 조일수록 오배정이
교정되기는커녕 \emph{강화}된다. 여기서는 방해면이 높이로도 더 가까워 세로 인자까지 같은 방향으로
가세한다. 따라서 날카로운 극한의 정확한 진술은 조건부다: $L_{\mathrm{SFTF}}\rightarrow J_w$ 는
모든 소스 면에서 $\mathcal C(i)\cup\{\mathrm{bed}\}$ 위 어피니티 최대점이 하드 수신면
$t_i$(또는 바닥)와 일치할 때 성립하며, $\softplus_\beta$ 오버행·시그모이드 게이트·soft-min 바닥
성분은 무조건 수렴한다. 요컨대 무게중심 어텐션은 완화된 가시성 모형이 아니라
\emph{근접성 휴리스틱 기울기 라우터}이고, 우리는 일반 위치에서 수신면 배정이 점별 수렴한다는
주장을 더 이상 하지 않는다.

세 가지 관찰이 이 결함이 본 논문 결과에 미치는 실질적 영향을 한정한다. 첫째, 예측 헤드라인은
무관하다: $S_g$ 와 $S_g^{\mathrm{hard}}$ 에는 구조상 수신 어텐션이 아예 들어가지 않으므로
$+0.80$/$+0.87$ 의 Cura 상관은 라우터에 의존하지 않는다. 둘째, 모든 배향·형상최적화 결과는
최적화된 형상을 CuraEngine 으로 직접 슬라이스해 \emph{외부에서} 검증한다. 오배정된 기울기는
최적화를 느리게 하거나 정체시킬 수는 있어도, 보고된 지지재 제거 수치를 부풀릴 수는 없다 ---
그 수치는 $L_{\mathrm{SFTF}}$ 가 아니라 슬라이서가 재기 때문이다. 셋째, 이 실패는 레이가
빗나가면서도 가로·세로로 모두 가까운 면을 요구한다. 본 논문이 쓰는 조밀하고 대체로 균일한
메쉬에서는 어피니티 최대점과 레이캐스트 수신면이 대체로 일치하며, 이는 관측된 최적화 거동과도
정합한다. 그러나 위와 같은 배치는 보통의 기계부품(오버행 옆의 얇은 리브·핀·브래킷)에서
실제로 나타나므로, 이 조건은 형식적 기술사항이 아니라 진짜 제약이다.

원리적인 수리 방향은 완화를 \emph{가시성 정합적}(visibility consistent)으로 만드는 것이다:
후보를 레이를 따라 앞뒤 가림 순서로 정렬하고 투과율 점화식(소프트 first-hit)으로 소프트
가중치를 배분하면, 날카로운 극한이 가정이 아니라 \emph{구성상} 레이캐스트 수신면을 되찾는다.
이 가림 인식 정식화와, 겹치는 지지 기둥에 대한 정확한 구간합집합 처리는 본 논문의 범위를 벗어난
진행 중인 작업이며, 여기서는 모든 주장을 위의 조건부 진술로 한정한다.

\section{결론}
본 연구의 출발점은 간단하다. 이전 연구의 SFTF 지지비용에서 미분을 막는 핵심은 하드 레이캐스팅이다.
이를 후보 수신면과 바닥 슬롯에 대한 소프트 어텐션으로 바꾸면, 빌드방향과 정점 양쪽에 대해
미분가능한 손실항 $L_{\mathrm{SFTF}}(V,\nvec)$ 를 얻는다. 온도 극한에서는 --- 날카로워진 어텐션이
레이캐스트 수신면과 일치하는 한 --- 이 손실이 이전 연구의 SFTF 로 되돌아가므로, 본 방법은 SFTF
비용을 버리는 새 대리모델이 아니라 하드 SFTF 비용의 매끄러운 완화다. 게이트·오버행·바닥 완화는
무조건 수렴하며, 수신면 배정에 붙는 조건은 절~\ref{sec:centroid-limit} 이 한정한다.
참조구현은 해석적 기울기가 유한차분과 일치하고, 경사하강 빌드방향이 격자 전수탐색 최소와
같은 분지에 도달함을 확인했다.

다음으로, 이전 연구의 SFTF 가 실제 지지질량을 얼마나 잘 설명하는지도 따졌다. watertight 솔리드에서의
TomoNV 교차검증은 이전 연구의 SFTF 비용이 복셀 기준 물리 지지질량의 \emph{느슨한} 프록시임을 드러냈다. 단순
가중치 재조정(순위공간)은 한 메쉬 내 held-out 상관을 $+0.21\to+0.40$ 으로 높였지만, 더 큰
개선은 물리기반 미분가능 \emph{지지부피} 항 $S$ \eqref{eq:supvol} 에서 나왔다. $S$ 는
\emph{메쉬 간} leave-one-out 일반화를 $+0.17\to+0.61$ 로 끌어올려 학습된 Ridge/GBR/MLP 와
비슷하거나 더 좋았다. 따라서 TomoNV 기준의 매끄러운 물리 프록시로는
$L_{\mathrm{SFTF}}+\lambda_S\,S$ 가 적절하다.

실제 생산 슬라이서 검증이 이를 가장 강하게 뒷받침한다. 3DWOX 가 정적 링크한 legacy CuraEngine
15.04 / DP103 PLA 로 g5test 5그룹 벤치마크(프리미티브·브래킷·Thingi10k 기계부품·유기 대형 스캔)를
48방향 슬라이싱해 \emph{서포트 전용} 질량과 맞대면, 손실을 슬라이서
자신의 임계각($60^\circ$)에서 게이트한 항 $S_g$ 가 실제 Cura 지지질량을 메쉬평균 Spearman
$\mathbf{+0.80}$(순위검증이 잘 정의되는 헤드라인 18메쉬 \emph{전부} 양, $95\%$ CI $[{+}.74,{+}.84]$ 가
$0$ 배제)으로 예측해, 복셀 추정기 TomoNV($+0.46$)와 게이트 없는 $L_{\mathrm{SFTF}}$/$S$($+0.26$--$+0.39$)를
크게 앞선다. 하드 게이트 대조군은 이 예측 자체가 미분가능성 덕이 아님을 보이고($S_g^{\mathrm{hard}}$
$+0.87$), 텐서 대조는 다중 메쉬 형상최적화 결과 역시 텐서 항과 무관함을 보인다(목적에 텐서
항이 없고, 텐서 단독은 실패한다): 완화의 기여는 정확히, 이 슬라이서-게이트 물리를 최적화
가능하게 만든 데 있다. 예측(날카로움)과 최적화(부드러움)의 이 긴장은 게이트 설계
수준에서 완화된다: 순전파는 하드 지시함수, 역전파만 시그모이드인 straight-through
게이트~\citep{bengio2013ste}는 소프트 레시피의 최적화 성능(Cura 제거율 $98.0\%$ 대
$98.4\%$)을 유지한 채 게이트 몫의 예측 편향을 없앤다. 완전 하드 대조군까지 남는
격차는 나머지 완화 성분(softplus 오버행 크기 가중·soft-min 바닥높이)의 몫이므로,
순수 평가·순위에는 완화 없는 $S_g^{\mathrm{hard}}$ 가 최선이다.
\emph{핵심은 슬라이서 자신의 임계각에서 게이트}하는 것이다: 게이트는 Cura 일치도를
$+0.45$--$+0.74$ 올리되 TomoNV 일치도는 낮추는데, $60^\circ$ 컷오프가 실제 슬라이서가 적용하는 규칙이라
게이트한 항은 \emph{실제 슬라이서}에, 게이트 없는 항은 복셀 \emph{추정기}에 정합하기 때문이다.
end-to-end 에서도 $L_{\mathrm{SFTF}}+S_g$($0.232$)가 기본($0.242$)·$+S$($0.240$)를 앞서 게이트한 물리항이
상관과 최적화 양쪽에서 최선이다. 한편 지지부피 항은 면별 오버행을 적분하므로 입력 메쉬를 데시메이션하지
않아야 변별력이 유지된다(Bunny $S$ 상관 $6$k면 $+0.58\to$ $50$k면 $+0.83$).

마지막으로, 구처럼 모든 방향이 동등하거나 원기둥처럼 한 원이 동등한 회전대칭 퇴화형에서는
단일 $\nvec^\ast$ 자체가 잘 정의되지 않는다. 본 연구는 평탄도 검정과 극각붕괴 축 검정으로 이런
대칭을 분류해, 임의의 한 방향 대신 최적해 \emph{집합}(점·원·구면)을 보고한다. 이 구조를 활용하는
회전등변(rotation-equivariant) 예측기 학습은 향후 과제로 남긴다.

두 헤드라인의 보증 범위는 서로 다르므로, 이를 구분해 밝히며 맺는다. \textbf{예측} 결과는
슬라이서를 넘어 전이된다(절~\ref{sec:crossslicer}): 맞춤 계수가 없고 $\theta_c$ 를 대상
프로파일에서 읽어 오며, 예측기가 한 번도 본 적 없는 슬라이서에서도 순위가 유지된다. \textbf{형상최적화} 결과는 그렇지 않다
(절~\ref{sec:shapeopt-transfer-limit}). 이 결과는 CuraEngine 이 청구하는 지지재를 제거하지만,
옵티마이저는 면 각도 기준을 만족시키려고 바닥 접촉을 점으로 붕괴시켜도 무방하며, PrusaSlicer 는
그렇게 남은 부품 아래의 공기를 청구하거나 --- 메쉬 자체를 거부한다. 정점 기울기가 \emph{우리가
적어 놓은 목적함수}의 최적점으로 메쉬를 옮긴다는 것은 실증되었다. 다만 그 목적함수는 아직
슬라이서가 실제로 청구하는 것의 충실한 모형이 아니다. 이 간극을 메우는 일 --- 면 각도만이 아니라
\emph{부품 아래의 공기}를 청구하고, 접지면적이 인쇄 가능하도록 제약하는 것 --- 이 향후 과제의
첫 항목이며, 슬라이서 프로파일 확장·인쇄시간 및 표면품질 목적 통합이 그 뒤를 잇는다.

\paragraph{자료 및 코드 공개.}
본 연구의 소스코드, 21개 메쉬 $\times$ 48방향 Cura 검증 캐시, 분석 스크립트는
공개 저장소 \url{https://github.com/cfms-lab/SFTFCluster_2026} 의 \texttt{sftfsoft/}
하위폴더에서 제공한다(자매 논문 SFTFCluster 와 저장소를 공유하되, 본 연구의 자산은
전부 그 하위폴더에 있다). 특히 슬라이서 상관 결과는 슬라이서 재실행 없이 캐시만으로
\texttt{sftfsoft/scripts/validate\_vs\_slicer.py} 로 재현되며, 게이트 민감도·Cura~5.13
이식·다중 메쉬 형상최적화 분석은 각각 \texttt{sftfsoft/scripts/sweep\_thetac\_gate.py},
\texttt{sftfsoft/scripts/transfer\_cura5.py},
\texttt{sftfsoft/scripts/shapeopt\_multimesh.py} 로 재현된다. 절~\ref{sec:crossslicer} 의
PrusaSlicer 전이는 \texttt{sftfsoft/scripts/prusa\_transfer\_validation.py} 로,
절~\ref{sec:shapeopt-transfer-limit} 의 전후 재슬라이스는
\texttt{sftfsoft/scripts/shapeopt\_bedweight\_ab.py} 로 재현되며, 그 표의 근거가 되는
전후 메쉬 9쌍도 함께 배포한다. 슬라이싱을 직접 재실행하려면 외부 도구 경로를 환경변수로
지정해야 한다(\texttt{sftfsoft/scripts/README\_prusa\_transfer.md} 참조). 제3자 메쉬 모델은
각 원 출처의 라이선스에 따라 원 배포처에서 받아야 한다.

\appendix
\section{실험 $\times$ 메쉬그룹 커버리지 (g5test 5그룹)}\label{app:coverage}
아래 표는 g5test 5그룹 벤치마크(기반 SFTF 연구·SFTFCluster 와 동일한 메쉬 정체성)에서 각 실험이
어느 부분집합을 쓰는지 정리한다. CuraEngine 검증은 A/B/C 전 그룹을 슬라이싱하되 헤드라인 평균은
순위검증이 잘 정의되는 18메쉬로 하고, 퇴화·내부공동 3종은 별도 블록으로 투명하게 보고한다.
\input{coverage_table_g5}

\section{메쉬 해상도와 coarse-to-fine 평가 상세}\label{app:mesh-mg}
본문의 해상도 권고는 두 관찰에 근거한다. 첫째, 슬라이서 실제 지지질량과의 비교에서는 데시메이션이
지지부피 항의 방향별 변별력을 낮춘다. 둘째, 계산시간을 줄이기 위해서는 coarse mesh 를 최종
평가값으로 쓰기보다 후보 축소용 proxy 로 쓰고, 마지막 판단은 fine mesh 에서 해야 한다.

\begin{table}[H]
  \centering
  \caption{Bunny 69k 의 SFTF support-volume 해상도 sweep. 값은 legacy CuraEngine 15.04 / DP103 PLA
  support-only 질량과의 방향별 상관이다. 설정은 $SFTFConfig(w_{\mathrm{supvol}}{=}1,
  \mathrm{gate\_supvol}{=}\mathrm{True}, \mathrm{supvol\_to\_bed}{=}\mathrm{True})$,
  $60^\circ$ 임계각, 단위대각 정규화, 거친 yaw/pitch 격자 기준이다.}
  \label{tab:mesh-resolution-sweep}
  \small
  \begin{tabular}{lrr}
    \toprule
    입력 면수 & Spearman & Pearson \\
    \midrule
    $6{,}000$  & $0.263$ & $0.563$ \\
    $15{,}000$ & $0.460$ & $0.649$ \\
    $30{,}000$ & $0.590$ & $0.719$ \\
    $40{,}000$ & $0.631$ & $0.745$ \\
    \bottomrule
  \end{tabular}
\end{table}

위 하락은 단순한 비교 하니스 오류가 아니다. 같은 Cura 격자와 같은 yaw/pitch 규약에 복셀
예측기 TOMO 를 통과시키면 Spearman $0.62$, Pearson $0.80$ 으로, 데시메이션된 프록시의
$0.26$ 보다 훨씬 높다. 즉 회전 규약과 측정 파이프라인이 상관을 깎는 것이 아니라,
데시메이션에서 사라지는 표면 overhang/height 정보가 $S$ 의 변별력을 낮춘다.

\begin{table}[H]
  \centering
  \caption{Bunny 15k--30k--69k coarse-to-fine case study. Quadric decimation, $K{=}24$
  Fibonacci 방향, float32, $k{=}64$ 후보 수신면, 기본 $L_{\mathrm{SFTF}}$ loss 를 사용했다.
  시간은 현재 실험 PC 의 wall-clock 이며, ``full best rank'' 는 full 69k 최적 방향이 해당
  level 의 점수 순위에서 몇 등인지를 뜻한다.}
  \label{tab:bunny-mg-levels}
  \small
  \begin{tabular}{lrrrrrr}
    \toprule
    level & 면수 & 초/방향 & 평균비 & $\rho$ vs full & 최적각 차이 & full best rank \\
    \midrule
    $15$k & $15{,}000$ & $0.583$ & $0.727$ & $0.890$ & $43.7^\circ$ & $4$ \\
    $30$k & $30{,}000$ & $2.230$ & $0.844$ & $0.957$ & $0.0^\circ$  & $1$ \\
    full  & $69{,}662$ & $11.480$ & $1.000$ & $1.000$ & $0.0^\circ$  & $1$ \\
    \bottomrule
  \end{tabular}
\end{table}

이 표는 coarse-to-fine 의 장점과 한계를 동시에 보인다. $15$k landscape 는 full 과 높은 순위상관을
갖지만 단독 최적 방향은 full 최적과 $43.7^\circ$ 다르다. 반면 $15$k 에서 top-$4$ 를 남기고,
$30$k 에서 top-$2$ 로 줄인 뒤, full mesh 에서 두 방향만 최종 평가하면 full sweep 과 같은 최적
방향을 찾으면서 예상 비용은 $275.5$\,s 에서 $45.9$\,s 로 줄어 약 $6.0\times$ 빨라진다. 따라서
coarse mesh 는 최종 물리량의 대체물이 아니라, fine 평가 횟수를 줄이는 후보 필터로 해석해야 한다.

\subsection{프로그램 실행 성능}\label{app:runtime}
실행시간은 현재 참조구현이 어느 크기의 메쉬를 실제로 다룰 수 있는지 확인하기 위한 보조 지표다.
측정 환경은 AMD Ryzen 9 9950X3D(16코어/32스레드), 물리 메모리 128\,GB, PyTorch 2.12.1 CPU
빌드(\texttt{torch.get\_num\_threads()=16}, CUDA 없음), Windows 이다. 모든 수치는 Bunny 69k 를
단위대각 정규화하고, 후보 수신면 $k{=}64$, 기본 $L_{\mathrm{SFTF}}$ 설정에서 한 대표 방향을
평가한 wall-clock 시간이다.

\begin{table}[H]
  \centering
  \caption{단일 방향 평가의 dtype 별 실행시간. ``$n$-grad'' 는 빌드방향에 대한 forward+backward
  한 회를 뜻하며, 정점에는 기울기를 요구하지 않는다.}
  \label{tab:runtime-dtype}
  \small
  \begin{tabular}{lrrrr}
    \toprule
    면수 & no-grad f32 & no-grad f64 & $n$-grad f32 & $n$-grad f64 \\
    \midrule
    $15$k & $0.523$\,s & $0.762$\,s & $0.658$\,s & $0.804$\,s \\
    $30$k & $1.872$\,s & $2.943$\,s & $2.322$\,s & $3.119$\,s \\
    $69{,}662$ & $9.738$\,s & $15.176$\,s & $12.123$\,s & $16.079$\,s \\
    \bottomrule
  \end{tabular}
\end{table}

\begin{table}[H]
  \centering
  \caption{float32 autograd 모드별 실행시간과 프로세스 RSS. RSS 는 PyTorch allocator 가 보유한
  메모리를 포함한 측정 후 resident set 이므로 정확한 peak allocation 이 아니라 실사용 상한의
  근사로 해석한다.}
  \label{tab:runtime-autograd}
  \small
  \begin{tabular}{llrr}
    \toprule
    level & 모드 & 시간 [s] & 측정 후 RSS [GiB] \\
    \midrule
    $15$k & no-grad & $0.594$ & $0.96$ \\
    $15$k & $n$-grad & $0.589$ & $0.96$ \\
    $15$k & $V$-grad & $0.636$ & $0.96$ \\
    $30$k & no-grad & $2.244$ & $1.72$ \\
    $30$k & $n$-grad & $2.250$ & $1.76$ \\
    $30$k & $V$-grad & $2.279$ & $1.75$ \\
    full & no-grad & $11.520$ & $4.50$ \\
    full & $n$-grad & $11.459$ & $4.69$ \\
    full & $V$-grad & $11.576$ & $4.89$ \\
    \bottomrule
  \end{tabular}
\end{table}

따라서 현재 PC 에서는 Bunny 65k--70k 급 메쉬를 fine level 로 직접 평가하고, 방향 또는 정점
기울기까지 계산하는 것이 가능하다. 병목은 메모리보다는 후보 수신면 선택의 시간이다. 초기 구현의
\texttt{soft\_receiver\_assignment} 는 $k$-NN 후보만 쓰더라도 방향마다 청크된 below-candidate
검색을 다시 수행했으나, 현재 구현은 정적 KD-tree pool 을 한 번 만든 뒤 각 방향에서 그 pool 안의
nearest-below top-$k$ 를 고르는 cache 경로도 제공한다. Bunny 69k, $K{=}6$ 방향에서 기존
directional $k{=}64$ 검색은 $68.9$\,s 가 걸렸고, static-pool $K_{\mathrm{pool}}{=}256$ 은
후보 생성 $1.4$\,s + 평가 $1.0$\,s 로 줄면서 directional 결과와 Spearman $1.00$, 평균비
$1.003$ 을 보였다. $K{=}24$ full sweep 도 $275.5$\,s 에서 $5.5$\,s 로 줄었다. 이 cache 이후에는
full 평가 자체가 충분히 싸져 작은 sweep 에서는 coarse-to-fine 의 추가 speedup 이 $1$--$1.5\times$
정도로 작아지지만, 수백 방향 탐색이나 반복 최적화에서는 15k--30k proxy 로 full 평가 횟수를 줄이는
전략이 여전히 유효하다.

\subsection{기존 지지비용 산출 방법과의 소요시간 비교}\label{app:runtime-compare}
위 두 표는 본 방법 내부의 dtype 및 autograd 모드별 비용만 보여줄 뿐, 기존 지지비용 산출 방법
대비 본 방법이 어디쯤에 위치하는지는 드러내지 않는다. 표~\ref{tab:runtime-methods} 는 동일한
Bunny 메쉬($69{,}662$면, $120$\,mm 대각)와 동일 빌드방향($\nvec{=}+z$)에서 각 방법이 단일
빌드방향의 지지비용을 산출하는 데 걸리는 시간을 같은 PC(표~\ref{tab:runtime-dtype}과 동일 환경,
단 TOMO\_gpu 만 DLL 의 CUDA 경로 사용)에서 비교한 것이다. 비교 대상은 실제 생산 슬라이서(legacy
CuraEngine 15.04), 복셀\footnote{물체를 규칙적 3차원 격자(부피 픽셀)로 이산화하여 지지질량을
근사하는 방식.} 기반 추정기의 CPU/GPU 구현(TOMO\_cpu / TOMO\_gpu, 즉 TomoNV~\citep{tomonv}
계열), 이전 연구의 SFTF 지지흐름 텐서장을 하드 레이캐스트\footnote{광선을 쏘아 교차면을 이산적으로
찾는 방식으로, 미분 불가능하다.}로 산출하는 C++ 구현, 그리고 본 방법(SFTFSoft)이다. 앞의 네
방법은 모두 미분 불가능하여 이산 방향 샘플링에만 쓸 수 있는 반면, 본 방법만 동일한 지지흐름
텐서장을 소프트 어텐션으로 미분가능하게 일반화한다.

\begin{table}[H]
  \centering
  \caption{방법별 단일 빌드방향 지지비용 산출 소요시간 비교(Bunny 69k, $120$\,mm 대각,
  $\nvec{=}+z$). 본 방법의 시간은 정적 후보-풀을 $1$회 구축(약 $1.46$\,s)한 뒤 재사용하는 cache
  경로 기준이므로, 방향마다 후보를 새로 탐색하는 표~\ref{tab:runtime-dtype}(full $9.7$\,s)보다
  작다.}
  \label{tab:runtime-methods}
  \small
  \begin{tabular}{llrc}
    \toprule
    방법 & 산출값 / 특성 & 방향당 시간 [s] & 미분가능 \\
    \midrule
    CuraEngine 15.04 (실제 슬라이스) & 실제 support 질량 & $5.245$ & 아니오 \\
    TOMO\_cpu (복셀 추정) & 지지질량 추정 & $0.058$ & 아니오 \\
    TOMO\_gpu (복셀 추정, CUDA) & 지지질량 추정 & $0.201$ & 아니오 \\
    SFTF 원본 (하드 레이캐스트, C++) & 지지흐름 점수 & $0.0005$ & 아니오 \\
    \textbf{본 방법 SFTFSoft} (no-grad) & 미분가능 손실 & $0.198$ & \textbf{예} \\
    \textbf{본 방법 SFTFSoft} ($n$-grad) & 손실 $+$ 방향 기울기 & $0.272$ & \textbf{예} \\
    \bottomrule
  \end{tabular}
\end{table}

비교 결과, 본 방법은 방향당 약 $0.2$\,s 로 실제 생산 슬라이서(약 $5.2$\,s)보다 약 $26$배 빠르며
복셀 추정기(TOMO)와 대등하다. 원본 SFTF(C++)와 TOMO 는 본 방법보다 빠르거나 대등하지만 모두
미분 불가능하여 이산 방향 샘플링에만 쓸 수 있는 반면, 본 방법은 방향 기울기를 함께 산출하여도
약 $0.27$\,s 에 그치면서 유일하게 빌드방향과 정점 좌표에 대한 기울기를 제공한다(단일 방향에서는
커널 실행 오버헤드로 TOMO\_gpu 가 TOMO\_cpu 보다 느릴 수 있다). 즉 본 방법은 실제 슬라이서 대비
큰 속도 이점과 미분가능성을 동시에 제공하여, 경사하강 기반 빌드방향 최적화 및 형상 최적화의 내부
루프에 적합하다.

% ---- 참고문헌 -------------------------------------------------------
\bibliographystyle{plainnat}
\bibliography{references}

\end{document}

