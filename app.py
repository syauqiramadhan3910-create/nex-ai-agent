import os
import json
import requests
import streamlit as st
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_community.tools import TavilySearchResults
from web3 import Web3

# Konfigurasi Halaman Streamlit
st.set_page_config(page_title="Nex AI Agent", page_icon="🤖")

st.title("🤖 Nex AI Agent")
st.write("Asisten AI serba bisa buatan Syauqi (Dilengkapi Tools Crypto & Web Search)!")

# Sidebar untuk Input API Key jika belum ada di Secrets
st.sidebar.header("🔑 Konfigurasi API Key")
groq_key = os.environ.get("GROQ_API_KEY")
tavily_key = os.environ.get("OS_ENV_TAVILY_KEY") or os.environ.get("TAVILY_API_KEY")

try:
    if not groq_key:
        groq_key = st.secrets.get("GROQ_API_KEY")
    if not tavily_key:
        tavily_key = st.secrets.get("TAVILY_API_KEY")
except:
    pass

groq_api_key = st.sidebar.text_input("Groq API Key:", value=groq_key or "", type="password")
tavily_api_key = st.sidebar.text_input("Tavily API Key:", value=tavily_key or "", type="password")

if not groq_api_key or not tavily_api_key:
    st.warning("⚠️ Masukkan Groq API Key dan Tavily API Key terlebih dahulu di sidebar atau secrets!")
else:
    # Inisialisasi koneksi Web3 & LLM
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

    web_search_tool = TavilySearchResults(
        max_results=3,
        tavily_api_key=tavily_api_key,
        description="Gunakan alat ini HANYA untuk mencari informasi luar seperti harga HP, berita, produk, atau fakta dunia."
    )

    tools = [get_eth_balance, get_crypto_price, web_search_tool]
    llm_with_tools = llm.bind_tools(tools)

    tool_map = {
        "get_eth_balance": get_eth_balance,
        "get_crypto_price": get_crypto_price,
        "tavily_search_results_json": web_search_tool
    }

    # Kelola riwayat chat Streamlit
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if user_prompt := st.chat_input("Tulis pesanmu di sini..."):
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        with st.chat_message("assistant"):
            with st.spinner("Nex sedang memikirkan jawaban..."):
                # Proses Agent dengan Tools LangChain
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
