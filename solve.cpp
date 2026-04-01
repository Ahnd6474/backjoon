#include <algorithm>
#include <array>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <limits>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

namespace {

constexpr double kEps = 1e-12;
constexpr double kAreaTolerance = 1e-12;
constexpr int kTriangleTypeCode = 1;
constexpr int kCircleTypeCode = 2;

struct Point {
    double x;
    double y;
};

struct TrianglePaper {
    std::array<Point, 3> vertices;
};

struct CirclePaper {
    Point center;
    double radius;
};

struct Paper {
    int type = 0;
    TrianglePaper triangle{};
    CirclePaper circle{};
};

struct BoundaryFunction {
    enum class Kind { kLine, kCircle };

    Kind kind = Kind::kLine;
    double slope = 0.0;
    double intercept = 0.0;
    double center_x = 0.0;
    double center_y = 0.0;
    double radius = 0.0;
    int sign = 1;

    double ValueAt(double x) const {
        if (kind == Kind::kLine) {
            return (slope * x) + intercept;
        }
        const double delta = std::max(0.0, (radius * radius) - ((x - center_x) * (x - center_x)));
        return center_y + (static_cast<double>(sign) * std::sqrt(delta));
    }

    double Integral(double left, double right) const {
        if (kind == Kind::kLine) {
            return (0.5 * slope * ((right * right) - (left * left))) + (intercept * (right - left));
        }
        return CircleIntegral(right) - CircleIntegral(left);
    }

    double CircleIntegral(double x) const {
        const double clamped = std::min(center_x + radius, std::max(center_x - radius, x));
        const double shifted = clamped - center_x;
        const double ratio =
            radius <= kEps ? 0.0 : std::max(-1.0, std::min(1.0, shifted / radius));
        const double root = std::sqrt(std::max(0.0, (radius * radius) - (shifted * shifted)));
        const double circular =
            0.5 * ((shifted * root) + ((radius * radius) * std::asin(ratio)));
        return (center_y * clamped) + (static_cast<double>(sign) * circular);
    }
};

struct ShapeSlab {
    double left;
    double right;
    BoundaryFunction lower;
    BoundaryFunction upper;
};

struct ShapeProfile {
    double xmin;
    double xmax;
    std::vector<ShapeSlab> slabs;
};

using VisibleAreas = std::vector<double>;
using VisibleAreaRows = std::vector<VisibleAreas>;

double AreaOfPaper(const Paper& paper) {
    if (paper.type == kCircleTypeCode) {
        return std::acos(-1.0) * paper.circle.radius * paper.circle.radius;
    }

    const auto& [a, b, c] = paper.triangle.vertices;
    return std::abs(
               (a.x * (b.y - c.y)) +
               (b.x * (c.y - a.y)) +
               (c.x * (a.y - b.y))) /
           2.0;
}

std::vector<std::pair<Point, Point>> TriangleEdges(const TrianglePaper& triangle) {
    const auto& vertices = triangle.vertices;
    return {
        {vertices[0], vertices[1]},
        {vertices[1], vertices[2]},
        {vertices[2], vertices[0]},
    };
}

bool XWithinEdge(double x, const Point& start, const Point& end) {
    const double lower_x = std::min(start.x, end.x);
    const double upper_x = std::max(start.x, end.x);
    return lower_x - kEps <= x && x <= upper_x + kEps;
}

bool TryLineFunctionForEdge(const Point& start, const Point& end, BoundaryFunction* line) {
    if (std::abs(start.x - end.x) <= kEps) {
        return false;
    }
    line->kind = BoundaryFunction::Kind::kLine;
    line->slope = (end.y - start.y) / (end.x - start.x);
    line->intercept = start.y - (line->slope * start.x);
    return true;
}

ShapeProfile BuildShapeProfile(const Paper& paper) {
    if (paper.type == kCircleTypeCode) {
        const double center_x = paper.circle.center.x;
        const double center_y = paper.circle.center.y;
        const double radius = paper.circle.radius;
        ShapeSlab slab{
            center_x - radius,
            center_x + radius,
            BoundaryFunction{
                BoundaryFunction::Kind::kCircle, 0.0, 0.0, center_x, center_y, radius, -1},
            BoundaryFunction{
                BoundaryFunction::Kind::kCircle, 0.0, 0.0, center_x, center_y, radius, 1},
        };
        return ShapeProfile{slab.left, slab.right, {slab}};
    }

    std::vector<double> xs;
    xs.reserve(3);
    for (const Point& vertex : paper.triangle.vertices) {
        xs.push_back(vertex.x);
    }
    std::sort(xs.begin(), xs.end());
    xs.erase(std::unique(xs.begin(), xs.end()), xs.end());

    std::vector<ShapeSlab> slabs;
    for (size_t i = 0; i + 1 < xs.size(); ++i) {
        const double left = xs[i];
        const double right = xs[i + 1];
        if (right - left <= kEps) {
            continue;
        }
        const double midpoint = (left + right) / 2.0;
        std::vector<BoundaryFunction> active_lines;
        for (const auto& [start, end] : TriangleEdges(paper.triangle)) {
            BoundaryFunction line;
            if (!TryLineFunctionForEdge(start, end, &line) || !XWithinEdge(midpoint, start, end)) {
                continue;
            }
            active_lines.push_back(line);
        }
        if (active_lines.size() < 2) {
            continue;
        }
        std::sort(active_lines.begin(), active_lines.end(), [midpoint](const BoundaryFunction& lhs,
                                                                      const BoundaryFunction& rhs) {
            return lhs.ValueAt(midpoint) < rhs.ValueAt(midpoint);
        });
        slabs.push_back(ShapeSlab{left, right, active_lines.front(), active_lines.back()});
    }

    if (slabs.empty()) {
        double xmin = paper.triangle.vertices[0].x;
        for (const Point& vertex : paper.triangle.vertices) {
            xmin = std::min(xmin, vertex.x);
        }
        return ShapeProfile{xmin, xmin, {}};
    }

    return ShapeProfile{slabs.front().left, slabs.back().right, std::move(slabs)};
}

std::vector<double> LineLineIntersections(const BoundaryFunction& left,
                                          const BoundaryFunction& right,
                                          double xmin,
                                          double xmax) {
    const double slope_delta = left.slope - right.slope;
    if (std::abs(slope_delta) <= kEps) {
        return {};
    }
    const double point = (right.intercept - left.intercept) / slope_delta;
    if (xmin - kEps <= point && point <= xmax + kEps) {
        return {point};
    }
    return {};
}

std::vector<double> LineCircleIntersections(const BoundaryFunction& line,
                                            const BoundaryFunction& circle,
                                            double xmin,
                                            double xmax) {
    const double shifted_intercept = line.intercept - circle.center_y;
    const double qa = 1.0 + (line.slope * line.slope);
    const double qb = (2.0 * line.slope * shifted_intercept) - (2.0 * circle.center_x);
    const double qc = (circle.center_x * circle.center_x) +
                      (shifted_intercept * shifted_intercept) -
                      (circle.radius * circle.radius);
    double discriminant = (qb * qb) - (4.0 * qa * qc);
    if (discriminant < -kEps) {
        return {};
    }
    discriminant = std::max(0.0, discriminant);
    const double sqrt_discriminant = std::sqrt(discriminant);
    const std::array<double, 2> roots = {
        (-qb - sqrt_discriminant) / (2.0 * qa),
        (-qb + sqrt_discriminant) / (2.0 * qa),
    };

    std::vector<double> matches;
    for (double root : roots) {
        if (!(xmin - kEps <= root && root <= xmax + kEps)) {
            continue;
        }
        if (std::abs(line.ValueAt(root) - circle.ValueAt(root)) <= 1e-9) {
            matches.push_back(root);
        }
    }
    std::sort(matches.begin(), matches.end());
    matches.erase(std::unique(matches.begin(), matches.end(), [](double lhs, double rhs) {
                      return std::abs(lhs - rhs) <= kEps;
                  }),
                  matches.end());
    return matches;
}

std::vector<double> CircleCircleIntersections(const BoundaryFunction& left,
                                              const BoundaryFunction& right,
                                              double xmin,
                                              double xmax) {
    const double dx = right.center_x - left.center_x;
    const double dy = right.center_y - left.center_y;
    const double distance = std::hypot(dx, dy);
    if (distance <= kEps) {
        return {};
    }
    if (distance > left.radius + right.radius + kEps) {
        return {};
    }
    if (distance < std::abs(left.radius - right.radius) - kEps) {
        return {};
    }

    const double a = ((left.radius * left.radius) - (right.radius * right.radius) +
                      (distance * distance)) /
                     (2.0 * distance);
    const double h_sq = (left.radius * left.radius) - (a * a);
    if (h_sq < -kEps) {
        return {};
    }
    const double h = std::sqrt(std::max(0.0, h_sq));
    const double x_mid = left.center_x + (a * dx / distance);
    const double y_mid = left.center_y + (a * dy / distance);
    const double offset_x = -dy * h / distance;
    const double offset_y = dx * h / distance;

    const std::array<Point, 2> candidates = {
        Point{x_mid + offset_x, y_mid + offset_y},
        Point{x_mid - offset_x, y_mid - offset_y},
    };

    std::vector<double> matches;
    for (const Point& point : candidates) {
        if (!(xmin - kEps <= point.x && point.x <= xmax + kEps)) {
            continue;
        }
        if (std::abs(point.y - left.ValueAt(point.x)) <= 1e-9 &&
            std::abs(point.y - right.ValueAt(point.x)) <= 1e-9) {
            matches.push_back(point.x);
        }
    }
    std::sort(matches.begin(), matches.end());
    matches.erase(std::unique(matches.begin(), matches.end(), [](double lhs, double rhs) {
                      return std::abs(lhs - rhs) <= kEps;
                  }),
                  matches.end());
    return matches;
}

std::vector<double> FunctionIntersections(const BoundaryFunction& left,
                                          const BoundaryFunction& right,
                                          double xmin,
                                          double xmax) {
    if (left.kind == BoundaryFunction::Kind::kLine &&
        right.kind == BoundaryFunction::Kind::kLine) {
        return LineLineIntersections(left, right, xmin, xmax);
    }
    if (left.kind == BoundaryFunction::Kind::kLine &&
        right.kind == BoundaryFunction::Kind::kCircle) {
        return LineCircleIntersections(left, right, xmin, xmax);
    }
    if (left.kind == BoundaryFunction::Kind::kCircle &&
        right.kind == BoundaryFunction::Kind::kLine) {
        return LineCircleIntersections(right, left, xmin, xmax);
    }
    return CircleCircleIntersections(left, right, xmin, xmax);
}

const ShapeSlab* FindSlab(const std::vector<ShapeSlab>& slabs, double x) {
    for (const ShapeSlab& slab : slabs) {
        if (slab.left - kEps <= x && x <= slab.right + kEps) {
            return &slab;
        }
    }
    return nullptr;
}

double IntegrateTargetProfile(const ShapeProfile& profile) {
    double total = 0.0;
    for (const ShapeSlab& slab : profile.slabs) {
        total += slab.upper.Integral(slab.left, slab.right) -
                 slab.lower.Integral(slab.left, slab.right);
    }
    return total;
}

std::vector<double> CollectBreakpoints(const ShapeProfile& target,
                                       const std::vector<ShapeProfile>& occluders) {
    std::set<double> points = {target.xmin, target.xmax};
    std::vector<ShapeSlab> slabs = target.slabs;
    for (const ShapeProfile& occluder : occluders) {
        for (const ShapeSlab& slab : occluder.slabs) {
            const double left = std::max(target.xmin, slab.left);
            const double right = std::min(target.xmax, slab.right);
            if (right - left <= kEps) {
                continue;
            }
            points.insert(left);
            points.insert(right);
            slabs.push_back(ShapeSlab{left, right, slab.lower, slab.upper});
        }
    }

    struct BoundaryPiece {
        double left;
        double right;
        BoundaryFunction function;
    };

    std::vector<BoundaryPiece> pieces;
    for (const ShapeSlab& slab : slabs) {
        pieces.push_back(BoundaryPiece{slab.left, slab.right, slab.lower});
        pieces.push_back(BoundaryPiece{slab.left, slab.right, slab.upper});
    }

    for (size_t i = 0; i < pieces.size(); ++i) {
        for (size_t j = i + 1; j < pieces.size(); ++j) {
            const double left = std::max({target.xmin, pieces[i].left, pieces[j].left});
            const double right = std::min({target.xmax, pieces[i].right, pieces[j].right});
            if (right - left <= kEps) {
                continue;
            }
            for (double point :
                 FunctionIntersections(pieces[i].function, pieces[j].function, left, right)) {
                if (left + kEps < point && point < right - kEps) {
                    points.insert(point);
                }
            }
        }
    }

    return {points.begin(), points.end()};
}

double CoveredAreaInSlab(const ShapeProfile& target,
                        const std::vector<ShapeProfile>& occluders,
                        double left,
                        double right) {
    const double midpoint = (left + right) / 2.0;
    const ShapeSlab* target_slab = FindSlab(target.slabs, midpoint);
    if (target_slab == nullptr) {
        return 0.0;
    }

    std::vector<std::pair<BoundaryFunction, BoundaryFunction>> clipped_intervals;
    for (const ShapeProfile& occluder : occluders) {
        const ShapeSlab* occluder_slab = FindSlab(occluder.slabs, midpoint);
        if (occluder_slab == nullptr) {
            continue;
        }

        const BoundaryFunction lower =
            occluder_slab->lower.ValueAt(midpoint) >= target_slab->lower.ValueAt(midpoint) - kEps
                ? occluder_slab->lower
                : target_slab->lower;
        const BoundaryFunction upper =
            occluder_slab->upper.ValueAt(midpoint) <= target_slab->upper.ValueAt(midpoint) + kEps
                ? occluder_slab->upper
                : target_slab->upper;

        if (upper.ValueAt(midpoint) - lower.ValueAt(midpoint) <= kEps) {
            continue;
        }
        clipped_intervals.push_back({lower, upper});
    }

    if (clipped_intervals.empty()) {
        return 0.0;
    }

    std::sort(clipped_intervals.begin(), clipped_intervals.end(), [midpoint](
                                                             const auto& lhs, const auto& rhs) {
        return lhs.first.ValueAt(midpoint) < rhs.first.ValueAt(midpoint);
    });

    double merged_area = 0.0;
    BoundaryFunction current_lower = clipped_intervals[0].first;
    BoundaryFunction current_upper = clipped_intervals[0].second;
    for (size_t i = 1; i < clipped_intervals.size(); ++i) {
        const BoundaryFunction& next_lower = clipped_intervals[i].first;
        const BoundaryFunction& next_upper = clipped_intervals[i].second;
        if (next_lower.ValueAt(midpoint) > current_upper.ValueAt(midpoint) + kEps) {
            merged_area += current_upper.Integral(left, right) - current_lower.Integral(left, right);
            current_lower = next_lower;
            current_upper = next_upper;
            continue;
        }
        if (next_upper.ValueAt(midpoint) > current_upper.ValueAt(midpoint) + kEps) {
            current_upper = next_upper;
        }
    }

    merged_area += current_upper.Integral(left, right) - current_lower.Integral(left, right);
    return merged_area;
}

double VisibleAreaAgainstOccluders(const ShapeProfile& target_profile,
                                   const std::vector<ShapeProfile>& occluders) {
    if (target_profile.xmax - target_profile.xmin <= kEps) {
        return 0.0;
    }

    std::vector<ShapeProfile> relevant_profiles;
    relevant_profiles.reserve(occluders.size());
    for (const ShapeProfile& profile : occluders) {
        if (profile.xmin <= target_profile.xmax + kEps &&
            profile.xmax >= target_profile.xmin - kEps) {
            relevant_profiles.push_back(profile);
        }
    }

    const std::vector<double> breakpoints = CollectBreakpoints(target_profile, relevant_profiles);
    const double target_area = IntegrateTargetProfile(target_profile);
    double covered_area = 0.0;
    for (size_t i = 0; i + 1 < breakpoints.size(); ++i) {
        const double left = breakpoints[i];
        const double right = breakpoints[i + 1];
        if (right - left <= kEps) {
            continue;
        }
        covered_area += CoveredAreaInSlab(target_profile, relevant_profiles, left, right);
    }

    const double visible_area = target_area - covered_area;
    if (std::abs(visible_area) <= kAreaTolerance) {
        return 0.0;
    }
    return std::max(0.0, visible_area);
}

VisibleAreas EvaluateVisibleAreas(const std::vector<Paper>& papers) {
    std::vector<ShapeProfile> profiles;
    profiles.reserve(papers.size());
    for (const Paper& paper : papers) {
        profiles.push_back(BuildShapeProfile(paper));
    }

    VisibleAreas visible_areas(papers.size(), 0.0);
    for (size_t index = 0; index < papers.size(); ++index) {
        std::vector<ShapeProfile> occluders;
        occluders.reserve(papers.size() - index - 1);
        for (size_t occluder = index + 1; occluder < papers.size(); ++occluder) {
            occluders.push_back(profiles[occluder]);
        }
        visible_areas[index] = VisibleAreaAgainstOccluders(profiles[index], occluders);
    }
    return visible_areas;
}

VisibleAreaRows EvaluatePrefixVisibleAreas(const std::vector<Paper>& papers) {
    VisibleAreaRows rows;
    rows.reserve(papers.size());
    std::vector<Paper> prefix;
    prefix.reserve(papers.size());
    for (const Paper& paper : papers) {
        prefix.push_back(paper);
        rows.push_back(EvaluateVisibleAreas(prefix));
    }
    return rows;
}

std::vector<Paper> ParseInput(std::istream& input) {
    int paper_count = 0;
    if (!(input >> paper_count)) {
        return {};
    }

    std::vector<Paper> papers;
    papers.reserve(std::max(0, paper_count));
    for (int i = 0; i < paper_count; ++i) {
        int type = 0;
        input >> type;
        if (type == kTriangleTypeCode) {
            Paper paper;
            paper.type = type;
            for (Point& vertex : paper.triangle.vertices) {
                input >> vertex.x >> vertex.y;
            }
            papers.push_back(paper);
            continue;
        }
        if (type == kCircleTypeCode) {
            Paper paper;
            paper.type = type;
            input >> paper.circle.center.x >> paper.circle.center.y >> paper.circle.radius;
            papers.push_back(paper);
            continue;
        }
        throw std::runtime_error("unsupported paper type");
    }
    return papers;
}

std::string FormatRows(const VisibleAreaRows& rows) {
    std::ostringstream output;
    output << std::fixed << std::setprecision(12);
    for (size_t i = 0; i < rows.size(); ++i) {
        for (size_t j = 0; j < rows[i].size(); ++j) {
            if (j > 0) {
                output << ' ';
            }
            output << rows[i][j];
        }
        if (i + 1 < rows.size()) {
            output << '\n';
        }
    }
    return output.str();
}

}  // namespace

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);

    const std::vector<Paper> papers = ParseInput(std::cin);
    const VisibleAreaRows rows = EvaluatePrefixVisibleAreas(papers);
    std::cout << FormatRows(rows);
    return 0;
}
