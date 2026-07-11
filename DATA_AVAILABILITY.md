# Data Availability

This snapshot includes the mesh/data corpus required for the paper review under
`sftf_Mesh_Data/`, with large mesh files excluded to keep the GitHub snapshot
small. Mesh files larger than 10 MB are intentionally not committed to GitHub.

Excluded files:

- `sftf_Mesh_Data/g5test/Group_D6_37111.stl`
- `sftf_Mesh_Data/g5test/Group_D7_37137.stl`
- `sftf_Mesh_Data/g5test/Group_E10_65942.stl`
- `sftf_Mesh_Data/g5test/Group_E1_39507.stl`
- `sftf_Mesh_Data/g5test/Group_E2_45809.stl`
- `sftf_Mesh_Data/g5test/Group_E2_790253.stl`
- `sftf_Mesh_Data/g5test/Group_E3_45811.stl`
- `sftf_Mesh_Data/g5test/Group_E3_931902.stl`
- `sftf_Mesh_Data/g5test/Group_E4_439142.stl`
- `sftf_Mesh_Data/g5test/Group_E4_46012.stl`
- `sftf_Mesh_Data/g5test/Group_E5_55280.stl`
- `sftf_Mesh_Data/g5test/Group_E6_59197.stl`
- `sftf_Mesh_Data/g5test/Group_E7_61384.stl`
- `sftf_Mesh_Data/g5test/Group_E8_64445.obj`
- `sftf_Mesh_Data/g5test/Group_E8_64445.obj.inverted.bak`
- `sftf_Mesh_Data/g5test/Group_E9_64446.obj.inverted.bak`
- `sftf_Mesh_Data/g5test/Group_E9_64446.obj.retired`
- `sftf_Mesh_Data/g5test/Group_E9_82675.stl`

To reproduce analyses that require any excluded mesh, download the corresponding
file from the project data archive supplied with the manuscript and place it at
the same relative path inside the repository. For example:

```text
sftf_Mesh_Data/g5test/Group_E10_65942.stl
```

All scripts resolve mesh data from the in-repository `sftf_Mesh_Data/` folder
first. In the development checkout they also fall back to a sibling
`../sftf_Mesh_Data/` folder.

Most paper reproduction scripts use the stored TOMO grids and the included
ratio-valid meshes. If an excluded mesh is absent, scripts that iterate over
available meshes should skip it or report it as missing; copy the file into the
path above before rerunning workflows that require the complete D/E-group mesh
set.
