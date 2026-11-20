#ifndef TEXASSOLVER_EV_EXPORT_H
#define TEXASSOLVER_EV_EXPORT_H

#include <cmath>
#include <stdexcept>

namespace ev_export {
// Opponent reach is accumulated as float sums and reduced by card-removal
// terms (PCfrSolver collecting_statics). A truly-zero mass can therefore land
// at a tiny positive or negative value (~1e-9), and utility/reach then
// explodes into meaningless magnitudes (observed: serialized EVs of +-1e12 in
// T0 slice-1 packs, and "negative opponent reach for EV" crashes once the
// guard existed). Residual utility noise against such a mass scales with the
// payoff magnitude; ~0.02 was observed on a real 100bb tree, so the corruption
// tripwire sits far above that at 1.0 (payoff units).
// Negligible mass means "unreachable against this hand": report EV 0,
// matching the zero convention below. A significantly negative reach, or
// large utility against negligible reach, is real corruption and still throws.
inline float normalize(float utility, float opponent_reach) {
    if (!std::isfinite(utility) || !std::isfinite(opponent_reach))
        throw std::runtime_error("non-finite EV input");
    const float reach_tol = 1e-4f;
    const float utility_tol = 1.0f;
    if (std::fabs(opponent_reach) < reach_tol) {
        if (std::fabs(utility) > utility_tol)
            throw std::runtime_error("large utility with negligible opponent reach");
        return 0.0f;
    }
    if (opponent_reach < 0.0f)
        throw std::runtime_error("significantly negative opponent reach for EV");
    const float value = utility / opponent_reach;
    if (!std::isfinite(value))
        throw std::runtime_error("non-finite normalized EV");
    return value;
}
}
#endif
