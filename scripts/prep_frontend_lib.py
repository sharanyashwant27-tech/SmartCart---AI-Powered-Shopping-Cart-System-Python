from pathlib import Path

p = Path("frontend/lib.py")
text = p.read_text(encoding="utf-8")
old = '''st.set_page_config(
    page_title="SmartCart",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

'''
new = '''def bootstrap_session() -> None:
    """Initialize session keys used across pages."""

'''
if old not in text:
    raise SystemExit("set_page_config block not found")
text = text.replace(old, new, 1)
if 'if __name__' in text:
    text = text.split('if __name__')[0]
p.write_text(text, encoding="utf-8")
print("ok", len(text))
