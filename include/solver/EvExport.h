#ifndef TEXASSOLVER_EV_EXPORT_H
#define TEXASSOLVER_EV_EXPORT_H

#include <cmath>
#include <stdexcept>

namespace ev_export {
// Zero utility and zero opponent reach have no conditional EV. Preserve the zero
// convention, but do not silently serialize an infinite/corrupt value.
inline float normalize(float utility, float opponent_reach) {
    if (!std::isfinite(utility) || !std::isfinite(opponent_reach))
        throw std::runtime_error("non-finite EV input");
    if (opponent_reach < 0.0f)
        throw std::runtime_error("negative opponent reach for EV");
    if (opponent_reach == 0.0f) {
        if (utility != 0.0f)
            throw std::runtime_error("nonzero utility with zero opponent reach");
        return 0.0f;
    }
    const float value = utility / opponent_reach;
    if (!std::isfinite(value))
        throw std::runtime_error("non-finite normalized EV");
    return value;
}
}
#endif
