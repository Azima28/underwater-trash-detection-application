import streamlit as st
import json
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- Page Config ---
st.set_page_config(
    page_title="EcoCitizen | Environmental Impact",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Sidebar Navigation ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1598/1598191.png", width=80)
    st.markdown("### Navigasi")
    st.markdown("""
        <a href="http://localhost:5000" target="_parent" style="text-decoration: none;">
            <div style="background-color: #2D5A27; color: white; padding: 10px 20px; border-radius: 8px; text-align: center; font-weight: 600; margin-bottom: 20px;">
                🏠 Kembali ke Beranda
            </div>
        </a>
    """, unsafe_allow_html=True)
    st.divider()
    st.info("Anda sedang melihat Dashboard Analitis EcoCitizen.")

# --- Premium Design System ---
# Using a refined "Eco-Tech" palette: Deep Slate, Sage Green, and Soft Silver
COLOR_PRIMARY = "#2D5A27"  # Deep Forest Green
COLOR_SECONDARY = "#E8F5E9"  # Very Light Sage
COLOR_ACCENT = "#4CAF50" # Vibrant but professional Green
COLOR_TEXT = "#2C3E50" # Deep Slate
COLOR_BG = "#FFFFFF"

st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {{
        font-family: 'Inter', sans-serif;
        color: {COLOR_TEXT};
    }}
    
    .main {{
        background-color: #F8FAFB;
    }}
    
    /* Premium Card Metric */
    div[data-testid="stMetric"] {{
        background-color: {COLOR_BG};
        padding: 24px;
        border-radius: 12px;
        border: 1px solid #E1E8ED;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }}
    
    div[data-testid="stMetric"] label {{
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-size: 0.8rem;
    }}
    
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {{
        font-weight: 700;
        color: {COLOR_PRIMARY};
    }}

    /* Title Styling */
    .app-header {{
        padding: 2rem 0;
        border-bottom: 2px solid #E1E8ED;
        margin-bottom: 2rem;
    }}
    
    .app-title {{
        font-size: 2.5rem;
        font-weight: 700;
        color: {COLOR_PRIMARY};
        margin-bottom: 0.5rem;
    }}
    
    .app-subtitle {{
        color: #64748B;
        font-size: 1.1rem;
    }}
    
    /* Section Headers */
    .section-header {{
        font-size: 1.5rem;
        font-weight: 600;
        color: {COLOR_TEXT};
        margin-top: 2rem;
        margin-bottom: 1.5rem;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- Data Loading ---
STATS_PATH = "data/global_stats.json"

@st.cache_data(ttl=60)
def load_stats():
    if os.path.exists(STATS_PATH):
        try:
            with open(STATS_PATH, 'r') as f:
                return json.load(f)
        except Exception:
            return None
    return None

data = load_stats()

if not data:
    st.info("Menunggu data statistik pertama dari aplikasi...")
    st.stop()

# --- Header Section ---
st.markdown("""
<div class="app-header">
    <div class="app-title">EcoCitizen Data Analytics</div>
    <div class="app-subtitle">Laporan dampat lingkungan dan kontribusi komunitas secara real-time.</div>
</div>
""", unsafe_allow_html=True)

# --- Summary Metrics ---
m_col1, m_col2, m_col3 = st.columns(3)

with m_col1:
    st.metric("Total Sampah Teridentifikasi", f"{data['total_detections']:,}")
with m_col2:
    st.metric("Volume Media Terproses", f"{data['total_media']:,}")
with m_col3:
    avg = round(data['total_detections'] / data['total_media'], 1) if data['total_media'] > 0 else 0
    st.metric("Rasio Deteksi per Media", f"{avg}")

# --- Analytics Section ---
st.markdown('<div class="section-header">Analisis Kontribusi</div>', unsafe_allow_html=True)

leaderboard = data.get("leaderboard", {})
if leaderboard:
    df = pd.DataFrame(list(leaderboard.items()), columns=['User', 'Total']).sort_values('Total', ascending=False)
    
    v_col1, v_col2 = st.columns([3, 2])
    
    with v_col1:
        # Refined Bar Chart
        fig_bar = px.bar(
            df, x='User', y='Total',
            color='Total',
            color_continuous_scale=[[0, '#A5D6A7'], [1, '#2E7D32']],
            labels={'Total': 'Jumlah Deteksi', 'User': 'Kontributor'}
        )
        fig_bar.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(t=20, b=20, l=0, r=0),
            coloraxis_showscale=False
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        
    with v_col2:
        # Clean Donut Chart
        fig_pie = go.Figure(data=[go.Pie(
            labels=df['User'], 
            values=df['Total'], 
            hole=.5,
            marker=dict(colors=['#2E7D32', '#43A047', '#66BB6A', '#81C784', '#A5D6A7'])
        )])
        fig_pie.update_layout(
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
            margin=dict(t=20, b=20, l=0, r=0),
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_pie, use_container_width=True)
else:
    st.write("Belum ada data kontribusi yang tercatat.")

# --- Category Breakdown Section ---
st.markdown('<div class="section-header">Komposisi Dampak Lingkungan</div>', unsafe_allow_html=True)

cat_stats = data.get("category_stats", {})
if cat_stats:
    # Prepare data for visualization
    cat_df = pd.DataFrame(list(cat_stats.items()), columns=['Kategori', 'Jumlah'])
    cat_df['Kategori'] = cat_df['Kategori'].str.upper()
    
    c_col1, c_col2 = st.columns([2, 3])
    
    with c_col1:
        st.markdown("""
        <div style="background-color: white; padding: 20px; border-radius: 12px; border: 1px solid #E1E8ED;">
            <h4 style="margin-top:0; color:#2D5A27;">Klasifikasi Objek</h4>
            <ul style="color: #64748B; padding-left: 20px;">
                <li><b>TRASH:</b> Sampah anorganik (plastik, logam, dll)</li>
                <li><b>BIO:</b> Limbah organik atau bangkai hewan</li>
                <li><b>ROV:</b> Deteksi unit pembersih di lapangan</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
    with c_col2:
        # Funnel or Horizontal Bar for Categories
        fig_cat = px.bar(
            cat_df, 
            y='Kategori', 
            x='Jumlah',
            orientation='h',
            text='Jumlah',
            color='Kategori',
            color_discrete_map={
                'TRASH': '#2E7D32',
                'BIO': '#81C784',
                'ROV': '#A5D6A7'
            }
        )
        fig_cat.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis_title="Total Deteksi",
            yaxis_title=None,
            showlegend=False,
            margin=dict(t=0, b=0, l=0, r=0)
        )
        st.plotly_chart(fig_cat, use_container_width=True)
else:
    st.write("Data kategori belum tersedia.")

# --- Technical Maturity Section ---
st.markdown('<div class="section-header">Klasifikasi Tingkat Pencemaran</div>', unsafe_allow_html=True)

t_col1, t_col2 = st.columns([1, 2])

with t_col1:
    st.markdown("""
    Sistem menggunakan *Severity Matrix* untuk mengkategorikan urgensi pembersihan:
    
    - **Normal:** < 50 deteksi
    - **Moderate:** 50 - 100 deteksi
    - **Elevated:** 100 - 300 deteksi
    - **Critical:** > 300 deteksi
    """)

with t_col2:
    # Minimalist Simulation
    st.write("Simulator Tingkat Urgensi")
    val = st.slider("Nilai Deteksi", 0, 500, 100, label_visibility="collapsed")
    
    if val < 50:
        st.info(f"Status: NORMAL ({val})")
    elif val < 100:
        st.warning(f"Status: MODERATE ({val})")
    else:
        status_color = "#E53935" if val >= 300 else "#FB8C00"
        st.markdown(f"""
            <div style="background-color:{status_color}; color:white; padding:15px; border-radius:8px; text-align:center; font-weight:600;">
                TINDAKAN DIPERLUKAN: {'CRITICAL' if val >= 300 else 'ELEVATED'} ({val})
            </div>
        """, unsafe_allow_html=True)

# --- Footer ---
st.markdown("""
<div style="margin-top: 5rem; padding: 2rem 0; border-top: 1px solid #E1E8ED; text-align: center; color: #94A3B8; font-size: 0.9rem;">
    EcoCitizen Platform &bull; Professional Data Visualization Layer &bull; v1.1
</div>
""", unsafe_allow_html=True)
