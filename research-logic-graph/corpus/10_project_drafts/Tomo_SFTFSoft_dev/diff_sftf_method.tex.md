# LaTeX source: diff_sftf_method.tex

Source: `D:\__SFTF_Projects(2026)\Tomo_SFTFSoft_dev\draft\diff_sftf_method.tex`

% =====================================================================
%  diff_sftf_method.tex — 미분가능 SFTF 손실항: 수식과 의사코드
%
%  빌드:  uv run python scripts/build_pdf.py  (단, _draft_paths 가 main.tex 를
%        자동탐색하므로 이 파일을 빌드하려면 main.tex 에 \input 하거나
%        직접:  xelatex diff_sftf_method.tex)
%  한글: xelatex + kotex.  시스템 한글 글꼴에 맞게 \setmainhangulfont 수정.
% =====================================================================
\documentclass[11pt]{article}

\usepackage{kotex}
\usepackage{fontspec}
\setmainhangulfont{Malgun Gothic}

\usepackage{amsmath,amssymb,amsfonts,bm}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{algorithm}
\usepackage{algpseudocode}
\usepackage{geometry}
\geometry{a4paper, margin=25mm}
\usepackage{hyperref}

\usepackage{tikz}
\usetikzlibrary{arrows.meta, calc, positioning, decorations.pathreplacing}

\newcommand{\nvec}{\bm{n}}
\newcommand{\mvec}{\bm{m}}
\newcommand{\cvec}{\bm{c}}
\newcommand{\softplus}{\operatorname{softplus}}
\newcommand{\relu}{\operatorname{relu}}

\title{미분가능 SFTF 손실항: 수식과 의사코드\\[2mm]
\large Differentiable Support Flow Tensor Field as a Loss Term}
\author{}
\date{\today}

\begin{document}
\maketitle

\begin{abstract}
원본 SFTF(Support Flow Tensor Field)는 빌드방향 $\nvec$ 에 대한 지지비용
$J_{\mathrm{SFTF}}(\nvec)=\tilde R_{\mathrm{aug}}(\nvec)+P(\nvec)=R(\nvec)+B(\nvec)+P(\nvec)$ 를
면별 레이캐스팅으로 계산해 최적 빌드방향을
\emph{이산 구면 샘플링}으로 고른다. 이 문서는 그 비용을 \textbf{빌드방향 $\nvec$ 과
정점 좌표 $V$ 양쪽에 대해 미분가능}하게 완화한 손실항 $L_{\mathrm{SFTF}}(V,\nvec)$ 를
유도한다. 비미분 연산은 본질적으로 하나뿐이다: 각 오버행 면을 단일 수신면(또는 바닥)으로
보내는 \emph{하드 레이캐스팅}. 이를 \textbf{후보 수신면과 바닥 슬롯에 대한 소프트
어텐션(softmax)} 으로 대체하고, 나머지(오버행, 면적, 법선, 높이)는 이미 $V,\nvec$ 의
매끄러운 함수임을 이용한다. 온도(temperature)를 sharpen 하면 $L_{\mathrm{SFTF}}\to J_w$
로 수렴하며, 기본 가중치에서는 $J_w=J_{\mathrm{SFTF}}$이다. 이 손실항은 (i) 경사 기반 빌드방향 최적화, (ii) 생성/위상 형상
최적화, (iii) 신경망 학습의 물리일관성 항으로 사용할 수 있다.
\end{abstract}

\section{원본 SFTF 지지비용 (이산)}
삼각형 면 $i$ 의 무게중심 $\cvec_i$, 단위 법선 $\mvec_i$, 면적 $A_i$ 라 하자.
빌드방향 $\nvec\in S^2$ 에 대해 바닥 높이와 면별 기본량은
\begin{align}
z_{\mathrm{plate}}(\nvec) &= \min_{\bm v\in V}\ \bm v\cdot\nvec, &
O_i(\nvec) &= \max\!\big(0,\,-\mvec_i\cdot\nvec\big), &
\eta_i(\nvec) &= \cvec_i\cdot\nvec - z_{\mathrm{plate}}(\nvec).
\end{align}
$O_i$ 는 오버행 강도다. 각 오버행 면에서 $-\nvec$ 방향으로 레이를 쏘아 수신면 $t_i$ 를
찾는다. 유효 수신 조건은 (코드와 동일하게) $t\neq i$, 레이거리 $>\varepsilon$,
지지높이 $h_{it}=(\cvec_i-\cvec_t)\cdot\nvec>\varepsilon$, 수신면 정렬
$\mvec_t\cdot\nvec>\tau_r\ (\tau_r{=}0.05)$ 이며, 여러 후보 중 \emph{가장 가까운}(최소 $h$)
면이 선택된다. 유효 수신이 없으면 면은 바닥으로 떨어진다. 이로부터
\begin{align}
P(\nvec) &= \!\!\sum_{i:\,\text{면지지}}\!\! O_i\,A_i\,A_{t_i},
&\text{(면–면 쌍 지지)}\label{eq:P}\\
B(\nvec) &= \!\!\sum_{i:\,\text{바닥지지}}\!\! O_i\,A_i\,\big(1+\alpha\,\eta_i\big),
\qquad \alpha=\tfrac{1}{D},
&\text{(바닥 지지)}\label{eq:B}\\
\bm F(\nvec) &= \!\!\sum_{i:\,\text{면지지}}\!\!
\frac{O_i A_i A_{t_i}}{1+\alpha\,h_{it_i}}\;\mvec_i\otimes\mvec_{t_i},
\qquad
R(\nvec)=\max\!\big(0,\,-\nvec^{\!\top}\!\operatorname{sym}(\bm F)\,\nvec\big),
\label{eq:F}
\end{align}
여기서 $D$ 는 메쉬 바운딩박스 대각, $\operatorname{sym}(\bm F)=\tfrac12(\bm F+\bm F^{\!\top})$.
출판된 SFTF의 기본 지지비용은
\begin{equation}
J_{\mathrm{SFTF}}(\nvec)=\tilde R_{\mathrm{aug}}(\nvec)+P(\nvec)
=R(\nvec)+B(\nvec)+P(\nvec),\qquad
\nvec^\ast=\arg\min_{\nvec\in S^2} J_{\mathrm{SFTF}}(\nvec).
\label{eq:J}
\end{equation}
$\tilde R_{\mathrm{aug}}=R+B$는 빌드플레이트를 법선 $n$의 가상 ground receiver로 추가한
증강 텐서의 Rayleigh 기여이다. 미분가능 완화와 물리 재가중을 위해
\begin{equation}
J_w(\nvec)=w_R\,R(\nvec)+w_P\,P(\nvec)+w_B\,B(\nvec)
\label{eq:Jw}
\end{equation}
도 사용한다. 기본 가중치 $w_R{=}w_P{=}w_B{=}1$이면 $J_w=J_{\mathrm{SFTF}}$이다.
원본의 핵–노름/$\sigma_1$ 항은 후보 선택을 바꾸지 않아 가중치 0으로 제외된 상태와 동일하다.

\paragraph{비미분 지점.} \eqref{eq:P}--\eqref{eq:F} 에서 미분을 막는 것은 오직
\emph{수신면 선택}($\arg\min$ 형태의 하드 레이캐스팅)과 그에 딸린 \emph{면/바닥
이진 판정}이다. $\max(0,\cdot)$, $\min$ 은 거의 모든 점에서 미분가능(부분기울기)하다.

\section{미분가능 완화}
\subsection{기하량 (정점 $V$ 의 매끄러운 함수)}
면 $i=(a,b,c)$ 에 대해
\begin{equation}
\cvec_i=\tfrac{\bm v_a+\bm v_b+\bm v_c}{3},\quad
\bm N_i=\tfrac12(\bm v_b-\bm v_a)\times(\bm v_c-\bm v_a),\quad
A_i=\lVert\bm N_i\rVert,\quad
\mvec_i=\frac{\bm N_i}{\lVert\bm N_i\rVert}.
\end{equation}
$\cvec_i,A_i,\mvec_i$ 는 (퇴화면을 제외하면) $V$ 에 대해 매끄럽다. 빌드방향은
$\nvec(\theta,\phi)=(\sin\theta\cos\phi,\sin\theta\sin\phi,\cos\theta)$ 로 두면
$S^2$ 제약이 자동 충족된다.

\subsection{소프트 오버행}
\begin{equation}
\tilde O_i=\softplus_\beta\!\big(-\mvec_i\cdot\nvec\big)
=\tfrac1\beta\log\!\big(1+e^{\,\beta(-\mvec_i\cdot\nvec)}\big)
\;\xrightarrow[\beta\to\infty]{}\;\max(0,-\mvec_i\cdot\nvec).
\end{equation}
임계각 $\theta_c$ 를 쓸 경우 게이트
$g_i=\sigma\!\big(\kappa(-\mvec_i\cdot\nvec-\cos\theta_c)\big)$ 를 곱한다($\sigma$: 로지스틱).

\subsection{소프트 수신면 배정 (핵심)}
소스 면 $i$ 의 후보 수신 집합 $\mathcal C(i)$ (전체 면, 또는 아래쪽 $k$-최근접). 각
후보 $j$ 에 대해 $\bm\delta=\cvec_j-\cvec_i$ 로 두고
\begin{equation}
h_{ij}=-(\bm\delta\cdot\nvec)\ \ (\text{$j$가 아래면}>0),\qquad
d_{ij}^2=\lVert\bm\delta\rVert^2-(\bm\delta\cdot\nvec)^2\ \ (\text{레이 횡오프셋}^2).
\end{equation}
원본의 하드 조건을 곱셈형 소프트 게이트로 완화한다:
\begin{equation}
a_{ij}=
\underbrace{\sigma\!\Big(\tfrac{h_{ij}}{\tau_b D}\Big)}_{\text{아래 게이트}}\;
\underbrace{\exp\!\Big(-\tfrac{d_{ij}^2}{2(\sigma_\ell D)^2}\Big)}_{\text{횡 정렬(레이)}}\;
\underbrace{\sigma\!\Big(\tfrac{\mvec_j\cdot\nvec-\tau_r}{\epsilon_r}\Big)}_{\text{수신면 상향}}\;
\underbrace{\exp\!\big(-\tfrac{\beta_n}{D}\,\relu(h_{ij})\big)}_{\text{최근접 선호}},
\quad a_{ii}=0.
\end{equation}
상수 \emph{바닥 슬롯} $a_0$ 를 더해 정규화하면 소스별 범주분포가 된다:
\begin{equation}
\pi_{ij}=\frac{a_{ij}}{\sum_{k\in\mathcal C(i)}a_{ik}+a_0},\qquad
\pi_i^{\mathrm{bed}}=\frac{a_0}{\sum_{k\in\mathcal C(i)}a_{ik}+a_0},\qquad
\sum_j\pi_{ij}+\pi_i^{\mathrm{bed}}=1.
\label{eq:pi}
\end{equation}
$a_0$ 는 레이가 바닥으로 "탈출"하는 정도를 조절한다. 게이트가 날카로워지고
$\beta_n\to\infty$ 면 $\pi_{i\cdot}$ 는 유효 최근접 수신면 하나로 집중되고, 유효 수신이
없으면 $\pi_i^{\mathrm{bed}}\to1$ 이 되어 원본 하드 레이캐스팅을 회복한다.

\subsection{소프트 지지비용}
바닥 높이는 soft-min 으로 (혹은 $\min$ 그대로) 둔다:
$z_{\mathrm{plate}}(\nvec)=-\tfrac{D}{\gamma}\log\sum_{\bm v}\exp\!\big(-\tfrac{\gamma}{D}\,\bm v\cdot\nvec\big)$.
\eqref{eq:P}--\eqref{eq:F} 의 단일 수신면 $t_i$ 를 기대값 $\sum_j\pi_{ij}(\cdot)$ 로 대체하면
\begin{align}
\tilde P &= \sum_i \tilde O_i\,A_i\sum_{j}\pi_{ij}A_j, \label{eq:Pt}\\
\tilde B &= \sum_i \tilde O_i\,A_i\;\pi_i^{\mathrm{bed}}\,\big(1+\alpha\,\relu(\eta_i)\big),\label{eq:Bt}\\
\tilde{\bm F}_{\mathrm{face}} &= \sum_i\sum_{j}\pi_{ij}\,
\frac{\tilde O_i A_i A_j}{1+\alpha\,\relu(h_{ij})}\;\mvec_i\otimes\mvec_j,
\qquad
\tilde R_{\mathrm{face}}=\softplus_\beta\!\big(-\nvec^{\!\top}\!\operatorname{sym}(\tilde{\bm F}_{\mathrm{face}})\,\nvec\big).\label{eq:Ft}
\end{align}
최종 손실항:
\begin{equation}
\boxed{\;L_{\mathrm{SFTF}}(V,\nvec)=w_R\,\tilde R_{\mathrm{face}}+w_P\,\tilde P+w_B\,\tilde B\;}
\qquad(\text{작을수록 지지 적음, 최소화 대상}).
\label{eq:loss}
\end{equation}

\begin{figure}[t]
\centering
\begin{tikzpicture}[>=Stealth, scale=1.0]
  % hard
  \begin{scope}
    \node at (1.4,2.6) {\small 하드 레이캐스팅 (원본)};
    \draw[thick] (0,2) -- (2.8,2);                       % surface
    \fill (1.4,2) circle (1.2pt) node[above=1pt] {\scriptsize $i$};
    \draw[thick] (0.4,0) -- (1.2,0); \fill (0.8,0) circle (1.0pt) node[below=1pt]{\scriptsize $t_2$};
    \draw[thick] (1.6,0.5) -- (2.4,0.5); \fill (2.0,0.5) circle (1.0pt) node[below=1pt]{\scriptsize $t_1$};
    \draw[->, red, thick] (1.4,1.95) -- (1.4,0.06);      % single hit (nearest)
    \node[red] at (2.25,1.1) {\scriptsize 단일 수신 $t_1$};
  \end{scope}
  % soft
  \begin{scope}[xshift=6.5cm]
    \node at (1.4,2.6) {\small 소프트 어텐션 (본 연구)};
    \draw[thick] (0,2) -- (2.8,2);
    \fill (1.4,2) circle (1.2pt) node[above=1pt] {\scriptsize $i$};
    \draw[thick] (0.4,0) -- (1.2,0); \fill (0.8,0) circle (1.0pt) node[below=1pt]{\scriptsize $j_2$};
    \draw[thick] (1.6,0.5) -- (2.4,0.5); \fill (2.0,0.5) circle (1.0pt) node[below=1pt]{\scriptsize $j_1$};
    \draw[->, blue, very thick] (1.4,1.95) -- (1.95,0.56) node[midway,right]{\scriptsize $\pi_{ij_1}$};
    \draw[->, blue!50, thick]   (1.4,1.95) -- (0.85,0.06) node[midway,left]{\scriptsize $\pi_{ij_2}$};
    \draw[->, blue!25] (1.4,1.95) -- (1.4,-0.35) node[below]{\scriptsize $\pi_i^{\mathrm{bed}}$};
  \end{scope}
\end{tikzpicture}
\caption{하드 레이캐스팅(좌)은 면 $i$ 를 최근접 수신면 하나로 보낸다(비미분).
본 연구(우)는 후보들과 바닥 슬롯에 대한 소프트 가중 $\pi$ 로 대체하여 미분가능하게 만든다.}
\label{fig:soft}
\end{figure}

\subsection{일관성 (soft$\to$hard)}
$\sigma_\ell\to0,\ \tau_b\to0,\ \epsilon_r\to0,\ \beta_n\to\infty,\ a_0\to0^+,\ \beta\to\infty,\ \gamma\to\infty$
극한에서 $\pi_{ij}\to\mathbb 1[j=t_i]$, $\pi_i^{\mathrm{bed}}\to\mathbb 1[\text{무수신}]$,
$\tilde O\to O$, $\tilde R_{\mathrm{face}}\to R$ 이 되어
$L_{\mathrm{SFTF}}\to J_w$ \eqref{eq:Jw} 를 회복한다. 기본 가중치에서는
$J_w=J_{\mathrm{SFTF}}$이므로 \eqref{eq:loss} 는 원본의 \emph{매끄러운 완화}다.

\section{기울기와 최적화}
\subsection{빌드방향에 대한 기울기}
$\nvec(\theta,\phi)$ 파라미터화에서는 자동미분이 $\partial L/\partial(\theta,\phi)$ 를 직접 준다.
$\nvec=\bm u/\lVert\bm u\rVert$ 로 직접 두는 경우, 단위구 접선공간으로 사영한다:
\begin{equation}
\bm g_\perp=(\bm I-\nvec\nvec^{\!\top})\,\nabla_{\nvec}L_{\mathrm{SFTF}},\qquad
\nvec\leftarrow \frac{\nvec-\rho\,\bm g_\perp}{\lVert\nvec-\rho\,\bm g_\perp\rVert}.
\end{equation}
예시로 $\tilde P$ 의 $\nvec$ 기울기는 $\tilde O_i,\ \pi_{ij}$ 의 $\nvec$ 의존을 통해
\[
\nabla_{\nvec}\tilde P=\sum_i\Big[(\nabla_{\nvec}\tilde O_i)A_i\!\sum_j\pi_{ij}A_j
+\tilde O_iA_i\!\sum_j(\nabla_{\nvec}\pi_{ij})A_j\Big],\quad
\nabla_{\nvec}\tilde O_i=-\sigma(\beta(-\mvec_i\!\cdot\!\nvec))\,\mvec_i,
\]
이며 $\nabla_{\nvec}\pi_{ij}$ 는 \eqref{eq:pi} 의 softmax 미분으로 닫힌 형태를 가진다.
실무에서는 자동미분(PyTorch)이 이 모두를 처리한다.

\subsection{정점에 대한 기울기}
$A_i,\mvec_i,\cvec_i,h_{ij},\eta_i$ 가 모두 $V$ 의 매끄러운 함수이므로
$\partial L_{\mathrm{SFTF}}/\partial V$ 가 연쇄법칙으로 흐른다. 이것이 생성/위상
최적화와 신경 형상 생성기 학습을 가능케 하는 핵심이다.

\subsection{온도 담금질(annealing)}
$D$ 상대 단위의 권장 초기값과 일정: $\sigma_\ell:0.05\!\to\!0.01$,
$a_0:0.05\!\to\!0.01$, $\beta_n:6\!\to\!24$, $\beta:16\!\to\!64$,
$\tau_b{=}10^{-3}$, $\tau_r{=}0.05$, $\epsilon_r{=}0.05$, $\gamma{=}64$.
초반에는 부드럽게(넓은 수용영역) 시작해 점차 날카롭게 만들어 하드 목적
\eqref{eq:J} 에 정렬시킨다.

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

\section{손실항의 활용}
\paragraph{(1) 빌드방향 최적화.} $V$ 고정, $\nvec$ 만 최적화. 원본의 512방향 구면샘플 +
콘 정련을 \emph{여러 시드의 경사하강 + 담금질}로 대체한다(알고리즘은 최종 정련 단계로도 유용).
\paragraph{(2) 생성/위상 형상 최적화.} $L=L_{\text{형상}}+\lambda\,L_{\mathrm{SFTF}}(V,\nvec^\ast)$
로 두고 $V$(또는 형상 생성기 파라미터)로 역전파하여 \emph{자기지지} 경향의 형상을 유도한다.
\paragraph{(3) 신경망 학습.} $L_{\mathrm{SFTF}}$ 를 미분가능 교사/물리일관성 항으로 사용한다.
예: 메쉬 그래프(면=노드, 지지쌍=엣지)를 입력받아 방향을 예측하는 GNN을 \emph{예측 방향의
$L_{\mathrm{SFTF}}$ 최소화}로 라벨 없이(self-supervised) 학습.

\section{검증}
참조구현 \texttt{python/src/SFTF\_Derivative/diff\_sftf.py} 의 스모크 테스트는 순전파/역전파
유한성, $\partial L/\partial\nvec$ 의 유한차분 일치(접선 성분 상대오차 $<10^{-3}$),
$\partial L/\partial V$ 흐름, 담금질 동작, 방향 최적화 수렴을 확인한다. (torch 미설치
환경에서는 동일 수식의 numpy 미러로 순전파 평활성, soft$\to$hard 집중[어텐션 엔트로피
$0.895\!\to\!0.029$], sharp 극한에서 $\arg\max_j\pi_{ij}$ 가 하드 최근접 수신면과 일치,
유한차분 기울기 안정[spread $\approx3\times10^{-5}$]을 검증했다.)

\end{document}

