import os
import json
import base64
import requests
import streamlit as st
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_community.tools import TavilySearchResults
from langchain_core.messages import HumanMessage, SystemMessage
from web3 import Web3

st.set_page_config(page_title="Nex AI Agent", page_icon="🤖")

# CSS untuk mengontrol perilaku scroll di mobile
st.markdown(
    """
    <style>
    html, body, [data-testid="stAppViewContainer"] {
        overscroll-behavior-y: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("🤖 Nex AI Agent")
st.write("Asisten AI serba bisa buatan Syauqi!")

# Ambil API Key dari Streamlit Secrets atau Environment
try:
    groq_api_key = st.secrets["GROQ_API_KEY"]
    tavily_api_key = st.secrets["TAVILY_API_KEY"]
except:
    groq_api_key = os.environ.get("GROQ_API_KEY")
    tavily_api_key = os.environ.get("TAVILY_API_KEY")

if not groq_api_key or not tavily_api_key:
    st.error("⚠️ API Key belum disetting di Secrets Streamlit!")
else:
    RPC_URL = "https://eth-mainnet.g.alchemy.com/v2/alch_5iYsxcDP0cS2bzLC6Rt8e"
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    
    # ---------------------------------------------------------
    # KONFIGURASI MODEL
    # ---------------------------------------------------------
    llm_main = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.3, api_key=groq_api_key)

    SYSTEM_PROMPT = """
    Kamu adalah 'nex', sebuah Agent AI serba bisa yang canggih, ramah, dan mahir menganalisis teks maupun gambar/foto tugas.
    SANGAT PENTING: Kamu diciptakan dan dikembangkan secara penuh oleh syauqi.
    Jika pengguna menanyakan siapa yang menciptakanmu, siapa pembuatmu, siapa namamu, atau pengembangmu, kamu HARUS LANGSUNG menjawab bahwa kamu adalah 'nex' yang diciptakan oleh syauqi. JANGAN PERNAH menggunakan alat pencari/browsing untuk menjawab pertanyaan tentang identitasmu sendiri!
    Jika pengguna mengirimkan gambar, analisis gambar tersebut dengan teliti dan jawab pertanyaan yang relevan secara jelas dan rinci.
    """

    # ---------------------------------------------------------
    # DEFINISI TOOLS
    # ---------------------------------------------------------
    @tool
    def get_eth_balance(wallet_address: str) -> str:
        """Gunakan alat ini HANYA untuk mengecek saldo ETH dari alamat wallet Ethereum. Input: address 0x..."""
        try:
            if not w3.is_address(wallet_address):
                return "Error: Alamat wallet tidak valid."
            balance_wei = w3.eth.get_balance(Web3.to_checksum_address(wallet_address))
            balance_eth = w3.from_wei(balance_wei, 'ether')
            return json.dumps({"address": wallet_address, "balance_eth": float(balance_eth)})
        except Exception as e:
            return f"Error: {str(e)}"

    @tool
    def get_crypto_price(symbol: str) -> str:
        """Gunakan alat ini HANYA untuk mengecek harga pasar koin crypto (Bitcoin, Ethereum, Solana, dll) dalam IDR/USD."""
        try:
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={symbol.lower()}&vs_currencies=usd,idr"
            response = requests.get(url).json()
            if symbol.lower() in response:
                data = response[symbol.lower()]
                return json.dumps({"coin": symbol, "price_usd": data["usd"], "price_idr": data["idr"]})
            return f"Error: Koin '{symbol}' tidak ditemukan."
        except Exception as e:
            return f"Gagal mengambil harga: {str(e)}"

    @tool
    def get_weather_forecast(city: str) -> str:
        """Gunakan alat ini untuk meramal atau mengecek cuaca hari ini dan perkiraan cuaca untuk besok di suatu kota."""
        try:
            url = f"https://wttr.in/{city}?format=j1"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                current = data['current_condition'][0]
                weather_forecasts = data['weather']
                
                result = {
                    "city": city,
                    "current_weather": {
                        "temp_C": current['temp_C'],
                        "condition": current['weatherDesc'][0]['value'],
                        "humidity": current['humidity']
                    },
                    "forecast_days": []
                }
                
                for day in weather_forecasts:
                    result["forecast_days"].append({
                        "date": day['date'],
                        "max_temp_C": day['maxtempC'],
                        "min_temp_C": day['mintempC'],
                        "condition": day['hourly'][4]['weatherDesc'][0]['value']
                    })
                
                return json.dumps(result)
            return f"Error: Gagal mendapatkan data cuaca untuk kota '{city}'."
        except Exception as e:
            return f"Gagal mengambil cuaca: {str(e)}"

    @tool
    def translate_text(text: str, target_language: str) -> str:
        """Gunakan alat ini untuk menerjemahkan teks ke bahasa tujuan tertentu."""
        try:
            prompt_translate = f"Terjemahkan teks berikut ke dalam Bahasa {target_language}:\n\n{text}"
            res = llm_main.invoke(prompt_translate)
            return json.dumps({"original_text": text, "target_language": target_language, "translation": res.content})
        except Exception as e:
            return f"Gagal menerjemahkan: {str(e)}"

    @tool
    def summarize_text(text: str) -> str:
        """Gunakan alat ini untuk meringkas catatan, artikel, atau teks panjang."""
        try:
            prompt_summary = f"Buatkan ringkasan poin-poin penting dari teks berikut:\n\n{text}"
            res = llm_main.invoke(prompt_summary)
            return json.dumps({"summary": res.content})
        except Exception as e:
            return f"Gagal meringkas teks: {str(e)}"

    web_search_tool = TavilySearchResults(
        max_results=3,
        tavily_api_key=tavily_api_key,
        description="Gunakan alat ini HANYA untuk mencari informasi luar seperti berita, produk, atau fakta dunia."
    )

    tools = [get_eth_balance, get_crypto_price, get_weather_forecast, translate_text, summarize_text, web_search_tool]
    llm_main_with_tools = llm_main.bind_tools(tools)

    tool_map = {
        "get_eth_balance": get_eth_balance,
        "get_crypto_price": get_crypto_price,
        "get_weather_forecast": get_weather_forecast,
        "translate_text": translate_text,
        "summarize_text": summarize_text,
        "tavily_search_results_json": web_search_tool
    }

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if st.sidebar.button("🗑️ Hapus Riwayat Chat"):
        st.session_state.messages = []
        st.rerun()

    st.sidebar.markdown("### 📷 Upload Foto Tugas")
    uploaded_file = st.sidebar.file_uploader("Pilih gambar tugas...", type=["jpg", "jpeg", "png"])

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if user_prompt := st.chat_input("Tulis pesanmu di sini..."):
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)
            if uploaded_file:
                st.image(uploaded_file, caption="Foto Tugas yang Diunggah", use_container_width=True)

        with st.chat_message("assistant"):
            with st.spinner("Nex sedang memikirkan jawaban..."):

                # ---------------------------------------------------------
                # SKENARIO 1: UPLOAD GAMBAR
                # ---------------------------------------------------------
                if uploaded_file:
                    try:
                        bytes_data = uploaded_file.getvalue()
                        base64_image = base64.b64encode(bytes_data).decode('utf-8')
                        
                        vision_payload = [
                            {
                                "role": "system",
                                "content": SYSTEM_PROMPT
                            },
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": f"Pertanyaan user: {user_prompt}"},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{base64_image}"
                                        }
                                    }
                                ]
                            }
                        ]
                        
                        headers = {
                            "Authorization": f"Bearer {groq_api_key}",
                            "Content-Type": "application/json"
                        }
                        
                        data = {
                            "messages": vision_payload,
                            "model": "qwen/qwen3.6-27b",
                            "temperature": 0.2
                        }
                        
                        response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data)
                        
                        if response.status_code == 200:
                            result = response.json()
                            reply_content = result['choices'][0]['message']['content']
                        else:
                            st.error(f"Gagal memanggil API Groq Vision: {response.text}")
                            reply_content = "Maaf, Nex gagal menganalisis gambar ini. Silakan coba lagi."

                    except Exception as vision_error:
                        st.error(f"Eror saat memproses gambar: {str(vision_error)}")
                        reply_content = "Terjadi kesalahan internal saat memproses gambar."

                # ---------------------------------------------------------
                # SKENARIO 2: CHAT TEKS
                # ---------------------------------------------------------
                else:
                    try:
                        messages_history = [SystemMessage(content=SYSTEM_PROMPT)]
                        for m in st.session_state.messages[:-1]:
                            if m["role"] == "user":
                                messages_history.append(HumanMessage(content=m["content"]))
                            else:
                                messages_history.append(m["content"])
                                
                        messages_history.append(HumanMessage(content=user_prompt))
                        ai_response = llm_main_with_tools.invoke(messages_history)

                        if ai_response.tool_calls:
                            tool_call = ai_response.tool_calls[0]
                            tool_name = tool_call['name']
                            selected_tool = tool_map[tool_name]
                            tool_output = selected_tool.invoke(tool_call['args'])

                            final_response = llm_main.invoke([
                                SystemMessage(content=SYSTEM_PROMPT),
                                HumanMessage(content=user_prompt),
                                ai_response,
                                {
                                    "role": "tool",
                                    "content": str(tool_output),
                                    "tool_call_id": tool_call["id"],
                                }
                            ])
                            reply_content = final_response.content
                        else:
                            reply_content = ai_response.content
                            
                    except Exception as text_error:
                        st.error(f"Eror saat memproses teks: {str(text_error)}")
                        reply_content = "Maaf, Nex mengalami masalah saat memproses pesan teks."

                st.markdown(reply_content)
        
        st.session_state.messages.append({"role": "assistant", "content": reply_content})
