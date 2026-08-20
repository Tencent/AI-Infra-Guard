"""Repeated-request Average Fidelity Loss (AFL) statistics.

The target API contributes only returned text.  Probability information is
required solely from the trusted reference API and is coarsened into a
predeclared finite outcome map before these estimators are used.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

import numpy as np
from scipy.special import digamma, xlogy


OTHER_CATEGORY = "<OTHER>"


def _normalize_probabilities(
    probabilities: Mapping[str, float],
) -> Dict[str, float]:
    normalized = {
        str(category): max(0.0, float(probability))
        for category, probability in probabilities.items()
    }
    total = sum(normalized.values())
    if total <= 0:
        raise ValueError("reference probabilities must have positive mass")
    return {
        category: probability / total
        for category, probability in normalized.items()
    }


def build_reference_categories(
    probabilities: Mapping[str, float],
    allowed_labels: Sequence[str],
) -> Dict[str, float]:
    """Coarsen reference token probabilities into labels plus ``<OTHER>``."""
    labels = [str(label) for label in allowed_labels]
    if not labels or len(labels) != len(set(labels)):
        raise ValueError("allowed_labels must contain distinct labels")
    if OTHER_CATEGORY in labels:
        raise ValueError(f"{OTHER_CATEGORY} is reserved")

    normalized = _normalize_probabilities(probabilities)
    result = {label: float(normalized.get(label, 0.0)) for label in labels}
    result[OTHER_CATEGORY] = max(0.0, 1.0 - sum(result.values()))
    return _normalize_probabilities(result)


def pool_reference_categories(
    reference: Mapping[str, float],
    *,
    samples: int,
    min_expected_count: float = 1.0,
) -> Dict[str, float]:
    """Pool rare labels using only the trusted reference distribution."""
    if samples < 2:
        raise ValueError("samples must be at least 2")
    if min_expected_count < 0:
        raise ValueError("min_expected_count must be nonnegative")

    normalized = _normalize_probabilities(reference)
    pooled: Dict[str, float] = {}
    other = float(normalized.get(OTHER_CATEGORY, 0.0))
    for category, probability in normalized.items():
        if category == OTHER_CATEGORY:
            continue
        if samples * probability >= min_expected_count:
            pooled[category] = probability
        else:
            other += probability
    pooled[OTHER_CATEGORY] = other
    return _normalize_probabilities(pooled)


def map_outcome(text: str, reference: Mapping[str, float]) -> str:
    """Apply the total, exact-match outcome map used by the paper protocol."""
    exact = str(text or "")
    if exact in reference and exact != OTHER_CATEGORY:
        return exact
    return OTHER_CATEGORY


def _aligned_arrays(
    counts: Mapping[str, int],
    reference_probabilities: Mapping[str, float],
    *,
    probability_floor: float = 1e-12,
) -> tuple[list[str], np.ndarray, np.ndarray]:
    categories = sorted(set(counts) | set(reference_probabilities))
    if not categories:
        raise ValueError("at least one category is required")
    reference_dict = _normalize_probabilities(
        {
            category: max(
                probability_floor,
                float(reference_probabilities.get(category, 0.0)),
            )
            for category in categories
        }
    )
    reference = np.asarray(
        [reference_dict[category] for category in categories], dtype=float
    )
    observed_counts = np.asarray(
        [int(counts.get(category, 0)) for category in categories], dtype=int
    )
    if np.any(observed_counts < 0):
        raise ValueError("counts must be nonnegative")
    if int(observed_counts.sum()) <= 0:
        raise ValueError("at least one sample is required")
    return categories, observed_counts, reference


def prior_parameters(
    reference: np.ndarray,
    *,
    prior_strength: float,
    prior_mode: str,
) -> np.ndarray:
    """Return a Dirichlet prior with fixed total concentration."""
    if prior_strength <= 0:
        raise ValueError("prior_strength must be positive")
    if prior_mode == "reference":
        return prior_strength * reference
    if prior_mode == "uniform":
        return np.full(len(reference), prior_strength / len(reference))
    raise ValueError("prior_mode must be 'reference' or 'uniform'")


def posterior_expected_kl(
    counts: Mapping[str, int],
    reference_probabilities: Mapping[str, float],
    *,
    prior_strength: float = 1.0,
    prior_mode: str = "reference",
) -> float:
    """Return ``E[KL(Q || P) | counts]`` under a Dirichlet posterior."""
    _, observed_counts, reference = _aligned_arrays(
        counts, reference_probabilities
    )
    posterior = observed_counts + prior_parameters(
        reference,
        prior_strength=prior_strength,
        prior_mode=prior_mode,
    )
    total = float(posterior.sum())
    expected_q_log_q = posterior / total * (
        digamma(posterior + 1.0) - digamma(total + 1.0)
    )
    expected_cross_entropy = -(posterior / total) * np.log(reference)
    return float(np.sum(expected_q_log_q + expected_cross_entropy))


def plugin_kl(
    counts: Mapping[str, int],
    reference_probabilities: Mapping[str, float],
    *,
    prior_strength: float = 1.0,
    prior_mode: str = "reference",
) -> float:
    _, observed_counts, reference = _aligned_arrays(
        counts, reference_probabilities
    )
    prior = prior_parameters(
        reference,
        prior_strength=prior_strength,
        prior_mode=prior_mode,
    )
    posterior_mean = (observed_counts + prior) / (
        observed_counts.sum() + prior.sum()
    )
    return float(np.sum(xlogy(posterior_mean, posterior_mean / reference)))


def unbiased_chi_square(
    counts: Mapping[str, int],
    reference_probabilities: Mapping[str, float],
) -> float:
    """Return the unbiased U-statistic for Pearson chi-square divergence."""
    _, observed_counts, reference = _aligned_arrays(
        counts, reference_probabilities
    )
    sample_size = int(observed_counts.sum())
    if sample_size < 2:
        raise ValueError("at least two samples are required")
    factorial_pairs = observed_counts * (observed_counts - 1.0)
    return float(
        np.sum(factorial_pairs / reference)
        / (sample_size * (sample_size - 1.0))
        - 1.0
    )


def estimate_repeated_context_kl(
    counts: Mapping[str, int],
    reference_probabilities: Mapping[str, float],
    *,
    prior_strength: float = 1.0,
    prior_mode: str = "reference",
    null_samples: int = 20_000,
    posterior_samples: int = 20_000,
    seed: int = 20260814,
) -> Dict[str, Any]:
    """Estimate coarsened KL, uncertainty, and the finite-sample null bias."""
    if null_samples < 1 or posterior_samples < 1:
        raise ValueError("null_samples and posterior_samples must be positive")
    categories, observed_counts, reference = _aligned_arrays(
        counts, reference_probabilities
    )
    sample_size = int(observed_counts.sum())
    prior = prior_parameters(
        reference,
        prior_strength=prior_strength,
        prior_mode=prior_mode,
    )
    posterior = observed_counts + prior
    rng = np.random.default_rng(seed)

    posterior_draws = rng.dirichlet(posterior, size=posterior_samples)
    posterior_kl_draws = np.sum(
        xlogy(posterior_draws, posterior_draws / reference), axis=1
    )
    posterior_mean = posterior_expected_kl(
        counts,
        reference_probabilities,
        prior_strength=prior_strength,
        prior_mode=prior_mode,
    )

    null_counts = rng.multinomial(sample_size, reference, size=null_samples)
    null_posterior = null_counts + prior
    null_total = sample_size + prior.sum()
    null_expected_q_log_q = null_posterior / null_total * (
        digamma(null_posterior + 1.0) - digamma(null_total + 1.0)
    )
    null_expected_cross_entropy = -(null_posterior / null_total) * np.log(
        reference
    )
    null_estimates = np.sum(
        null_expected_q_log_q + null_expected_cross_entropy, axis=1
    )
    baseline = float(null_estimates.mean())
    bias_corrected = posterior_mean - baseline
    chi_square = unbiased_chi_square(counts, reference_probabilities)
    return {
        "categories": categories,
        "effective_reference_probabilities": {
            category: float(probability)
            for category, probability in zip(categories, reference)
        },
        "sample_size": sample_size,
        "prior_mode": prior_mode,
        "prior_strength": prior_strength,
        "posterior_expected_KL": posterior_mean,
        "posterior_median_KL": float(np.median(posterior_kl_draws)),
        "posterior_credible_interval_95": [
            float(np.quantile(posterior_kl_draws, 0.025)),
            float(np.quantile(posterior_kl_draws, 0.975)),
        ],
        "plugin_KL": plugin_kl(
            counts,
            reference_probabilities,
            prior_strength=prior_strength,
            prior_mode=prior_mode,
        ),
        "unbiased_chi_square": chi_square,
        "half_unbiased_chi_square": 0.5 * chi_square,
        "null_baseline_mean": baseline,
        "null_baseline_sd": float(null_estimates.std(ddof=1))
        if null_samples > 1
        else 0.0,
        "bias_corrected_KL": bias_corrected,
        "nonnegative_bias_corrected_effect": max(0.0, bias_corrected),
        "null_bootstrap_one_sided_p": float(
            (np.count_nonzero(null_estimates >= posterior_mean - 1e-15) + 1)
            / (null_samples + 1)
        ),
        "null_samples": null_samples,
        "posterior_samples": posterior_samples,
    }


def aggregate_context_estimates(
    estimates: Sequence[Mapping[str, Any]],
) -> Dict[str, float | int]:
    """Aggregate context estimates; the AFL field is the paper's ``S_r``."""
    if not estimates:
        raise ValueError("at least one context estimate is required")
    weights = np.asarray(
        [float(item["sample_size"]) for item in estimates], dtype=float
    )
    weights /= weights.sum()
    afl = float(
        sum(
            weight * float(item["bias_corrected_KL"])
            for weight, item in zip(weights, estimates)
        )
    )
    return {
        "contexts": len(estimates),
        "total_samples": int(
            sum(int(item["sample_size"]) for item in estimates)
        ),
        "average_fidelity_loss": afl,
        "weighted_posterior_expected_KL": float(
            sum(
                weight * float(item["posterior_expected_KL"])
                for weight, item in zip(weights, estimates)
            )
        ),
        "weighted_null_baseline": float(
            sum(
                weight * float(item["null_baseline_mean"])
                for weight, item in zip(weights, estimates)
            )
        ),
        "weighted_bias_corrected_KL": afl,
        "weighted_half_unbiased_chi_square": float(
            sum(
                weight * float(item["half_unbiased_chi_square"])
                for weight, item in zip(weights, estimates)
            )
        ),
    }
