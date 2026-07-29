# SFTFCluster notation crosswalk

작성일: 2026-07-15
적용 버전: `SFTFCluster-v2-field`
상태: main/supplementary TeX에 표기 정규화 적용

## 적용된 변경

| 이전 표기 | 현재 표기 | 이유 |
|---|---|---|
| \(S(n)\) | \(J_{\mathrm{score}}(n)\) | direction score와 support mass 분리 |
| 암묵적 score samples | \(\Psi_K^{\mathrm{score}}(n)\) | selector field 명시 |
| 암묵적 all-face records | \(\Psi_F^{\mathrm{part}}(n)\) | partition field 명시 |
| receiver count \(r_i\) | \(\nu_i^{\mathrm{in}}\) | receiver normal/micro-sample과 충돌 제거 |
| \(\Phi_{\mathrm{SFTF}}\) | \(X_F^{\mathrm{part}}\) | tensor payload \(\Phi\)와 분리 |
| clustering matrix \(M\) | \(X_{\mathrm{cluster}}\) | mesh \(\mathcal M\)과 분리 |
| \(S(\Pi)\) | \(\widehat J_{\mathrm{part}}(\Pi)\) | ray-free proxy임을 표시 |
| \(P_\ell(d)\) | \(C_\ell(d)\) | part proxy를 명확히 표시 |
| \(g_i(d;\theta_c)\) | \(\gamma_i(d;t_d)\) | angle convention과 threshold 분리 |

## 해상도 계약

- selector: 8,192 deterministic surface samples로 2,048 directions를 평가하는
  \(\Psi_K^{\mathrm{score}}\)
- partitioner: 선택 방향에서 모든 \(N\) face의 record를 다시 계산하는
  \(\Psi_F^{\mathrm{part}}\)
- graph consumer: \(\Psi_F^{\mathrm{part}}\)와 \(G_F=(F,E_F)\)를 함께 사용

따라서 direction-score samples만으로 partition을 생성하거나, scalar score에서
all-face field를 복원한다고 주장하지 않는다.

## 변경하지 않은 것

코드 identifier, partition label, frozen benchmark, CuraEngine 결과, 표의 수치,
그림 및 실험 protocol은 변경하지 않았다. 원고의 수학 표기와 설명만
정규화했다.
