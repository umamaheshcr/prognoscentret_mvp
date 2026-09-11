"""The pilot's forecast: ordinary least squares, fitted once at start-up.

    log(starts_t) = a + b1·TobinsQ_t + b2·RealMortgageRate_t + Q2 + Q3 + Q4

`LRA` is already a model type in the production `model_library.py` — Office,
Education, Other buildings and Transport all use it, and the Office model is a
log-log OLS. So this is an in-house method, not a shortcut around the method.

Why OLS and not the production ensemble: under a moving slider an ensemble
containing a seasonal-naive member and a pipeline overlay capped at four
quarters responds discontinuously, and the analyst sees movement they cannot
attribute. OLS responds smoothly, monotonically, and its decomposition is
exact — coefficient times driver change, with no residual to explain away.

The cost is stated everywhere it is reported: this is a DEMO MODEL. It is less
accurate than the production ensemble, whose weights were set by hold-out
backtest for exactly that reason.

No statsmodels. The algebra is eight lines and belongs where it can be read.
"""

from dataclasses import dataclass
import numpy as np
import pandas as pd

from .data import STARTS, DRIVERS, SEGMENTS, RATE

HOLDOUT = 8          # quarters held back to measure error
SEASONS = (2, 3, 4)  # Q1 is the base


@dataclass(frozen=True)
class Spec:
    """A config row, in the production sense: which variables the model takes,
    which transform, and whether the seasonals are in. Gate 2 edits THIS —
    never a number. A hand-edited value is untraceable; a weight is not."""
    tobins_q: str
    use_rate: bool = True
    seasonals: bool = True
    tq_transform: str = "level"     # level | sq  (production Flats uses sq)
    holdout: int = HOLDOUT

    def as_dict(self):
        return {"tobins_q": self.tobins_q, "use_rate": self.use_rate,
                "seasonals": self.seasonals, "tq_transform": self.tq_transform,
                "holdout": self.holdout}


@dataclass
class Fit:
    segment: str
    spec: Spec
    beta: np.ndarray          # [const, tobins_q, (rate), (Q2, Q3, Q4)]
    se: np.ndarray
    r2: float
    n: int
    holdout_mape: float
    sigma: float              # residual sd, in logs — the band
    index: pd.PeriodIndex     # the fitted sample

    @property
    def tobins_q_name(self):
        return self.spec.tobins_q

    @property
    def b_tobins_q(self):
        return float(self.beta[1])

    @property
    def b_rate(self):
        return float(self.beta[2]) if self.spec.use_rate else 0.0


def _transform(tq: np.ndarray, how: str) -> np.ndarray:
    return tq ** 2 if how == "sq" else tq


def _design(tq: np.ndarray, rate: np.ndarray, quarters: np.ndarray,
            spec: Spec) -> np.ndarray:
    cols = [np.ones(len(tq)), _transform(tq, spec.tq_transform)]
    if spec.use_rate:
        cols.append(rate)
    if spec.seasonals:
        cols += [(quarters == k).astype(float) for k in SEASONS]
    return np.column_stack(cols)


def _ols(X, y):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    dof = max(len(y) - X.shape[1], 1)
    s2 = float(resid @ resid) / dof
    xtx_inv = np.linalg.pinv(X.T @ X)
    se = np.sqrt(np.maximum(np.diag(xtx_inv) * s2, 0.0))
    r2 = 1.0 - float(resid @ resid) / float(((y - y.mean()) ** 2).sum())
    return beta, se, r2, float(np.sqrt(s2))


DEFAULT_SPECS = {
    seg: Spec(tobins_q=meta["tobins_q"]) for seg, meta in SEGMENTS.items()
}

# Candidate Tobin's Q series a gate-2 config row may point at. Every one of
# them shares the same hpi numerator, which is the point.
TQ_CHOICES = [
    "Tobins-Q (Flats)",
    "Tobins-Q (Detached houses)",
    "Tobins-Q (Holiday homes)",
]


def fit(segment: str, spec: Spec | None = None) -> Fit:
    spec = spec or DEFAULT_SPECS[segment]
    frame = pd.concat(
        [np.log(STARTS[segment]).rename("ly"),
         DRIVERS[spec.tobins_q].rename("tq"),
         DRIVERS[RATE].rename("rate")],
        axis=1,
    ).dropna()

    q = frame.index.quarter.to_numpy()
    X = _design(frame["tq"].to_numpy(), frame["rate"].to_numpy(), q, spec)
    y = frame["ly"].to_numpy()
    beta, se, r2, sigma = _ols(X, y)

    # Hold-out: refit without the last `holdout` quarters, score on them.
    cut = len(frame) - spec.holdout
    b_ho, *_ = np.linalg.lstsq(X[:cut], y[:cut], rcond=None)
    pred = np.exp(X[cut:] @ b_ho)
    act = np.exp(y[cut:])
    mape = float(np.mean(np.abs(pred - act) / act) * 100.0)

    return Fit(segment=segment, spec=spec, beta=beta, se=se, r2=r2,
               n=len(frame), holdout_mape=mape, sigma=sigma, index=frame.index)


_CACHE: dict = {}


def get_fit(segment: str, spec: Spec | None = None) -> Fit:
    """Fits are cached by (segment, spec), so a gate-2 config change refits
    once and every later slider move is a matrix multiply again."""
    spec = spec or DEFAULT_SPECS[segment]
    key = (segment, spec)
    if key not in _CACHE:
        _CACHE[key] = fit(segment, spec)
    return _CACHE[key]


FITS = {seg: get_fit(seg) for seg in SEGMENTS}


def predict(f: Fit, tq: pd.Series, rate: pd.Series) -> pd.DataFrame:
    """Predict on a driver path. Returns level, lo, hi — the band is ±1 sigma
    in logs, which is asymmetric in levels, as it should be."""
    idx = tq.index
    X = _design(tq.to_numpy(), rate.to_numpy(), idx.quarter.to_numpy(), f.spec)
    ly = X @ f.beta
    return pd.DataFrame(
        {"level": np.exp(ly),
         "lo": np.exp(ly - f.sigma),
         "hi": np.exp(ly + f.sigma)},
        index=idx,
    )


def decompose(f: Fit, tq_base: pd.Series, rate_base: pd.Series,
              tq_new: pd.Series, rate_new: pd.Series) -> dict:
    """Exact attribution. In logs the model is additive, so the effect of each
    driver is its coefficient times its change — no residual, no approximation.
    Reported as a percentage effect on the level."""
    tb = _transform(tq_base.to_numpy(), f.spec.tq_transform)
    tn = _transform(tq_new.to_numpy(), f.spec.tq_transform)
    d_tq = float((tn - tb).mean())
    d_rate = float((rate_new - rate_base).mean())
    eff_tq = (np.exp(f.b_tobins_q * d_tq) - 1.0) * 100.0
    eff_rate = (np.exp(f.b_rate * d_rate) - 1.0) * 100.0
    net = (np.exp(f.b_tobins_q * d_tq + f.b_rate * d_rate) - 1.0) * 100.0
    return {
        "tobins_q": {"delta": float(d_tq), "effect_pct": float(eff_tq),
                     "coef": f.b_tobins_q},
        "rate": {"delta": float(d_rate), "effect_pct": float(eff_rate),
                 "coef": f.b_rate},
        "net_pct": float(net),
    }


def diagnostics(specs: dict | None = None) -> list:
    out = []
    for seg in SEGMENTS:
        f = get_fit(seg, (specs or {}).get(seg))
        out.append({
            "segment": seg,
            "spec": f.spec.as_dict(),
            "label": SEGMENTS[seg]["label"],
            "unit": SEGMENTS[seg]["unit"],
            "n": f.n,
            "sample": f"{f.index.min()} .. {f.index.max()}",
            "r2": round(f.r2, 3),
            "holdout_mape": round(f.holdout_mape, 1),
            "b_tobins_q": round(f.b_tobins_q, 4),
            "b_tobins_q_se": round(float(f.se[1]), 4),
            "b_rate": round(f.b_rate, 4),
            "b_rate_se": round(float(f.se[2]), 4),
            "sign_tobins_q_ok": f.b_tobins_q > 0,
            "sign_rate_ok": f.b_rate < 0,
            "production": SEGMENTS[seg]["production"],
        })
    return out
