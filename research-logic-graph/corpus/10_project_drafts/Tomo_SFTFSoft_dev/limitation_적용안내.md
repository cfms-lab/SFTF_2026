# SFTFSoft 한계 절 적용 안내 (2026-07-14)

> 근거: Codex 지적 + `Tomo_DiffSupport_dev\tests\test_centroid_counterexample.py` 반례.
> 무게중심 기반 receiver attention 은 sharp 극한에서 ray-cast receiver 로 수렴하지
> 않을 수 있음(광선이 빗나가는 면이 무게중심상 더 가까우면 σ→0 에서 오배정이 강화).
> 본 문서는 `limitation_centroid_attention.tex` 삽입 위치와, 기존 수렴 주장 3곳의
> 문구 한정(claim-scoping) 수정안을 제시한다. **원고 본문은 수정하지 않았음** —
> 검토 후 직접 반영 요망.

## 0. 새 subsection 삽입

- 파일: `limitation_centroid_attention.tex` (이 폴더에 배치됨)
- 위치: `\subsection{Applications and Degenerate Optima}` 끝난 뒤,
  `\section{Conclusion}` 직전 권장.
- 사전 작업: `\subsection{From Hard Routing to Soft Flow}` 에
  `\label{sec:softflow}` 가 없으면 추가 (새 절이 `\ref{sec:softflow}` 참조).

## 1. Method 절 수렴 주장 한정 (main_en.tex 약 253–263행)

**현행:**
> As the temperature parameters sharpen and the candidate set contains the
> unique hard receiver, $\pi_{ij}$ concentrates on $t_i$ and
> $L_{\mathrm{SFTF}}\rightarrow J_w$.

**수정안:**
> As the temperature parameters sharpen, $\pi_{ij}$ concentrates on the
> affinity-maximizing candidate; whenever this maximizer coincides with the
> hard receiver $t_i$ --- a geometric condition that holds on the meshes used
> here but can fail in adversarial configurations
> (Section~\ref{sec:centroid-limit}) --- $L_{\mathrm{SFTF}}\rightarrow J_w$.

**같은 문단 끝의:**
> ...so the differentiable version adds gradients without changing the
> support relation it converges to.

**수정안:**
> ...so, under the receiver-agreement condition of
> Section~\ref{sec:centroid-limit}, the differentiable version adds gradients
> without changing the support relation it converges to.

## 2. Figure `fig:relaxation` 캡션 (약 271–272행)

**현행:**
> The soft receiver assignment converges to the hard SFTF objective as the
> attention sharpens, while retaining gradients ...

**수정안:**
> The soft receiver assignment converges to the hard SFTF objective as the
> attention sharpens whenever the sharpened attention selects the ray-cast
> receiver (Section~\ref{sec:centroid-limit}), while retaining gradients ...

## 3. Conclusion (약 941–943행)

**현행:**
> The loss recovers the weighted original objective in the sharp limit and
> provides accurate gradients ...

**수정안:**
> The loss recovers the weighted original objective in the sharp limit
> whenever the sharpened attention agrees with the ray-cast receiver --- the
> gate, overhang, and plate relaxations converge unconditionally, and
> Section~\ref{sec:centroid-limit} delimits the receiver condition --- and
> provides accurate gradients ...

## 4. (선택) Contribution 절 (약 181–186행)

"soft-attention relaxation framework" 기여 서술에 다음 한 구절 추가 권장:

> ..., and we delimit exactly when the sharp limit of the attention recovers
> the ray-cast assignment (Section~\ref{sec:centroid-limit}).

정직성 규율(자기 헤드라인 반증 대조군)과 톤이 일치하며, 리뷰어가 반례를 먼저
발견했을 때의 리스크를 선제 차단한다.

## 5. 손대지 말 것

- `S_g`/`S_g^{hard}` 예측 서사(+0.80/+0.87), Cura 96–100% 제거 결과, STE 게이트
  절 — 이 결함과 무관하므로 수정 불요.
- supplementary 의 gradient 유한차분 검증(3×10⁻¹⁰) — soft 목적함수 자체의
  gradient 정확성 주장이므로 유효. 단 "hard 와의 일치" 로 오독될 문구가 있으면
  동일하게 한정.

## 6. 특허 관련 별도 확인 (변리사)

개량발명(Soft) 명세서(`draft/patent/명세서/SFTFSoft_특허명세서.tex`)의 독립항이
무게중심 attention 구현에 특정돼 있는지 확인. 필요 시:
(a) 라우팅 완화를 상위 개념으로 청구, (b) first-hit transmittance 방식(DFSVR)을
별건 발명으로 분리 검토. ※ 본 안내는 법률 자문이 아님.
