"""Editable ranking weight configuration for each supported use case."""

# Each score component is on a 0-10 scale and the weights below should sum to 1.0.
# Keep these values simple and explicit so product teams can tune ranking behavior quickly.
USE_CASE_WEIGHTS: dict[str, dict[str, float]] = {
    # UI/UX design laptops benefit from strong RAM and CPU for design tools and multitasking.
    # Storage matters for large assets and project files.
    # Budget and value are still important for affordability in the local market.
    # GPU has a smaller weight because many UI workflows are not GPU-dominant.
    "ui/ux design": {
        "budget": 0.20,
        "ram": 0.20,
        "storage": 0.15,
        "cpu": 0.20,
        "gpu": 0.05,
        "rating": 0.10,
        "value": 0.10,
    },
    # Programming prioritizes RAM, CPU, and storage for IDE performance, local services,
    # containers, and compilation. GPU is not usually a core requirement.
    "programming": {
        "budget": 0.20,
        "ram": 0.25,
        "storage": 0.20,
        "cpu": 0.20,
        "gpu": 0.00,
        "rating": 0.05,
        "value": 0.10,
    },
    # Gaming relies heavily on GPU, then RAM and CPU for stable frame rates.
    # Budget gets slightly less weight because performance hardware is often pricier.
    "gaming": {
        "budget": 0.15,
        "ram": 0.20,
        "storage": 0.10,
        "cpu": 0.15,
        "gpu": 0.25,
        "rating": 0.05,
        "value": 0.10,
    },
    # General fallback profile for non-specific prompts.
    "general": {
        "budget": 0.30,
        "ram": 0.15,
        "storage": 0.10,
        "cpu": 0.15,
        "gpu": 0.05,
        "rating": 0.15,
        "value": 0.10,
    },
}

