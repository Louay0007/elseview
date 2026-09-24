"""Versioned single-call ceilings, not multi-call depth or a quality guarantee."""

from decimal import Decimal
from typing import Literal

Depth = Literal["quick", "standard", "deep"]
REVISION = "1"
LIMITATIONS = [
    "Single provider call only; no multi-call chunk processing or resumable synthesis.",
    "Coverage is limited to supplied authorized snapshot text, not the whole study.",
    "UTF-8/protocol upper-bound estimate, not a quote or a guarantee of provider charges.",
    "Human review required; greater depth does not guarantee better findings.",
]


def resolve(settings, depth: Depth = "standard"):
    if depth not in {"quick", "standard", "deep"}:
        raise ValueError("invalid_depth")
    standard_chars = max(500, settings.llm_context_limit // 3)
    max_chars = {
        "quick": max(500, standard_chars // 2),
        "standard": standard_chars,
        "deep": max(500, settings.llm_context_limit // 2),
    }[depth]
    return {
        "name": depth,
        "revision": REVISION,
        "execution": "single_call",
        "max_provider_calls": 1,
        "max_source_chars": max_chars,
        # Each nonempty span consumes at least one character of the shared ceiling.
        "max_chunks": max_chars,
        "chunk_size": 2400,
        "chunk_overlap": 200,
        "max_output_tokens": max(1, settings.llm_max_output_tokens // 2)
        if depth == "quick"
        else settings.llm_max_output_tokens,
        "max_output_bytes": 50000 if depth == "quick" else 100000,
        "limitations": list(LIMITATIONS),
    }


def orchestration(settings, depth: Depth):
    """Revision 2: bounded source maps followed by evidence-preserving synthesis."""
    profile = resolve(settings, depth)
    maps = {"quick": 1, "standard": 2, "deep": 4}[depth]
    return profile | {
        "revision": "2",
        "execution": "bounded_graph",
        "max_provider_calls": 1 if maps == 1 else maps + 1,
        "max_maps": maps,
        "max_source_chars": min(96000, maps * 24000),
        "max_chunks": maps * 32,
        "max_output_bytes": 16000,
        "intermediate_bytes": min(
            16000, max(0, settings.llm_context_limit - profile["max_output_tokens"] - 4096) // 2
        ),
        "limitations": [
            "Bounded source maps and synthesis; not exhaustive study findings.",
            "UTF-8/protocol upper bound, not a guarantee of provider charges.",
            "Human review required; counts refer to answer revisions, not people.",
        ],
    }


def effective(run_config):
    """Legacy JSON keeps its original configured limits without a data migration."""
    if "depth_profile" in run_config:
        return run_config["depth_profile"]
    from types import SimpleNamespace

    return resolve(
        SimpleNamespace(
            llm_context_limit=int(run_config["llm_context_limit"]),
            llm_max_output_tokens=int(run_config["llm_max_output_tokens"]),
        )
    ) | {"revision": "legacy"}


def execution_settings(settings, run_config):
    """Pin monetary and token limits even if operators change settings during I/O."""
    return settings.model_copy(
        update={
            "llm_max_output_tokens": effective(run_config)["max_output_tokens"],
            "llm_context_limit": int(run_config["llm_context_limit"]),
            **{
                key: Decimal(run_config[key])
                for key in (
                    "llm_input_price_per_million",
                    "llm_output_price_per_million",
                    "llm_other_charge_reserve",
                )
            },
        }
    )
