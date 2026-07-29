# LaTeX source: SFTF_Cluster_TDP_draft_KO.tex

Source: `D:\__SFTF_Projects(2026)\Tomo_SFTFCluster_dev\draft\SFTF_Cluster_TDP_draft_KO.tex`

% =====================================================================
%  SFTF-Cluster -- 투고 영문본(SFTF_Cluster_TDP_draft.tex)의 참고용 한글본.
%  구조·표·그림·수치는 영문 투고본과 동일하며, 본문만 한국어로 옮겼다.
%  컴파일: xelatex (kotex).
% =====================================================================
% !TEX program = xelatex
\documentclass[11pt,a4paper]{article}

\usepackage{kotex}
\usepackage{amsmath,amssymb,amsfonts,bm}
\usepackage{graphicx}
\graphicspath{{pics/}}
\usepackage[labelfont=bf,labelsep=space]{caption}
\captionsetup[figure]{name=그림}
\captionsetup[table]{name=표}
\usepackage{booktabs}
\usepackage{float}
\usepackage{algorithm}
\usepackage{algpseudocode}
\usepackage[margin=25mm]{geometry}
\usepackage{xcolor}
\usepackage[hidelinks]{hyperref}

\title{Support Flow Tensor Field 기반 출력지향 메쉬 분할\\[4pt]
\large ── 3D Printing and Additive Manufacturing 투고본의 참고용 한글본 ──}
\author{설인환\\
\small 금오공과대학교 소재디자인공학과, 경북 구미 39177\\
\small Email: snowman0@kumoh.ac.kr \quad ORCID: 0000-0003-0105-920X}
\date{}

\begin{document}
\maketitle

\begin{abstract}
\noindent
메쉬 분할은 크거나 복잡한 적층제조 부품을 만들 때 널리 쓰이지만, 기존 분할기는 주로
좌표만 묶어서 각 조각이 서포트를 적게 쓰고 출력 가능한지를 잘 반영하지 못한다. 본
논문은 Support Flow Tensor Field(SFTF)가 만들어 내는 \emph{면별 지지흐름 정보}를 재사용하는
출력지향 메쉬 분할 방법을 제안한다. SFTF를 빌드 방향 순위 매기기에만 쓰는 대신, 각 면의
오버행 강도, 지지 수신자 종류, 지지 높이, 지지 역할을 군집화 특징으로 노출한다. 이 특징은
두 계열의 분할을 구동한다: 지지 쌍과 역할에 기반한 순수 지지흐름 분할과, 표준 군집화에
SFTF 특징을 더한 특징 융합 군집화이다. 모든 핵심 비교는 오픈소스 CuraEngine으로 직접
평가하였다. 즉 모든 분할의 모든 연결 부품을 48방향 슬라이서 탐색으로 재배향하며, 열두
형상 벤치마크에서 약 $1.4\times10^5$회 슬라이싱에 해당한다. 이 슬라이서 기준에서는 어떤
분할기도 보편적으로 최선은 아니지만, 같은 라벨의 분리된 컴포넌트를 독립 부품으로 처리하면
특징 융합 $k$-medoids가 가장 좋은 평균 순위를 얻는다. 그러나 최종 부품 수를 맞춘 통제에서는
좌표 $k$-means가 열두 형상 모두에서 더 적은 지지를 사용하여, 특징 집합보다
부품 예산이 슬라이서 지지를 우선적으로 좌우함을 보인다. SFTF 기반 분할은 또한 가장 일관된
지지역할 분할을 만든다. SFTF 정의 클래스에서는 순수 지지흐름 영역 성장이, 실제 CuraEngine
지지 접촉에서 클래스를 다시 유도하면 특징 융합 $k$-medoids가 가장 높다. 이 결과는 서포트
감소가 기존 지지 기둥의 보존보다 \emph{각 부품이 유리한 빌드 방향을 자유롭게 고르는 것}에
더 크게 좌우됨을 보인다. 따라서 제안 방법은 보편적 서포트 최소화기가 아니라, 해석 가능하고
역할이 일관된 부품을 만들며 슬라이서가 각 부품의 배향을 고르면 경쟁력 있는 서포트를 내는
출력지향 분할기로 특징지어진다.
\end{abstract}

\noindent\textbf{키워드:} 적층제조; 메쉬 분할; 지지구조; 빌드 배향; support flow tensor
field; 군집화

% ============================ 1. 서론 ========================
\section{서론}

크거나 복잡한 메쉬를 출력 가능한 조각으로 나누는 것은 적층제조(AM)의 실용적 전략이다.
특히 마네킨·드레스폼, 웨어러블 디바이스, 맞춤 보호장구, 보조기, 해부 모형처럼 인체에
밀착하거나 인체를 본뜬 대형 자유곡면 쉘에서 직접적으로 요구된다~[1]. 이런 응용에서 분할은
결과 조각이 서포트 흔적을 최소한으로 남기며 출력·조립·마감될 수 있어야만 유용하다. 따라서
분할 경계는 기하적 근접성뿐 아니라 선택한 빌드 방향이 유발하는 지지 거동도 반영해야 한다.

많은 메쉬 분할 파이프라인은 여전히 DBSCAN~[2], $k$-means, $k$-medoids~[3], 응집형
군집화, 스펙트럴 군집화 같은 알고리즘으로 정점 또는 면 중심을 군집화한다. 고전적 메쉬
분할도 계층적 절단 분해~[4], 형상 지름 함수~[5], 곡률 텐서 분석~[6], 근사 볼록
분해~[7]와 같은 강력한 기하 기준을 제공한다. AM 특화 분해 방법은 작업부피·조립·지지 관련
목적을 추가하며, Chopper~[8], 무지지 골격 분할~[9], 다방향 지지면적 최소화~[10]가 그
예이다. 이들은 중요한 비교 기준이지만, 빌드 방향 분석의 \emph{면별} 지지흐름 물리량을
군집화 특징으로 직접 노출하지는 않는다. 이 비교 기준들과 제안하는 SFTF 기반 경로의
분류를 그림~\ref{fig:taxonomy}에 정리하였다.

Support Flow Tensor Field(SFTF)는 빠른 빌드 방향 후보 생성기로 제안되었다~[11]. 현재 v2는
모든 방향에 동일한 정규화 면적측도 기반 결정론적 표면 표본을 쓰고, ray 높이를 경계상자
대각선 $D$로 나누며, 기존의 source-area--receiver-area 곱을 제거한다. 면-면 흐름 텐서는
대칭 Rayleigh 수축 $R(n)=\max[0,-n^{\mathsf T}\operatorname{sym}(F_{\rm pair})n]$으로만
점수에 기여하고, 면 수신자가 없는 ray는 무차원 베드 점수 $B(n)$을 만들어 최종
$S(n)=R(n)+B(n)$이 된다. 따라서 점수는 메쉬의 균일 스케일 변환에 불변이며, 반대칭 텐서
성분은 불확실성 진단으로만 남는다. 본 논문은 이 면별 지지흐름 물리량을 메쉬 분할 자체에
다시 쓸 수 있는가를 묻는다.

답은 ``그렇다''이다. 본 연구는 보통 전역 방향 점수로 압축되어 버려지는 면별 지지흐름장을
보존하여 출력지향 분할기의 토대로 삼는다. 기여는 다음과 같다. (i) 메쉬의 선택된 빌드
방향에서 SFTF 지지흐름 데이터로 만든 적응형 면별 특징행렬; (ii) 두 계열의 분할 --- 순수
지지흐름 분할과 SFTF 특징 융합 군집화; (iii) 한 조건화 방향에 대한 의존을 줄이는 무차원
SFTF v2 basin·난수 시드 다중시작 선택기; (iv) 부품을 자르고 재배향하는 지지 효과를 추정하는
ray-free 지지 목적함수; (v) 선행 다방향 분해의 재구현과 순도 지표의 슬라이서 기반 재검증을
포함하여, 보고된 모든 분할을 열두 형상에 걸쳐 CuraEngine으로 검증. 초점은 의도적으로
좁다. SFTF 자체는 선행연구로 두고, 본 기여는 버려지던 그 면별 흐름 정보를 메쉬 분할
신호로 재구성하는 데 있다.

\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{fig_method_taxonomy_from_pdf-1.png}
\caption{좌표·기하·SFTF 기반 분할 방법의 분류. 왼쪽 가지는 지지 거동을 부호화하지 않는
기존 비교 기준(좌표 전용 $k$-means, 평면 BSP, graph-cut/MRF, 스펙트럴/normalized-cut)이다.
오른쪽 가지가 제안하는 SFTF 기반 경로로, 선행 SFTF 계산이 면별 지지흐름 특징을 공급하고,
이를 특징 융합 군집화와 순수 지지흐름 분할로 재사용하며, 다방향 확장은 부품을 서로 다른
유리한 빌드 방향에 배정한다.}
\label{fig:taxonomy}
\end{figure}

% ============================ 2. 재료 및 방법 ===============
\section{재료 및 방법}

\subsection{면별 지지흐름 특징}

면 $i$의 중심을 $c_i$, 외향 단위법선을 $m_i$, 면적을 $A_i$, 경계상자 대각선을
$D=\lVert b_{\max}-b_{\min}\rVert_2$라 하자. 빌드 방향 $n$에 대해
빌드플레이트 높이
\begin{equation}
z_{\mathrm{plate}}(n)=\min_{v\in V} v\cdot n ,
\end{equation}
과 기본 면별 양
\begin{align}
O_i(n) &= \max(0,-m_i\cdot n),\\
\tau_i(n) &= m_i\cdot n,\\
\eta_i(n) &= \frac{c_i\cdot n - z_{\mathrm{plate}}(n)}{D}
\end{align}
을 정의한다. 여기서 $O_i$는 오버행 강도, $\tau_i$는 부호 있는 기울기, $\eta_i$는
빌드플레이트 위 무차원 높이를 나타낸다.

분할은 무차원 SFTF v2 점수로 조건화한다. 고정된 v2 후보 프로토콜에 따라 정규화 면적 표본
$8{,}192$개를 $2{,}048$개 Fibonacci 구면 방향에 공통으로 쓰고, $S(n)=R(n)+B(n)$ 순으로
정렬한 뒤 최소 $12^\circ$ 떨어진 basin만 비최대 억제로 남긴다. 단일시작은 최저 점수 basin,
다중시작은 앞의 $K_o$개 분리 basin $\{n_q\}_{q=1}^{K_o}$에 대해 특징 추출을 반복한다.
기존 v1 라우터는 과거 결과 재현 옵션으로만 유지하고 v1--v2 영향은 별도 감사한다. 각 오버행
면에서 SFTF와 동일한 수신자 판정으로 $-n$ 방향 ray를
쏜다~[11]. 이로부터 면별 지지 기술자를 기록한다: 지지 역할
$\rho_i\in\{\mathrm{none},\mathrm{face},\mathrm{bed}\}$(지지 불필요, 면-면 자기지지, 빌드
플레이트 지지); 유효 수신자 $t_i$에 대한 무차원 지지 높이
$\hat h_i=(c_i-c_{t_i})\cdot n/D$(없으면 0);
수신자 인덱스 $t_i$(없으면 $-1$); 수신 횟수 $r_i$. 표준 특징행렬은
\begin{equation}
\Phi_{\mathrm{SFTF}}
=\operatorname{zscore}\!\left([O,\tau,\eta,\hat h,r]\right)\in\mathbb{R}^{N\times5}
\label{eq:phi}
\end{equation}
이며, 상수 열은 0으로 둔다. 두 높이 채널은 이미 무차원이며, 표준화로 방향 항과 수신 횟수
채널의 기여를 균형화한다. SFTF가 구분하는 두 지지 사례 --- 면-면 자기지지와 가상 접지 노드를
통한 빌드플레이트 지지 --- 를 그림~\ref{fig:unified-flow}에 도시하였다.

\begin{figure}[H]
\centering
\includegraphics[width=0.86\textwidth]{FTree4x_fig1_unified_flow_supp-1.png}
\caption{분할기가 재사용하는 통합 지지흐름 표현. 하향 오버행 면은 아래의 다른 면에
받쳐지거나(면-면 흐름) 수신자를 못 찾아 빌드플레이트까지 지지되어야 한다(가상 접지 노드
흐름). SFTF는 이 사건들을 방향 점수로 누적하지만, 본 방법은 이를 면별 지지 역할·수신자·
수신 횟수·지지 높이로 보존하여 출력지향 분할 특징으로 삼는다.}
\label{fig:unified-flow}
\end{figure}

\subsection{분할 계열}

\paragraph{순수 지지흐름 분할.}
첫 계열은 지지흐름 관계만 사용한다. \texttt{support\_flow}에서 각 면은 네 가지 클래스
$\kappa_i\in\{\mathrm{bed},\mathrm{needs},\mathrm{supporter},\mathrm{free}\}$로 분류된다.
빌드플레이트 근처 면은 \textsc{bed}, 오버행 면은 \textsc{needs}, ray를 하나 이상 받는
면은 \textsc{supporter}, 나머지는 \textsc{free}이다. 이어 union--find가 (i) 각 지지 쌍
$(i,t_i)$와 (ii) $\kappa_i$가 같은 인접면을 병합한다. 결과 컴포넌트는 지지 basin으로,
오버행과 이를 받치는 국소 표면이 한 부품에 남는다. \texttt{flow\_region}에서는 지지 쌍을
강제 병합하지 않고, 인접면 $i,j$를
\begin{equation}
\rho_i=\rho_j \quad\mathrm{이고}\quad m_i\cdot m_j\ge \cos\theta_{\mathrm{sim}}
\end{equation}
일 때 병합한다($\theta_{\mathrm{sim}}=35^\circ$ 기본값). 이 변형은 지지 역할이 일관된
기하적으로 매끄러운 영역을 선호한다. 두 변형 모두 아주 작은 컴포넌트는 가장 많이 접한
이웃으로 흡수되며, 톱니 경계를 줄이려 이면각 가중 graph-cut 평활화를 적용할 수 있다(기본
$\lambda=3$, manikin 스윕에서 선정; 보충 그림~S3).

\paragraph{특징 융합 군집화.}
둘째 계열은 표준 군집화에 SFTF 특징을 주입한다. $C\in\mathbb{R}^{N\times3}$를 면 중심
행렬이라 하면, 주 군집화 행렬은
\begin{equation}
M=\left[w_s\,\operatorname{zscore}(C)\mid w_f\,\Phi_{\mathrm{SFTF}}\right]
\in\mathbb{R}^{N\times8}
\label{eq:cluster-matrix}
\end{equation}
이다. DBSCAN, $k$-means, 응집형 군집화, 그리고 확장 $k$-medoids 구현을 $M$에 적용한다.
대형 메쉬에서 $k$-medoids는 $O(N^2)$ 거리행렬을 피하여, 반복마다 $O(NK)$로 면을 최근접
medoid에 배정하고 각 medoid를 맨해튼 거리 기준 군집 평균에 가장 가까운 구성원으로 갱신한다.
분할기가 면 라벨을 반환한 뒤에는 각 비음수 라벨을 면 인접 연결성으로 쪼개어, 같은 색이지만
물리적으로 분리된 쉘을 독립 부품으로 다루고 각자 배향·지지 평가를 받게 한다. 따라서 요청
군집 수는 초기 그룹핑 매개변수이며, 보고 부품 수는 이 후처리 뒤 연결 부품 수이다. 다방향
확장에서는 분리된 v2 조건화 방향 $K$개 $\{n_k\}$로 $c_{ik}=\max(0,-m_i\cdot n_k)$, hard 선호
방향 $b_i=\arg\min_k c_{ik}$, soft 가중치
$w_{ik}=\exp(-\beta c_{ik})/\sum_{k'}\exp(-\beta c_{ik'})$($\beta=8$)를 정의한다. 라벨
$b_i$는 지지영역 성장(\texttt{build\_direction})을 구동하고, soft 블록 $W=[w_{ik}]$은
식~\eqref{eq:cluster-matrix}에 덧붙일 수 있다.

\subsection{Ray-free 분할 목적함수}

분할 $\Pi=\{\mathcal{P}_\ell\}$을 채점·최적화하기 위해 ray-free 지지 모델을 쓴다. 분할의
실제 지지량은
\begin{equation}
S(\Pi)\approx S_{\mathrm{whole}}
 +\Delta S_{\mathrm{cut}}(\Pi)
 -\Delta S_{\mathrm{reorient}}(\Pi)
\label{eq:support-decomp}
\end{equation}
로 볼 수 있다. 여기서 $\Delta S_{\mathrm{cut}}$은 오버행을 그 수신자에서 분리해 생기는
지지, $\Delta S_{\mathrm{reorient}}$은 각 부품이 자기 최적 배향에 설 때 아끼는 지지이다.
수신자 $t_i$를 갖는 오버행 면 $i$에 대해 저렴한 절단 가중치 $w_i=A_iO_i\eta_i$를 두면 절단
비용은
\begin{equation}
\Delta S_{\mathrm{cut}}(\Pi)
=\sum_{i:\rho_i=\mathrm{face},\ \ell(i)\ne\ell(t_i)} w_i
\label{eq:dscut}
\end{equation}
이고, $\sum_i w_i$로 정규화하면 끊긴 지지 기둥 비율이 된다. 재배향 항은 가산성에 의존한다.
방향 $d$에서 면별 지지 proxy를
\begin{equation}
\begin{aligned}
g_i(d;\theta_c)&=\mathbf{1}\{-m_i\cdot d>\cos\theta_c\},\\
s_i(d)&=A_i\,g_i(d;\theta_c)\max(0,-m_i\cdot d)
\end{aligned}
\label{eq:sik}
\end{equation}
로 정의한다(기둥 부피 강조 시 높이 항 곱). 이 게이트는 분할 지지 proxy에만 쓰여 슬라이서
임계각 규약에 맞추며, 선행 SFTF 후보 생성 계수 $O_i(n)=\max(0,-m_i\cdot n)$ 자체는 바꾸지
않는다. 부품 지지 proxy는 $P_\ell(d)=\sum_{i\in\mathcal{P}_\ell}s_i(d)$이고, 그 최적 방향은
이산 방향 집합에서 $P_\ell$을 최소화해 얻어, ray-free 예측 지지
\begin{equation}
\hat S_{\mathrm{fp}}(\Pi)=
\sum_\ell \min_d \sum_{i\in\mathcal{P}_\ell}s_i(d)
\label{eq:shat}
\end{equation}
를 준다. 이 footprint proxy는 자기지지를 못 보므로, height-field 보정
$\hat S_{\mathrm{hf}}$도 평가한다(각 부품 방향을 $\hat S_{\mathrm{fp}}$로 고른 뒤, 각
오버행 기둥이 같은 투영 셀의 가장 가까운 윗면까지만 내려간다고 봄). 다중시작 선택을 켜면
v2의 $K_o$개 분리 basin 방향 $n_q$와 각 난수 시드 $s$에 대해 후보 분할을 만들고
$\Pi^\star=\arg\min_{\Pi(q,s)} \hat S_{\mathrm{hf}}(\Pi(q,s))$을 고른다. 이는 전역 탐색이
아니라 물리 유도 다중시작 탐색이며, 기본값은 $K_o=5$, 시드 $\{0,\dots,4\}$이다. 전체
절차는 알고리즘~\ref{alg:workflow}에 요약한다.

\begin{algorithm}[H]
\caption{출력지향 메쉬 분할 워크플로.}
\label{alg:workflow}
\begin{algorithmic}[1]
\State 무차원 SFTF v2 후보를 정렬하여 분리 basin $\{n_q\}_{q=1}^{K_o}$을 선택.
\For{각 조건화 방향 $n_q$}
  \State 면별 특징 $(O,\tau,\eta,\rho,h,t,r)$과 $\Phi_{\mathrm{SFTF}}(n_q)$ 계산.
  \For{선택한 군집화 방법의 각 난수 시드 $s$}
    \If{\texttt{support\_flow}}
      \State $\kappa_i$로 분류하고 지지 쌍과 동일 클래스 인접면 병합.
    \ElsIf{\texttt{flow\_region} 또는 다방향 성장}
      \State 역할/regime이 같고 법선이 유사한 인접면 병합.
    \Else
      \State $M=[w_s z(C)\mid w_f\Phi_{\mathrm{SFTF}}(n_q)]$ 구성 후 시드 $s$로 군집화.
    \EndIf
    \State 작은 컴포넌트 흡수, 필요 시 경계 평활화, 분리된 동일 라벨을 별도 부품으로 재라벨, $\hat S_{\mathrm{fp}}$ 또는 $\hat S_{\mathrm{hf}}$로 채점.
  \EndFor
\EndFor
\State 최저 점수 후보 분할 출력.
\end{algorithmic}
\end{algorithm}

\subsection{데이터와 구현}
\label{sec:data}

특징 추출·면 보존 검증에는 Stanford Bunny($69{,}662$면), 출력지향 분할에는 세 응용 메쉬 ---
BodyParts3D의 간($19{,}416$면)~[12], \emph{Nefertiti} 흉상($99{,}938$면), 전신
마네킨($13{,}672$면) --- 를 사용하였다. 광역 벤치마크는 primitive·기계·스캔 해부·그래픽
스캔·장기·인체 폼 부류를 아우르는 열두 형상으로 확장하며, torus, hook, 스캔 해부 형상 셋,
Stanford dragon($99{,}999$면), Happy Buddha($49{,}944$면), Lucy($49{,}999$면),
BodyParts3D 신장($12{,}394$면)을 추가한다. 한 스캔 형상(anat-D9)은 241개의 분리 컴포넌트로
이루어진 파편 스캔으로, 데이터 품질 스트레스 사례로 의도적으로 남긴다. 분할 전에 쓰는 SFTF
전단(소스면 표본화와 방향 점수 지형)은 보충 그림~S1, S2에 있다.

기준 슬라이서는 오픈소스 CuraEngine이다. 직접 슬라이서 평가에서는 각 부품을 균일 48방향
메뉴에 대한 CuraEngine 탐색으로 배향하며, 실무 구현으로 coarse-to-local slicer-in-the-loop
최적화기를 쓴다. 즉 SFTF가 분할과 warm-start 방향을 제안하고 CuraEngine이 각 부품의 최종
배향을 고른다. 모든 직접 슬라이서 결과는 support everywhere와 FDM 임계 오버행각
$\theta_c=45^\circ$를 쓴다. 후보 생성과 ray-free 목적 점검에는 빠른 내부 screening 추정도
쓰지만, 이는 개발 중 후보 분할 순위와 재배향 메커니즘 설명에만 사용한다. 열두 형상 벤치마크를
포함한 보고된 모든 지지 비교는 CuraEngine으로 직접 평가한다(\S\ref{sec:cura},
\S\ref{sec:broad}). 이 구분은 중요하다. 두 스캔 해부 형상에서 screening 추정은 CuraEngine
대비 방법 순위를 뒤집으므로(보충 노트~S1), screening 수치는 핵심 주장 근거로 절대 쓰지
않는다. 내부 추정은 방향당 CuraEngine 슬라이스보다 약 $110\times$ 빠르지만(보충 표~S10)
통짜 배향 수준에서는 잘 일치하며(보충 그림~S5), 그래서 광역 screening 전용으로만 남긴다.
모든 실험은 Microsoft Windows 11(64-bit), AMD Ryzen 9 9950X3D(16코어/32스레드), 64 GB
메모리, NVIDIA GeForce RTX 5070 Ti(16 GB)에서 수행하였다. Python 3.12 환경은 NumPy, SciPy,
Trimesh, scikit-learn과 로컬 \texttt{tomo-sftf} 패키지를 사용하였고, 기준 슬라이서는
CuraEngine legacy 15.04이다.

\subsection{평가 지표}
\label{sec:metrics}

지지 클래스 순도는 각 부품이 일관된 지지 역할을 갖는지 잰다. 지지 클래스는
\[
\kappa_i\in\{\mathrm{bed},\mathrm{needs},\mathrm{supporter},\mathrm{free}\}
\]
이고, 분할 $\{\mathcal{P}_\ell\}$에 대해
\begin{equation}
\mathrm{Purity}=\frac{1}{N}
\sum_\ell \max_\kappa |\{i\in\mathcal{P}_\ell:\kappa_i=\kappa\}|.
\end{equation}
순도가 높을수록 각 부품이 오버행 위주 또는 자기지지 위주처럼 단일 지지 거동에 가깝다.
클래스 $\kappa_i$를 SFTF가 만들므로 순도만으로는 자기참조라는 비판이 가능하다. 두 가지
안전장치를 둔다. 첫째, 클래스를 외부 검증한다. 각 통짜 메쉬를 같은 기준 방향에서 CuraEngine
으로 슬라이싱하고, G-code의 지지 압출 경로를 파싱해 각 면을 슬라이서 출력만으로 재분류한다.
열두 형상 전체에서, 실제 CuraEngine 지지 접촉을 받는 면은 모두 SFTF가 \textsc{needs}로
라벨한다(열두 형상 모두 재현율 $1.0$). 정밀도는 $0.06$--$0.40$인데, 성긴 선패턴 지지가 그것이
보호하는 오버행 면의 일부에만 물리적으로 닿기 때문이다. 둘째, 모든 순도 비교를 이 슬라이서
유도 클래스로도 다시 계산한다(보충 표~S9). 두 정의의 형상별 방법 순위는 열두 형상 모두에서
일관되게 정렬되지 않는다. 여덟 분할기에서 Spearman $\rho$는 $-0.58$부터 $0.77$이고, 정의
가능한 열한 형상의 중앙값은 $0.42$이다. 따라서 슬라이서 유도 순도는
중복이 아니라 강건성 점검으로 다룬다.

% ============================ 3. 결과 =============================
\section{결과}

\subsection{분할 거동}

Bunny에서 DBSCAN 외 모든 방법이 전 면을 분할하였다. SFTF v2 조건화와 특징 추출은 $3.20$초,
선택된 빌드 방향은 $n^\ast\approx(-0.883,-0.277,0.379)$였다. 순수 지지흐름 방법은 각각
$1.84$초, $1.50$초에 5개, 14개 연결 부품을, 특징 융합 $k$-medoids는 분리 컴포넌트 분할 후
$1.11$초에 28개 연결 부품을 만들었다. DBSCAN은 더 느리고($9.11$초) 202개 잡음 면을 남겨
밀도 매개변수 민감성을
확인하였다(보충 표~S1). 응용 메쉬에서 주요 정성 거동이 드러난다. 간에서는 대부분의 방법이
거의 무지지 배향을 찾아 지지 질량의 변별력이 낮고 순도가 더 민감하다(보충 그림~S4).
\emph{Nefertiti}에서는 좌표 군집화가 공간 근접으로만 자르는 반면 SFTF 방법은 자기지지 왕관·
뒤통수를 안면·턱밑 오버행에서 분리한다(그림~\ref{fig:support-nefertiti}). 여러 지지 역할이
섞인 마네킨(그림~\ref{fig:support-manikin})에서는 좌표·기하 기준이 순도 약 $0.5$에 그치는
반면 SFTF 방법은 훨씬 일관된 지지 역할의 부품을 만든다. 마네킨의 방법별 순도 세부는 보충
표~S2에 있다.

\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{support_manikin_review_paired.png}
\caption{마네킨 분할 예시. 각 패널은 부모 분할과, 분리 부품을 screening 배향에 세워 추정
지지를 빨강으로 그린 것이다. SFTF 특징 융합 군집화는 컴팩트한 저지지 후보를, 순수 지지흐름
방법은 해석 가능한 지지역할 분할을 준다.}
\label{fig:support-manikin}
\end{figure}

\begin{figure}[H]
\centering
\includegraphics[width=0.86\textwidth]{support_nefertiti_equal_scale.png}
\caption{동일 스케일의 \emph{Nefertiti} 분할·지지. 좌표 전용 군집화는 공간 근접으로
자르지만 SFTF 방법은 자기지지 왕관·뒤통수를 안면·턱밑 오버행에서 분리한다.}
\label{fig:support-nefertiti}
\end{figure}

표~\ref{tab:application}은 현재 내부 TOMO screening 결과이다. 이 단계가 최종 슬라이서를
대체할 수 없는 이유가 드러난다. 내부 추정은 간의 세 분할에서 0으로 포화되고
\emph{Nefertiti}에서는 다방향 분할을 고르지만, 표~\ref{tab:siloop}의 CuraEngine 평가는
간에서 좌표 $k$-means, \emph{Nefertiti}에서 다방향 분할, 마네킨에서 $k$-medoids를 고른다.
따라서 screening은 후보와 메커니즘 탐색에만 쓰고
핵심 비교에는 쓰지 않는다.

\begin{table}[H]
\centering
\caption{SFTF v2 조건화를 적용한 응용 형상 내부 screening 결과. 순도는 SFTF 지지 클래스
순도(높을수록 좋음). 지지는 분리 부품을 v2 진단 배향에 세운 현재 CPU TOMO 추정
(g, 낮을수록 좋음)이며 최종 CuraEngine 결과가 아니다.}
\label{tab:application}
\begin{tabular}{llrrr}
\toprule
형상 & 방법 & 부품수 & 순도 & 지지 질량 (g)\\
\midrule
\input{generated_v2/sftf_v2_internal_tomo_rows_ko.tex}
\end{tabular}
\end{table}

\subsection{Ray-free screening 목적함수}

표~\ref{tab:validate}는 평활화 없는 원시 마네킨 분할에서 ray-free 목적을 평가한다. 이 형상에서
footprint proxy $\hat S_{\mathrm{fp}}$의 순위 상관은 중간 수준(Spearman $\rho=0.50$)이고,
height-field 보정 $\hat S_{\mathrm{hf}}$는 다섯 방법의 순서를 재현한다($\rho=1.00$). 그러나 세
응용 형상 전체에서는 일치도가 형상 의존적이며, 간에서는 두 proxy 열이 모두 0으로 퇴화해 순위
상관을 정의할 수 없다(보충 표~S10). 따라서 이 proxy는 후보 제안에 유용하지만 지지 질량의
보정된 대리 모델은 아니다. 실질적 메커니즘은 각
부품이 전체 형상이 취할 수 없는 방향으로 설 수 있는 재배향 자유도이다.

\begin{table}[H]
\centering
\caption{원시 마네킨 분할에서 ray-free 예측 지지 대 빠른 screening 지지 $S$. 예측량은 임의
proxy 단위, $S$는 그램 상당 screening 단위이다. $S$ 기준 정렬.}
\label{tab:validate}
\begin{tabular}{lrrrrr}
\toprule
방법 & cut & reorient & $\hat S_{\mathrm{fp}}$ & $\hat S_{\mathrm{hf}}$ & $S$ (g)\\
\midrule
\input{generated_v2/sftf_v2_proxy_rows.tex}
\end{tabular}
\end{table}

\subsection{CuraEngine 지지 검증}
\label{sec:cura}

screening 추정은 최종 슬라이서 결과로 쓰지 않는다. 핵심 비교에서는 같은 원시 분할을
CuraEngine으로 재평가하고 각 부품이 균일 48방향 메뉴에서 자기 슬라이서 최적 방향을 고르게
하였다. SFTF가 분할·warm-start를 제안하고 CuraEngine이 최종 배향을 탐색하는 실무
coarse-to-local 구현은 부품당 약 20회 슬라이싱을 예산으로 쓰지만, 여기 보고한 값은 모두
48방향 전체 메뉴를 사용한다.
표~\ref{tab:siloop}은 이 공정한 슬라이서 기준에서 세 응용 형상을 보인다. 최저 방법은 형상마다
다르다. 간은 좌표 $k$-means, \emph{Nefertiti}는 다방향 분할, 마네킨은 특징 융합
$k$-medoids가 최저이다. SFTF
screening 배향과 CuraEngine 최적 배향을 비교한 진단(보충 표~S5)은, SFTF 방향에 세우면 슬라이서
선택 대비 $1.9$--$19.7\times$ 많은 지지가 든다는 것을 보이며, 그래서 최종 배향은 슬라이서가 골라야
한다.

\begin{table}[H]
\centering
\caption{응용 형상의 부품별 CuraEngine 최적 지지(g): 각 부품을 48방향 탐색으로 자기
CuraEngine 최적 방향에 배향(CuraEngine legacy 15.04, $\theta_c=45^\circ$). 형상별 최저는
볼드; 평균 순위는 이 세 형상만 대상(열두 형상은 표~\ref{tab:broad}).}
\label{tab:siloop}
\begin{tabular}{lrrrrr}
\toprule
형상 & $k$-medoids & $k$-means & \texttt{flow\_region} & \texttt{support\_flow} & \texttt{build\_direction}\\
\midrule
\input{generated_v2/sftf_v2_application_cura_rows_ko.tex}
\end{tabular}
\end{table}

\subsection{선행 다방향 분해와의 비교}

가장 가까운 경쟁자는 Gao 등~[10]의 다방향 지지 최소화 분해이다. 원본 코드를 쓰지 않았으므로
핵심을 충실히 재구현하였다(면적가중 greedy set-cover로 무지지 방향 선택, ICM으로 공간
일관 라벨, 연결 컴포넌트로 부품 형성; Gao는 자연 부품 수로 평가). 재생성 마네킨 screening에서
Gao가 $0.021$ g로 최저이고 특징 융합 $k$-medoids가 $0.038$ g로 가깝다. 슬라이서 기준에서는
$k$-medoids가 마네킨($0.84$ 대 $6.59$ g)과 \emph{Nefertiti}($7.59$ 대 $30.70$ g)에서 Gao보다
낮지만, 간에서는 둘 다 좌표 $k$-means($4.72$ g)에 뒤진다. 순도는 별개의 비교축이다. 간에서
Gao 순도는 $0.60$인 반면 SFTF 지지흐름 분할은 $0.94$--$0.96$이다(보충 표~S6). 즉 SFTF는
역할 일관 부품을 만들지만 지지 우위는 형상과 부품 예산에 의존한다.

\subsection{광역 슬라이서 벤치마크와 자동 부품 수 결정}
\label{sec:broad}

ray-free 점수는 부품 수도 고를 수 있다. 특징 융합 과분할에서 인접 영역을 greedy 병합하고,
각 부품 수 $K$에 대해
\begin{equation}
K^\ast=\arg\min_K
\frac{\mathrm{score}(K)}{\max_K\mathrm{score}}
\;+\;
\alpha\frac{K}{K_{\max}}
\label{eq:auto}
\end{equation}
를 $\hat S_{\mathrm{hf}}$($\alpha=0.2$)로 평가한다. 재생성 마네킨 screening에서 이는 9개
연결 부품을 고른다. 광역 벤치마크는 여덟 분할기를 열두 형상에 적용하고, 결과 연결 부품
전부를 \S\ref{sec:cura}과 같은 48방향 프로토콜로 CuraEngine 재평가한다(총 $3{,}152$개 연결
부품, $142{,}100$회 슬라이싱). 표~\ref{tab:broad}은 부품별 CuraEngine 최적 지지의
합이다. 정성 개요와 대표 방법 비교는 보충 그림~S6, S7에, 열두 형상 v1--v2 영향 감사는
보충 표~S7에 있다.

\begin{table}[H]
\centering
\caption{광역 슬라이서 벤치마크: 모든 연결 부품을 같은 48방향 탐색으로 배향한 부품별
CuraEngine 최적 지지 합(g, 낮을수록 좋음; CuraEngine legacy 15.04, $\theta_c=45^\circ$).
\emph{no split} 열은 군집화 없이 각 자연 연결 컴포넌트를 자기 최적 방향에 세운 바닥 기준선.
각 행 최저는 볼드; 마지막 행은 동점 보정 평균 순위. 같은 분할의 지지 클래스 순도는 보충
표~S8.}
\label{tab:broad}
\resizebox{\textwidth}{!}{%
\begin{tabular}{lrrrrrrrrr}
\toprule
형상 (면수) & no split & $k$-means & Planar & Gao & basin & region & medoids & multi-dir & auto\\
\midrule
\input{generated_v2/sftf_v2_broad_rows_ko.tex}
\end{tabular}}
\end{table}

세 가지가 뒤따른다. 첫째, 모든 형상에서 최선인 분할기는 없지만 방법 간 차이는
유의하다(Friedman $\chi^2(8)=31.44$, $p=1.17\times10^{-4}$). 분리된 동일 라벨 쉘을 독립
배향하면 특징 융합 $k$-medoids가 최고 평균 순위($2.58$; bootstrap $95\%$ CI
$1.75$--$3.50$, 재표집의 $81.7\%$에서 최저 평균 순위 또는 동률)를 갖는다. 좌표 $k$-means 대비 쌍대
우위는 유의하지 않다(양측 Wilcoxon $p=0.733$). 또한 no-split 기준(평균 순위 $5.54$)이
anat-D1에서 단독 최선이다.

$k$-medoids는 더 많은 연결 부품을 만들므로 낮은 지지가 세밀한 분할이 산 재배향 자유일 수 있다.
최종 부품 수를 가장 가까운 값(차이 최대 2개)으로 맞춘 직접 통제는 이를 확인한다. 좌표
$k$-means가 열두 형상 모두에서 더 낮고(평균 $1.81$ 대 $6.07$ g; Wilcoxon
$p=0.0005$), dragon은 $3.30$ 대 $26.38$ g, anat-D1은 $1.66$ g으로 no-split
$4.68$ g보다도 낮다. 입력 특징만 바꾼 절제의 평균
순위는 좌표 $2.25$, 융합 $2.33$, SFTF-only $1.42$이다. 융합은 좌표보다 낫지 않고
($p=0.622$), SFTF-only는 융합보다 낮지만($p=0.016$), 연결성 후처리가 서로 다른 최종 부품
수를 만든다. 따라서 특징 자체의 고정 예산 인과 효과로 해석할 수 없다.

둘째, 연결 부피 프로토콜에서 $k$-medoids는 열두 중 넷에서 최저이다. 형상별 최저 방법은
좌표 $k$-means, Planar BSP, no-split, 다방향 분할, \texttt{flow\_region}으로도 나뉜다.
안전한 주장은 기본 부품 예산에서 특징 융합의 평균 순위가 가장 낮다는 것이지, 보편 또는 예산
일치 최적이라는 것이 아니다. 셋째, SFTF 정의 클래스에서는 \texttt{support\_flow}와
\texttt{flow\_region}의 평균 순도가 $0.770$, $0.753$으로 높고, 실제 CuraEngine 접촉으로
클래스를 유도하면 특징 융합 $k$-medoids가 최고($0.853$; 보충 표~S9)이다. SFTF 특징은 역할
일관성을 주지만 어느 분해의 지지가 최소인지는 슬라이서가 결정한다.

% ============================ 4. 고찰 ==========================
\section{고찰}

결과는 SFTF 기반 분할의 위치를 재설정한다. 가치는 한 방법이 어디서나 지지를 최소화한다는
것이 아니라, 버려지던 면별 지지흐름장을 재사용해 해석 가능하고 역할이 일관된 부품을 만들며
슬라이서가 각 부품 배향을 고르면 지지가 경쟁력 있다는 점이다. 식~\eqref{eq:support-decomp}이
그 이유를 설명한다. 시험 형상에서 재배향 항이 절단 항을 지배하므로, 지지 기둥 보존보다 각
부품이 잘 설 자유가 더 중요하다. 이는 부품을 v2 진단 방향에 세우면 공통 48방향 슬라이서
탐색보다 $1.9$--$19.7\times$ 나쁘다는 CuraEngine 진단과 일치한다. 따라서 최종 배향은 v2
점수가 아니라 슬라이서가 골라야 한다. 동일 부품 수 통제에서도 좌표 기준이
특징 융합과 같거나 더 낮으므로, SFTF 특징의 구별되는 가치는 원시 지지 최소화보다 해석 가능한
역할 일관 절단에 있다.

여러 한계가 뒤따른다. ray-free 점수는 절대 슬라이서 지지 질량 모델이 아니라 순위 proxy이다.
footprint 점수는 자기지지를 무시하고, height-field 보정도 격자 해상도에 의존한다. 열두 형상
재검증이 한계를 구체화한다. 두 스캔 해부 형상에서 screening 추정이 CuraEngine 대비 순위를
뒤집고(보충 노트~S1), proxy 구동 자동 부품 수 선택은 표~\ref{tab:broad}에서 특징 융합
$k$-medoids에 뒤진다. 다중시작 선택기는 단일 SFTF 방향·시드 민감도를 줄이지만 여전히 유한
후보 집합의 최선을 고르며 전역 최적 증명은 아니다. 실제 seed 0--4 재실행은 간에서
$3.12$--$8.71$ g, \emph{Nefertiti}에서 $3.23$--$7.59$ g, 마네킨에서 $0.65$--$3.82$ g의
변동을 보이므로 단일 seed 표를
이 분산과 함께 읽어야 한다. 본 방법은 접합을 경계 평활화로만 다루고,
조립 중심 분해~[8]와 달리 커넥터 기하·접합 강도·절단면 면적·조립 순서를 최적화하지 않는다.
끝으로 실험은 약 $10^5$면 이하 열두 형상이고, Gao 비교는 원저자 코드가 아닌 충실한 재구현이며,
무지지 골격 분할~[9]과는 아직 비교하지 않았다. 남은 핵심 방향은 최종 배향 탐색을 넘어
CuraEngine 평가를 분할 목적함수 자체에 통합하여 분할과 배향을 슬라이서 지지에 함께 최적화하는
것이다.

% ============================ 5. 결론 =========================
\section{결론}

본 논문은 SFTF의 면별 지지흐름 정보를 재사용하는 출력지향 메쉬 분할 방법을 제시하였다. 지지
역할·수신자·높이를 특징으로 노출함으로써 빌드 방향 후보 생성기를 분할 구동기로 바꾸며,
ray-free 지지 목적함수가 주요 메커니즘을 설명한다. 지지 감소는 원 지지 기둥 보존보다 각
부품이 유리한 배향을 자유롭게 고르는 데 더 좌우된다. 모든 분할의 모든 연결 부품을 같은 48방향
슬라이서 탐색으로 배향한 열두 형상 CuraEngine 재검증은 주장을 정직하게 한정한다. 어떤 분할기도
보편 최선은 아니지만, 분리된 동일 라벨 쉘을 독립 출력 부피로 다루면 특징 융합 $k$-medoids가
최고 평균 순위를 얻는다. 그러나 동일 최종 부품 수에서는 좌표 $k$-means가 열두 형상 모두에서
더 낮아, 그 평균순위 우위는 주로 더 세밀한 분할이 제공한 재배향 자유를 반영한다.
SFTF 방법이 일관되게 제공하는 것은 해석 가능성이다. 순수 지지흐름
영역 성장은 SFTF 클래스 순도가, 특징 융합 $k$-medoids는 Cura 유도 순도가 최고이다. 따라서
SFTF 기반 분할은 자유곡면 AM 형상을 위한 해석 가능·역할 일관 분해 도구로 가장 유용하며, 최종
배향과 부품 수 결정은 proxy가 아니라 슬라이서가 맡아야 한다.

% ============================ 후문 ============================
\section*{감사의 글}
이 논문은 정부(과학기술정보통신부)의 재원으로 한국연구재단의 지원을 받아 수행된 연구
(NRF-2022R1A2C1010072)이다. 연구 코드 구현, 그림 생성 스크립트, 원고 지원 자동화 일부에 AI
코딩 보조도구(OpenAI Codex, Anthropic Claude Code)를 사용하였다. 생성된 모든 코드·결과·원고
변경은 저자가 검토·검증하였으며, 방법론·데이터·결과·결론의 정확성에 대한 책임은 저자에게 있다.
연구 데이터, 신규 연구 이미지로 제시된 그림, 참고문헌 생성에는 생성형 AI를 쓰지 않았다.

\section*{참고문헌}
\begin{enumerate}
\item Oh Y, Zhou C, Behdad S. Part decomposition and assembly-based (re)design for additive manufacturing: a review. Addit Manuf 2018;22:230-242.
\item Ester M, Kriegel HP, Sander J, et al. A density-based algorithm for discovering clusters in large spatial databases with noise. In: Proc 2nd Int Conf Knowledge Discovery and Data Mining (KDD-96); 1996. p. 226-231.
\item Kaufman L, Rousseeuw PJ. Finding groups in data: an introduction to cluster analysis. New York: Wiley; 1990.
\item Katz S, Tal A. Hierarchical mesh decomposition using fuzzy clustering and cuts. ACM Trans Graph 2003;22(3):954-961.
\item Shapira L, Shamir A, Cohen-Or D. Consistent mesh partitioning and skeletonisation using the shape diameter function. Vis Comput 2008;24(4):249-259.
\item Lavou\'e G, Dupont F, Baskurt A. A new CAD mesh segmentation method, based on curvature tensor analysis. Comput Aided Des 2005;37(10):975-987.
\item Mamou K, Ghorbel F. A simple and efficient approach for 3D mesh approximate convex decomposition. In: Proc 16th IEEE Int Conf Image Processing (ICIP); 2009. p. 3501-3504.
\item Luo L, Baran I, Rusinkiewicz S, et al. Chopper: partitioning models into 3D-printable parts. ACM Trans Graph 2012;31(6):129:1-129:9.
\item Wei X, Qiu S, Zhu L, et al. Toward support-free 3D printing: a skeletal approach for partitioning models. IEEE Trans Vis Comput Graph 2018;24(10):2799-2812.
\item Gao Y, Wu L, Yan DM, et al. Near support-free multi-directional 3D printing via global-optimal decomposition. Graph Models 2019;104:101097.
\item Sul I. Support flow tensor field for fast build-orientation candidate generation in support-requiring additive manufacturing. 3D Print Addit Manuf. 2026. Submitted (code: \url{https://github.com/cfms-lab/SFTF_2026}).
\item Mitsuhashi N, Fujieda K, Tamura T, et al. BodyParts3D: 3D structure database for anatomical concepts. Nucleic Acids Res 2009;37(Database issue):D782-D785.
\end{enumerate}

\end{document}

