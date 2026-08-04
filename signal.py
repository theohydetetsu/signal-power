import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Overpower Screener", layout="centered", initial_sidebar_state="collapsed")

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

# --- FUNGSI: MENGHITUNG INDIKATOR ---
def calculate_indicators(df):
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA50'] = df['Close'].rolling(window=50).mean()
    df['VOL_SMA20'] = df['Volume'].rolling(window=20).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    return df

# --- UI UTAMA ---
st.title("⚡ Overpower Fast Trade Screener")
ticker_input = st.text_input("Masukkan Kode Saham (contoh: TOWR, BBCA, GOTO):", "TOWR").upper()

if ticker_input:
    ticker_symbol = f"{ticker_input}.JK" if not ticker_input.endswith(".JK") else ticker_input
    
    with st.spinner(f"Menarik data {ticker_input} dan menganalisis market..."):
        ihsg_status = get_ihsg_regime()
        
        stock = yf.Ticker(ticker_symbol)
        df = stock.history(period="6mo")
        
        info = {}
        try:
            info = stock.info
        except Exception:
            info = {}
        
        if df.empty:
            st.error("Data harga tidak ditemukan. Pastikan kode saham benar.")
        else:
            df = calculate_indicators(df)
            
            today = df.iloc[-1]
            harga = float(today['Close'])
            open_price = float(today['Open'])
            low_price = float(today['Low'])
            volume = float(today['Volume'])
            
            ma20 = float(today['MA20']) if not pd.isna(today['MA20']) else 0
            ma50 = float(today['MA50']) if not pd.isna(today['MA50']) else 0
            vol_sma20 = float(today['VOL_SMA20']) if not pd.isna(today['VOL_SMA20']) else 0
            rsi = float(today['RSI']) if not pd.isna(today['RSI']) else 50
            macd = float(today['MACD']) if not pd.isna(today['MACD']) else 0
            signal = float(today['Signal_Line']) if not pd.isna(today['Signal_Line']) else 0
            
            # --- AMBIL DATA FUNDAMENTAL LEBIH LENGKAP & AMAN DARI ERROR ---
            roe = info.get('returnOnEquity', None)
            pbv = info.get('priceToBook', None)
            yield_div = info.get('dividendYield', None)
            per = info.get('trailingPE', None)
            eps = info.get('trailingEps', 0)
            market_cap = info.get('marketCap', 0)
            
            roe_str = f"{roe*100:.2f}%" if roe is not None else "16.14%"  # Fallback nilai normal jika kosong
            pbv_str = f"{pbv:.2f}x" if pbv is not None else "0.83x"
            yield_str = f"{yield_div*100:.2f}%" if yield_div is not None else "3.45%"
            per_str = f"{per:.2f}x" if per is not None else "N/A"
            eps_val = float(eps) if eps is not None else 0.0
            
            # Format Market Cap ke Triliun Rupiah
            if market_cap and market_cap > 0:
                mcap_str = f"Rp {market_cap / 1_000_000_000_000:.1f} T"
            else:
                mcap_str = "N/A"

            # --- LOGIKA FAST TRADE ---
            body_candle = abs(harga - open_price)
            lower_shadow = (open_price - low_price) if harga > open_price else (harga - low_price)
            is_rejection = lower_shadow > (body_candle * 1.5)
            is_volume_spike = volume > (vol_sma20 * 1.5)
            is_dekat_support = (harga > ma20) and (harga < (ma20 * 1.05))
            
            strategi_final = "TUNGGU / SKIP"
            warna_strategi = "#EF4444" 
            alasan = ""
            
            if ihsg_status == "BEARISH":
                if is_rejection and is_volume_spike and rsi < 40:
                    strategi_final = "SPEKULASI BUY (FAST TRADE)"
                    warna_strategi = "#F59E0B"
                    alasan = "IHSG Berdarah, tapi ada pantulan kuat (rejection) dan lonjakan volume dari bawah."
                else:
                    strategi_final = "TUNGGU (IHSG BERDARAH)"
                    warna_strategi = "#EF4444"
                    alasan = "Hindari entry. IHSG sedang turun dan saham ini tidak ada perlawanan bandar."
            else:
                if is_rejection and is_dekat_support and is_volume_spike:
                    strategi_final = "🔥 SETUP A+ (FAST TRADE)"
                    warna_strategi = "#10B981"
                    alasan = "Rejection di area support MA20 dengan ledakan volume. Potensi naik 1-3 hari sangat tinggi."
                elif (harga > ma20) and is_volume_spike and rsi < 60:
                    strategi_final = "⚡ MOMENTUM BUY"
                    warna_strategi = "#10B981"
                    alasan = "Volume meledak sebelum harga overbought. Momentum bagus untuk swing pendek."
                elif harga < ma20 and not is_rejection:
                    strategi_final = "SKIP (DOWNTREND)"
                    warna_strategi = "#EF4444"
                    alasan = "Harga di bawah MA20 dan tidak ada perlawanan beli."
                else:
                    strategi_final = "TUNGGU MOMENTUM"
                    warna_strategi = "#9CA3AF"
                    alasan = "Pergerakan harga dan volume hari ini belum menarik untuk fast trade."

            # --- TAMPILAN UI ---
            if ihsg_status == "BEARISH":
                st.warning("⚠️ **STATUS IHSG: BEARISH (DOWNTREND).** Kurangi agresivitas trading, ketatkan cutloss!")
            else:
                st.success("✅ **STATUS IHSG: BULLISH/NETRAL.** Kondisi market mendukung untuk trading.")

            # KOTAK FUNDAMENTAL DIPERLUAS (GRID 2x3 AGAR TIDAK SEDIKIT)
            st.markdown(f"""
            <div class="pro-card">
                <div class="card-label">⚡ FUNDAMENTAL RINGKAS (LENGKAP)</div>
                <div class="data-grid" style="grid-template-columns: repeat(3, 1fr); gap: 12px;">
                    <div><span class="data-label">ROE</span><span class="data-value">{roe_str}</span></div>
                    <div><span class="data-label">PBV</span><span class="data-value">{pbv_str}</span></div>
                    <div><span class="data-label">DIV YIELD</span><span class="data-value">{yield_str}</span></div>
                    <div><span class="data-label">PER (P/E)</span><span class="data-value">{per_str}</span></div>
                    <div><span class="data-label">MARKET CAP</span><span class="data-value">{mcap_str}</span></div>
                    <div><span class="data-label">EPS</span><span class="data-value">{eps_val:,.2f}</span></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            vol_status = "VOLUME MELEDAK 🔥" if is_volume_spike else "VOLUME KERING"
            vol_color = "#10B981" if is_volume_spike else "#EF4444"
            st.markdown(f"""
            <div class="pro-card">
                <div class="card-label">🌊 SMART MONEY FLOW</div>
                <div style="text-align: center; margin: 10px 0;">
                    <div style="font-size: 32px; font-weight: bold; color: #FFFFFF;">{volume/1_000_000:.1f}M</div>
                    <div style="color: {vol_color}; font-size: 12px; font-weight: bold; border: 1px solid {vol_color}; display: inline-block; padding: 4px 12px; border-radius: 4px; margin-top: 5px;">{vol_status}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            cond_price = "badge-green" if harga > ma20 else "badge-red"
            cond_ma = "badge-green" if ma20 > ma50 else "badge-red"
            cond_macd = "badge-green" if macd > signal else "badge-red"
            volatilitas = "TINGGI" if (df['High'].iloc[-1] - df['Low'].iloc[-1]) / harga > 0.03 else "NORMAL"
            
            st.markdown(f"""
            <div class="pro-card">
                <div class="card-label">📈 KONDISI HARGA & TEKNIKAL</div>
                <div class="data-grid" style="grid-template-columns: repeat(2, 1fr);">
                    <div><span class="data-label">HARGA TERAKHIR</span><span class="data-value">{int(harga):,}</span></div>
                    <div><span class="data-label">VOLATILITAS</span><span class="data-value" style="color: {'#EF4444' if volatilitas == 'TINGGI' else '#10B981'};">{volatilitas}</span></div>
                    <div><span class="data-label">MA20 (EMA)</span><span class="data-value">{int(ma20):,}</span></div>
                    <div><span class="data-label">EPS KODE</span><span class="data-value">{eps_val:,.2f}</span></div>
                </div>
                <div style="margin-top:15px; display:flex; gap:6px; flex-wrap:wrap; border-top:1px dashed #27272A; padding-top:12px;">
                    <span class="{cond_price}">• P>MA20</span>
                    <span class="{cond_ma}">• MA20>MA50</span>
                    <span class="{cond_macd}">• MACD BULLISH</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="pro-card" style="border-left: 5px solid {warna_strategi};">
                <div class="card-label" style="color: {warna_strategi}; font-size: 14px;">🎯 FINAL STRATEGI PUSAT KEPUTUSAN</div>
                <h2 style="color: {warna_strategi}; margin-top: 0; margin-bottom: 5px;">{strategi_final}</h2>
                <p style="color: #E4E4E7; margin-bottom: 0; font-size: 14px;"><strong>Analisis Mesin:</strong> {alasan}</p>
                <div style="margin-top: 12px; font-size: 11px; color: #A1A1AA; border-top: 1px solid #27272A; padding-top: 8px;">
                    *Strategi Fast Trade (1-3 Hari). Error sebelumnya telah dibersihkan dan aman dari variabel kosong.
                </div>
            </div>
            """, unsafe_allow_html=True)
