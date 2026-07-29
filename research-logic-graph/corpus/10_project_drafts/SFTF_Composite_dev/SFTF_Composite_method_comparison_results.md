# Drape partition benchmark (R5)

Lower lock_area / dart_frac / seam / flatten / arap = better; purity higher.
(flatten = LSCM conformal flattening distortion; arap = ARAP inextensible
 stretch -- both 0 on a developable patch; arap is closer to the trellis.)

| part | tier | method | lock_area | dart_frac | purity | seam | flatten | arap |
|---|---|---|---|---|---|---|---|---|
| kidney_FMA7204 | real | coordinate | 0.273 | 0.470 | 0.716 | 956.4 | 0.224 | 0.078 |
| kidney_FMA7204 | real | axis_bsp | 0.474 | 0.655 | 0.684 | 1184.6 | 0.542 | 0.150 |
| kidney_FMA7204 | real | curvature | 0.651 | 0.871 | 0.871 | 1877.1 | 3.875 | 0.554 |
| kidney_FMA7204 | real | vsa | 0.478 | 0.764 | 0.785 | 1248.4 | 2.164 | 0.036 |
| kidney_FMA7204 | real | sftf_drape | 0.360 | 0.660 | 0.734 | 1377.3 | 3.701 | 0.150 |
| liver_FMA7197 | real | coordinate | 0.337 | 0.641 | 0.732 | 2172.9 | 5.541 | 0.255 |
| liver_FMA7197 | real | axis_bsp | 0.532 | 0.817 | 0.817 | 2943.3 | 0.498 | 0.135 |
| liver_FMA7197 | real | curvature | 0.690 | 0.907 | 0.907 | 4243.3 | 6.184 | 0.613 |
| liver_FMA7197 | real | vsa | 0.528 | 0.816 | 0.816 | 4184.6 | 3.904 | 0.075 |
| liver_FMA7197 | real | sftf_drape | 0.401 | 0.717 | 0.717 | 2850.7 | 5.043 | 0.240 |
| obj_airplane_b787 | real | coordinate | 0.075 | 0.287 | 0.547 | 1732.7 | 7.453 | 0.456 |
| obj_airplane_b787 | real | axis_bsp | 0.075 | 0.287 | 0.506 | 2767.9 | 4.381 | 0.425 |
| obj_airplane_b787 | real | curvature | 0.075 | 0.287 | 0.480 | 81.5 | 11.689 | 0.788 |
| obj_airplane_b787 | real | vsa | 0.075 | 0.287 | 0.450 | 1931.0 | 3.723 | 0.163 |
| obj_airplane_b787 | real | sftf_drape | 0.075 | 0.287 | 0.578 | 2282.0 | 7.459 | 0.479 |
| obj_car_supra | real | coordinate | 0.154 | 0.655 | 0.655 | 316.6 | 5.981 | 0.291 |
| obj_car_supra | real | axis_bsp | 0.154 | 0.655 | 0.655 | 287.1 | 3.152 | 0.291 |
| obj_car_supra | real | curvature | 0.154 | 0.655 | 0.655 | 148.0 | 7.017 | 0.415 |
| obj_car_supra | real | vsa | 0.154 | 0.655 | 0.655 | 2000.9 | 2.874 | 0.026 |
| obj_car_supra | real | sftf_drape | 0.154 | 0.655 | 0.655 | 311.5 | 7.468 | 0.315 |
| obj_yacht | real | coordinate | 0.081 | 0.126 | 0.666 | 2.2 | 4.499 | 0.108 |
| obj_yacht | real | axis_bsp | 0.081 | 0.126 | 0.666 | 2.9 | 4.053 | 0.105 |
| obj_yacht | real | curvature | 0.081 | 0.126 | 0.713 | 0.7 | 4.220 | 0.154 |
| obj_yacht | real | vsa | 0.081 | 0.126 | 0.672 | 4.9 | 0.670 | 0.008 |
| obj_yacht | real | sftf_drape | 0.081 | 0.126 | 0.666 | 2.2 | 4.499 | 0.108 |
| thingi_oxystele_shell_46774 | real | coordinate | 0.913 | 0.955 | 0.955 | 82.1 | 0.591 | 0.100 |
| thingi_oxystele_shell_46774 | real | axis_bsp | 0.907 | 0.950 | 0.950 | 46.9 | 0.709 | 0.227 |
| thingi_oxystele_shell_46774 | real | curvature | 0.958 | 0.969 | 0.969 | 5.3 | 11.859 | 0.728 |
| thingi_oxystele_shell_46774 | real | vsa | 0.958 | 0.969 | 0.969 | 197.2 | 18.656 | 0.422 |
| thingi_oxystele_shell_46774 | real | sftf_drape | 0.905 | 0.946 | 0.946 | 105.1 | 1.937 | 0.163 |
| thingi_shell01_41909 | real | coordinate | 0.761 | 0.873 | 0.873 | 760.6 | 0.986 | 0.161 |
| thingi_shell01_41909 | real | axis_bsp | 0.889 | 0.917 | 0.917 | 2799.1 | 2.335 | 0.126 |
| thingi_shell01_41909 | real | curvature | 0.948 | 0.936 | 0.936 | 28.4 | 5.441 | 0.728 |
| thingi_shell01_41909 | real | vsa | 0.948 | 0.936 | 0.936 | 1212.7 | 3.743 | 0.120 |
| thingi_shell01_41909 | real | sftf_drape | 0.799 | 0.892 | 0.892 | 957.1 | 1.147 | 0.146 |
| thingi_turritella_shell_44704 | real | coordinate | 0.916 | 0.942 | 0.942 | 1484.1 | 3.552 | 0.187 |
| thingi_turritella_shell_44704 | real | axis_bsp | 0.902 | 0.927 | 0.927 | 641.7 | 1.360 | 0.269 |
| thingi_turritella_shell_44704 | real | curvature | 0.952 | 0.953 | 0.953 | 2800.7 | 11.333 | 0.655 |
| thingi_turritella_shell_44704 | real | vsa | 0.957 | 0.952 | 0.952 | 6548.9 | 7.030 | 0.244 |
| thingi_turritella_shell_44704 | real | sftf_drape | 0.899 | 0.926 | 0.926 | 3738.4 | 7.201 | 0.201 |
| nefertiti | real | coordinate | 0.716 | 0.844 | 0.844 | 3928.0 | 0.955 | 0.209 |
| nefertiti | real | axis_bsp | 0.767 | 0.894 | 0.894 | 4627.0 | 1.194 | 0.235 |
| nefertiti | real | curvature | 0.851 | 0.941 | 0.941 | 38093.5 | 4.998 | 0.643 |
| nefertiti | real | vsa | 0.797 | 0.900 | 0.900 | 25965.3 | 6.438 | 0.216 |
| nefertiti | real | sftf_drape | 0.738 | 0.869 | 0.869 | 10222.9 | 6.199 | 0.292 |

## Aggregate (mean over shapes)

| method | lock_area | dart_frac | purity | seam | flatten | arap |
|---|---|---|---|---|---|---|
| coordinate | 0.469 | 0.643 | 0.770 | 1270.6 | 3.309 | 0.205 |
| axis_bsp | 0.531 | 0.692 | 0.780 | 1700.1 | 2.025 | 0.218 |
| curvature | 0.596 | 0.738 | 0.825 | 5253.2 | 7.402 | 0.586 |
| vsa | 0.553 | 0.712 | 0.793 | 4810.4 | 5.467 | 0.146 |
| sftf_drape | 0.490 | 0.675 | 0.776 | 2427.5 | 4.962 | 0.232 |