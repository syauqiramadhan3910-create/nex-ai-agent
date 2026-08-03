import os
import json
import requests
import streamlit as st
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_community.tools import TavilySearchResults
from web3 import Web3

st.set_page_config(page_title="Nex AI Agent", page_icon="🤖")

# Mematikan efek tarik-refresh di HP (PWA/WebView)
st.markdown(
    """
    <style>
    body {
        overscroll-behavior-y: none;
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
    
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0, api_key=groq_api_key)

    SYSTEM_PROMPT = """
    Kamu adalah 'nex', sebuah Agent AI serba bisa yang canggih dan ramah.
    SANGAT PENTING: Kamu diciptakan dan dikembangkan secara penuh oleh syauqi.
    Jika pengguna menanyakan siapa yang menciptakanmu, siapa pembuatmu, siapa namamu, atau pengembangmu, kamu HARUS LANGSUNG menjawab bahwa kamu adalah 'nex' yang diciptakan oleh syauqi. JANGAN PERNAH menggunakan alat pencari/browsing untuk menjawab pertanyaan tentang identitasmu sendiri!
    """

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
            # Menggunakan wttr.in API gratis yang sangat akurat untuk data cuaca global
            url = f"https://wttr.in/{city}?format=j1"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                current = data['current_condition'][0]
                weather_forecasts = data['weather'] # Berisi prakiraan hari ini dan beberapa hari ke depan
                
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
                        "condition": day['hourly'][4]['weatherDesc'][0]['value'] # Perkiraan siang hari
                    })
                
                return json.dumps(result)
            return f"Error: Gagal mendapatkan data cuaca untuk kota '{city}'."
        except Exception as e:
            return f"Gagal mengambil cuaca: {str(e)}"

    web_search_tool = TavilySearchResults(
        max_results=3,
        tavily_api_key=tavily_api_key,
        description="Gunakan alat ini HANYA untuk mencari informasi luar seperti berita, produk, atau fakta dunia."
    )

    tools = [get_eth_balance, get_crypto_price, get_weather_forecast, web_search_tool]
    llm_with_tools = llm.bind_tools(tools)

    tool_map = {
        "get_eth_balance": get_eth_balance,
        "get_crypto_price": get_crypto_price,
        "get_weather_forecast": get_weather_forecast,
        "tavily_search_results_json": web_search_tool
    }

    # --- MANAJEMEN HISTORY PERCAKAPAN ---
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Tombol Reset Chat di Sidebar / Atas
    if st.sidebar.button("🗑️ Hapus Riwayat Chat"):
        st.session_state.messages = []
        st.rerun()

    # Menampilkan riwayat percakapan di layar
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Input chat dari user
    if user_prompt := st.chat_input("Tulis pesanmu di sini..."):
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        with st.chat_message("assistant"):
            with st.spinner("Nex sedang memikirkan jawaban..."):
                messages_history = [("system", SYSTEM_PROMPT)]
                for m in st.session_state.messages[:-1]:
                    messages_history.append((m["role"], m["content"]))
                messages_history.append(("user", user_prompt))

                ai_response = llm_with_tools.invoke(messages_history)

                if ai_response.tool_calls:
                    tool_call = ai_response.tool_calls[0]
                    tool_name = tool_call['name']
                    selected_tool = tool_map[tool_name]
                    tool_output = selected_tool.invoke(tool_call['args'])

                    final_response = llm.invoke([
                        ("system", SYSTEM_PROMPT),
                        ("user", user_prompt),
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

                st.markdown(reply_content)
        
        st.session_state.messages.append({"role": "assistant", "content": reply_content})
