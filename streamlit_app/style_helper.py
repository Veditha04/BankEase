# streamlit_app/style_helper.py
import streamlit as st, base64

def _b64(svg: str) -> str:
    return base64.b64encode(svg.encode("utf-8")).decode("ascii")

def inject_noise_gradient():
    noise_svg = """
    <svg xmlns='http://www.w3.org/2000/svg' width='220' height='220' viewBox='0 0 220 220'>
      <filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='2' stitchTiles='stitch'/>
        <feColorMatrix type='saturate' values='0'/>
        <feComponentTransfer><feFuncA type='table'
          tableValues='0 0 0 0 0 .018 .04 .055 .07 .08 .09 .1'/></feComponentTransfer>
      </filter><rect width='100%' height='100%' filter='url(#n)'/></svg>""".strip()
    noise_b64 = _b64(noise_svg)

    st.markdown(f"""
    <style>
      .stApp {{
        background:
          linear-gradient(180deg, #14181C 0%, #0E1013 60%, #0A0C0F 100%),
          url("data:image/svg+xml;base64,{noise_b64}");
        background-size: cover, 220px 220px;
        background-attachment: fixed;
      }}
      [data-testid="stSidebar"] > div:first-child {{
        background: linear-gradient(180deg, rgba(26,30,36,.95), rgba(22,26,32,.95));
        border-right: 1px solid rgba(255,255,255,0.06);
      }}
      section.main > div:has(> div[data-testid="stForm"]) {{
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 16px;
        padding: 18px 18px 8px 18px;
        backdrop-filter: saturate(130%) blur(2px);
      }}
      .stButton > button {{
        background: #2B7FFF; color: #fff; border-radius: 10px; border: 1px solid rgba(255,255,255,.12);
      }}
      .stButton > button:hover {{ background:#1D6BE6; }}
      .stProgress > div > div {{ background: linear-gradient(90deg, #2B7FFF, #7AA9FF); }}
    </style>
    """, unsafe_allow_html=True)
def inject_diagonal_hatch():
    pattern_svg = """
    <svg xmlns='http://www.w3.org/2000/svg' width='32' height='32' viewBox='0 0 32 32'>
      <defs><pattern id='p' width='32' height='32' patternUnits='userSpaceOnUse' patternTransform='rotate(35)'>
        <line x1='0' y1='0' x2='0' y2='32' stroke='rgba(255,255,255,0.04)' stroke-width='8'/>
      </pattern></defs>
      <rect width='100%' height='100%' fill='url(#p)'/>
    </svg>""".strip()
    p_b64 = base64.b64encode(pattern_svg.encode()).decode()
    st.markdown(f"""
    <style>
      .stApp {{
        background:
          radial-gradient(1200px 600px at 20% -10%, #1a2230 0%, transparent 60%),
          radial-gradient(1000px 500px at 120% 10%, #141a24 0%, transparent 60%),
          #0E1013 url("data:image/svg+xml;base64,{p_b64}");
        background-size: cover, cover, 32px 32px;
      }}
    </style>
    """, unsafe_allow_html=True)
def inject_subtle_grid():
    grid_svg = """
    <svg xmlns='http://www.w3.org/2000/svg' width='40' height='40' viewBox='0 0 40 40'>
      <path d='M40 0H0v40' fill='none' stroke='rgba(255,255,255,0.05)'/>
    </svg>""".strip()
    g_b64 = base64.b64encode(grid_svg.encode()).decode()
    st.markdown(f"""
    <style>
      .stApp {{
        background:
          linear-gradient(180deg, #12161b 0%, #0f1216 100%),
          url("data:image/svg+xml;base64,{g_b64}");
        background-size: cover, 40px 40px;
        background-attachment: fixed;
      }}
    </style>
    """, unsafe_allow_html=True)
