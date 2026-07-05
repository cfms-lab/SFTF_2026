#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

#ifdef _OPENMP
#include <omp.h>
#endif

struct Vec3 {
    double x = 0.0;
    double y = 0.0;
    double z = 0.0;
};

struct Tri {
    Vec3 a;
    Vec3 b;
    Vec3 c;
};

struct Plane {
    Vec3 origin;
    Vec3 normal;
};

struct InputData {
    int yaw_count = 0;
    int pitch_count = 0;
    std::vector<double> angles_yaw;
    std::vector<double> angles_pitch;
    std::vector<Tri> triangles;
    std::vector<Vec3> normals;
    std::vector<Plane> bottom_planes;
    std::vector<int> visible_face_ids;
    std::vector<double> vtc;
    std::vector<double> expected_vss;
    double critical_angle_rad = 0.0;
};

static Vec3 operator-(const Vec3& a, const Vec3& b) {
    return {a.x - b.x, a.y - b.y, a.z - b.z};
}

static Vec3 operator*(const Vec3& a, double s) {
    return {a.x * s, a.y * s, a.z * s};
}

static double dot(const Vec3& a, const Vec3& b) {
    return a.x * b.x + a.y * b.y + a.z * b.z;
}

static Vec3 cross(const Vec3& a, const Vec3& b) {
    return {
        a.y * b.z - a.z * b.y,
        a.z * b.x - a.x * b.z,
        a.x * b.y - a.y * b.x,
    };
}

static Vec3 normalize(const Vec3& a) {
    const double length = std::sqrt(dot(a, a));
    if (length < 1e-15) {
        throw std::runtime_error("zero-length normal in input file");
    }
    return a * (1.0 / length);
}

static Vec3 triangle_normal(const Tri& tri) {
    return normalize(cross(tri.b - tri.a, tri.c - tri.a));
}

static Vec3 orientation_vector(double yaw_deg, double pitch_deg) {
    constexpr double pi = 3.141592653589793238462643383279502884;
    const double yaw = yaw_deg * pi / 180.0;
    const double pitch = pitch_deg * pi / 180.0;
    const double cos_pitch = std::cos(pitch);
    return {
        -std::sin(pitch),
        std::sin(yaw) * cos_pitch,
        std::cos(yaw) * cos_pitch,
    };
}

static Vec3 project_to_plane(const Vec3& p, const Vec3& origin, const Vec3& unit_normal) {
    return p - unit_normal * dot(p - origin, unit_normal);
}

static double tetra_volume(const Vec3& a, const Vec3& b, const Vec3& c, const Vec3& d) {
    return std::abs(dot(a - d, cross(b - d, c - d))) / 6.0;
}

static double tri_prism_volume(const Tri& tri, const Vec3& plane_origin, const Vec3& unit_normal) {
    const Vec3 p1 = project_to_plane(tri.a, plane_origin, unit_normal);
    const Vec3 p2 = project_to_plane(tri.b, plane_origin, unit_normal);
    const Vec3 p3 = project_to_plane(tri.c, plane_origin, unit_normal);
    const Vec3 p4 = tri.a;
    const Vec3 p5 = tri.b;
    const Vec3 p6 = tri.c;
    return tetra_volume(p1, p2, p3, p4)
        + tetra_volume(p2, p3, p4, p5)
        + tetra_volume(p3, p4, p5, p6);
}

static void expect_label(std::istream& in, const std::string& expected) {
    std::string label;
    in >> label;
    if (label != expected) {
        throw std::runtime_error("expected label '" + expected + "', got '" + label + "'");
    }
}

static InputData read_input_stream(std::istream& in);

static InputData read_input(const std::string& path) {
    if (path == "-") {
        return read_input_stream(std::cin);
    }

    std::ifstream in(path);
    if (!in) {
        throw std::runtime_error("failed to open input file: " + path);
    }

    return read_input_stream(in);
}

static InputData read_input_stream(std::istream& in) {

    InputData data;
    std::string version;
    in >> version;
    if (version != "TSE6VSS1" && version != "TSE6VSS2") {
        throw std::runtime_error("expected input version 'TSE6VSS1' or 'TSE6VSS2', got '" + version + "'");
    }

    std::size_t tri_count = 0;
    std::size_t plane_count = 0;
    std::size_t visible_count = 0;
    expect_label(in, "COUNTS");
    if (version == "TSE6VSS1") {
        in >> data.yaw_count >> data.pitch_count >> tri_count >> plane_count >> visible_count;
    } else {
        in >> data.yaw_count >> data.pitch_count >> tri_count >> visible_count;
        plane_count = static_cast<std::size_t>(data.yaw_count) * static_cast<std::size_t>(data.pitch_count);
    }

    expect_label(in, "CRITICAL_ANGLE_RAD");
    in >> data.critical_angle_rad;

    data.vtc.resize(plane_count);
    expect_label(in, "VTC");
    for (double& v : data.vtc) {
        in >> v;
    }

    if (version == "TSE6VSS2") {
        data.angles_yaw.resize(static_cast<std::size_t>(data.yaw_count));
        expect_label(in, "ANGLES_YAW");
        for (double& v : data.angles_yaw) {
            in >> v;
        }

        data.angles_pitch.resize(static_cast<std::size_t>(data.pitch_count));
        expect_label(in, "ANGLES_PITCH");
        for (double& v : data.angles_pitch) {
            in >> v;
        }
    }

    data.triangles.resize(tri_count);
    expect_label(in, "TRIANGLES");
    for (Tri& tri : data.triangles) {
        in >> tri.a.x >> tri.a.y >> tri.a.z
           >> tri.b.x >> tri.b.y >> tri.b.z
           >> tri.c.x >> tri.c.y >> tri.c.z;
    }

    if (version == "TSE6VSS1") {
        data.normals.resize(tri_count);
        expect_label(in, "NORMALS");
        for (Vec3& n : data.normals) {
            in >> n.x >> n.y >> n.z;
        }

        data.bottom_planes.resize(plane_count);
        expect_label(in, "BOTTOM_PLANES");
        for (Plane& plane : data.bottom_planes) {
            in >> plane.origin.x >> plane.origin.y >> plane.origin.z
               >> plane.normal.x >> plane.normal.y >> plane.normal.z;
        }
    }

    data.visible_face_ids.resize(visible_count);
    expect_label(in, "VISIBLE_FACE_IDS");
    for (int& id : data.visible_face_ids) {
        in >> id;
    }

    if (version == "TSE6VSS1") {
        data.expected_vss.resize(plane_count);
        expect_label(in, "EXPECTED_VSS");
        for (double& v : data.expected_vss) {
            in >> v;
        }
    }

    if (!in) {
        throw std::runtime_error("input file is truncated or malformed");
    }
    return data;
}

struct VssResult {
    std::vector<double> v_alpha;
    std::vector<double> v_beta;
    std::vector<double> v_nv;
    std::vector<double> v_o;
    std::vector<double> v_ss;
};

static std::vector<Vec3> compute_triangle_normals(const std::vector<Tri>& triangles) {
    std::vector<Vec3> normals;
    normals.reserve(triangles.size());
    for (const Tri& tri : triangles) {
        normals.push_back(triangle_normal(tri));
    }
    return normals;
}

static std::vector<Vec3> collect_triangle_vertices(const std::vector<Tri>& triangles) {
    std::vector<Vec3> vertices;
    vertices.reserve(triangles.size() * 3);
    for (const Tri& tri : triangles) {
        vertices.push_back(tri.a);
        vertices.push_back(tri.b);
        vertices.push_back(tri.c);
    }
    return vertices;
}

static std::vector<Plane> build_bottom_planes_from_angles(
    const std::vector<Tri>& triangles,
    const std::vector<double>& angles_yaw,
    const std::vector<double>& angles_pitch) {
    const std::vector<Vec3> vertices = collect_triangle_vertices(triangles);
    if (vertices.empty()) {
        return {};
    }

    std::vector<Plane> planes;
    planes.reserve(angles_yaw.size() * angles_pitch.size());

    for (const double pitch : angles_pitch) {
        for (const double yaw : angles_yaw) {
            const Vec3 normal = orientation_vector(yaw, pitch);
            std::size_t best_id = 0;
            double best_distance = dot(vertices[0], normal);
            for (std::size_t i = 1; i < vertices.size(); ++i) {
                const double distance = dot(vertices[i], normal);
                if (distance > best_distance) {
                    best_distance = distance;
                    best_id = i;
                }
            }
            planes.push_back({vertices[best_id], normal});
        }
    }

    return planes;
}

static void complete_sh_tensor_inputs(InputData& data) {
    if (data.normals.empty()) {
        data.normals = compute_triangle_normals(data.triangles);
    }
    if (data.bottom_planes.empty()) {
        if (data.angles_yaw.empty() || data.angles_pitch.empty()) {
            throw std::runtime_error("TSE6VSS2 input requires ANGLES_YAW and ANGLES_PITCH");
        }
        data.bottom_planes = build_bottom_planes_from_angles(
            data.triangles,
            data.angles_yaw,
            data.angles_pitch);
    }
}

static unsigned int default_thread_count() {
#ifdef _OPENMP
    const int max_threads = omp_get_max_threads();
    return max_threads <= 0 ? 1u : static_cast<unsigned int>(max_threads);
#else
    const unsigned int hardware_threads = std::thread::hardware_concurrency();
    return hardware_threads == 0 ? 1 : hardware_threads;
#endif
}

static VssResult compute_vss(const InputData& data, unsigned int thread_count = default_thread_count()) {
    const std::size_t plane_count = data.bottom_planes.size();
    const std::size_t tri_count = data.triangles.size();
    const double cos_critical = std::cos(data.critical_angle_rad);

    std::vector<unsigned char> is_visible(tri_count, 0);
    for (const int id : data.visible_face_ids) {
        if (id < 0 || static_cast<std::size_t>(id) >= tri_count) {
            throw std::runtime_error("visible face id outside triangle range");
        }
        is_visible[static_cast<std::size_t>(id)] = 1;
    }

    VssResult out;
    out.v_alpha.assign(plane_count, 0.0);
    out.v_beta.assign(plane_count, 0.0);
    out.v_nv.assign(plane_count, 0.0);
    out.v_o.assign(plane_count, 0.0);
    out.v_ss.assign(plane_count, 0.0);

    if (plane_count == 0 || tri_count == 0) {
        return out;
    }

    thread_count = std::max(1u, std::min<unsigned int>(thread_count, static_cast<unsigned int>(plane_count)));
    const int omp_threads = static_cast<int>(std::min<unsigned int>(
        thread_count,
        static_cast<unsigned int>(std::numeric_limits<int>::max())));

#ifdef _OPENMP
#pragma omp parallel for schedule(dynamic) num_threads(omp_threads)
#endif
    for (long long p_signed = 0; p_signed < static_cast<long long>(plane_count); ++p_signed) {
        const std::size_t p = static_cast<std::size_t>(p_signed);
        const Plane& plane = data.bottom_planes[p];
        const Vec3 unit_normal = normalize(plane.normal);

        for (std::size_t t = 0; t < tri_count; ++t) {
            const double volume = tri_prism_volume(data.triangles[t], plane.origin, unit_normal);
            const double normal_dot = dot(data.normals[t], unit_normal);

            if (normal_dot < 0.0) {
                out.v_alpha[p] += volume;
                if (is_visible[t] && normal_dot >= -cos_critical) {
                    out.v_nv[p] += volume;
                }
            } else {
                out.v_beta[p] += volume;
            }
        }

        out.v_o[p] = out.v_alpha[p] - out.v_beta[p];
        out.v_ss[p] = data.vtc[p] - out.v_o[p] - out.v_nv[p];
    }

    return out;
}

struct Options {
    std::string input_path = "tse6_cpp_input.txt";
    bool quiet = false;
    bool emit_vss = false;
    unsigned int thread_count = default_thread_count();
};

static Options parse_options(int argc, char** argv) {
    Options options;
    bool input_seen = false;

    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--quiet") {
            options.quiet = true;
        } else if (arg == "--emit-vss") {
            options.emit_vss = true;
        } else if (arg == "--threads") {
            if (i + 1 >= argc) {
                throw std::runtime_error("--threads requires a positive integer");
            }
            options.thread_count = static_cast<unsigned int>(std::stoul(argv[++i]));
        } else if (arg.rfind("--threads=", 0) == 0) {
            options.thread_count = static_cast<unsigned int>(std::stoul(arg.substr(10)));
        } else if (!input_seen) {
            options.input_path = arg;
            input_seen = true;
        } else {
            throw std::runtime_error("unknown argument: " + arg);
        }
    }

    if (options.thread_count == 0) {
        throw std::runtime_error("--threads must be greater than zero");
    }

    return options;
}

static void print_grid(const std::vector<double>& values, int rows, int cols) {
    std::cout << std::fixed << std::setprecision(6);
    for (int r = 0; r < rows; ++r) {
        for (int c = 0; c < cols; ++c) {
            if (c > 0) {
                std::cout << ' ';
            }
            std::cout << std::setw(12) << values[static_cast<std::size_t>(r * cols + c)];
        }
        std::cout << '\n';
    }
}

static void print_flat_values(const std::vector<double>& values) {
    std::cout << "VSS_FLAT";
    std::cout << std::setprecision(17);
    for (const double value : values) {
        std::cout << ' ' << value;
    }
    std::cout << '\n';
}

int main(int argc, char** argv) {
    try {
        const Options options = parse_options(argc, argv);

        InputData data = read_input(options.input_path);
        complete_sh_tensor_inputs(data);

        const auto start = std::chrono::steady_clock::now();
        const VssResult result = compute_vss(data, options.thread_count);
        const auto end = std::chrono::steady_clock::now();
        const double elapsed_ms =
            std::chrono::duration<double, std::milli>(end - start).count();

        double max_abs_error = 0.0;
        const bool has_expected_vss = data.expected_vss.size() == result.v_ss.size();
        if (has_expected_vss) {
            for (std::size_t i = 0; i < result.v_ss.size(); ++i) {
                max_abs_error = std::max(max_abs_error, std::abs(result.v_ss[i] - data.expected_vss[i]));
            }
        }

        std::cout << "C++ v_ss compute time (" << options.thread_count << " thread"
                  << (options.thread_count == 1 ? "" : "s") << "): "
                  << std::fixed << std::setprecision(3)
                  << elapsed_ms << " ms\n";
        if (has_expected_vss) {
            std::cout << "max abs error vs Python export: " << std::setprecision(12)
                      << max_abs_error << "\n";
        }

        if (!options.quiet) {
            std::cout << "v_ss:\n";
            print_grid(result.v_ss, data.pitch_count, data.yaw_count);
        }
        if (options.emit_vss) {
            print_flat_values(result.v_ss);
        }
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << "error: " << exc.what() << '\n';
        return 1;
    }
}
