# streamlit_app.py  (SAFE MODE)
# Minimal version to fix blank page issues on Streamlit Cloud.
# - No experimental UI args (e.g., border=True)
# - No secrets required (Meta Pixel disabled by default)
# - Pure Python 3.9–3.13 compatible

from dataclasses import dataclass
from typing import List, Dict, Any
import streamlit as st

# ---------- Data structures ----------
@dataclass
class Fragrance:
    id: str
    brand: str
    name: str
    weight: float
    brightness: float
    sillage: int
    longevity: int
    seasonality: List[str]
    occasions: List[str]
    archetypes: List[str]
    price: float
    def full_name(self) -> str:
        return f"{self.brand} {self.name}"

@dataclass
class UserProfile:
    climate: str
    occasion: str
    intensity: str
    longevity_goal: str
    weight_pref: float
    brightness_pref: float
    aspiration: List[str]

# ---------- Helpers ----------
def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))

def closeness(x: float, y: float) -> float:
    return 1.0 - abs(x - y)

def map_intensity_to_sillage(intensity: str) -> float:
    return {"skin": 1.0, "moderate": 3.0, "trail": 5.0}.get(intensity, 3.0)

def map_longevity_goal(goal: str) -> float:
    return {"short": 2.0, "workday": 4.0, "allday": 5.0}.get(goal, 4.0)

# ---------- Scoring ----------
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
    if not already:
        return 0.05
    have = set(x for f in already for x in f.archetypes)
    new = set(candidate.archetypes) - have
    return 0.05 if new else 0.0

WEIGHTS = {"climate": 0.20, "occasion": 0.15, "intensity": 0.15, "longevity": 0.15, "latent": 0.20, "aspiration": 0.10, "diversity": 0.05}

# ---------- Catalog (demo) ----------
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

# ---------- Recommender ----------

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


def explain_pick(user: UserProfile, r: Dict[str, Any]) -> str:
    p = r["parts"]
    mood = ("skin-close" if user.intensity == "skin" else
            "moderately projecting" if user.intensity == "moderate" else
            "leaves a trail")
    asp = ", ".join(user.aspiration) if user.aspiration else "your style"
    return (
        f"Because you chose **{user.occasion}** in a **{user.climate}** climate and prefer **{mood}** with **{user.longevity_goal}** longevity, "
        f"we prioritized weight/brightness close to your taste and scents mapped to **{asp}**."
    )

# ---------- UI ----------
st.set_page_config(page_title="Fragrance Match (MVP)", page_icon="🧪", layout="centered")

st.title("Find Your Fragrance Match")
st.write("Answer a few quick questions. Get 3 tailored picks — no note knowledge needed.")

with st.form("quiz"):
    col1, col2 = st.columns(2)
    with col1:
        climate = st.selectbox("Your usual climate", ["hot", "mild", "cool", "mixed"], index=1)
        occasion = st.selectbox("Main occasion", ["everyday", "office", "date", "formal", "gym"], index=1)
        intensity = st.select_slider("How noticeable?", options=["skin", "moderate", "trail"], value="skin")
    with col2:
        longevity_goal = st.select_slider("How long should it last?", options=["short", "workday", "allday"], value="workday")
        weight_pref = st.slider("Texture (light ↔ heavy)", 0.0, 1.0, 0.4, 0.05)
        brightness_pref = st.slider("Brightness (fresh ↔ sweet)", 0.0, 1.0, 0.35, 0.05)

    aspiration = st.multiselect(
        "How do you want to be perceived? (aspiration)",
        ["elegant", "bold", "mysterious", "approachable", "refined", "youthful", "adventurous", "sensual"],
        default=["elegant"],
    )

    submitted = st.form_submit_button("Show my matches")

if submitted:
    user = UserProfile(
        climate=climate,
        occasion=occasion,
        intensity=intensity,
        longevity_goal=longevity_goal,
        weight_pref=weight_pref,
        brightness_pref=brightness_pref,
        aspiration=aspiration,
    )
    recs = recommend(user, k=3)

    st.subheader("Your top matches")
    for i, r in enumerate(recs, 1):
        st.markdown(f"### {i}. {r['name']}")
        st.caption(f"Archetypes: {', '.join(r['archetypes'])}")
        st.write(explain_pick(user, r))
        st.progress(min(1.0, r["parts"]["total"]))
        with st.expander("Why this pick (scores)"):
            st.json(r["parts"])
        st.divider()

# NOTE: Meta Pixel intentionally disabled in SAFE MODE to avoid rendering issues.
# When ready, add pixel snippet back guarded with try/except and a Secrets check.
