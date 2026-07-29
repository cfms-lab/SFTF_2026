# SFTF notation crosswalk

작성일: 2026-07-15
적용 버전: `SFTF-v2-surface`
상태: revision-only; 현재 제출 artifact에는 소급 적용하지 않음

## 현재 제출본과 계열 표준의 대응

| 현재 원고 | 계열 표준 | 비고 |
|---|---|---|
| \(\{(x_k,m_k)\}_{k=1}^K\) | \(\Psi_K^{\mathrm{score}}(n)\) | deterministic area-uniform score field |
| \(n\) | \(n\) | build direction, ray는 \(-n\) |
| \(O_k=\max(0,-m_k\cdot n)\) | \(d_k(n)\) 또는 gated \(O_k\) | 무차원 downwardness |
| \(r_k\) | \(m_{t_k}\) 또는 \(m_k^{\mathrm{recv}}\) | 제출본의 historical receiver-normal alias |
| \(F_{\mathrm{pair}}\) | \(F_\Pi\)의 hard one-hot corollary | tensor moment consumer |
| \(S_{v2}(n)=R(n)+B(n)\) | \(J_{\mathrm{score}}(n)\) | dimensionless direction score |

## revision에서 적용할 변경

1. Method 첫 문단에 `SFTF-v2-surface`를 표시한다.
2. sample field를 \(\Psi_K^{\mathrm{score}}\)로 선언한다.
3. receiver normal \(r_k\)를 \(m_{t_k}\)로 바꿔 micro-sample index 및
   Cluster in-degree와 충돌하지 않게 한다.
4. score의 렌더링 이름을 \(J_{\mathrm{score}}\)로 맞추되, 코드/ESM의
   `S_v2` identifier는 reproducibility alias로 남긴다.
5. process angle을 `(angle_value, angle_semantics, t_d)`로 기록한다.

## 반드시 구별할 대상

- `SFTF-v1-face`: face/area-product legacy functional
- `SFTFSoft-v1-centroid`: \(\pi^{\mathrm{cent}}\) affinity router
- `EB-DFSVR-v2-sparse`: \(\Xi_S^{\mathrm{vis}}\)와 \(\pi^{\mathrm{fh}}\)
- `SFTFCluster-v2-field`: all-face \(\Psi_F^{\mathrm{part}}\)와 adjacency graph

특히 score sample field는 all-face partition field가 아니며, 현재 제출된
SFTF PDF의 수치와 protocol hash는 이 crosswalk 때문에 바뀌지 않는다.
