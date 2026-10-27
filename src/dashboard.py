"""
Smart Agriculture Crop Disease Intelligence Platform - Streamlit Dashboard
==========================================================================
Module: src.dashboard

A modern, production-grade Neo-Brutalist web frontend for the crop disease
classification FastAPI backend (src.api). Guides end-users, farmers, and
agronomists through instant leaf disease diagnostics with rich visual metrics,
top-k distributions, and actionable treatment advice.

Run with:
    streamlit run src/dashboard.py
"""

import io
import time
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image
import streamlit as st

# -----------------------------------------------------------------------------
# Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="AgriVision AI | Crop Disease Intelligence",
    page_icon="[AGRI]",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# Project Path Resolution & Sample Gallery Constants
# -----------------------------------------------------------------------------
_CURRENT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _CURRENT_DIR.parent
DATA_DIR = _PROJECT_ROOT / "data" / "processed" / "PlantVillage"

DEFAULT_BACKEND_URL = "http://localhost:8000"

# Curated samples for one-click testing
SAMPLE_PRESETS = [
    {
        "id": "tomato_healthy",
        "title": "Tomato: Healthy",
        "crop": "Tomato",
        "folder": "Tomato_healthy",
        "icon": "[TOMATO]",
        "badge": "Healthy",
        "badge_color": "#10B981",
    },
    {
        "id": "tomato_early_blight",
        "title": "Tomato: Early Blight",
        "crop": "Tomato",
        "folder": "Tomato_Early_blight",
        "icon": "[TOMATO]",
        "badge": "Fungal Infection",
        "badge_color": "#F59E0B",
    },
    {
        "id": "tomato_late_blight",
        "title": "Tomato: Late Blight",
        "crop": "Tomato",
        "folder": "Tomato_Late_blight",
        "icon": "[TOMATO]",
        "badge": "High Risk",
        "badge_color": "#EF4444",
    },
    {
        "id": "tomato_ylcv",
        "title": "Tomato: Yellow Leaf Curl",
        "crop": "Tomato",
        "folder": "Tomato__Tomato_YellowLeaf__Curl_Virus",
        "icon": "[TOMATO]",
        "badge": "Viral / Vector",
        "badge_color": "#EF4444",
    },
    {
        "id": "potato_late_blight",
        "title": "Potato: Late Blight",
        "crop": "Potato",
        "folder": "Potato___Late_blight",
        "icon": "[POTATO]",
        "badge": "Critical Risk",
        "badge_color": "#EF4444",
    },
    {
        "id": "pepper_bacterial_spot",
        "title": "Pepper: Bacterial Spot",
        "crop": "Pepper",
        "folder": "Pepper__bell___Bacterial_spot",
        "icon": "[PEPPER]",
        "badge": "Bacterial",
        "badge_color": "#F59E0B",
    },
]

# Agronomic Knowledge Base: Disease Details & Recommended Treatments
DISEASE_KNOWLEDGE_BASE: Dict[str, Dict[str, Any]] = {
    "Pepper__bell___Bacterial_spot": {
        "display_name": "Bell Pepper - Bacterial Spot",
        "scientific_name": "Xanthomonas campestris pv. vesicatoria",
        "crop": "Bell Pepper",
        "severity": "High",
        "status_tag": "CRITICAL RISK",
        "theme_color": "#EF4444",
        "overview": "Bacterial leaf spots that cause premature defoliation and severe fruit blistering.",
        "treatments": [
            "Apply preventive copper-based bactericides combined with mancozeb early in the season.",
            "Avoid overhead sprinkler irrigation; switch to drip irrigation to keep foliage dry.",
            "Sanitize all pruning tools with a 10% bleach solution between crop rows.",
            "Destroy and bury heavily infected crop residue immediately to prevent overwintering.",
        ],
    },
    "Pepper__bell___healthy": {
        "display_name": "Bell Pepper - Healthy Plant",
        "scientific_name": "Capsicum annuum",
        "crop": "Bell Pepper",
        "severity": "None",
        "status_tag": "OPTIMAL HEALTH",
        "theme_color": "#10B981",
        "overview": "Vibrant foliage with balanced chlorophyll density and no active pathogen signs.",
        "treatments": [
            "Maintain consistent soil moisture and well-balanced N-P-K fertilization.",
            "Conduct routine weekly scouting under leaf canopies for early aphid or thrip activity.",
            "Ensure proper spacing for optimal canopy airflow and sunlight penetration.",
        ],
    },
    "Potato___Early_blight": {
        "display_name": "Potato - Early Blight",
        "scientific_name": "Alternaria solani",
        "crop": "Potato",
        "severity": "Moderate",
        "status_tag": "ACTION REQUIRED",
        "theme_color": "#F59E0B",
        "overview": "Concentric ring 'target' lesions primarily attacking older foliage near the ground.",
        "treatments": [
            "Apply protectant fungicides (chlorothalonil or azoxystrobin) at first lesion detection.",
            "Prune and remove infected lower foliage touching the soil line.",
            "Practice a 3-year crop rotation with non-solanaceous crops (cereals, legumes).",
        ],
    },
    "Potato___Late_blight": {
        "display_name": "Potato - Late Blight",
        "scientific_name": "Phytophthora infestans",
        "crop": "Potato",
        "severity": "Critical",
        "status_tag": "HIGH SEVERITY ALERT",
        "theme_color": "#EF4444",
        "overview": "Rapidly spreading water-soaked dark lesions with white fungal growth on leaf undersides in humid weather.",
        "treatments": [
            "Emergency intervention: spray systemic fungicides (mefenoxam, cymoxanil, or mandipropamid).",
            "Immediately destroy cull piles and rogue out infected volunteer potato plants.",
            "Hill tubers well to prevent rain from washing down spores onto maturing potatoes.",
            "Do not harvest during wet conditions; kill vines 2 weeks prior to harvest.",
        ],
    },
    "Potato___healthy": {
        "display_name": "Potato - Healthy Plant",
        "scientific_name": "Solanum tuberosum",
        "crop": "Potato",
        "severity": "None",
        "status_tag": "OPTIMAL HEALTH",
        "theme_color": "#10B981",
        "overview": "Uniform green leaf tissue with strong vigor and zero necrotic symptoms.",
        "treatments": [
            "Maintain regular hilling and uniform soil moisture to support tuber initiation.",
            "Apply balanced potassium to promote natural resistance against opportunistic fungal spores.",
            "Continue periodic leaf-underside inspections following rain events.",
        ],
    },
    "Tomato_Bacterial_spot": {
        "display_name": "Tomato - Bacterial Spot",
        "scientific_name": "Xanthomonas vesicatoria",
        "crop": "Tomato",
        "severity": "High",
        "status_tag": "ACTION REQUIRED",
        "theme_color": "#EF4444",
        "overview": "Small, dark, greasy circular lesions on leaves and scab-like spots on tomato fruits.",
        "treatments": [
            "Apply copper-mancozeb sprays every 7-10 days under warm, moist conditions.",
            "Never cultivate, prune, or harvest while tomato plants are wet with dew or rain.",
            "Use certified pathogen-free seed stocks and resistant cultivars where possible.",
        ],
    },
    "Tomato_Early_blight": {
        "display_name": "Tomato - Early Blight",
        "scientific_name": "Alternaria linariae",
        "crop": "Tomato",
        "severity": "Moderate",
        "status_tag": "ACTION REQUIRED",
        "theme_color": "#F59E0B",
        "overview": "Bullseye target-pattern brown spots with surrounding yellow chlorotic halos on lower leaves.",
        "treatments": [
            "Prune lowest leaves to maintain a 12-inch clear air zone above mulch.",
            "Apply organic bio-fungicides (Bacillus subtilis) or copper hydroxide sprays.",
            "Apply organic straw or plastic mulch to stop soil-dwelling spores splashing onto leaves.",
        ],
    },
    "Tomato_Late_blight": {
        "display_name": "Tomato - Late Blight",
        "scientific_name": "Phytophthora infestans",
        "crop": "Tomato",
        "severity": "Critical",
        "status_tag": "HIGH SEVERITY ALERT",
        "theme_color": "#EF4444",
        "overview": "Devastating water-soaked lesions that cause whole branches and green fruit to collapse quickly.",
        "treatments": [
            "Apply systemic oomycete-targeted fungicides (dimethomorph, fluopicolide, or cyazofamid).",
            "Bag and remove infected plants immediately on a dry day; do not compost.",
            "Ensure wide row spacing (minimum 24-36 inches) for maximum airflow and canopy drying.",
        ],
    },
    "Tomato_Leaf_Mold": {
        "display_name": "Tomato - Leaf Mold",
        "scientific_name": "Passalora fulva",
        "crop": "Tomato",
        "severity": "Moderate",
        "status_tag": "MONITOR CLOSELY",
        "theme_color": "#F59E0B",
        "overview": "Pale green/yellow spots on leaf upper surface with olive-green velvety molds on leaf undersides.",
        "treatments": [
            "Significantly increase greenhouse ventilation and lower relative humidity below 85%.",
            "Circulate air with horizontal fans to prevent stagnant damp microclimates.",
            "Apply copper fungicide or sulfur sprays if greenhouse humidity cannot be reduced.",
        ],
    },
    "Tomato_Septoria_leaf_spot": {
        "display_name": "Tomato - Septoria Leaf Spot",
        "scientific_name": "Septoria lycopersici",
        "crop": "Tomato",
        "severity": "Moderate",
        "status_tag": "ACTION REQUIRED",
        "theme_color": "#F59E0B",
        "overview": "Numerous small circular spots with grayish-white centers and dark brown borders.",
        "treatments": [
            "Remove affected lower leaves as soon as first spots emerge.",
            "Apply chlorothalonil or copper-based protectant sprays at 7-day intervals.",
            "Maintain clean trellising to keep foliage off the ground.",
        ],
    },
    "Tomato_Spider_mites_Two_spotted_spider_mite": {
        "display_name": "Tomato - Two-Spotted Spider Mites",
        "scientific_name": "Tetranychus urticae",
        "crop": "Tomato",
        "severity": "Moderate",
        "status_tag": "PEST MANAGEMENT",
        "theme_color": "#F59E0B",
        "overview": "Fine stippling (yellow speckling) on foliage with delicate silky webbing under leaves.",
        "treatments": [
            "Introduce beneficial predatory mites (Phytoseiulus persimilis or Neoseiulus californicus).",
            "Spray insecticidal soap, neem oil, or horticultural oils targeting the leaf undersides.",
            "Avoid excessive nitrogen fertilization, which fuels explosive spider mite reproduction.",
        ],
    },
    "Tomato__Target_Spot": {
        "display_name": "Tomato - Target Spot",
        "scientific_name": "Corynespora cassiicola",
        "crop": "Tomato",
        "severity": "Moderate",
        "status_tag": "ACTION REQUIRED",
        "theme_color": "#F59E0B",
        "overview": "Brown lesions with light brown centers that cause upper canopy blight in humid climates.",
        "treatments": [
            "Apply strobilurin or carboxamide fungicides according to resistance management rotations.",
            "Avoid high plant density; prune suckers to optimize light and wind penetration.",
            "Remove weeds and alternate solanaceous hosts in field surroundings.",
        ],
    },
    "Tomato__Tomato_YellowLeaf__Curl_Virus": {
        "display_name": "Tomato - Yellow Leaf Curl Virus (TYLCV)",
        "scientific_name": "Begomovirus (Whitefly-transmitted)",
        "crop": "Tomato",
        "severity": "Critical",
        "status_tag": "VIRAL VECTOR ALERT",
        "theme_color": "#EF4444",
        "overview": "Severe upward leaf cupping, severe stunting, chlorotic margins, and flower abortion.",
        "treatments": [
            "Target vector whiteflies (Bemisia tabaci) using yellow sticky cards and systemic imidacloprid.",
            "Install 50-mesh fine insect exclusion netting in high tunnels and greenhouses.",
            "Rogue out and destroy infected plants immediately-viral infection has no chemical cure.",
            "Select TYLCV-resistant hybrids (e.g., Tycoon, Securitas) for future planting cycles.",
        ],
    },
    "Tomato__Tomato_mosaic_virus": {
        "display_name": "Tomato - Tomato Mosaic Virus (ToMV)",
        "scientific_name": "Tobamovirus",
        "crop": "Tomato",
        "severity": "High",
        "status_tag": "VIRAL INFECTION",
        "theme_color": "#EF4444",
        "overview": "Mottled light and dark green mosaic patterns with blistered, fern-like leaf distortion.",
        "treatments": [
            "Wash hands and dip tools in skim milk or 20% trisodium phosphate (TSP) solution before handling crops.",
            "Prohibit tobacco use near tomatoes (virus easily spreads mechanically via hands).",
            "Remove and incinerate infected plants to avoid mechanical sap transmission to healthy rows.",
        ],
    },
    "Tomato_healthy": {
        "display_name": "Tomato - Healthy Plant",
        "scientific_name": "Solanum lycopersicum",
        "crop": "Tomato",
        "severity": "None",
        "status_tag": "OPTIMAL HEALTH",
        "theme_color": "#10B981",
        "overview": "Rich emerald foliage with vigorous cell structure, balanced veins, and zero blemishes.",
        "treatments": [
            "Maintain deep, infrequent drip irrigation to encourage deep root establishment.",
            "Top-dress with compost and balanced micronutrients (calcium/magnesium) to prevent blossom-end rot.",
            "Continue regular IPM scouting for pests and early season fungal onset.",
        ],
    },
}

# -----------------------------------------------------------------------------
# Neo-Brutalism Custom CSS Injection
# -----------------------------------------------------------------------------
NEO_BRUTALISM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700;800&family=Inter:wght@400;600;700;900&display=swap');

/* Main Canvas */
html, body, [data-testid="stAppViewContainer"] {
    background-color: #F8F9FA;
    font-family: 'Inter', -apple-system, sans-serif;
    color: #111827;
}

/* Base Headings */
h1, h2, h3, h4, h5, h6 {
    font-family: 'Space Grotesk', -apple-system, sans-serif !important;
    font-weight: 800 !important;
    letter-spacing: -0.5px !important;
    color: #111827 !important;
}

/* Brutalist Card Container */
.nb-card {
    background-color: #FFFFFF;
    border: 3px solid #111827;
    border-radius: 12px;
    box-shadow: 5px 5px 0px #111827;
    padding: 24px;
    margin-bottom: 16px;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.nb-card:hover {
    transform: translate(-2px, -2px);
    box-shadow: 7px 7px 0px #111827;
}

/* Header Hero Banner */
.nb-hero {
    background: linear-gradient(135deg, #ECFDF5 0%, #D1FAE5 100%);
    border: 3px solid #111827;
    border-radius: 14px;
    box-shadow: 6px 6px 0px #111827;
    padding: 18px 24px;
    margin-bottom: 24px;
}

/* Badges & Pills */
.nb-pill {
    display: inline-block;
    padding: 6px 14px;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.82rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border: 2px solid #111827;
    border-radius: 8px;
    box-shadow: 2px 2px 0px #111827;
    margin-right: 8px;
    margin-bottom: 8px;
}

.pill-green { background-color: #10B981; color: #FFFFFF; }
.pill-amber { background-color: #F59E0B; color: #111827; }
.pill-red { background-color: #EF4444; color: #FFFFFF; }
.pill-white { background-color: #FFFFFF; color: #111827; }
.pill-purple { background-color: #8B5CF6; color: #FFFFFF; }
.pill-blue { background-color: #3B82F6; color: #FFFFFF; }

/* Telemetry Strip */
.nb-telemetry-box {
    background-color: #FFFFFF;
    border: 2.5px solid #111827;
    border-radius: 10px;
    box-shadow: 3px 3px 0px #111827;
    padding: 12px 18px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 18px;
}

/* Streamlit Native Progress Bar Theming */
div[data-testid="stProgress"] > div {
    background: #E5E7EB !important;
    border: 2px solid #111827 !important;
    border-radius: 8px !important;
    height: 20px !important;
    overflow: hidden;
}
div[data-testid="stProgress"] > div > div {
    border-radius: 6px !important;
    height: 20px !important;
}

/* Sample Quick-Test Grid Card */
.nb-sample-item {
    background: #FFFFFF;
    border: 2.5px solid #111827;
    border-radius: 10px;
    box-shadow: 3px 3px 0px #111827;
    padding: 14px;
    text-align: center;
    transition: all 0.15s ease;
    cursor: pointer;
}

.nb-sample-item:hover {
    transform: translate(-2px, -2px);
    box-shadow: 5px 5px 0px #111827;
    background-color: #F9FAFB;
}

/* Streamlit Native Buttons in Brutalist Style */
div.stButton > button {
    background-color: #10B981 !important;
    color: #FFFFFF !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 0.95rem !important;
    font-weight: 800 !important;
    border: 2.5px solid #111827 !important;
    border-radius: 10px !important;
    box-shadow: 3px 3px 0px #111827 !important;
    padding: 8px 20px !important;
    transition: all 0.12s ease !important;
    width: 100% !important;
}

div.stButton > button:hover {
    transform: translate(-2px, -2px) !important;
    box-shadow: 5px 5px 0px #111827 !important;
    background-color: #059669 !important;
}

div.stButton > button:active {
    transform: translate(1px, 1px) !important;
    box-shadow: 1px 1px 0px #111827 !important;
}

/* Sidebar Customization */
[data-testid="stSidebar"] {
    background-color: #FFFFFF !important;
    border-right: 3px solid #111827 !important;
}

/* Expander styling */
.streamlit-expanderHeader {
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 800 !important;
    border: 2px solid #111827 !important;
    border-radius: 8px !important;
    background-color: #FFFFFF !important;
    box-shadow: 2px 2px 0px #111827 !important;
}
</style>
"""
st.markdown(NEO_BRUTALISM_CSS, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# API Client Helper Functions
# -----------------------------------------------------------------------------
@st.cache_data(ttl=5)
def check_backend_health(base_url: str) -> Dict[str, Any]:
    """Polls FastAPI /health endpoint to check service status & metadata."""
    try:
        url = f"{base_url.rstrip('/')}/health"
        resp = requests.get(url, timeout=2.5)
        if resp.status_code == 200:
            return resp.json()
        return {"status": "degraded", "model_loaded": False, "error": f"HTTP {resp.status_code}"}
    except requests.exceptions.RequestException as e:
        return {"status": "offline", "model_loaded": False, "error": str(e)}


def call_predict_api(
    image_bytes: bytes, filename: str, base_url: str, top_k: int = 3
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Sends image payload to /predict and returns structured JSON response."""
    url = f"{base_url.rstrip('/')}/predict"
    try:
        files = {"file": (filename, image_bytes, "image/jpeg")}
        params = {"top_k": top_k}
        t0 = time.perf_counter()
        resp = requests.post(url, files=files, params=params, timeout=15)
        client_elapsed_ms = (time.perf_counter() - t0) * 1000

        if resp.status_code == 200:
            data = resp.json()
            data["client_roundtrip_ms"] = round(client_elapsed_ms, 2)
            return data, None
        else:
            try:
                err_detail = resp.json().get("detail", resp.text)
            except Exception:
                err_detail = resp.text
            return None, f"API Error ({resp.status_code}): {err_detail}"
    except requests.exceptions.ConnectionError:
        return None, f"Could not connect to FastAPI server at '{base_url}'. Is it running?"
    except Exception as exc:
        return None, f"Request failed: {str(exc)}"


def get_sample_image(folder_name: str) -> Optional[Tuple[str, bytes]]:
    """Retrieves the first available sample image from a given class folder."""
    target_dir = DATA_DIR / folder_name
    if not target_dir.exists():
        return None
    # Look for common image extensions
    for ext in ("*.JPG", "*.jpg", "*.PNG", "*.png", "*.jpeg"):
        imgs = list(target_dir.glob(ext))
        if imgs:
            sample_path = imgs[0]
            with open(sample_path, "rb") as f:
                return sample_path.name, f.read()
    return None


# -----------------------------------------------------------------------------
# Sidebar Navigation & Settings
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### [SETTINGS] SYSTEM SETTINGS")

    backend_url = st.text_input(
        "Backend API URL",
        value=DEFAULT_BACKEND_URL,
        help="FastAPI host exposing /health and /predict endpoints",
    )

    # Live Health Check
    health_info = check_backend_health(backend_url)
    is_online = health_info.get("status") == "healthy" and health_info.get("model_loaded")

    if is_online:
        st.markdown(
            f"""
            <div style="background-color: #ECFDF5; border: 2px solid #111827; border-radius: 8px; padding: 12px; box-shadow: 2px 2px 0px #111827; margin-bottom: 16px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 1.2rem;">[OK]</span>
                    <div>
                        <strong style="color: #065F46; font-size: 0.9rem;">BACKEND ONLINE</strong><br>
                        <span style="font-size: 0.75rem; color: #047857;">Device: <b>{health_info.get('device', 'unknown').upper()}</b> | Epoch {health_info.get('checkpoint_epoch', 'N/A')}</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div style="background-color: #FEF2F2; border: 2px solid #111827; border-radius: 8px; padding: 12px; box-shadow: 2px 2px 0px #111827; margin-bottom: 16px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 1.2rem;">[ALERT]</span>
                    <div>
                        <strong style="color: #991B1B; font-size: 0.9rem;">BACKEND OFFLINE</strong><br>
                        <span style="font-size: 0.75rem; color: #B91C1C;">Start server: <code>python src/api.py</code></span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("### [TARGET] INFERENCE CONFIG")
    top_k_val = st.slider("Top-K Predictions", min_value=1, max_value=5, value=3)

    st.markdown("---")
    st.markdown("### [METRICS] MODEL BENCHMARK")
    st.markdown(
        """
        <div style="background: #FFFFFF; border: 2px solid #111827; border-radius: 8px; padding: 12px; box-shadow: 2px 2px 0px #111827; font-size: 0.8rem;">
            <b>Architecture:</b> ResNet-50 (Transfer Learning)<br>
            <b>Test Accuracy:</b> <span style="color: #059669; font-weight: bold;">98.98%</span> (Top-1)<br>
            <b>Top-3 Accuracy:</b> <span style="color: #059669; font-weight: bold;">100.00%</span><br>
            <b>Latency (P50):</b> 6.42 ms (NVIDIA RTX 4050)<br>
            <b>Classes Covered:</b> 15 crop diseases
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.caption("AI-Based Smart Agriculture Intelligence Platform (c) 2026")


# -----------------------------------------------------------------------------
# Main Hero Section
# -----------------------------------------------------------------------------
st.markdown(
    """
    <div class="nb-hero">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;">
            <div>
                <span class="nb-pill pill-green">[AGRI] AGRI-INTELLIGENCE v1.1</span>
                <span class="nb-pill pill-white">[FAST] RESNET-50 BACKED</span>
                <h1 style="font-size: 2.4rem; margin: 8px 0 4px 0;">CROP DISEASE DIAGNOSTIC STUDIO</h1>
                <p style="font-size: 1.05rem; color: #374151; margin: 0; font-weight: 500;">
                    Instant computer-vision pathology inspection for Tomato, Potato, and Pepper crops.
                </p>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Collapsible Onboarding Guide
# -----------------------------------------------------------------------------
with st.expander("[GUIDE] HOW TO USE THIS DIAGNOSTIC TOOL (3-STEP FIELD GUIDE)", expanded=False):
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 2px solid #111827; border-radius: 10px; padding: 16px; box-shadow: 3px 3px 0px #111827; height: 100%;">
                <span class="nb-pill pill-purple">STEP 1</span>
                <h4 style="margin: 8px 0;">Capture or Select</h4>
                <p style="font-size: 0.88rem; color: #4B5563;">
                    Upload a sharp leaf photograph on a neutral background, or click any sample in the <b>Quick-Test Gallery</b> below.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 2px solid #111827; border-radius: 10px; padding: 16px; box-shadow: 3px 3px 0px #111827; height: 100%;">
                <span class="nb-pill pill-blue">STEP 2</span>
                <h4 style="margin: 8px 0;">Neural Inference</h4>
                <p style="font-size: 0.88rem; color: #4B5563;">
                    Our fine-tuned ResNet-50 processes the tensor on GPU in ~6 ms and computes the multi-class softmax probability vector.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 2px solid #111827; border-radius: 10px; padding: 16px; box-shadow: 3px 3px 0px #111827; height: 100%;">
                <span class="nb-pill pill-green">STEP 3</span>
                <h4 style="margin: 8px 0;">Actionable Plan</h4>
                <p style="font-size: 0.88rem; color: #4B5563;">
                    Review disease severity, Top-K alternatives, and expert agronomist recommendations for treatment and containment.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

# Session state initialization for selected image
if "active_image_bytes" not in st.session_state:
    st.session_state["active_image_bytes"] = None
if "active_filename" not in st.session_state:
    st.session_state["active_filename"] = None
if "selected_preset_title" not in st.session_state:
    st.session_state["selected_preset_title"] = None


# -----------------------------------------------------------------------------
# Quick-Test Sample Gallery
# -----------------------------------------------------------------------------
st.markdown("### [FAST] QUICK-TEST SAMPLE GALLERY")
st.caption("Click any leaf below to test the diagnostic engine without uploading your own photo:")

sample_cols = st.columns(len(SAMPLE_PRESETS))
for idx, preset in enumerate(SAMPLE_PRESETS):
    with sample_cols[idx]:
        st.markdown(
            f"""
            <div style="background: #FFFFFF; border: 2.5px solid #111827; border-radius: 10px; padding: 10px; box-shadow: 3px 3px 0px #111827; text-align: center; margin-bottom: 8px;">
                <div style="font-size: 1.8rem; margin-bottom: 4px;">{preset['icon']}</div>
                <strong style="font-size: 0.85rem; display: block; height: 38px; line-height: 1.2;">{preset['title']}</strong>
                <span style="font-size: 0.72rem; background: {preset['badge_color']}; color: #fff; padding: 2px 6px; border-radius: 4px; font-weight: 700; border: 1px solid #111827;">
                    {preset['badge']}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(f"Test Leaf", key=f"btn_sample_{preset['id']}"):
            sample_data = get_sample_image(preset["folder"])
            if sample_data:
                fname, bdata = sample_data
                st.session_state["active_image_bytes"] = bdata
                st.session_state["active_filename"] = f"{preset['title'].replace(' ', '_')}_{fname}"
                st.session_state["selected_preset_title"] = preset["title"]
                st.rerun()
            else:
                st.warning(f"Sample file not found in local data directory ({preset['folder']}). Please upload a photo.")

st.markdown("---")


# -----------------------------------------------------------------------------
# Main Diagnostic Interaction Area
# -----------------------------------------------------------------------------
col_input, col_results = st.columns([1, 1.3], gap="medium")

with col_input:
    st.markdown("### [PHOTO] LEAF PHOTOGRAPH")

    uploaded_file = st.file_uploader(
        "Upload a leaf image (JPEG, PNG, WebP)",
        type=["jpg", "jpeg", "png", "webp"],
        help="Upload a single crop leaf image. Close-up photos with good lighting work best.",
    )

    if uploaded_file is not None:
        st.session_state["active_image_bytes"] = uploaded_file.getvalue()
        st.session_state["active_filename"] = uploaded_file.name
        st.session_state["selected_preset_title"] = None

    # Display active image preview
    if st.session_state["active_image_bytes"]:
        try:
            pil_image = Image.open(io.BytesIO(st.session_state["active_image_bytes"])).convert("RGB")
            st.markdown(
                """
                <div style="border: 3px solid #111827; border-radius: 12px; box-shadow: 4px 4px 0px #111827; overflow: hidden; margin-top: 10px; margin-bottom: 12px;">
                """,
                unsafe_allow_html=True,
            )
            st.image(pil_image, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

            img_w, img_h = pil_image.size
            file_kb = len(st.session_state["active_image_bytes"]) / 1024

            st.markdown(
                f"""
                <div style="background: #F3F4F6; border: 2px solid #111827; border-radius: 8px; padding: 10px 14px; font-size: 0.8rem; box-shadow: 2px 2px 0px #111827;">
                    <b>File:</b> <code>{st.session_state['active_filename']}</code><br>
                    <b>Dimensions:</b> {img_w} x {img_h} px | <b>Size:</b> {file_kb:.1f} KB
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Clear button
            if st.button("[CLEAR] Clear Active Image", key="clear_img"):
                st.session_state["active_image_bytes"] = None
                st.session_state["active_filename"] = None
                st.session_state["selected_preset_title"] = None
                st.rerun()

        except Exception as exc:
            st.error(f"Failed to render image: {exc}")
    else:
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 2.5px dashed #9CA3AF; border-radius: 12px; padding: 48px 24px; text-align: center; margin-top: 12px;">
                <div style="font-size: 3rem; margin-bottom: 12px;">[LEAF]</div>
                <h4 style="color: #6B7280; margin-bottom: 6px;">No Leaf Image Selected</h4>
                <p style="font-size: 0.85rem; color: #9CA3AF; margin: 0;">
                    Drag & drop a photo above or click any sample card from the Quick-Test gallery.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )


with col_results:
    st.markdown("### [DIAGNOSIS] DIAGNOSTIC RESULTS")

    if not is_online:
        st.markdown(
            """
            <div class="nb-card" style="border-color: #EF4444; background: #FEF2F2;">
                <span class="nb-pill pill-red">[WARN] BACKEND OFFLINE</span>
                <h3 style="color: #991B1B; margin: 8px 0;">Cannot Connect to Inference Engine</h3>
                <p style="font-size: 0.9rem; color: #7F1D1D;">
                    The FastAPI backend is not responding at the configured URL. Please start the API service in your terminal:
                </p>
                <div style="background: #111827; color: #34D399; padding: 10px 14px; border-radius: 6px; font-family: monospace; font-size: 0.85rem; margin-top: 8px;">
                    python src/api.py
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    elif not st.session_state["active_image_bytes"]:
        st.markdown(
            """
            <div class="nb-card" style="text-align: center; padding: 48px 24px;">
                <div style="font-size: 2.5rem; margin-bottom: 8px;">[WAIT]</div>
                <h3 style="color: #4B5563; margin-bottom: 6px;">Waiting for Input</h3>
                <p style="font-size: 0.9rem; color: #6B7280;">
                    Select an image from the left panel to trigger real-time neural classification.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        # Run inference against the API
        with st.spinner("Classifying leaf pathology via ResNet-50..."):
            pred_response, error_msg = call_predict_api(
                image_bytes=st.session_state["active_image_bytes"],
                filename=st.session_state["active_filename"] or "sample.jpg",
                base_url=backend_url,
                top_k=top_k_val,
            )

        if error_msg:
            st.error(error_msg)
        elif pred_response:
            primary = pred_response["primary_prediction"]
            top_k_list = pred_response["top_k_predictions"]
            inf_time = pred_response.get("inference_time_ms", 0.0)
            device_str = pred_response.get("inference_device", "CPU")
            raw_class_name = primary["class_name"]

            # Lookup knowledge base metadata
            kb_entry = DISEASE_KNOWLEDGE_BASE.get(
                raw_class_name,
                {
                    "display_name": raw_class_name.replace("_", " "),
                    "scientific_name": "Pathogen unlisted",
                    "crop": "Crop",
                    "severity": "Unknown",
                    "status_tag": "DIAGNOSED",
                    "theme_color": "#3B82F6",
                    "overview": "Diagnosis complete.",
                    "treatments": ["Consult local agricultural extension service for specialized protocols."],
                },
            )

            # Telemetry Strip
            st.markdown(
                f"""
                <div class="nb-telemetry-box">
                    <div>
                        <span class="nb-pill pill-white">[FAST] LATENCY: <b>{inf_time:.2f} ms</b></span>
                        <span class="nb-pill pill-purple">[DEVICE] HARDWARE: <b>{device_str.upper()}</b></span>
                    </div>
                    <div>
                        <span class="nb-pill pill-green">ACCURACY: <b>98.98%</b></span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Primary Diagnosis Card
            card_border_color = kb_entry["theme_color"]
            pill_class = "pill-green" if kb_entry["severity"] == "None" else ("pill-amber" if kb_entry["severity"] == "Moderate" else "pill-red")

            st.markdown(
                f"""
                <div class="nb-card" style="border-color: {card_border_color}; border-width: 3.5px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span class="nb-pill {pill_class}">{kb_entry['status_tag']}</span>
                        <span style="font-family: 'Space Grotesk', sans-serif; font-size: 1.25rem; font-weight: 800; color: {card_border_color};">
                            {primary['confidence_pct']}
                        </span>
                    </div>
                    <h2 style="font-size: 1.6rem; margin: 4px 0 2px 0;">{kb_entry['display_name']}</h2>
                    <p style="font-size: 0.85rem; font-style: italic; color: #4B5563; margin-bottom: 12px;">
                        Pathogen: {kb_entry['scientific_name']}
                    </p>

                    <p style="font-size: 0.9rem; color: #374151; margin-top: 14px; margin-bottom: 4px; line-height: 1.4;">
                        <b>Diagnostic Overview:</b> {kb_entry['overview']}
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Native Streamlit confidence progress bar
            conf_val = min(1.0, primary['confidence'])
            conf_color = kb_entry['theme_color']
            st.markdown(
                f'<p style="font-size:0.78rem;font-weight:700;color:#374151;margin:4px 0 2px 0;">'
                f'CONFIDENCE &nbsp;<span style="color:{conf_color};font-size:0.9rem;">{primary["confidence_pct"]}</span></p>',
                unsafe_allow_html=True
            )
            st.progress(conf_val)

            # Agronomic Action Card
            st.markdown(
                f"""
                <div class="nb-card" style="background-color: #FAFAFA; border-color: #111827;">
                    <h4 style="margin-top: 0; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
                        <span>[TREATMENT]</span> Recommended Agronomic Interventions
                    </h4>
                    <ul style="margin: 0; padding-left: 20px; font-size: 0.88rem; color: #1F2937; line-height: 1.6;">
                        {''.join(f'<li style="margin-bottom: 6px;">{t}</li>' for t in kb_entry['treatments'])}
                    </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Top-K Comparison Card
            st.markdown(
                """
                <div class="nb-card">
                    <h4 style="margin-top: 0; margin-bottom: 14px;">[METRICS] Top Alternative Class Distributions</h4>
                """,
                unsafe_allow_html=True,
            )

            for alt in top_k_list:
                alt_name = alt["class_name"]
                alt_conf = min(1.0, alt["confidence"])
                alt_pct = alt["confidence_pct"]
                alt_display = DISEASE_KNOWLEDGE_BASE.get(alt_name, {}).get("display_name", alt_name.replace("_", " "))
                rank_color = "#10B981" if alt["rank"] == 1 else ("#3B82F6" if alt["rank"] == 2 else "#6B7280")
                rank_badge = "#10B981" if alt["rank"] == 1 else ("#3B82F6" if alt["rank"] == 2 else "#9CA3AF")
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:2px;margin-top:8px;">'
                    f'<span style="font-size:0.83rem;font-weight:700;color:#111827;">'
                    f'<span style="background:{rank_badge};color:#fff;padding:1px 7px;border-radius:4px;font-size:0.72rem;margin-right:6px;border:1px solid #111827;">#{alt["rank"]}</span>'
                    f'{alt_display}</span>'
                    f'<span style="font-size:0.82rem;font-weight:800;color:{rank_color};">{alt_pct}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                st.progress(alt_conf)

            st.markdown("</div>", unsafe_allow_html=True)

            # Raw Developer JSON Inspection
            with st.expander("[DEV] Raw JSON Response (Developer Telemetry)"):
                st.json(pred_response)

# -----------------------------------------------------------------------------
# Footer
# -----------------------------------------------------------------------------
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #6B7280; font-size: 0.82rem; padding: 12px 0;">
        <b>Smart Agriculture Crop Disease Intelligence Platform</b> | Powered by PyTorch, ResNet-50 & FastAPI<br>
        Trained on the PlantVillage Benchmark Dataset | 98.98% Test Accuracy across 2,063 Untouched Samples
    </div>
    """,
    unsafe_allow_html=True,
)

