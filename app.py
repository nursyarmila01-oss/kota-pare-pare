import streamlit as st
import pandas as pd
import plotly.express as px

# =========================
# KONFIGURASI DASHBOARD
# =========================
st.set_page_config(
    page_title="Dashboard Fiskal Kota Parepare",
    page_icon="📊",
    layout="wide",
)

DATA_URL = (
    "https://raw.githubusercontent.com/nursyarmila01-oss/"
    "kota-pare-pare/2d470f00ca57edaf587cfe69223573b27f56b1f5/"
    "dataset_fiskal_97_hipoFull.csv"
)

# =========================
# TAMPILAN
# =========================
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(180deg, #f2f8fc 0%, #ffffff 50%);
    }
    [data-testid="stSidebar"] {
        background-color: #e7f1f7;
    }
    .hero {
        padding: 1.5rem 1.8rem;
        border-radius: 18px;
        background: linear-gradient(120deg, #073b5c, #087e8b);
        color: white;
        margin-bottom: 1.2rem;
    }
    .hero h1 {
        color: white;
        margin: 0;
        font-size: 2.1rem;
    }
    .hero p {
        color: #e1f5f7;
        margin: .45rem 0 0 0;
    }
    div[data-testid="stMetric"] {
        background: white;
        padding: 15px;
        border-radius: 14px;
        border: 1px solid #dce8ef;
        box-shadow: 0 2px 8px #1232;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
        <h1>📊 Dashboard Fiskal Kota Parepare</h1>
        <p>
            Eksplorasi indikator fiskal dan sosial-ekonomi
            melalui visualisasi data interaktif.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# =========================
# MEMUAT DATA
# =========================
@st.cache_data(ttl=3600)
def load_data():
    data = pd.read_csv(DATA_URL)
    data.columns = data.columns.astype(str).str.strip()

    if "Kota" not in data.columns:
        raise ValueError("Kolom 'Kota' tidak ditemukan pada dataset.")

    data["Kota"] = data["Kota"].astype(str).str.strip()

    if "Tahun" in data.columns:
        data["Tahun"] = pd.to_numeric(data["Tahun"], errors="coerce")

    # Konversi kolom selain nama kota menjadi numerik jika memungkinkan.
    for column in data.columns:
        if column not in ["Kota", "Tahun"]:
            data[column] = pd.to_numeric(data[column], errors="coerce")

    return data


with st.sidebar:
    st.header("⚙️ Pengaturan")
    st.write("Atur kota dan tahun yang ingin dianalisis.")

    if st.button("🔄 Muat ulang data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

try:
    all_data = load_data()
except Exception as error:
    st.error(
        "Dataset tidak berhasil dimuat. Periksa koneksi internet "
        "dan pastikan file CSV di GitHub dapat diakses."
    )
    st.exception(error)
    st.stop()

# =========================
# FILTER KOTA DAN TAHUN
# =========================
cities = sorted(all_data["Kota"].dropna().unique().tolist())

if not cities:
    st.error("Dataset tidak memiliki nama kota yang dapat ditampilkan.")
    st.stop()

parepare_options = [
    city for city in cities
    if "pare" in city.lower().replace("-", "").replace(" ", "")
]
default_city = parepare_options[0] if parepare_options else cities[0]

with st.sidebar:
    selected_city = st.selectbox(
        "Pilih kota",
        options=cities,
        index=cities.index(default_city),
    )

city_data = all_data[all_data["Kota"] == selected_city].copy()

if "Tahun" in city_data.columns and city_data["Tahun"].notna().any():
    available_years = sorted(
        city_data["Tahun"].dropna().astype(int).unique().tolist()
    )

    with st.sidebar:
        if len(available_years) > 1:
            year_range = st.slider(
                "Rentang tahun",
                min_value=min(available_years),
                max_value=max(available_years),
                value=(min(available_years), max(available_years)),
            )
        else:
            year_range = (available_years[0], available_years[0])
            st.write(f"Tahun tersedia: {available_years[0]}")

    data = city_data[
        city_data["Tahun"].between(year_range[0], year_range[1])
    ].sort_values("Tahun")
else:
    data = city_data.copy()

if data.empty:
    st.warning("Tidak ada data untuk pilihan kota dan tahun tersebut.")
    st.stop()

numeric_columns = [
    column
    for column in data.select_dtypes(include="number").columns
    if column != "Tahun"
]

# =========================
# KARTU RINGKASAN
# =========================
st.subheader(f"Ringkasan Data — {selected_city}")

col1, col2, col3, col4 = st.columns(4)

year_count = (
    data["Tahun"].nunique()
    if "Tahun" in data.columns
    else len(data)
)
col1.metric("Jumlah tahun", f"{year_count:,}")

def metric_average(column_name):
    if column_name in data.columns and data[column_name].notna().any():
        return f"{data[column_name].mean():,.2f}"
    return "Tidak tersedia"

col2.metric("Rata-rata PAD", metric_average("PAD"))
col3.metric("Rata-rata IPM", metric_average("IPM"))
col4.metric("Rata-rata kemiskinan", metric_average("KEMISKINAN"))

st.caption(
    "Angka mengikuti skala dalam dataset sumber. Periksa dokumentasi dataset "
    "sebelum menafsirkan satuan sebagai rupiah, persen, atau indeks."
)

# =========================
# TAB DASHBOARD
# =========================
tab_trend, tab_compare, tab_table = st.tabs(
    ["📈 Tren Indikator", "📊 Perbandingan", "📋 Tabel Data"]
)

with tab_trend:
    st.subheader("Perkembangan indikator dari tahun ke tahun")

    preferred_columns = [
        name for name in [
            "PAD", "DAU_Grant", "DAK_Fisik",
            "IPM", "KEMISKINAN", "PENGANGGURAN"
        ]
        if name in numeric_columns
    ]

    selected_metrics = st.multiselect(
        "Pilih indikator untuk ditampilkan",
        options=numeric_columns,
        default=preferred_columns[:3],
    )

    if selected_metrics and "Tahun" in data.columns:
        chart_data = data[["Tahun"] + selected_metrics].melt(
            id_vars="Tahun",
            var_name="Indikator",
            value_name="Nilai",
        )

        figure = px.line(
            chart_data,
            x="Tahun",
            y="Nilai",
            color="Indikator",
            markers=True,
            template="plotly_white",
            title="Tren Indikator Terpilih",
        )
        figure.update_layout(
            xaxis_title="Tahun",
            yaxis_title="Nilai",
            legend_title="Indikator",
            hovermode="x unified",
        )
        st.plotly_chart(figure, use_container_width=True)
    elif not numeric_columns:
        st.info("Dataset tidak memiliki kolom numerik untuk divisualisasikan.")
    else:
        st.info("Pilih setidaknya satu indikator untuk melihat grafik.")

with tab_compare:
    st.subheader("Perbandingan indikator")

    if numeric_columns:
        default_index = (
            numeric_columns.index("PAD")
            if "PAD" in numeric_columns
            else 0
        )
        selected_metric = st.selectbox(
            "Pilih indikator",
            options=numeric_columns,
            index=default_index,
        )

        if "Tahun" in data.columns:
            figure = px.bar(
                data,
                x="Tahun",
                y=selected_metric,
                template="plotly_white",
                title=f"{selected_metric} per Tahun",
                text_auto=".2f",
                color_discrete_sequence=["#087e8b"],
            )
            figure.update_layout(
                xaxis_title="Tahun",
                yaxis_title=selected_metric,
            )
            st.plotly_chart(figure, use_container_width=True)

        left, right = st.columns(2)
        left.metric(
            f"Nilai tertinggi — {selected_metric}",
            f"{data[selected_metric].max():,.2f}",
        )
        right.metric(
            f"Nilai terendah — {selected_metric}",
            f"{data[selected_metric].min():,.2f}",
        )
    else:
        st.info("Tidak ada kolom numerik untuk dibandingkan.")

with tab_table:
    st.subheader("Tabel data fiskal")

    search_text = st.text_input(
        "Cari data",
        placeholder="Masukkan kata kunci...",
    )

    table_data = data.copy()

    if search_text:
        match_mask = table_data.astype(str).apply(
            lambda column: column.str.contains(
                search_text,
                case=False,
                na=False,
                regex=False,
            )
        ).any(axis=1)
        table_data = table_data[match_mask]

    st.dataframe(
        table_data,
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        label="⬇️ Unduh data sebagai CSV",
        data=table_data.to_csv(index=False).encode("utf-8-sig"),
        file_name="data_fiskal_parepare.csv",
        mime="text/csv",
    )

with st.expander("ℹ️ Informasi dashboard"):
    st.write(
        "Dashboard mengambil data langsung dari CSV pada repositori GitHub. "
        "Gunakan filter kota dan tahun untuk mengubah tampilan."
    )
    st.write(
        "Interpretasikan indikator sesuai definisi, satuan, dan metodologi "
        "yang dijelaskan oleh sumber dataset."
    )

st.divider()
st.caption(
    "Dashboard Fiskal Kota Parepare • Dibuat menggunakan Streamlit, "
    "Pandas, dan Plotly."
)
