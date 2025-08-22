"""
A minimal fragrance recommender demonstrating the ASPIRATION factor.
- Hybrid score: climate_fit, occasion_fit, intensity_fit, longevity_fit,
  latent_sim (weight/brightness), aspiration_fit, diversity_bonus (light).
- Standalone for quick experimentation.

Run locally with Python 3.10+.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any
import math

# -----------------------------
# Data structures
# -----------------------------
@dataclass
class Fragrance:
    id: str
    brand: str
    name: str
    weight: float           # 0 = very light, 1 = very heavy
    brightness: float       # 0 = very fresh/green, 1 = very sweet/resinous
    sillage: int            # 1..5
    longevity: int          # 1..5
    seasonality: List[str]  # e.g., ["hot", "mild", "cool"]
    occasions: List[str]    # e.g., ["office", "date", "formal", "everyday"]
    archetypes: List[str]   # e.g., ["elegant", "bold", "mysterious", "approachable", "refined", "youthful", "adventurous", "sensual"]
    price: float

    def full_name(self) -> str:
        return f"{self.brand} {self.name}"

@dataclass
class UserProfile:
    climate: str            # hot | mild | cool | mixed
    occasion: str           # office | date | formal | gym | everyday
    intensity: str          # skin | moderate | trail
    longevity_goal: str     # short | workday | allday
    weight_pref: float      # 0..1 target
    brightness_pref: float  # 0..1 target
    aspiration: List[str]   # desired identity cues

# -----------------------------
# Helpers
# -----------------------------
def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def closeness(x: float, y: float) -> float:
    """1 - normalized distance on [0,1]."""
    return 1.0 - abs(x - y)


def map_intensity_to_sillage(intensity: str) -> float:
    return {
        "skin": 1.0,
        "moderate": 3.0,
        "trail": 5.0,
    }.get(intensity, 3.0)


def map_longevity_goal(goal: str) -> float:
    return {
        "short": 2.0,
        "workday": 4.0,
        "allday": 5.0,
    }.get(goal, 4.0)

# -----------------------------
# Scoring components
# -----------------------------

def climate_fit(user: UserProfile, f: Fragrance) -> float:
    if user.climate == "mixed":
        return 1.0 if len(f.seasonality) >= 2 else 0.7
    return 1.0 if user.climate in f.seasonality else 0.3


def occasion_fit(user: UserProfile, f: Fragrance) -> float:
    return 1.0 if user.occasion in f.occasions else (0.6 if "everyday" in f.occasions else 0.2)


def intensity_fit(user: UserProfile, f: Fragrance) -> float:
    target = map_intensity_to_sillage(user.intensity)
    return clamp01(1 - abs((f.sillage - target) / 4.0))


def longevity_fit(user: UserProfile, f: Fragrance) -> float:
    target = map_longevity_goal(user.longevity_goal)
    return clamp01(1 - abs((f.longevity - target) / 4.0))


def latent_sim(user: UserProfile, f: Fragrance) -> float:
    a = closeness(user.weight_pref, f.weight)
    b = closeness(user.brightness_pref, f.brightness)
    return 0.5 * a + 0.5 * b


def aspiration_fit(user: UserProfile, f: Fragrance) -> float:
    if not user.aspiration:
        return 0.5
    overlap = len(set(user.aspiration) & set(f.archetypes))
    return clamp01(overlap / max(1, len(user.aspiration)))


def diversity_bonus(already: List[Fragrance], candidate: Fragrance) -> float:
    """Small bonus if candidate adds new archetypes vs. already picked ones."""
    if not already:
        return 0.05
    have = set(x for f in already for x in f.archetypes)
    new = set(candidate.archetypes) - have
    return 0.05 if new else 0.0

# -----------------------------
# Catalog (tiny demo)
# -----------------------------
CATALOG: List[Fragrance] = [
    Fragrance("1", "Chanel", "Bleu de Chanel", 0.45, 0.35, 3, 4, ["mild", "hot"], ["office", "everyday", "date"], ["refined", "approachable"], 110.0),
    Fragrance("2", "Dior", "Sauvage EDT", 0.50, 0.40, 4, 4, ["hot", "mild"], ["everyday", "date"], ["bold", "youthful"], 100.0),
    Fragrance("3", "Le Labo", "Santal 33", 0.70, 0.60, 4, 5, ["mild", "cool"], ["office", "date", "formal"], ["adventurous", "sensual"], 220.0),
    Fragrance("4", "MFK", "Baccarat Rouge 540", 0.80, 0.85, 5, 5, ["cool", "mild"], ["formal", "date"], ["bold", "mysterious", "elegant"], 300.0),
    Fragrance("5", "Chanel", "No.5 EDP", 0.65, 0.70, 3, 5, ["cool", "mild"], ["formal", "office"], ["elegant", "refined"], 200.0),
    Fragrance("6", "Tom Ford", "Black Orchid", 0.85, 0.80, 5, 5, ["cool"], ["date", "formal"], ["mysterious", "bold", "sensual"], 180.0),
    Fragrance("7", "Jo Malone", "Wood Sage & Sea Salt", 0.25, 0.15, 2, 3, ["hot", "mild"], ["office", "everyday"], ["approachable", "refined"], 120.0),
    Fragrance("8", "Prada", "Infusion d'Iris", 0.35, 0.30, 2, 4, ["mild", "cool"], ["office", "formal"], ["elegant", "refined"], 150.0),
    Fragrance("9", "Giorgio Armani", "Acqua di Giò Profondo", 0.40, 0.25, 3, 4, ["hot", "mild"], ["everyday", "office"], ["approachable", "youthful"], 120.0),
]

# -----------------------------
# Master score
# -----------------------------
WEIGHTS = {
    "climate": 0.20,
    "occasion": 0.15,
    "intensity": 0.15,
    "longevity": 0.15,
    "latent": 0.20,
    "aspiration": 0.10,
    "diversity": 0.05,
}


def score_user_to_fragrance(user: UserProfile, f: Fragrance, picked: List[Fragrance]) -> Dict[str, float]:
    parts = {
        "climate": climate_fit(user, f),
        "occasion": occasion_fit(user, f),
        "intensity": intensity_fit(user, f),
        "longevity": longevity_fit(user, f),
        "latent": latent_sim(user, f),
        "aspiration": aspiration_fit(user, f),
        "diversity": diversity_bonus(picked, f),
    }
    total = sum(WEIGHTS[k] * parts[k] for k in WEIGHTS)
    parts["total"] = total
    return parts


def recommend(user: UserProfile, k: int = 3) -> List[Dict[str, Any]]:
    picked: List[Fragrance] = []
    candidates = CATALOG[:]
    results = []

    # Greedy MMR-ish selection with diversity bonus applied in scoring
    for _ in range(k):
        best = None
        best_parts = None
        best_score = -1
        for f in candidates:
            parts = score_user_to_fragrance(user, f, picked)
            if parts["total"] > best_score and f not in picked:
                best, best_parts, best_score = f, parts, parts["total"]
        if best is None:
            break
        picked.append(best)
        results.append({
            "id": best.id,
            "name": best.full_name(),
            "score": round(best_score, 3),
            "parts": {k: round(v, 3) for k, v in best_parts.items()},
            "archetypes": best.archetypes,
        })
        candidates.remove(best)
    return results

# -----------------------------
# Demo run
# -----------------------------
if __name__ == "__main__":
    user = UserProfile(
        climate="mild",
        occasion="office",
        intensity="skin",
        longevity_goal="workday",
        weight_pref=0.40,
        brightness_pref=0.35,
        aspiration=["elegant", "mysterious"],
    )

    recs = recommend(user, k=3)
    print("Top picks (with aspiration factor):\n")
    for i, r in enumerate(recs, 1):
        print(f"{i}. {r['name']}  — score {r['score']}  archetypes={r['archetypes']}")
        p = r["parts"]
        print(f"   parts: climate={p['climate']} occasion={p['occasion']} intensity={p['intensity']} longevity={p['longevity']} latent={p['latent']} aspiration={p['aspiration']} diversity={p['diversity']}")
