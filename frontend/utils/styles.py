"""Shared Streamlit UI styles and helpers — vibrant SmartCart theme."""

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=Sora:wght@600;700;800&display=swap');

:root {
  --sc-ink: #0b1f2a;
  --sc-muted: #4a6570;
  --sc-teal: #00bfa5;
  --sc-teal-deep: #009688;
  --sc-coral: #ff5c5c;
  --sc-amber: #ffb020;
  --sc-sky: #2f80ed;
  --sc-lime: #7cde5a;
  --sc-card: rgba(255, 255, 255, 0.92);
  --sc-line: rgba(11, 31, 42, 0.08);
}

html, body, [class*="css"], .stApp, .stMarkdown, p, label, span, div {
  font-family: 'Outfit', system-ui, sans-serif !important;
  color: var(--sc-ink);
}

.stApp {
  background:
    radial-gradient(920px 520px at 0% -5%, rgba(0, 191, 165, 0.35) 0%, transparent 55%),
    radial-gradient(780px 480px at 100% 0%, rgba(47, 128, 237, 0.28) 0%, transparent 52%),
    radial-gradient(700px 420px at 80% 100%, rgba(255, 92, 92, 0.18) 0%, transparent 50%),
    radial-gradient(600px 380px at 10% 90%, rgba(255, 176, 32, 0.2) 0%, transparent 45%),
    linear-gradient(165deg, #e8f9f6 0%, #eaf3ff 42%, #fff6ee 100%) !important;
}

h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
  font-family: 'Sora', 'Outfit', sans-serif !important;
  letter-spacing: -0.03em !important;
  color: var(--sc-ink) !important;
  font-weight: 700 !important;
}

/* ——— Hero ——— */
.sc-hero {
  padding: 1.25rem 1.35rem 1.1rem;
  margin-bottom: 1.15rem;
  border-radius: 18px;
  background:
    linear-gradient(125deg, rgba(0, 191, 165, 0.95) 0%, rgba(47, 128, 237, 0.9) 55%, rgba(255, 92, 92, 0.85) 100%);
  box-shadow: 0 12px 32px rgba(0, 150, 136, 0.22);
  position: relative;
  overflow: hidden;
  animation: scFadeUp 0.55s ease both;
}

.sc-hero::after {
  content: "";
  position: absolute;
  right: -40px;
  top: -40px;
  width: 180px;
  height: 180px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.12);
}

.sc-brand {
  font-family: 'Sora', sans-serif;
  font-size: 2.55rem;
  font-weight: 800;
  color: #ffffff;
  margin: 0;
  line-height: 1.05;
  letter-spacing: -0.04em;
  text-shadow: 0 2px 0 rgba(0, 0, 0, 0.06);
}

.sc-tagline {
  color: rgba(255, 255, 255, 0.92);
  font-size: 1.05rem;
  margin: 0.4rem 0 0;
  font-weight: 500;
}

.sc-brand-dark {
  font-family: 'Sora', sans-serif;
  font-size: 2rem;
  font-weight: 800;
  color: var(--sc-teal-deep);
  margin: 0;
  line-height: 1.1;
}

/* ——— Cards & commerce bits ——— */
.sc-product-card {
  background: var(--sc-card);
  border: 1px solid var(--sc-line);
  border-radius: 16px;
  padding: 0.95rem;
  height: 100%;
  margin-bottom: 0.75rem;
  transition: transform 0.22s ease, box-shadow 0.22s ease, border-color 0.22s ease;
  animation: scFadeUp 0.45s ease both;
}

.sc-product-card:hover {
  transform: translateY(-4px);
  border-color: rgba(0, 191, 165, 0.45);
  box-shadow: 0 14px 30px rgba(0, 150, 136, 0.14);
}

.sc-price {
  font-family: 'Sora', sans-serif;
  font-weight: 700;
  color: var(--sc-coral);
  font-size: 1.25rem;
  letter-spacing: -0.02em;
}

.sc-muted {
  color: var(--sc-muted);
  font-size: 0.9rem;
}

.sc-badge {
  display: inline-block;
  background: linear-gradient(90deg, var(--sc-amber), #ff8a3d);
  color: #1a1200;
  font-size: 0.72rem;
  font-weight: 700;
  padding: 0.2rem 0.55rem;
  border-radius: 6px;
  margin-bottom: 0.4rem;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}

.sc-section-title {
  display: inline-block;
  font-family: 'Sora', sans-serif;
  font-weight: 700;
  font-size: 1.05rem;
  padding: 0.35rem 0.85rem;
  border-radius: 8px;
  margin-bottom: 0.65rem;
  background: linear-gradient(90deg, rgba(0, 191, 165, 0.18), rgba(47, 128, 237, 0.14));
  color: var(--sc-teal-deep);
}

.sc-kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.85rem;
  margin: 0.5rem 0 1.1rem;
}

.sc-kpi {
  background: var(--sc-card);
  border-radius: 14px;
  padding: 1rem 1.05rem;
  border: 1px solid var(--sc-line);
  border-top: 4px solid var(--sc-teal);
  box-shadow: 0 6px 18px rgba(11, 31, 42, 0.05);
  animation: scFadeUp 0.5s ease both;
}

.sc-kpi.coral { border-top-color: var(--sc-coral); }
.sc-kpi.sky { border-top-color: var(--sc-sky); }
.sc-kpi.amber { border-top-color: var(--sc-amber); }
.sc-kpi.lime { border-top-color: var(--sc-lime); }

.sc-kpi .label {
  font-size: 0.78rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--sc-muted);
  margin: 0;
}

.sc-kpi .value {
  font-family: 'Sora', sans-serif;
  font-size: 1.55rem;
  font-weight: 800;
  margin: 0.25rem 0 0;
  letter-spacing: -0.03em;
  color: var(--sc-ink);
}

.sc-panel {
  background: var(--sc-card);
  border: 1px solid var(--sc-line);
  border-radius: 16px;
  padding: 1rem 1.1rem;
  margin-bottom: 1rem;
  box-shadow: 0 8px 22px rgba(11, 31, 42, 0.04);
}

.sc-sidebar-brand {
  font-family: 'Sora', sans-serif;
  font-size: 1.55rem;
  font-weight: 800;
  background: linear-gradient(90deg, #5ff5df, #7eb6ff, #ff9a9a);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0.2rem 0 0.15rem;
  letter-spacing: -0.03em;
  cursor: pointer;
  text-decoration: none;
}

.sc-sidebar-brand:hover {
  filter: brightness(1.12);
}

.sc-sidebar-sub {
  color: rgba(232, 248, 245, 0.75) !important;
  font-size: 0.85rem;
  margin-bottom: 0.85rem;
}

/* ——— Sidebar ——— */
div[data-testid="stSidebar"] {
  background:
    radial-gradient(400px 280px at 0% 0%, rgba(0, 191, 165, 0.35) 0%, transparent 60%),
    radial-gradient(360px 240px at 100% 30%, rgba(47, 128, 237, 0.3) 0%, transparent 55%),
    linear-gradient(180deg, #062a32 0%, #0a3d48 40%, #0d4a3f 100%) !important;
  border-right: 1px solid rgba(95, 245, 223, 0.12);
}

div[data-testid="stSidebar"] * {
  color: #e8f8f5 !important;
}

div[data-testid="stSidebar"] .stRadio label {
  background: rgba(255, 255, 255, 0.04);
  border-radius: 10px;
  padding: 0.35rem 0.55rem !important;
  margin-bottom: 0.2rem;
  border: 1px solid transparent;
  transition: background 0.15s ease, border-color 0.15s ease;
}

div[data-testid="stSidebar"] .stRadio label:hover {
  background: rgba(0, 191, 165, 0.18);
  border-color: rgba(95, 245, 223, 0.25);
}

div[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
  color: #e8f8f5 !important;
}

/* ——— Buttons ——— */
.stButton > button {
  border-radius: 10px !important;
  font-weight: 600 !important;
  border: none !important;
  transition: transform 0.15s ease, box-shadow 0.15s ease, filter 0.15s ease !important;
}

.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {
  background: linear-gradient(135deg, #00bfa5 0%, #2f80ed 100%) !important;
  color: white !important;
  box-shadow: 0 6px 16px rgba(0, 191, 165, 0.28) !important;
}

.stButton > button[kind="secondary"],
.stButton > button[data-testid="baseButton-secondary"],
.stButton > button {
  background: linear-gradient(135deg, rgba(0, 191, 165, 0.14), rgba(47, 128, 237, 0.12)) !important;
  color: var(--sc-ink) !important;
  border: 1px solid rgba(0, 191, 165, 0.35) !important;
}

.stButton > button:hover {
  transform: translateY(-1px);
  filter: brightness(1.05);
}

/* ——— Inputs ——— */
.stTextInput input, .stNumberInput input, .stSelectbox [data-baseweb="select"] > div,
.stTextArea textarea {
  border-radius: 10px !important;
  border: 1.5px solid rgba(0, 191, 165, 0.28) !important;
  background: rgba(255, 255, 255, 0.9) !important;
}

.stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {
  border-color: var(--sc-teal) !important;
  box-shadow: 0 0 0 3px rgba(0, 191, 165, 0.18) !important;
}

/* ——— Metrics ——— */
div[data-testid="stMetric"] {
  background: var(--sc-card);
  border: 1px solid var(--sc-line);
  border-radius: 14px;
  padding: 0.85rem 1rem;
  border-left: 5px solid var(--sc-teal);
  box-shadow: 0 6px 16px rgba(11, 31, 42, 0.05);
}

div[data-testid="stMetric"]:nth-child(4n+2) { border-left-color: var(--sc-coral); }
div[data-testid="stMetric"]:nth-child(4n+3) { border-left-color: var(--sc-sky); }
div[data-testid="stMetric"]:nth-child(4n+4) { border-left-color: var(--sc-amber); }

div[data-testid="stMetric"] label {
  color: var(--sc-muted) !important;
  font-weight: 600 !important;
  text-transform: uppercase;
  font-size: 0.72rem !important;
  letter-spacing: 0.04em;
}

div[data-testid="stMetric"] [data-testid="stMetricValue"] {
  font-family: 'Sora', sans-serif !important;
  font-weight: 800 !important;
  color: var(--sc-ink) !important;
}

/* ——— Tables / dataframes ——— */
div[data-testid="stDataFrame"], .stTable {
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--sc-line);
  background: white;
}

/* ——— Alerts ——— */
div[data-testid="stAlert"] {
  border-radius: 12px !important;
}

/* ——— Tabs & headers ——— */
.stTabs [data-baseweb="tab-list"] {
  gap: 0.35rem;
}

.stTabs [data-baseweb="tab"] {
  border-radius: 10px 10px 0 0;
  background: rgba(0, 191, 165, 0.08);
  font-weight: 600;
}

.stTabs [aria-selected="true"] {
  background: linear-gradient(135deg, rgba(0, 191, 165, 0.25), rgba(47, 128, 237, 0.2)) !important;
}

hr {
  border: none !important;
  height: 2px !important;
  background: linear-gradient(90deg, transparent, rgba(0, 191, 165, 0.45), rgba(255, 92, 92, 0.35), transparent) !important;
  margin: 1.25rem 0 !important;
}

@keyframes scFadeUp {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 900px) {
  .sc-kpi-row { grid-template-columns: repeat(2, 1fr); }
  .sc-brand { font-size: 2rem; }
}
</style>
"""


def money(value) -> str:  # noqa: ANN001
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value)


def kpi_html(label: str, value: str, tone: str = "") -> str:
    """Colored KPI tile for admin / analytics pages."""
    cls = f"sc-kpi {tone}".strip()
    return (
        f'<div class="{cls}">'
        f'<p class="label">{label}</p>'
        f'<p class="value">{value}</p>'
        f"</div>"
    )
