// sftf_cpp.cpp -- C++/DLL port of the Support Flow Tensor Field (SFTF) candidate
// generator (the lean compute path used by G5Test.py:
//   evaluate_support_flow_candidate_pool -> support_flow_directions_from_candidate_pool).
//
// Rendering (Plotly/Polyscope) and the convex-hull boolean / PCA cavity axes are
// intentionally excluded: the SFTF candidate pool is computed from the input mesh
// alone. The DLL receives vertex/face arrays from Python (matching the
// Tomo_Shell2026.dll ctypes pattern) and returns the optimal and worst build
// orientations, so only the compute time is measured.
//
// Windows x64 / MSVC, OpenMP over the candidate-direction loops.
//
// Algorithm constants mirror python_src/SupportFlowTensorField/support_flow_tensor_field.py.

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <iterator>
#include <numeric>
#include <vector>

#ifdef _OPENMP
#include <omp.h>
#endif

#if defined(_WIN32)
#define SFTF_API extern "C" __declspec(dllexport)
#else
#define SFTF_API extern "C"
#endif

namespace {

// --- SFTF module constants (support_flow_tensor_field.py lines 24-56) ---------
constexpr double kSupportCriticalAngleDeg = 60.0;
constexpr int    kRefineParentCount       = 12;
constexpr double kRefineConeDegrees[]     = {2.0, 4.0, 6.0, 8.0};
constexpr int    kRefineAzimuthCount      = 16;
constexpr int    kMinRayCount             = 500;
constexpr int    kMaxRayCount             = 3000;
constexpr double kFaceFraction            = 0.02;
constexpr double kRayEpsScale             = 1e-6;
constexpr double kHeightEpsScale          = 1e-5;
constexpr double kReceiverNormalThreshold = 0.05;
constexpr double kParentMinAngleDeg       = 8.0;

// Rank-tuning weights [J, rayleigh, pair, bed, hit, nuclear, sigma1].
constexpr double kRankWeights[7] = {0.0, 0.731, -2.3897, 2.1447, 2.3109, -2.2922, 1.6363};

constexpr double kPi = 3.141592653589793238462643383279502884;

// --- small vector math --------------------------------------------------------
struct Vec3 {
    double x = 0.0, y = 0.0, z = 0.0;
};
inline Vec3 operator-(const Vec3& a, const Vec3& b) { return {a.x - b.x, a.y - b.y, a.z - b.z}; }
inline Vec3 operator+(const Vec3& a, const Vec3& b) { return {a.x + b.x, a.y + b.y, a.z + b.z}; }
inline Vec3 operator*(const Vec3& a, double s) { return {a.x * s, a.y * s, a.z * s}; }
inline double dot(const Vec3& a, const Vec3& b) { return a.x * b.x + a.y * b.y + a.z * b.z; }
inline Vec3 cross(const Vec3& a, const Vec3& b) {
    return {a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x};
}
inline double norm(const Vec3& a) { return std::sqrt(dot(a, a)); }
inline Vec3 safe_unit(const Vec3& a) {
    const double n = norm(a);
    return (n <= 1e-12) ? Vec3{0.0, 0.0, 0.0} : Vec3{a.x / n, a.y / n, a.z / n};
}

// --- mesh + BVH ---------------------------------------------------------------
struct BvhNode {
    Vec3 bmin, bmax;
    int left = -1;   // child index, or -1 for leaf
    int start = 0;   // leaf: first index into ordered triangle list
    int count = 0;   // leaf: triangle count (0 for interior)
};

struct Mesh {
    std::vector<Vec3> vertices;
    std::vector<std::array<int, 3>> faces;
    std::vector<Vec3> normals;   // unit face normals (0 for degenerate)
    std::vector<double> areas;   // face areas (0 for degenerate)
    std::vector<Vec3> centers;   // face centroids
    double diagonal = 1.0;
    double alpha = 1.0;
    double ray_eps = 0.0;
    double height_eps = 0.0;

    // BVH over faces
    std::vector<int> tri_order;       // ordered face indices for leaves
    std::vector<BvhNode> nodes;
};

void compute_surface_data(Mesh& m) {
    const std::size_t nf = m.faces.size();
    m.normals.assign(nf, Vec3{});
    m.areas.assign(nf, 0.0);
    m.centers.assign(nf, Vec3{});
    for (std::size_t i = 0; i < nf; ++i) {
        const Vec3& a = m.vertices[m.faces[i][0]];
        const Vec3& b = m.vertices[m.faces[i][1]];
        const Vec3& c = m.vertices[m.faces[i][2]];
        const Vec3 cr = cross(b - a, c - a);
        const double twice_area = norm(cr);
        m.areas[i] = 0.5 * twice_area;
        m.normals[i] = (twice_area > 1e-15) ? cr * (1.0 / twice_area) : Vec3{0.0, 0.0, 0.0};
        m.centers[i] = (a + b + c) * (1.0 / 3.0);
        if (!std::isfinite(m.areas[i]) || m.areas[i] <= 0.0) {
            m.areas[i] = 0.0;  // matches the Python "valid face" filter
            m.normals[i] = Vec3{0.0, 0.0, 0.0};
        }
    }
    // bbox diagonal of the vertex cloud (np.ptp then norm)
    if (!m.vertices.empty()) {
        Vec3 lo = m.vertices[0], hi = m.vertices[0];
        for (const Vec3& v : m.vertices) {
            lo.x = std::min(lo.x, v.x); lo.y = std::min(lo.y, v.y); lo.z = std::min(lo.z, v.z);
            hi.x = std::max(hi.x, v.x); hi.y = std::max(hi.y, v.y); hi.z = std::max(hi.z, v.z);
        }
        m.diagonal = std::max(norm(hi - lo), 1e-12);
    } else {
        m.diagonal = 1e-12;
    }
    m.alpha = 1.0 / m.diagonal;
    m.ray_eps = m.diagonal * kRayEpsScale;
    m.height_eps = m.diagonal * kHeightEpsScale;
}

void tri_bounds(const Mesh& m, int f, Vec3& lo, Vec3& hi) {
    const Vec3& a = m.vertices[m.faces[f][0]];
    const Vec3& b = m.vertices[m.faces[f][1]];
    const Vec3& c = m.vertices[m.faces[f][2]];
    lo = {std::min({a.x, b.x, c.x}), std::min({a.y, b.y, c.y}), std::min({a.z, b.z, c.z})};
    hi = {std::max({a.x, b.x, c.x}), std::max({a.y, b.y, c.y}), std::max({a.z, b.z, c.z})};
}

// Median-split BVH over face centroids.
void build_bvh(Mesh& m) {
    const int nf = static_cast<int>(m.faces.size());
    m.tri_order.resize(nf);
    std::iota(m.tri_order.begin(), m.tri_order.end(), 0);
    m.nodes.clear();
    if (nf == 0) return;

    std::vector<Vec3> centroid(nf);
    for (int i = 0; i < nf; ++i) centroid[i] = m.centers[i];

    struct Task { int start, count, node; };
    m.nodes.reserve(static_cast<std::size_t>(2 * nf));
    m.nodes.push_back(BvhNode{});
    std::vector<Task> stack;
    stack.push_back({0, nf, 0});
    const int kLeaf = 8;

    while (!stack.empty()) {
        const Task t = stack.back();
        stack.pop_back();
        Vec3 lo{1e300, 1e300, 1e300}, hi{-1e300, -1e300, -1e300};
        Vec3 clo{1e300, 1e300, 1e300}, chi{-1e300, -1e300, -1e300};
        for (int i = t.start; i < t.start + t.count; ++i) {
            Vec3 tl, th;
            tri_bounds(m, m.tri_order[i], tl, th);
            lo = {std::min(lo.x, tl.x), std::min(lo.y, tl.y), std::min(lo.z, tl.z)};
            hi = {std::max(hi.x, th.x), std::max(hi.y, th.y), std::max(hi.z, th.z)};
            const Vec3& c = centroid[m.tri_order[i]];
            clo = {std::min(clo.x, c.x), std::min(clo.y, c.y), std::min(clo.z, c.z)};
            chi = {std::max(chi.x, c.x), std::max(chi.y, c.y), std::max(chi.z, c.z)};
        }
        BvhNode& node = m.nodes[t.node];
        node.bmin = lo;
        node.bmax = hi;

        if (t.count <= kLeaf) {
            node.left = -1;
            node.start = t.start;
            node.count = t.count;
            continue;
        }
        const Vec3 ext = chi - clo;
        const int axis = (ext.x >= ext.y && ext.x >= ext.z) ? 0 : (ext.y >= ext.z ? 1 : 2);
        const int mid = t.start + t.count / 2;
        auto comp = [&](int fa, int fb) {
            const Vec3& ca = centroid[fa];
            const Vec3& cb = centroid[fb];
            return (axis == 0 ? ca.x : axis == 1 ? ca.y : ca.z) <
                   (axis == 0 ? cb.x : axis == 1 ? cb.y : cb.z);
        };
        std::nth_element(m.tri_order.begin() + t.start,
                         m.tri_order.begin() + mid,
                         m.tri_order.begin() + t.start + t.count, comp);
        const int left_id = static_cast<int>(m.nodes.size());
        m.nodes.push_back(BvhNode{});
        m.nodes.push_back(BvhNode{});
        m.nodes[t.node].left = left_id;
        m.nodes[t.node].count = 0;
        stack.push_back({t.start, mid - t.start, left_id});
        stack.push_back({mid, t.start + t.count - mid, left_id + 1});
    }
}

// Ray-AABB slab test; returns entry distance (or returns false).
inline bool ray_aabb_axis(double origin, double dir, double slab_min, double slab_max,
                          double& t0, double& t1) {
    if (std::abs(dir) <= 1e-15) {
        return origin >= slab_min && origin <= slab_max;
    }
    double a = (slab_min - origin) / dir;
    double b = (slab_max - origin) / dir;
    if (a > b) std::swap(a, b);
    t0 = std::max(t0, a);
    t1 = std::min(t1, b);
    return t1 >= t0;
}

inline bool ray_aabb(const Vec3& o, const Vec3& dir, const Vec3& bmin, const Vec3& bmax,
                     double max_t, double& tmin_out) {
    double t0 = 0.0, t1 = max_t;
    if (!ray_aabb_axis(o.x, dir.x, bmin.x, bmax.x, t0, t1)) return false;
    if (!ray_aabb_axis(o.y, dir.y, bmin.y, bmax.y, t0, t1)) return false;
    if (!ray_aabb_axis(o.z, dir.z, bmin.z, bmax.z, t0, t1)) return false;
    tmin_out = t0;
    return t1 >= t0;
}

// Moller-Trumbore; t = signed distance along (unit) dir. Non-culling.
inline bool ray_tri(const Vec3& o, const Vec3& dir, const Vec3& v0, const Vec3& v1, const Vec3& v2,
                    double& t_out) {
    const Vec3 e1 = v1 - v0, e2 = v2 - v0;
    const Vec3 p = cross(dir, e2);
    const double det = dot(e1, p);
    if (std::abs(det) < 1e-15) return false;
    const double inv = 1.0 / det;
    const Vec3 tvec = o - v0;
    const double u = dot(tvec, p) * inv;
    if (u < 0.0 || u > 1.0) return false;
    const Vec3 q = cross(tvec, e1);
    const double v = dot(dir, q) * inv;
    if (v < 0.0 || u + v > 1.0) return false;
    const double t = dot(e2, q) * inv;
    if (t <= 1e-12) return false;
    t_out = t;
    return true;
}

// Nearest receiver face that satisfies the SFTF validity predicate. Returns -1 if none.
int nearest_valid_hit(const Mesh& m, const Vec3& origin, const Vec3& dir, int src_face,
                      const Vec3& n) {
    if (m.nodes.empty()) return -1;
    const double dist_eps = std::max(1e-10, m.height_eps);
    int best_face = -1;
    double best_t = 1e300;

    int stack[128];
    int sp = 0;
    stack[sp++] = 0;
    while (sp > 0) {
        const BvhNode& node = m.nodes[stack[--sp]];
        double tmin;
        if (!ray_aabb(origin, dir, node.bmin, node.bmax, best_t, tmin)) continue;
        if (node.left < 0) {
            for (int i = node.start; i < node.start + node.count; ++i) {
                const int f = m.tri_order[i];
                if (f == src_face) continue;
                double t;
                if (!ray_tri(origin, dir,
                             m.vertices[m.faces[f][0]], m.vertices[m.faces[f][1]],
                             m.vertices[m.faces[f][2]], t)) continue;
                if (t <= dist_eps || t >= best_t) continue;
                // receiver normal must face the build direction
                if (dot(m.normals[f], n) <= kReceiverNormalThreshold) continue;
                // height of the source above the receiver along n must be positive
                const double height = dot(m.centers[src_face] - m.centers[f], n);
                if (height <= m.height_eps) continue;
                best_t = t;
                best_face = f;
            }
        } else {
            stack[sp++] = node.left;
            stack[sp++] = node.left + 1;
        }
    }
    return best_face;
}

// --- symmetric 3x3 eigenvalues (descending), for singular values of F ---------
std::array<double, 3> eig_sym3(double a, double b, double c, double d, double e, double f) {
    // matrix [[a,d,f],[d,b,e],[f,e,c]]
    const double p1 = d * d + f * f + e * e;
    std::array<double, 3> w;
    if (p1 <= 0.0) {
        w = {a, b, c};
    } else {
        const double q = (a + b + c) / 3.0;
        const double p2 = (a - q) * (a - q) + (b - q) * (b - q) + (c - q) * (c - q) + 2.0 * p1;
        const double p = std::sqrt(p2 / 6.0);
        const double ba = (a - q) / p, bb = (b - q) / p, bc = (c - q) / p;
        const double bd = d / p, be = e / p, bf = f / p;
        const double detB = ba * (bb * bc - be * be) - bd * (bd * bc - be * bf) + bf * (bd * be - bb * bf);
        double r = detB / 2.0;
        r = std::max(-1.0, std::min(1.0, r));
        const double phi = std::acos(r) / 3.0;
        const double e1 = q + 2.0 * p * std::cos(phi);
        const double e3 = q + 2.0 * p * std::cos(phi + 2.0 * kPi / 3.0);
        const double e2 = 3.0 * q - e1 - e3;
        w = {e1, e2, e3};
    }
    std::sort(w.begin(), w.end(), std::greater<double>());
    return w;
}

// --- direction sampling -------------------------------------------------------
std::vector<Vec3> fibonacci_sphere(int count) {
    count = std::max(count, 1);
    std::vector<Vec3> dirs(static_cast<std::size_t>(count));
    const double golden = kPi * (3.0 - std::sqrt(5.0));
    for (int i = 0; i < count; ++i) {
        const double z = 1.0 - 2.0 * (i + 0.5) / count;
        const double r = std::sqrt(std::max(0.0, 1.0 - z * z));
        const double theta = i * golden;
        dirs[i] = {r * std::cos(theta), r * std::sin(theta), z};
    }
    return dirs;
}

void orthonormal_basis(const Vec3& n, Vec3& u, Vec3& v) {
    Vec3 seed{1.0, 0.0, 0.0};
    if (std::abs(dot(seed, n)) > 0.85) seed = {0.0, 1.0, 0.0};
    u = safe_unit(cross(n, seed));
    v = safe_unit(cross(n, u));
}

std::vector<Vec3> cone_sample(const Vec3& center) {
    const Vec3 n = safe_unit(center);
    std::vector<Vec3> dirs;
    if (norm(n) <= 1e-12) return dirs;
    Vec3 u, v;
    orthonormal_basis(n, u, v);
    dirs.push_back(n);
    for (double deg : kRefineConeDegrees) {
        const double ang = deg * kPi / 180.0;
        for (int a = 0; a < kRefineAzimuthCount; ++a) {
            const double az = 2.0 * kPi * a / kRefineAzimuthCount;
            const Vec3 tangent = u * std::cos(az) + v * std::sin(az);
            dirs.push_back(safe_unit(n * std::cos(ang) + tangent * std::sin(ang)));
        }
    }
    return dirs;
}

int adaptive_k_ray(int face_count) {
    const double by_fraction = std::ceil(std::max(face_count, 1) * kFaceFraction);
    const int k = static_cast<int>(by_fraction);
    return std::min(std::max(k, kMinRayCount), kMaxRayCount);
}

// Faithful port of _sample_ray_face_ids.
std::vector<int> sample_ray_face_ids(const Mesh& m, const std::vector<double>& overhang, int k_ray) {
    const std::size_t nf = m.faces.size();
    std::vector<int> valid_ids;
    std::vector<double> weights(nf);
    for (std::size_t i = 0; i < nf; ++i) {
        const double w = m.areas[i] * overhang[i];
        weights[i] = w;
        if (w > 0.0) valid_ids.push_back(static_cast<int>(i));
    }
    k_ray = std::max(k_ray, 1);
    if (static_cast<int>(valid_ids.size()) <= k_ray) return valid_ids;

    double total = 0.0;
    for (int id : valid_ids) total += weights[id];
    if (total <= 1e-12) return {};

    std::vector<double> cumulative(valid_ids.size());
    double run = 0.0;
    for (std::size_t i = 0; i < valid_ids.size(); ++i) {
        run += weights[valid_ids[i]];
        cumulative[i] = run;
    }
    // stratified targets -> searchsorted(side="left") == lower_bound
    std::vector<int> sampled;
    sampled.reserve(static_cast<std::size_t>(k_ray));
    for (int t = 0; t < k_ray; ++t) {
        const double target = (t + 0.5) * total / k_ray;
        auto it = std::lower_bound(cumulative.begin(), cumulative.end(), target);
        std::size_t idx = static_cast<std::size_t>(it - cumulative.begin());
        if (idx >= valid_ids.size()) idx = valid_ids.size() - 1;
        sampled.push_back(valid_ids[idx]);
    }
    std::sort(sampled.begin(), sampled.end());
    sampled.erase(std::unique(sampled.begin(), sampled.end()), sampled.end());
    if (static_cast<int>(sampled.size()) >= k_ray) {
        sampled.resize(static_cast<std::size_t>(k_ray));
        return sampled;
    }
    // top-up with the largest-weight remaining valid faces (descending)
    const int missing = k_ray - static_cast<int>(sampled.size());
    std::vector<int> remainder;
    std::set_difference(valid_ids.begin(), valid_ids.end(), sampled.begin(), sampled.end(),
                        std::back_inserter(remainder));
    if (remainder.empty()) return sampled;
    std::sort(remainder.begin(), remainder.end(),
              [&](int a, int b) { return weights[a] > weights[b]; });
    const int take = std::min(missing, static_cast<int>(remainder.size()));
    sampled.insert(sampled.end(), remainder.begin(), remainder.begin() + take);
    return sampled;
}

// --- per-direction SFTF candidate evaluation ---------------------------------
struct Candidate {
    double score = 0.0;     // J = R + P + B (pre-tuning)
    double rayleigh = 0.0;
    double pair = 0.0;
    double bed = 0.0;
    int    hit = 0;
    double nuclear = 0.0;
    double sigma1 = 0.0;
    Vec3   dir{};
    bool   valid = false;
};

Candidate evaluate_candidate(
    const Mesh& m, const Vec3& direction, bool use_critical_angle, double critical_angle_deg) {
    Candidate out;
    const Vec3 n = safe_unit(direction);
    if (norm(n) <= 1e-12) return out;
    const std::size_t nf = m.faces.size();
    if (nf == 0 || m.vertices.empty()) return out;
    out.dir = n;

    static thread_local std::vector<double> overhang;
    overhang.assign(nf, 0.0);
    const double critical_cos = std::cos(critical_angle_deg * kPi / 180.0);
    for (std::size_t i = 0; i < nf; ++i) {
        double o = -dot(m.normals[i], n);
        if (o < 0.0) o = 0.0;
        if (use_critical_angle && o <= critical_cos) o = 0.0;
        overhang[i] = o;
    }

    const int k_ray = adaptive_k_ray(static_cast<int>(m.areas.size()));
    const std::vector<int> source_ids = sample_ray_face_ids(m, overhang, k_ray);
    out.valid = true;  // finite score
    if (source_ids.empty()) return out;  // all-zero scores

    // ray cast each source face, accumulate flow tensor + pair score
    double F[3][3] = {{0, 0, 0}, {0, 0, 0}, {0, 0, 0}};
    double pair_score = 0.0;
    int hit_count = 0;
    std::vector<unsigned char> has_hit(source_ids.size(), 0);
    for (std::size_t s = 0; s < source_ids.size(); ++s) {
        const int src = source_ids[s];
        const Vec3 origin = m.centers[src] - n * m.ray_eps;
        const Vec3 ray_dir = n * -1.0;
        const int tgt = nearest_valid_hit(m, origin, ray_dir, src, n);
        if (tgt < 0) continue;
        has_hit[s] = 1;
        ++hit_count;
        const double height = dot(m.centers[src] - m.centers[tgt], n);
        const double pair_base = overhang[src] * m.areas[src] * m.areas[tgt];
        pair_score += pair_base;
        const double w = pair_base / (1.0 + m.alpha * height);
        const Vec3& mi = m.normals[src];
        const Vec3& mj = m.normals[tgt];
        F[0][0] += w * mi.x * mj.x; F[0][1] += w * mi.x * mj.y; F[0][2] += w * mi.x * mj.z;
        F[1][0] += w * mi.y * mj.x; F[1][1] += w * mi.y * mj.y; F[1][2] += w * mi.y * mj.z;
        F[2][0] += w * mi.z * mj.x; F[2][1] += w * mi.z * mj.y; F[2][2] += w * mi.z * mj.z;
    }

    // build-plate (bed) term for unsupported overhang sources
    double support_floor = 1e300;
    for (const Vec3& v : m.vertices) support_floor = std::min(support_floor, dot(v, n));
    double bed_score = 0.0;
    for (std::size_t s = 0; s < source_ids.size(); ++s) {
        if (has_hit[s]) continue;
        const int src = source_ids[s];
        const double bed_height = dot(m.centers[src], n) - support_floor;
        if (bed_height <= m.height_eps) continue;
        bed_score += overhang[src] * m.areas[src] * (1.0 + m.alpha * bed_height);
    }

    // Rayleigh support cost: n^T sym(F) n == n^T F n
    const Vec3 Fn{F[0][0] * n.x + F[0][1] * n.y + F[0][2] * n.z,
                  F[1][0] * n.x + F[1][1] * n.y + F[1][2] * n.z,
                  F[2][0] * n.x + F[2][1] * n.y + F[2][2] * n.z};
    const double raw_rayleigh = dot(n, Fn);
    const double rayleigh = std::max(0.0, -raw_rayleigh);

    // singular values of F via eig of F^T F
    double M00 = 0, M11 = 0, M22 = 0, M01 = 0, M02 = 0, M12 = 0;
    for (int k = 0; k < 3; ++k) {
        M00 += F[k][0] * F[k][0];
        M11 += F[k][1] * F[k][1];
        M22 += F[k][2] * F[k][2];
        M01 += F[k][0] * F[k][1];
        M02 += F[k][0] * F[k][2];
        M12 += F[k][1] * F[k][2];
    }
    const std::array<double, 3> ev = eig_sym3(M00, M11, M22, M01, M12, M02);
    const double s1 = std::sqrt(std::max(0.0, ev[0]));
    const double s2 = std::sqrt(std::max(0.0, ev[1]));
    const double s3 = std::sqrt(std::max(0.0, ev[2]));

    out.rayleigh = rayleigh;
    out.pair = pair_score;
    out.bed = bed_score;
    out.hit = hit_count;
    out.nuclear = s1 + s2 + s3;
    out.sigma1 = s1;
    out.score = rayleigh + pair_score + bed_score;  // J = R + P + B (nuclear/sigma1 weight 0)
    return out;
}

// --- ranking / tuning / NMS ---------------------------------------------------
// angular non-maximum suppression: pick lowest-score candidates >= min_angle apart
std::vector<int> angular_nms(const std::vector<Candidate>& cands, const std::vector<int>& order,
                             int limit, double min_angle_deg) {
    std::vector<int> picked;
    const double min_dot = std::cos(min_angle_deg * kPi / 180.0);
    for (int id : order) {
        bool ok = true;
        for (int p : picked) {
            if (std::abs(dot(cands[id].dir, cands[p].dir)) >= min_dot) { ok = false; break; }
        }
        if (!ok) continue;
        picked.push_back(id);
        if (static_cast<int>(picked.size()) >= limit) break;
    }
    return picked;
}

// rank-normalize a feature column to [0,1] by stable ascending rank
std::vector<double> rank_normalized(const std::vector<double>& values) {
    const std::size_t n = values.size();
    std::vector<double> out(n, 0.0);
    if (n <= 1) return out;
    std::vector<int> order(n);
    std::iota(order.begin(), order.end(), 0);
    std::stable_sort(order.begin(), order.end(),
                     [&](int a, int b) { return values[a] < values[b]; });
    for (std::size_t i = 0; i < n; ++i) {
        out[order[i]] = static_cast<double>(i) / static_cast<double>(n - 1);
    }
    return out;
}

void tune_scores(std::vector<Candidate>& cands) {
    const std::size_t n = cands.size();
    if (n <= 1) return;
    std::array<std::vector<double>, 7> cols;
    for (auto& c : cols) c.resize(n);
    for (std::size_t i = 0; i < n; ++i) {
        cols[0][i] = cands[i].score;
        cols[1][i] = cands[i].rayleigh;
        cols[2][i] = cands[i].pair;
        cols[3][i] = cands[i].bed;
        cols[4][i] = static_cast<double>(cands[i].hit);
        cols[5][i] = cands[i].nuclear;
        cols[6][i] = cands[i].sigma1;
    }
    std::array<std::vector<double>, 7> ranks;
    for (int f = 0; f < 7; ++f) ranks[f] = rank_normalized(cols[f]);
    for (std::size_t i = 0; i < n; ++i) {
        double tuned = 0.0;
        for (int f = 0; f < 7; ++f) tuned += kRankWeights[f] * ranks[f][i];
        cands[i].score = tuned;  // replace J with the tuned score
    }
}

void configure_threads(int n_threads) {
#ifdef _OPENMP
    if (n_threads > 0) omp_set_num_threads(n_threads);
#else
    (void)n_threads;
#endif
}

}  // namespace

// -----------------------------------------------------------------------------
// Exported C ABI. Output layout per direction (stride 8):
//   [dir_x, dir_y, dir_z, tuned_score, rayleigh, pair, bed, hit]
// out_optimal / out_worst are caller-allocated buffers of length >= top_k*8.
// Returns 0 on success, nonzero on error.
// -----------------------------------------------------------------------------
SFTF_API int sftf_compute_directions(
    const double* vertices, int n_vertices,
    const int* faces, int n_faces,
    int coarse_count, double critical_angle_deg, int use_critical_angle,
    int top_k, double min_angle_deg, int n_threads,
    double* out_optimal, double* out_worst,
    int* out_optimal_count, int* out_worst_count,
    double* out_compute_ms) {
    if (out_optimal_count) *out_optimal_count = 0;
    if (out_worst_count) *out_worst_count = 0;
    if (out_compute_ms) *out_compute_ms = 0.0;
    if (!vertices || !faces || n_vertices <= 0 || n_faces <= 0 || top_k <= 0) return 1;
    if (coarse_count <= 0) coarse_count = 512;
    if (!std::isfinite(critical_angle_deg) || critical_angle_deg <= 0.0 || critical_angle_deg >= 90.0) {
        critical_angle_deg = kSupportCriticalAngleDeg;
    }
    if (min_angle_deg <= 0.0) min_angle_deg = 3.0;

    configure_threads(n_threads);
    const auto t_start = std::chrono::steady_clock::now();

    Mesh m;
    m.vertices.resize(static_cast<std::size_t>(n_vertices));
    for (int i = 0; i < n_vertices; ++i) {
        m.vertices[i] = {vertices[3 * i + 0], vertices[3 * i + 1], vertices[3 * i + 2]};
    }
    m.faces.resize(static_cast<std::size_t>(n_faces));
    for (int i = 0; i < n_faces; ++i) {
        m.faces[i] = {faces[3 * i + 0], faces[3 * i + 1], faces[3 * i + 2]};
    }
    compute_surface_data(m);
    build_bvh(m);

    const bool gate = use_critical_angle != 0;

    // coarse Fibonacci sphere
    const std::vector<Vec3> coarse = fibonacci_sphere(coarse_count);
    std::vector<Candidate> coarse_results(coarse.size());
#ifdef _OPENMP
#pragma omp parallel for schedule(dynamic)
#endif
    for (long long i = 0; i < static_cast<long long>(coarse.size()); ++i) {
        coarse_results[static_cast<std::size_t>(i)] =
            evaluate_candidate(m, coarse[static_cast<std::size_t>(i)], gate, critical_angle_deg);
    }

    std::vector<Candidate> results;
    for (const Candidate& c : coarse_results) if (c.valid) results.push_back(c);

    // parents: ascending-score NMS over coarse results
    std::vector<int> coarse_order(results.size());
    std::iota(coarse_order.begin(), coarse_order.end(), 0);
    std::stable_sort(coarse_order.begin(), coarse_order.end(),
                     [&](int a, int b) { return results[a].score < results[b].score; });
    const std::vector<int> parents = angular_nms(results, coarse_order, kRefineParentCount, kParentMinAngleDeg);

    // refine: cone resample around parents, dedup
    std::vector<Vec3> refine_dirs;
    for (int p : parents) {
        for (const Vec3& d : cone_sample(results[p].dir)) {
            const Vec3 unit = safe_unit(d);
            if (norm(unit) <= 1e-12) continue;
            bool dup = false;
            for (const Vec3& e : refine_dirs) {
                if (std::abs(dot(e, unit)) >= 1.0 - 1e-10) { dup = true; break; }
            }
            if (!dup) refine_dirs.push_back(unit);
        }
    }
    std::vector<Candidate> refine_results(refine_dirs.size());
#ifdef _OPENMP
#pragma omp parallel for schedule(dynamic)
#endif
    for (long long i = 0; i < static_cast<long long>(refine_dirs.size()); ++i) {
        refine_results[static_cast<std::size_t>(i)] =
            evaluate_candidate(m, refine_dirs[static_cast<std::size_t>(i)], gate, critical_angle_deg);
    }
    for (const Candidate& c : refine_results) if (c.valid) results.push_back(c);

    // rank tuning over the full pool
    tune_scores(results);

    // optimal = ascending NMS, worst = descending NMS
    std::vector<int> asc(results.size());
    std::iota(asc.begin(), asc.end(), 0);
    std::stable_sort(asc.begin(), asc.end(),
                     [&](int a, int b) { return results[a].score < results[b].score; });
    std::vector<int> desc(asc.rbegin(), asc.rend());

    const std::vector<int> opt = angular_nms(results, asc, top_k, min_angle_deg);
    const std::vector<int> wst = angular_nms(results, desc, top_k, min_angle_deg);

    auto fill = [&](const std::vector<int>& ids, double* buf) {
        for (std::size_t i = 0; i < ids.size(); ++i) {
            const Candidate& c = results[ids[i]];
            double* row = buf + i * 8;
            row[0] = c.dir.x; row[1] = c.dir.y; row[2] = c.dir.z;
            row[3] = c.score; row[4] = c.rayleigh; row[5] = c.pair;
            row[6] = c.bed; row[7] = static_cast<double>(c.hit);
        }
    };
    if (out_optimal) fill(opt, out_optimal);
    if (out_worst) fill(wst, out_worst);
    if (out_optimal_count) *out_optimal_count = static_cast<int>(opt.size());
    if (out_worst_count) *out_worst_count = static_cast<int>(wst.size());

    const auto t_end = std::chrono::steady_clock::now();
    if (out_compute_ms) {
        *out_compute_ms = std::chrono::duration<double, std::milli>(t_end - t_start).count();
    }
    return 0;
}
