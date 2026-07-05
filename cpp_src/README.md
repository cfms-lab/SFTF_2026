# TSE6 C++ v_ss Benchmark

This folder contains a Visual Studio 2022 compatible C++17 console benchmark for
the `v_ss` calculation path.

The current Python project depends on `trimesh`, `scipy`, `moderngl`, `coacd`,
`plotly`, and `polyscope`. To keep the C++ side buildable with Visual Studio
2022 alone, the Python exporter prepares `v_tc` and visible face ids. The C++
program builds the core `ShTensor` data and benchmarks the numeric `v_ss` path:

```text
v_ss = v_tc - V_o - V_nv
V_o  = V_al - V_be
```

## 1. Export Python Data

Run from the repository root:

```powershell
python cpp_test.py
```

Optional:

```powershell
python cpp_test.py --mesh "Experimental/etc/(7)Bunny_1k.obj" --angle-step 5
```

This writes:

```text
cpp_src/tse6_cpp_input.txt
```

To skip writing that file and pass the generated data directly to the executable:

```powershell
python cpp_test.py --pipe --threads 8
```

The current `TSE6VSS2` path leaves triangle normals, bottom planes, and
support-volume accumulation to C++.

## 2. Build With Visual Studio 2022

From a Developer PowerShell:

```powershell
cmake -S cpp_src -B cpp_src/build -G "Visual Studio 17 2022" -A x64
cmake --build cpp_src/build --config Release
```

Or open the `cpp_src` folder directly in Visual Studio 2022 as a CMake project.

If CMake is not available, compile directly from a Visual Studio 2022 Developer
PowerShell:

```powershell
cl /EHsc /O2 /openmp /std:c++17 /Fe:cpp_src\tse6_vss.exe cpp_src\TSE6_vss.cpp
```

## 3. Run C++ Benchmark

```powershell
.\cpp_src\build\Release\tse6_vss.exe cpp_src\tse6_cpp_input.txt
```

Direct `cl.exe` build output:

```powershell
.\cpp_src\tse6_vss.exe cpp_src\tse6_cpp_input.txt
```

For timing only:

```powershell
.\cpp_src\build\Release\tse6_vss.exe cpp_src\tse6_cpp_input.txt --quiet
```

Control CPU worker threads:

```powershell
.\cpp_src\build\Release\tse6_vss.exe cpp_src\tse6_cpp_input.txt --quiet --threads 8
```

The program prints the C++ compute time, maximum absolute error versus the
Python-exported `v_ss` when legacy expected values are present, and the C++
`v_ss` matrix unless `--quiet` is used.

## Scope

This is not a full replacement for `moderngl`, `coacd`, `trimesh`, or Plotly.
It is a focused C++ port of the `ShTensor` numeric path after the Python side
has prepared visibility and `v_tc` data.
