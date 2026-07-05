cmake_minimum_required(VERSION 3.20)

project(TSE6VssCpp LANGUAGES CXX)

find_package(OpenMP)

add_executable(tse6_vss "${CMAKE_CURRENT_SOURCE_DIR}/TSE6_vss.cpp")
target_compile_features(tse6_vss PRIVATE cxx_std_17)
if (OpenMP_CXX_FOUND)
    target_link_libraries(tse6_vss PRIVATE OpenMP::OpenMP_CXX)
elseif (MSVC)
    target_compile_options(tse6_vss PRIVATE /openmp)
else()
    message(FATAL_ERROR "OpenMP was not found for the selected C++ compiler")
endif()

set(TSE6_CPP_INPUT "${CMAKE_CURRENT_SOURCE_DIR}/tse6_cpp_input.txt")
if (EXISTS "${TSE6_CPP_INPUT}")
    add_custom_command(
        TARGET tse6_vss
        POST_BUILD
        COMMAND "${CMAKE_COMMAND}" -E copy_if_different
            "${TSE6_CPP_INPUT}"
            "$<TARGET_FILE_DIR:tse6_vss>/tse6_cpp_input.txt"
        VERBATIM
    )
endif()

set_property(
    TARGET tse6_vss
    PROPERTY VS_DEBUGGER_WORKING_DIRECTORY "$<TARGET_FILE_DIR:tse6_vss>"
)

if (MSVC)
    target_compile_options(tse6_vss PRIVATE
        $<$<CONFIG:Release>:/O2>
        $<$<CONFIG:RelWithDebInfo>:/O2>
        $<$<CONFIG:MinSizeRel>:/O2>
        $<$<CONFIG:Debug>:/Od>
        /W4
        /permissive-
    )
else()
    target_compile_options(tse6_vss PRIVATE -O3 -Wall -Wextra)
endif()

# ---------------------------------------------------------------------------
# sftf_cpp: C++/DLL port of the Support Flow Tensor Field candidate generator.
# Built as a shared library (Windows x64 DLL) and copied next to
# Tomo_Shell2026.dll inside the Tomo_GPU2026 bridge package so the ctypes bridge
# (tomo_sftf.py) can load it.
# ---------------------------------------------------------------------------
add_library(sftf_cpp SHARED "${CMAKE_CURRENT_SOURCE_DIR}/sftf_cpp.cpp")
target_compile_features(sftf_cpp PRIVATE cxx_std_17)
set_target_properties(sftf_cpp PROPERTIES OUTPUT_NAME "sftf_cpp" PREFIX "")

if (OpenMP_CXX_FOUND)
    target_link_libraries(sftf_cpp PRIVATE OpenMP::OpenMP_CXX)
elseif (MSVC)
    target_compile_options(sftf_cpp PRIVATE /openmp)
endif()

if (MSVC)
    target_compile_options(sftf_cpp PRIVATE
        $<$<CONFIG:Release>:/O2>
        $<$<CONFIG:RelWithDebInfo>:/O2>
        $<$<CONFIG:MinSizeRel>:/O2>
        $<$<CONFIG:Debug>:/Od>
        /W4
        /permissive-
    )
else()
    target_compile_options(sftf_cpp PRIVATE -O3 -Wall -Wextra)
endif()

# Copy the built DLL into the Tomo_GPU2026 bridge package (alongside Tomo_Shell2026.dll).
set(SFTF_PACKAGE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/Tomo_GPU2026")
add_custom_command(
    TARGET sftf_cpp
    POST_BUILD
    COMMAND "${CMAKE_COMMAND}" -E copy_if_different
        "$<TARGET_FILE:sftf_cpp>"
        "${SFTF_PACKAGE_DIR}/sftf_cpp.dll"
    VERBATIM
)
