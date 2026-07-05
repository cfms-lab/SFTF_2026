# SFTF 논문 수정 지시서 — 데이터셋 기술을 §Evaluation Protocol and Datasets로 통합

> 대상 파일: `SFTF_draft.tex` (재구조화 완료본).
> 목적: `\section{Evaluation Protocol and Datasets}` 제목이 내용과 맞도록, 현재 Results 아래
> `Verification … Five-Group > Experimental Setup`에 흩어져 있는 **데이터셋(A–E) 정의와 하드웨어/소프트웨어 환경**을
> 이 섹션으로 끌어올린다. 5그룹의 **타이밍 측정/실험 구성**은 Results에 그대로 둔다.
> 규칙: **본문 텍스트·표·수치·`\label`·`\cite`는 그대로 유지**(이동만 하고 문구는 바꾸지 않음). 새 `\label` 1개만 추가.

---

## 편집 1 — §3에 데이터셋 하위절 신설(이동된 텍스트 붙여넣기)

§Evaluation Protocol and Datasets 시작부에 새 `\subsection{Datasets and Experimental Environment}`를 만들고,
아래 블록을 그 안에 넣는다.

**현재 (find):**
```latex
\section{Evaluation Protocol and Datasets}

\subsection{Comparison Targets and Evaluation Protocol}
```

**교체 (replace):**
```latex
\section{Evaluation Protocol and Datasets}

\subsection{Datasets and Experimental Environment}
\label{sec:datasets}

The dataset consists of five groups that deliberately separate and control the two axes of \emph{shape difficulty} and \emph{mesh scale}.
A--C set the scale in the $\sim$$10^1$--$10^5$-face range and vary the difficulty axis from basic shapes to freeform organic shapes,
revealing the \emph{fixed-cost floor} of the exhaustive sweep (a cost almost independent of mesh complexity).
D--E fix the difficulty as real manufacturing parts while pushing the scale axis from $256$ faces to $1.04\times10^6$ faces,
revealing the \emph{adaptive cost} by which the SFTF candidate-evaluation cost increases adaptively to mesh complexity.
Therefore A--E is not a single size ramp, and the partial overlap of the face-count ranges of groups C and D
is the result of a design that separates and controls the two axes, not an ordering error.
\begin{itemize}
\item \textbf{A (basic shapes, 5; lower difficulty)}: cube, sphere, cylinder, cone, torus (face count $\sim$$10^1$--$10^3$).
\item \textbf{B (simple functional parts, 5; mid difficulty)}: u\_bracket, hook, c\_clamp, pipe\_elbow, hollow\_box.
\item \textbf{C (organic/freeform benchmarks, 5; upper difficulty)}: standard scan/sculpture meshes such as Bunny ($69{,}662$ faces), manikin, dragon ($\sim$$10^5$ faces), happy, lucy. The Stanford grid meshes used in \S\ref{sec:baseline} are exactly this group.
\item \textbf{D (Thingi10K set 1, 10; lower scale)}: real manufacturing parts with $256$--$88{,}106$ faces~\cite{Thingi10K}.
\item \textbf{E (Thingi10K set 2, 10; upper scale)}: large high-resolution meshes with about $5.1\times10^5$--$1.04\times10^6$ faces.
\end{itemize}
All timing experiments were run on a Windows 11 Education 64-bit workstation with an AMD Ryzen 9 9950X3D CPU
(16 cores, 32 logical threads), 125 GB RAM, and an NVIDIA GeForce RTX 5080 GPU (16 GB, driver 595.79).
The Python implementation used Python 3.12.13 with NumPy 1.26.4, SciPy 1.17.1, Trimesh 4.4.0, Matplotlib 3.11.0, and scikit-learn 1.9.0.
TOMO\_CPU and TOMO\_CUDA were called through Windows DLL interfaces, and the SFTF\_C++ implementation was built as a Windows x64 C++ DLL
using the Visual Studio 2022/MSVC toolchain with OpenMP parallelization.

\subsection{Comparison Targets and Evaluation Protocol}
```

> 주의: 위 itemize의 C 항목에서 원문의 `the preceding sections`를 `\S\ref{sec:baseline}`로 바꿨다(이제 데이터셋이
> 앞에 오므로 "preceding"이 맞지 않기 때문). 나머지 문장은 원문과 동일하다.

---

## 편집 2 — Five-Group의 Experimental Setup에서 이동분 제거 후 포인터로 대체

`\subsubsection{Experimental Setup}` 안에서, 위로 옮긴 **데이터셋 정의 + 하드웨어/소프트웨어 문단**(이동된 블록과
동일한 텍스트)을 지우고 한 줄 포인터로 바꾼다. 그 아래 측정 항목 설명("For the $35$ meshes A--E, we recorded …")은 **그대로 둔다.**

**현재 (find):**
```latex
The dataset consists of five groups that deliberately separate and control the two axes of \emph{shape difficulty} and \emph{mesh scale}.
```
… (이 문장부터) …
```latex
using the Visual Studio 2022/MSVC toolchain with OpenMP parallelization.
```
**조치:** 위 두 anchor 사이의 전체 블록(데이터셋 설명 문단 + `\begin{itemize}…\end{itemize}` + 하드웨어/소프트웨어 문단)을
다음 한 줄로 **교체**한다.

**교체 (replace):**
```latex
The five-group dataset (A--E) and the hardware/software environment used for all timing measurements are described in \S\ref{sec:datasets}.
```

(결과적으로 `\subsubsection{Experimental Setup}`에는 이 포인터 문장과, 기존의 "For the $35$ meshes A--E, we recorded …"
이하 측정 설명만 남는다.)

---

## 확인 (Definition of Done)

- [ ] §Evaluation Protocol and Datasets가 `Datasets and Experimental Environment` + `Comparison Targets and Evaluation Protocol`
      두 하위절을 가지며, 제목의 "Datasets"가 실제 내용과 일치함.
- [ ] 데이터셋/itemize/하드웨어 문단이 §3에만 존재하고 Five-Group에는 중복되지 않음(원위치는 포인터 한 줄).
- [ ] `\label{sec:datasets}` 추가됨, Five-Group 포인터의 `\S\ref{sec:datasets}`가 정상 해소됨.
- [ ] C 항목의 `\S\ref{sec:baseline}` 참조가 정상 해소됨(전방참조 깨짐 없음).
- [ ] 어떤 표·수치도 변경되지 않음. LaTeX 정상 컴파일, 모든 `\ref`/`\cite`/그림·표 번호 정상.
