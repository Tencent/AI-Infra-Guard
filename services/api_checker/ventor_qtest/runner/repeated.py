"""Configuration-driven runner for repeated-request AFL audits."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, Mapping, MutableMapping, Sequence

import numpy as np
from scipy.special import digamma, xlogy

from ..repeated_request import (
    aggregate_context_estimates,
    build_reference_categories,
    estimate_repeated_context_kl,
    map_outcome,
    pool_reference_categories,
    prior_parameters,
)
from .orchestrator import UnifiedClient, sanitize_for_json

if TYPE_CHECKING:
    from ..check import DeepSeekSequenceTester


DEFAULT_CONTEXTS: tuple[dict[str, Any], ...] = (
    {
        "id": "coin_1_8",
        "allowed_labels": ("1", "8"),
        "prompt": "Flip a fair virtual coin once. Return 1 for heads or 8 for tails. Reply with exactly one digit and nothing else.",
    },
    {
        "id": "tetra_0_3_6_9",
        "allowed_labels": ("0", "3", "6", "9"),
        "prompt": "Roll a fair four-sided virtual die whose faces are labeled 0, 3, 6, and 9. Reply with exactly the resulting one digit and nothing else.",
    },
    {
        "id": "wheel_2_5_7",
        "allowed_labels": ("2", "5", "7"),
        "prompt": "Spin a virtual wheel once with probabilities P(2)=0.20, P(5)=0.50, and P(7)=0.30. Reply with exactly one digit and nothing else.",
    },
    {
        "id": "bag_1_4",
        "allowed_labels": ("1", "4"),
        "prompt": "Draw one ticket from a virtual bag containing one ticket labeled 1 and three tickets labeled 4. Reply with exactly one digit and nothing else.",
    },
    {
        "id": "urn_0_4_7",
        "allowed_labels": ("0", "4", "7"),
        "prompt": "Choose uniformly at random one label from the set {0, 4, 7}. Reply with exactly one digit and nothing else.",
    },
    {
        "id": "urn_2_6_9",
        "allowed_labels": ("2", "6", "9"),
        "prompt": "A virtual urn contains equal numbers of balls labeled 2, 6, and 9. Draw one ball and reply with exactly its one-digit label and nothing else.",
    },
    {
        "id": "endpoint_0_9",
        "allowed_labels": ("0", "9"),
        "prompt": "Select either endpoint of the digit interval from 0 to 9 with equal probability. Reply with exactly 0 or 9 and nothing else.",
    },
    {
        "id": "suits_1_3_7_9",
        "allowed_labels": ("1", "3", "7", "9"),
        "prompt": "Select one of four equally likely card suits mapped to digits 1, 3, 7, and 9. Reply with exactly the selected digit and nothing else.",
    },
    {
        "id": "biased_2_6",
        "allowed_labels": ("2", "6"),
        "prompt": "Sample one digit with probabilities P(2)=0.65 and P(6)=0.35. Reply with exactly one digit and nothing else.",
    },
    {
        "id": "doors_3_5_8",
        "allowed_labels": ("3", "5", "8"),
        "prompt": "Choose uniformly among three closed doors labeled 3, 5, and 8. Reply with exactly the chosen one-digit label and nothing else.",
    },
    {
        "id": "lottery_1_2_7_8",
        "allowed_labels": ("1", "2", "7", "8"),
        "prompt": "Run a virtual lottery with P(1)=0.10, P(2)=0.20, P(7)=0.30, and P(8)=0.40. Reply with exactly one digit and nothing else.",
    },
    {
        "id": "multiples_3_6_9",
        "allowed_labels": ("3", "6", "9"),
        "prompt": "Choose uniformly at random one nonzero single-digit multiple of 3. Reply with exactly one digit and nothing else.",
    },
)


def _default_data_dir() -> Path:
    return Path(
        os.environ.get(
            "AIG_API_CHECKER_DATA_DIR",
            Path(__file__).resolve().parents[2] / "runtime",
        )
    )


def _contexts(config: Mapping[str, Any]) -> list[Dict[str, Any]]:
    raw_contexts = config.get("contexts") or DEFAULT_CONTEXTS
    contexts: list[Dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw in enumerate(raw_contexts):
        if not isinstance(raw, Mapping):
            raise ValueError(f"contexts[{index}] must be an object")
        context_id = str(raw.get("id") or f"context-{index + 1}")
        prompt = str(raw.get("prompt") or "")
        labels = raw.get("allowed_labels", raw.get("allowed_digits"))
        if not prompt or not isinstance(labels, Sequence) or isinstance(labels, str):
            raise ValueError(
                f"context {context_id!r} requires prompt and allowed_labels"
            )
        allowed_labels = [str(label) for label in labels]
        if context_id in seen_ids:
            raise ValueError(f"duplicate context id: {context_id}")
        if not allowed_labels or len(allowed_labels) != len(set(allowed_labels)):
            raise ValueError(f"context {context_id!r} has invalid allowed_labels")
        seen_ids.add(context_id)
        contexts.append(
            {
                "id": context_id,
                "prompt": prompt,
                "allowed_labels": allowed_labels,
            }
        )
    if not contexts:
        raise ValueError("at least one context is required")
    return contexts


def _endpoint(config: Mapping[str, Any]) -> str:
    endpoint = str(config.get("endpoint") or "").strip()
    if endpoint:
        return endpoint
    base_url = str(config.get("base_url") or "").rstrip("/")
    path = str(config.get("path") or "")
    if not base_url:
        raise ValueError("reference requires endpoint or base_url")
    return f"{base_url}/{path.lstrip('/')}" if path else base_url


def _reference_tester(config: Mapping[str, Any]) -> "DeepSeekSequenceTester":
    from ..check import DeepSeekSequenceTester

    return DeepSeekSequenceTester(
        api_key=str(config.get("api_key") or ""),
        base_url=_endpoint(config),
        model=str(config.get("model") or ""),
        temperature=float(config.get("temperature", 1.0)),
        top_logprobs=int(config.get("top_logprobs", 20)),
        max_workers=1,
        request_delay=float(config.get("request_delay", 0.0)),
        extra_headers=dict(config.get("extra_headers") or {}),
        provider=dict(config["provider"]) if config.get("provider") else None,
        extra_payload=dict(config.get("extra_payload") or {}),
        timeout_sec=float(config.get("timeout_sec", config.get("timeout", 45.0))),
        include_assistant_prefix_metadata=False,
    )


def _vendor_clients(
    vendors: Sequence[Mapping[str, Any]],
) -> Dict[str, UnifiedClient]:
    clients: Dict[str, UnifiedClient] = {}
    for index, vendor in enumerate(vendors):
        if not isinstance(vendor, Mapping):
            raise ValueError(f"vendors[{index}] must be an object")
        conf: MutableMapping[str, Any] = dict(vendor)
        name = str(conf.get("name") or "")
        if not name or name in clients:
            raise ValueError(f"vendor name must be nonempty and unique: {name!r}")
        conf.setdefault("path", "/v1/chat/completions")
        conf["max_tokens"] = 1
        conf["strip_response"] = False
        clients[name] = UnifiedClient(conf)
    if not clients:
        raise ValueError("at least one vendor is required")
    return clients


def _redact_secrets(value: Any) -> Any:
    if isinstance(value, Mapping):
        result = {}
        for key, item in value.items():
            lowered = str(key).lower().replace("-", "_")
            if lowered in {
                "api_key",
                "authorization",
                "x_api_key",
                "access_token",
                "secret",
            } or lowered.endswith("_secret"):
                result[str(key)] = "<redacted>"
            else:
                result[str(key)] = _redact_secrets(item)
        return result
    if isinstance(value, (list, tuple)):
        return [_redact_secrets(item) for item in value]
    return value


def _public_endpoint_config(
    config: Mapping[str, Any], *, reference: bool = False
) -> Dict[str, Any]:
    fields = (
        "name",
        "endpoint",
        "base_url",
        "path",
        "model",
        "schema",
        "provider",
        "temperature",
    )
    result = {field: config[field] for field in fields if field in config}
    if reference and "top_logprobs" in config:
        result["top_logprobs"] = int(config["top_logprobs"])
    return result


def _protocol_fingerprint(
    config: Mapping[str, Any], contexts: Sequence[Mapping[str, Any]]
) -> str:
    protocol = {
        "samples_per_context": int(config.get("samples_per_context", 50)),
        "temperature": float(config.get("temperature", 1.0)),
        "contexts": list(contexts),
        "reference": _redact_secrets(config.get("reference") or {}),
        "vendors": _redact_secrets(config.get("vendors") or []),
    }
    serialized = json.dumps(
        protocol, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def _save_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(
        sanitize_for_json(payload), ensure_ascii=False, indent=2
    ) + "\n"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(content)
    os.chmod(path, 0o600)


def _sample_once(
    client: UnifiedClient,
    route: str,
    prompt: str,
    sample_index: int,
    temperature: float,
) -> Dict[str, Any]:
    try:
        text = client.generate(prompt, temperature=temperature)
        return {
            "route": route,
            "sample_index": sample_index,
            "text": text,
            "request_failed": False,
        }
    except Exception as exc:  # Every request remains part of the total map.
        return {
            "route": route,
            "sample_index": sample_index,
            "text": "",
            "request_failed": True,
            "error": f"{type(exc).__name__}: {exc}"[:500],
        }


def collect_repeated_requests(
    config: Mapping[str, Any],
    *,
    contexts: Sequence[Mapping[str, Any]],
    checkpoint: Path,
    resume: bool = True,
    tester_factory: Callable[
        [Mapping[str, Any]], "DeepSeekSequenceTester"
    ] = _reference_tester,
    client_factory: Callable[
        [Sequence[Mapping[str, Any]]], Dict[str, UnifiedClient]
    ] = _vendor_clients,
) -> tuple[list[Dict[str, Any]], Dict[str, Dict[str, float]], list[str]]:
    """Collect reference distributions and target text, with safe resume."""
    samples = int(config.get("samples_per_context", 50))
    if samples < 2:
        raise ValueError("samples_per_context must be at least 2")
    workers = max(1, int(config.get("workers", 8)))
    checkpoint_every = max(1, int(config.get("checkpoint_every", 25)))
    fingerprint = _protocol_fingerprint(config, contexts)

    if resume and checkpoint.exists():
        saved = json.loads(checkpoint.read_text(encoding="utf-8"))
        if saved.get("protocol_fingerprint") != fingerprint:
            raise RuntimeError(
                "checkpoint protocol fingerprint does not match this configuration"
            )
    else:
        saved = {
            "protocol_fingerprint": fingerprint,
            "base_reference_probabilities": {},
            "raw_samples": [],
        }

    references = {
        str(key): {str(k): float(v) for k, v in value.items()}
        for key, value in (saved.get("base_reference_probabilities") or {}).items()
    }
    raw_by_key: Dict[tuple[str, str, int], Dict[str, Any]] = {}
    for raw in saved.get("raw_samples") or []:
        row = dict(raw)
        key = (
            str(row.get("context_id")),
            str(row.get("route")),
            int(row.get("sample_index", -1)),
        )
        raw_by_key[key] = row

    reference_conf = config.get("reference")
    vendors = config.get("vendors")
    if not isinstance(reference_conf, Mapping):
        raise ValueError("reference configuration is required")
    if not isinstance(vendors, Sequence) or isinstance(vendors, (str, bytes)):
        raise ValueError("vendors must be a list")
    tester = tester_factory(reference_conf)
    clients = client_factory(vendors)
    route_names = list(clients)
    default_temperature = float(config.get("temperature", 1.0))
    route_temperatures = {
        str(vendor.get("name")): float(
            vendor.get("temperature", default_temperature)
        )
        for vendor in vendors
    }

    def save_checkpoint() -> None:
        _save_json(
            checkpoint,
            {
                "protocol_fingerprint": fingerprint,
                "base_reference_probabilities": references,
                "raw_samples": list(raw_by_key.values()),
            },
        )

    for context_index, context in enumerate(contexts):
        context_id = str(context["id"])
        prompt = str(context["prompt"])
        if context_id not in references:
            _, probabilities = tester.get_token_probabilities(
                [{"role": "user", "content": prompt}], max_tokens=1
            )
            if not probabilities:
                raise RuntimeError(
                    f"reference returned no logprobs for context {context_id!r}"
                )
            references[context_id] = build_reference_categories(
                probabilities, context["allowed_labels"]
            )
            save_checkpoint()

        jobs = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            for sample_index in range(samples):
                for route, client in clients.items():
                    key = (context_id, route, sample_index)
                    if key in raw_by_key:
                        continue
                    jobs.append(
                        executor.submit(
                            _sample_once,
                            client,
                            route,
                            prompt,
                            sample_index,
                            route_temperatures[route],
                        )
                    )
            for completed, future in enumerate(
                concurrent.futures.as_completed(jobs), start=1
            ):
                row = future.result()
                row.update(
                    {"context_index": context_index, "context_id": context_id}
                )
                key = (context_id, str(row["route"]), int(row["sample_index"]))
                raw_by_key[key] = row
                if completed % checkpoint_every == 0:
                    save_checkpoint()
        save_checkpoint()
        print(
            f"[AFL] context {context_index + 1}/{len(contexts)} complete; "
            f"new requests={len(jobs)}",
            flush=True,
        )

    return list(raw_by_key.values()), references, route_names


def _seed_for(seed: int, *parts: str) -> int:
    digest = hashlib.sha256("\0".join(parts).encode("utf-8")).digest()
    return seed + int.from_bytes(digest[:4], "big")


def _add_route_inference(
    context_rows: Sequence[Mapping[str, Any]],
    route_rows: list[Dict[str, Any]],
    *,
    seed: int,
    inference_samples: int,
    prior_strength: float,
    prior_mode: str,
) -> None:
    contexts = sorted({str(row["context_id"]) for row in context_rows})
    representative_rows = {
        context_id: next(
            row for row in context_rows if row["context_id"] == context_id
        )
        for context_id in contexts
    }
    context_null_raw: Dict[str, np.ndarray] = {}
    for context_id in contexts:
        row = representative_rows[context_id]
        categories = list(row["categories"])
        effective = row["effective_reference_probabilities"]
        reference = np.asarray([effective[category] for category in categories])
        sample_size = int(row["sample_size"])
        prior = prior_parameters(
            reference,
            prior_strength=prior_strength,
            prior_mode=prior_mode,
        )
        rng = np.random.default_rng(_seed_for(seed, "null", context_id))
        null_counts = rng.multinomial(
            sample_size, reference, size=inference_samples
        )
        posterior = null_counts + prior
        total = sample_size + prior.sum()
        null_raw = np.sum(
            posterior
            / total
            * (
                digamma(posterior + 1.0)
                - digamma(total + 1.0)
                - np.log(reference)
            ),
            axis=1,
        )
        context_null_raw[context_id] = null_raw

    by_route = {str(row["route"]): row for row in route_rows}
    for route, route_result in by_route.items():
        rows = sorted(
            (row for row in context_rows if row["route"] == route),
            key=lambda row: str(row["context_id"]),
        )
        posterior_route_draws = np.zeros(inference_samples)
        route_null_draws = np.zeros(inference_samples)
        for row in rows:
            categories = list(row["categories"])
            effective = row["effective_reference_probabilities"]
            reference = np.asarray(
                [effective[category] for category in categories]
            )
            counts = np.asarray(
                [int(row["counts"].get(category, 0)) for category in categories]
            )
            prior = prior_parameters(
                reference,
                prior_strength=prior_strength,
                prior_mode=prior_mode,
            )
            rng = np.random.default_rng(
                _seed_for(seed, "posterior", route, str(row["context_id"]))
            )
            draws = rng.dirichlet(counts + prior, size=inference_samples)
            posterior_route_draws += (
                np.sum(xlogy(draws, draws / reference), axis=1)
                - float(row["null_baseline_mean"])
            ) / len(rows)
            route_null_draws += (
                context_null_raw[str(row["context_id"])]
                - float(row["null_baseline_mean"])
            ) / len(rows)

        observed = float(route_result["average_fidelity_loss"])
        route_result.update(
            {
                "afl_credible_interval_95": [
                    float(np.quantile(posterior_route_draws, 0.025)),
                    float(np.quantile(posterior_route_draws, 0.975)),
                ],
                "route_null_p_one_sided": float(
                    (
                        np.count_nonzero(
                            route_null_draws >= observed - 1e-15
                        )
                        + 1
                    )
                    / (inference_samples + 1)
                ),
                "route_null_draws": inference_samples,
            }
        )

    ordered = sorted(
        (
            float(result["route_null_p_one_sided"]),
            str(result["route"]),
        )
        for result in route_rows
    )
    running = 0.0
    total_routes = len(ordered)
    for rank, (p_value, route) in enumerate(ordered):
        adjusted = min(1.0, (total_routes - rank) * p_value)
        running = max(running, adjusted)
        by_route[route]["route_null_p_holm"] = running


def analyze_repeated_requests(
    config: Mapping[str, Any],
    *,
    contexts: Sequence[Mapping[str, Any]],
    raw_samples: Sequence[Mapping[str, Any]],
    references: Mapping[str, Mapping[str, float]],
    route_names: Sequence[str],
) -> Dict[str, Any]:
    """Calculate context-level coarsened KL and route-level AFL."""
    samples = int(config.get("samples_per_context", 50))
    min_expected_count = float(config.get("min_expected_count", 1.0))
    null_samples = int(config.get("null_samples", 20_000))
    posterior_samples = int(config.get("posterior_samples", 20_000))
    inference_samples = int(config.get("inference_samples", 20_000))
    prior_strength = float(config.get("prior_strength", 1.0))
    prior_mode = str(config.get("prior_mode", "reference"))
    seed = int(config.get("seed", 20260814))
    if inference_samples < 1:
        raise ValueError("inference_samples must be positive")

    context_rows: list[Dict[str, Any]] = []
    for context_index, context in enumerate(contexts):
        context_id = str(context["id"])
        reference = pool_reference_categories(
            references[context_id],
            samples=samples,
            min_expected_count=min_expected_count,
        )
        for route in route_names:
            rows = [
                row
                for row in raw_samples
                if row.get("context_id") == context_id
                and row.get("route") == route
            ]
            if len(rows) != samples:
                raise RuntimeError(
                    f"expected {samples} samples for {context_id}/{route}; "
                    f"got {len(rows)}"
                )
            counts = Counter(
                map_outcome(str(row.get("text") or ""), reference)
                for row in rows
            )
            estimate = estimate_repeated_context_kl(
                counts,
                reference,
                prior_strength=prior_strength,
                prior_mode=prior_mode,
                null_samples=null_samples,
                posterior_samples=posterior_samples,
                # Keep the nominal Monte Carlo setup context-stable across
                # routes; target identity must not set the null protocol.
                seed=_seed_for(seed, "estimate", context_id),
            )
            context_rows.append(
                {
                    "context_index": context_index,
                    "context_id": context_id,
                    "prompt": context["prompt"],
                    "route": route,
                    "reference_probabilities": reference,
                    "counts": dict(counts),
                    "request_failures": sum(
                        bool(row.get("request_failed")) for row in rows
                    ),
                    **estimate,
                }
            )

    route_rows: list[Dict[str, Any]] = []
    for route in route_names:
        rows = [row for row in context_rows if row["route"] == route]
        route_rows.append(
            {
                "route": route,
                "request_failures": sum(
                    int(row["request_failures"]) for row in rows
                ),
                **aggregate_context_estimates(rows),
            }
        )

    _add_route_inference(
        context_rows,
        route_rows,
        seed=seed,
        inference_samples=inference_samples,
        prior_strength=prior_strength,
        prior_mode=prior_mode,
    )
    return {
        "context_results": context_rows,
        "route_results": route_rows,
    }


def run_repeated_request(
    config: Mapping[str, Any],
    *,
    output: str | Path | None = None,
    checkpoint: str | Path | None = None,
    resume: bool = True,
) -> Dict[str, Any]:
    """Run a complete repeated-request AFL audit from a config mapping."""
    contexts = _contexts(config)
    result_dir = _default_data_dir() / "qtest" / "result" / "afl"
    output_path = Path(output or config.get("output") or result_dir / "latest.json")
    checkpoint_path = Path(
        checkpoint
        or config.get("checkpoint")
        or result_dir / "checkpoint.json"
    )

    raw_samples, references, route_names = collect_repeated_requests(
        config,
        contexts=contexts,
        checkpoint=checkpoint_path,
        resume=resume,
    )
    analysis = analyze_repeated_requests(
        config,
        contexts=contexts,
        raw_samples=raw_samples,
        references=references,
        route_names=route_names,
    )
    payload = {
        "method": "repeated_request_afl",
        "description": (
            "Average Fidelity Loss: null-bias-corrected within-window mean "
            "coarsened KL from repeated target text"
        ),
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "protocol_fingerprint": _protocol_fingerprint(config, contexts),
        "protocol": {
            "samples_per_context": int(config.get("samples_per_context", 50)),
            "contexts": len(contexts),
            "temperature": float(config.get("temperature", 1.0)),
            "min_expected_count": float(config.get("min_expected_count", 1.0)),
            "prior_mode": str(config.get("prior_mode", "reference")),
            "prior_strength": float(config.get("prior_strength", 1.0)),
            "null_samples": int(config.get("null_samples", 20_000)),
            "posterior_samples": int(config.get("posterior_samples", 20_000)),
            "inference_samples": int(config.get("inference_samples", 20_000)),
            "seed": int(config.get("seed", 20260814)),
        },
        "reference": _public_endpoint_config(
            config.get("reference") or {}, reference=True
        ),
        "route_configs": [
            _public_endpoint_config(vendor)
            for vendor in (config.get("vendors") or [])
        ],
        "routes": list(route_names),
        "contexts": list(contexts),
        "base_reference_probabilities": references,
        **analysis,
        "raw_samples": raw_samples,
    }
    _save_json(output_path, payload)
    print(f"[ok] AFL result: {output_path}")
    return payload
