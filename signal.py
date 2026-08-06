import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Overpower Screener (God Mode)", layout="centered", initial_sidebar_state="collapsed")

# --- CSS KUSTOM ---
st.markdown("""
    <style>
    .main { background-color: #0E0E11; color: #FFFFFF; }
    .pro-card { background-color: #18181B; border-radius: 12px; padding: 20px; margin-bottom: 15px; border: 1px solid #27272A; }
    .card-label { color: #D4D4D8; font-size: 12px; font-weight: bold; letter-spacing: 1px; margin-bottom: 15px; text-transform: uppercase; }
    .data-grid { display: grid; gap: 15px; }
    .data-label { color: #A1A1AA; font-size: 11px; display: block; margin-bottom: 3px; }
    .data-value { color: #FFFFFF; font-size: 15px; font-weight: bold; }
    .badge-green { background-color: rgba(16, 185, 129, 0.2); color: #10B981; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }
    .badge-red { background-color: rgba(239, 68, 68, 0.2); color: #EF4444; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }
    .badge-blue { background-color: rgba(59, 130, 246, 0.2); color: #3B82F6; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- FUNGSI: MENGAMBIL TREN IHSG ---
@st.cache_data(ttl=3600)
def get_ihsg_regime():
    try:
        ihsg = yf.download("^JKSE", period="3mo", progress=False)
        if ihsg.empty: return "NETRAL"
        close_ihsg = float(ihsg['Close'].iloc[-1])
        ma20_ihsg = float(ihsg['Close'].rolling(window=20).mean().iloc[-1])
        return "BULLISH" if close_ihsg > ma20_ihsg else "BEARISH"
    except Exception:
        return "NETRAL"

# --- FUNGSI: MENGHITUNG INDIKATOR DEWA ---
def calculate_indicators(df):
    # Moving Averages
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA50'] = df['Close'].rolling(window=50).mean()
    df['VOL_SMA20'] = df['Volume'].rolling(window=20).mean()
    
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    # UPGRADE 2: Support & Resistance (20 Hari)
    df['Support'] = df['Low'].rolling(window=20).min()
    df['Resistance'] = df['High'].rolling(window=20).max()
    
    # UPGRADE 3: On-Balance Volume (OBV) - Jejak Bandar
    df['OBV'] = (np.sign(delta) * df['Volume']).fillna(0).cumsum()
    df['OBV_MA'] = df['OBV'].rolling(window=20).mean()
    
    return df

# --- FUNGSI: MEMBUAT CHART MINI INTERAKTIF ---
def create_mini_chart(df, ticker):
    df_chart = df.tail(60) # Ambil 3 bulan terakhir agar chart tidak terlalu rapat
    fig = go.Figure(data=[go.Candlestick(x=df_chart.index,
                    open=df_chart['Open'],
                    high=df_chart['High'],
                    low=df_chart['Low'],
                    close=df_chart['Close'],
                    name='Harga')])
    
    fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['MA20'], line=dict(color='#F59E0B', width=2), name='MA20'))
    
    fig.update_layout(
        title=dict(text=f'Grafik {ticker} (3 Bulan Terakhir)', font=dict(color='#D4D4D8', size=14)),
        yaxis_title='Harga',
        xaxis_title='',
        template='plotly_dark',
        margin=dict(l=0, r=0, t=30, b=0),
        height=350,
        paper_bgcolor='#18181B',
        plot_bgcolor='#18181B'
    )
    fig.update_xaxes(rangeslider_visible=False, gridcolor='#27272A')
    fig.update_yaxes(gridcolor='#27272A')
    return fig

# --- LOGIKA KEPUTUSAN UTAMA ---
def analisis_saham(ticker_input, ihsg_status):
    ticker_symbol = f"{ticker_input}.JK" if not ticker_input.endswith(".JK") else ticker_input
    
    try:
        stock = yf.Ticker(ticker_symbol)
        df = stock.history(period="6mo")
        if df.empty: return None
        
        df = calculate_indicators(df)
        today = df.iloc[-1]
        
        harga = float(today['Close']) if pd.notna(today['Close']) else 0.0
        open_price = float(today['Open']) if pd.notna(today['Open']) else 0.0
        low_price = float(today['Low']) if pd.notna(today['Low']) else 0.0
        high_price = float(today['High']) if pd.notna(today['High']) else 0.0
        volume = float(today['Volume']) if pd.notna(today['Volume']) else 0.0
        
        ma20 = float(today['MA20']) if pd.notna(today['MA20']) else 0.0
        ma50 = float(today['MA50']) if pd.notna(today['MA50']) else 0.0
        vol_sma20 = float(today['VOL_SMA20']) if pd.notna(today['VOL_SMA20']) else 0.0
        rsi = float(today['RSI']) if pd.notna(today['RSI']) else 50.0
        macd = float(today['MACD']) if pd.notna(today['MACD']) else 0.0
        signal = float(today['Signal_Line']) if pd.notna(today['Signal_Line']) else 0.0
        obv = float(today['OBV']) if pd.notna(today['OBV']) else 0.0
        obv_ma = float(today['OBV_MA']) if pd.notna(today['OBV_MA']) else 0.0
        support = float(today['Support']) if pd.notna(today['Support']) else 0.0
        resistance = float(today['Resistance']) if pd.notna(today['Resistance']) else 0.0

        body_candle = abs(harga - open_price)
        lower_shadow = (open_price - low_price) if harga > open_price else (harga - low_price)
        is_rejection = lower_shadow > (body_candle * 1.5)
        is_volume_spike = volume > (vol_sma20 * 1.5) if vol_sma20 > 0 else False
        is_dekat_support = (harga > ma20) and (harga < (ma20 * 1.05)) if ma20 > 0 else False
        
        strategi_final = "SKIP (DOWNTREND)"
        warna_strategi = "#EF4444" 
        alasan = "Harga di bawah MA20 dan tidak ada perlawanan beli."
        
        if ihsg_status == "BEARISH":
            if is_rejection and is_volume_spike and rsi < 40:
                strategi_final = "SPEKULASI BUY"
                warna_strategi = "#F59E0B"
            else:
                strategi_final = "TUNGGU (IHSG BERDARAH)"
                warna_strategi = "#EF4444"
        else:
            if is_rejection and is_dekat_support and is_volume_spike:
                strategi_final = "🔥 SETUP A+"
                warna_strategi = "#10B981"
            elif (ma20 > 0 and harga > ma20) and is_volume_spike and rsi < 60:
                strategi_final = "⚡ MOMENTUM BUY"
                warna_strategi = "#10B981"
            elif ma20 > 0 and harga < ma20 and not is_rejection:
                pass # Tetap SKIP
            else:
                strategi_final = "TUNGGU MOMENTUM"
                warna_strategi = "#9CA3AF"
                
        return {
            "df": df, "stock_info": stock.info, "harga": harga, "volume": volume,
            "rsi": rsi, "macd": macd, "signal": signal, "ma20": ma20, "ma50": ma50,
            "obv": obv, "obv_ma": obv_ma, "support": support, "resistance": resistance,
            "strategi_final": strategi_final, "warna_strategi": warna_strategi,
            "is_volume_spike": is_volume_spike, "high_price": high_price, "low_price": low_price
        }
    except Exception:
        return None

# --- HEADER APLIKASI ---
st.title("⚡ Overpower Fast Trade (God Mode)")
ihsg_status = get_ihsg_regime()

if ihsg_status == "BEARISH":
    st.warning("⚠️ **STATUS IHSG: BEARISH (DOWNTREND).** Hati-hati, market sedang tidak ramah!")
else:
    st.success("✅ **STATUS IHSG: BULLISH/NETRAL.** Kondisi market mendukung untuk trading.")

# --- UPGRADE 1: TABS UNTUK SINGLE ANALISIS & MASSAL ---
tab1, tab2 = st.tabs(["🎯 GOD MODE (Detail per Saham)", "📡 RADAR MASSAL (Screener Banyak Saham)"])

# ==========================================
# TAB 1: GOD MODE (DETAIL)
# ==========================================
with tab1:
    ticker_input = st.text_input("🔍 Masukkan Kode Saham (contoh: AMMN, GOTO, SULI):", "GOTO").upper()
    
    if ticker_input:
        with st.spinner(f"Menganalisis {ticker_input} dengan kekuatan penuh..."):
            hasil = analisis_saham(ticker_input, ihsg_status)
            
            if not hasil:
                st.error("Data gagal ditarik atau saham tidak ditemukan.")
            else:
                kode_tampil = ticker_input.replace('.JK', '')
                info = hasil["stock_info"]
                harga = hasil["harga"]
                
                # --- IDENTITAS PERUSAHAAN ---
                nama_perusahaan = info.get('longName', 'Nama Perusahaan Tidak Tersedia')
                sektor = info.get('sector', 'Sektor Tidak Tersedia')
                st.markdown(f"""
                <div style="display: flex; align-items: center; background-color: #18181B; padding: 20px; border-radius: 12px; border: 1px solid #27272A; margin-bottom: 20px;">
                    <div style="background-color: #27272A; padding: 15px 20px; border-radius: 10px; margin-right: 20px; border: 1px solid #3F3F46;"><span style="font-size: 28px;">🏢</span></div>
                    <div>
                        <h1 style="margin: 0; color: #FFFFFF; font-size: 28px; font-weight: 800;">{kode_tampil}</h1>
                        <p style="margin: 2px 0 0 0; color: #E4E4E7; font-size: 16px;">{nama_perusahaan} | <span style="color: #A1A1AA; font-size: 13px;">{sektor}</span></p>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if harga < 100 and harga > 0:
                    st.error("🚨 **PERINGATAN SAHAM PENNY:** Harga di bawah Rp 100. Risiko manipulasi sangat tinggi!")

                # --- UPGRADE 4: MINI CHART INTERAKTIF ---
                st.plotly_chart(create_mini_chart(hasil["df"], kode_tampil), use_container_width=True)

                col1, col2 = st.columns(2)
                
                with col1:
                    # SMART MONEY & JEJAK BANDAR (UPGRADE 3)
                    vol = hasil["volume"]
                    vol_display = f"{vol / 1_000_000_000:.2f}B" if vol >= 1_000_000_000 else f"{vol / 1_000_000:.1f}M"
                    vol_status = "VOLUME MELEDAK 🔥" if hasil["is_volume_spike"] else "VOLUME KERING"
                    vol_color = "#10B981" if hasil["is_volume_spike"] else "#EF4444"
                    
                    bandar_status = "AKUMULASI (BANDAR MASUK) 📈" if hasil["obv"] > hasil["obv_ma"] else "DISTRIBUSI (BANDAR KELUAR) 📉"
                    bandar_color = "badge-blue" if hasil["obv"] > hasil["obv_ma"] else "badge-red"

                    st.markdown(f"""
                    <div class="pro-card">
                        <div class="card-label">🌊 SMART MONEY & BANDARMOLOGI</div>
                        <div style="text-align: center; margin: 10px 0;">
                            <div style="font-size: 32px; font-weight: bold; color: #FFFFFF;">{vol_display}</div>
                            <div style="color: {vol_color}; font-size: 12px; font-weight: bold; border: 1px solid {vol_color}; display: inline-block; padding: 4px 12px; border-radius: 4px; margin-bottom: 10px;">{vol_status}</div>
                            <br><span class="{bandar_color}">JEJAK OBV: {bandar_status}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                with col2:
                    # TRADING PLAN OTOMATIS (UPGRADE 2)
                    potensi_profit = ((hasil["resistance"] - harga) / harga) * 100 if harga > 0 else 0
                    risiko_loss = ((harga - hasil["support"]) / harga) * 100 if harga > 0 else 0
                    
                    st.markdown(f"""
                    <div class="pro-card">
                        <div class="card-label">🎯 AUTO TRADING PLAN (S&R)</div>
                        <div class="data-grid" style="grid-template-columns: repeat(2, 1fr);">
                            <div><span class="data-label">HARGA ENTRY (SAAT INI)</span><span class="data-value">{harga:,.0f}</span></div>
                            <div><span class="data-label">RISK REWARD RATIO</span><span class="data-value" style="color: {'#10B981' if potensi_profit > risiko_loss else '#EF4444'};">{"BAIK" if potensi_profit > risiko_loss else "BURUK"}</span></div>
                            
                            <div><span class="data-label">TARGET JUAL (RESISTANCE)</span><span class="data-value" style="color: #10B981;">{hasil["resistance"]:,.0f} <span style="font-size:11px;">(UP {potensi_profit:.1f}%)</span></span></div>
                            <div><span class="data-label">BATAS CUT LOSS (SUPPORT)</span><span class="data-value" style="color: #EF4444;">{hasil["support"]:,.0f} <span style="font-size:11px;">(DOWN {risiko_loss:.1f}%)</span></span></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                # FINAL DECISION
                st.markdown(f"""
                <div class="pro-card" style="border-left: 5px solid {hasil['warna_strategi']};">
                    <div class="card-label" style="color: {hasil['warna_strategi']}; font-size: 14px;">⚡ FINAL KEPUTUSAN SISTEM</div>
                    <h2 style="color: {hasil['warna_strategi']}; margin-top: 0; margin-bottom: 5px;">{hasil['strategi_final']}</h2>
                </div>
                """, unsafe_allow_html=True)

# ==========================================
# TAB 2: RADAR MASSAL (SCREENER)
# ==========================================
with tab2:
    st.markdown("### 📡 Scan Puluhan Saham Sekaligus")
    mass_input = st.text_area("Masukkan kode saham pisahkan dengan koma (Contoh: BBCA, BREN, GOTO, AMMN, PANI, SULI):", "GOTO, AMMN, BREN, PANI, SIDO, SULI, BBCA, BRPT, CUAN")
    
    if st.button("🚀 AKTIFKAN RADAR", use_container_width=True):
        tickers = [t.strip().upper() for t in mass_input.split(',')]
        hasil_scan = []
        
        progress_text = "Memindai pasar..."
        my_bar = st.progress(0, text=progress_text)
        
        for i, t in enumerate(tickers):
            if t == "": continue
            my_bar.progress((i + 1) / len(tickers), text=f"Memindai {t}...")
            
            data_saham = analisis_saham(t, ihsg_status)
            if data_saham:
                trend = "BULLISH" if data_saham['harga'] > data_saham['ma20'] else "BEARISH"
                bandar = "AKUMULASI" if data_saham['obv'] > data_saham['obv_ma'] else "DISTRIBUSI"
                vol_str = "MELEDAK" if data_saham['is_volume_spike'] else "KERING"
                
                hasil_scan.append({
                    "Ticker": t.replace('.JK', ''),
                    "Harga": f"{data_saham['harga']:,.0f}",
                    "Sinyal Mesin": data_saham['strategi_final'],
                    "Trend (MA20)": trend,
                    "Jejak Bandar (OBV)": bandar,
                    "Volume": vol_str,
                    "RSI": f"{data_saham['rsi']:.1f}"
                })
        
        my_bar.empty()
        
        if hasil_scan:
            df_hasil = pd.DataFrame(hasil_scan)
            
            def color_cells(val):
                color = '#10B981' if 'BUY' in val or 'SETUP A+' in val or val == 'BULLISH' or val == 'AKUMULASI' or val == 'MELEDAK' else '#EF4444' if 'SKIP' in val or val == 'BEARISH' or val == 'DISTRIBUSI' or val == 'KERING' else 'white'
                return f'color: {color}'

            st.dataframe(df_hasil.style.map(color_cells, subset=['Sinyal Mesin', 'Trend (MA20)', 'Jejak Bandar (OBV)', 'Volume']), use_container_width=True, hide_index=True)
            st.success("✨ Pindai selesai! Fokus pada saham dengan Sinyal '🔥 SETUP A+' atau '⚡ MOMENTUM BUY'.")
        else:
            st.warning("Tidak ada data yang berhasil dipindai. Cek kembali kode saham Anda.")
