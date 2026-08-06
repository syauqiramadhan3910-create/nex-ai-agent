import os
import json
import base64
import requests
import urllib.parse
import math
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

# ---------------------------------------------------------
# SINKRONISASI MULTI-API KEY GROQ (AUTO FALLBACK)
# ---------------------------------------------------------
groq_keys = []

# Ambil semua kemungkinan key dari Secrets
for i in range(1, 6):
    key = st.secrets.get(f"GROQ_API_KEY_{i}") or st.secrets.get("GROQ_API_KEY") if i == 1 else None
    if key and key not in groq_keys:
        groq_keys.append(key)

if not groq_keys:
    env_key = os.environ.get("GROQ_API_KEY")
    if env_key:
        groq_keys.append(env_key)

tavily_api_key = st.secrets.get("TAVILY_API_KEY") or os.environ.get("TAVILY_API_KEY")

if not groq_keys or not tavily_api_key:
    st.error("⚠️ API Key belum disetting di Secrets Streamlit!")
else:
    RPC_URL = "https://eth-mainnet.g.alchemy.com/v2/alch_5iYsxcDP0cS2bzLC6Rt8e"
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    
    SYSTEM_PROMPT = """
    Kamu adalah 'nex', sebuah Agent AI serba bisa yang canggih, ramah, dan sangat mahir.
    SANGAT PENTING: Kamu diciptakan dan dikembangkan secara penuh oleh syauqi.
    Jika pengguna menanyakan siapa yang menciptakanmu, siapa pembuatmu, siapa namamu, atau pengembangmu, kamu HARUS LANGSUNG menjawab bahwa kamu adalah 'nex' yang diciptakan oleh syauqi. JANGAN PERNAH menggunakan alat pencari/browsing untuk menjawab pertanyaan tentang identitasmu sendiri!
    Gunakan alat-alat (tools) yang tersedia dengan efisien sesuai kebutuhan pengguna:
    - Untuk membuat gambar: gunakan `generate_image`.
    - Untuk membuat QR Code: gunakan `generate_qrcode`.
    - Untuk perhitungan matematika presisi: gunakan `calculate_math`.
    - Untuk fakta/ensiklopedia: gunakan `get_wikipedia_summary`.
    - Untuk cek IP/Jaringan: gunakan `get_ip_info`.
    - Untuk cek Repo GitHub: gunakan `extract_github_repo_info`.
    """

    # ---------------------------------------------------------
    # DEFINISI TOOLS (Lama + 5 Tool Baru)
    # ---------------------------------------------------------
    @tool
    def generate_image(prompt: str) -> str:
        """Gunakan alat ini HANYA ketika pengguna meminta untuk membuat, meng-generate, atau menggambar sesuatu (Image Generator). Input: prompt deskripsi gambar dalam Bahasa Inggris."""
        try:
            encoded_prompt = urllib.parse.quote(prompt)
            image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"
            return json.dumps({"image_url": image_url, "prompt": prompt})
        except Exception as e:
            return f"Gagal membuat gambar: {str(e)}"

    # TOOL BARU 1: KALKULATOR MATEMATIKA PERSISI
    @tool
    def calculate_math(expression: str) -> str:
        """Gunakan alat ini untuk menghitung kalkulasi matematika presisi, ekspresi aljabar, trigonometri, statistik, atau logaritma. Input: ekspresi matematika dalam format string standar seperti '2**10', 'sqrt(144)', 'sin(30)'."""
        try:
            allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
            allowed_names.update({"abs": abs, "round": round, "min": min, "max": max, "sum": sum})
            result = eval(expression, {"__builtins__": None}, allowed_names)
            return json.dumps({"expression": expression, "result": result})
        except Exception as e:
            return f"Eror saat menghitung matematika: {str(e)}"

    # TOOL BARU 2: ENSIKLOPEDIA WIKIPEDIA
    @tool
    def get_wikipedia_summary(query: str) -> str:
        """Gunakan alat ini untuk mencari ringkasan artikel ensiklopedia, latar belakang fakta sejarah, sains, tokoh, atau topik umum dari Wikipedia. Input: kata kunci pencarian."""
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"https://id.wikipedia.org/api/rest_v1/page/summary/{encoded_query}"
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                data = res.json()
                return json.dumps({
                    "title": data.get("title"),
                    "extract": data.get("extract"),
                    "url": data.get("content_urls", {}).get("desktop", {}).get("page")
                })
            # Try English Wikipedia as fallback
            url_en = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded_query}"
            res_en = requests.get(url_en, timeout=10)
            if res_en.status_code == 200:
                data_en = res_en.json()
                return json.dumps({
                    "title": data_en.get("title"),
                    "extract": data_en.get("extract"),
                    "url": data_en.get("content_urls", {}).get("desktop", {}).get("page")
                })
            return f"Tidak ditemukan informasi Wikipedia untuk '{query}'."
        except Exception as e:
            return f"Gagal mengambil data Wikipedia: {str(e)}"

    # TOOL BARU 3: GENERATOR QR CODE
    @tool
    def generate_qrcode(text_or_url: str) -> str:
        """Gunakan alat ini ketika pengguna meminta untuk membuat QR Code dari tautan URL, teks, nomor WhatsApp, atau email. Input: teks atau URL yang ingin diubah jadi QR Code."""
        try:
            encoded_text = urllib.parse.quote(text_or_url)
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={encoded_text}"
            return json.dumps({"qr_code_url": qr_url, "content": text_or_url})
        except Exception as e:
            return f"Gagal membuat QR Code: {str(e)}"

    # TOOL BARU 4: CEK DETEKSI IP & GEOLOKASI JARINGAN
    @tool
    def get_ip_info(ip_address: str) -> str:
        """Gunakan alat ini untuk mengecek lokasi geografis, ISP, negara, kota, atau detail dari alamat IP publik tertentu. Input: Alamat IP (misal '8.8.8.8')."""
        try:
            url = f"https://ipapi.co/{ip_address.strip()}/json/"
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                data = res.json()
                return json.dumps({
                    "ip": data.get("ip"),
                    "city": data.get("city"),
                    "region": data.get("region"),
                    "country": data.get("country_name"),
                    "org": data.get("org")
                })
            return f"Gagal melacak Alamat IP '{ip_address}'."
        except Exception as e:
            return f"Gagal memeriksa IP: {str(e)}"

    # TOOL BARU 5: CEK STATISTIK REPOSITORI GITHUB
    @tool
    def extract_github_repo_info(repo_owner_name: str) -> str:
        """Gunakan alat ini untuk mengecek detail repositori GitHub (jumlah stars, forks, bahasa utama, lisensi). Input: format 'owner/repository_name' (misal 'facebook/react' atau 'python/cpython')."""
        try:
            url = f"https://api.github.com/repos/{repo_owner_name.strip()}"
            headers = {"User-Agent": "NexAIAgent"}
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                return json.dumps({
                    "repo": data.get("full_name"),
                    "stars": data.get("stargazers_count"),
                    "forks": data.get("forks_count"),
                    "language": data.get("language"),
                    "description": data.get("description"),
                    "url": data.get("html_url")
                })
            return f"Repositori GitHub '{repo_owner_name}' tidak ditemukan."
        except Exception as e:
            return f"Gagal mengambil info GitHub: {str(e)}"

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
            llm_temp = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.3, api_key=groq_keys[0])
            prompt_translate = f"Terjemahkan teks berikut ke dalam Bahasa {target_language}:\n\n{text}"
            res = llm_temp.invoke(prompt_translate)
            return json.dumps({"original_text": text, "target_language": target_language, "translation": res.content})
        except Exception as e:
            return f"Gagal menerjemahkan: {str(e)}"

    @tool
    def summarize_text(text: str) -> str:
        """Gunakan alat ini untuk meringkas catatan, artikel, atau teks panjang."""
        try:
            llm_temp = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.3, api_key=groq_keys[0])
            prompt_summary = f"Buatkan ringkasan poin-poin penting dari teks berikut:\n\n{text}"
            res = llm_temp.invoke(prompt_summary)
            return json.dumps({"summary": res.content})
        except Exception as e:
            return f"Gagal meringkas teks: {str(e)}"

    web_search_tool = TavilySearchResults(
        max_results=3,
        tavily_api_key=tavily_api_key,
        description="Gunakan alat ini HANYA untuk mencari informasi luar seperti berita, produk, atau fakta dunia."
    )

    tools = [
        generate_image, calculate_math, get_wikipedia_summary, generate_qrcode, 
        get_ip_info, extract_github_repo_info, get_eth_balance, get_crypto_price, 
        get_weather_forecast, translate_text, summarize_text, web_search_tool
    ]
    
    tool_map = {
        "generate_image": generate_image,
        "calculate_math": calculate_math,
        "get_wikipedia_summary": get_wikipedia_summary,
        "generate_qrcode": generate_qrcode,
        "get_ip_info": get_ip_info,
        "extract_github_repo_info": extract_github_repo_info,
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
            if "image_url" in message:
                st.markdown(message["content"])
                st.image(message["image_url"], use_container_width=True)
            elif "qr_url" in message:
                st.markdown(message["content"])
                st.image(message["qr_url"], width=250)
            else:
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
                    reply_content = None
                    bytes_data = uploaded_file.getvalue()
                    base64_image = base64.b64encode(bytes_data).decode('utf-8')
                    
                    vision_payload = [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": f"Pertanyaan user: {user_prompt}"},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                            ]
                        }
                    ]

                    for api_key in groq_keys:
                        try:
                            headers = {
                                "Authorization": f"Bearer {api_key}",
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
                                break
                        except Exception:
                            continue
                    
                    if not reply_content:
                        reply_content = "Maaf, semua API Key sedang mencapai batas limit harian. Silakan coba beberapa saat lagi."

                    st.markdown(reply_content)
                    st.session_state.messages.append({"role": "assistant", "content": reply_content})

                # ---------------------------------------------------------
                # SKENARIO 2: CHAT TEKS & TOOL EXECUTION
                # ---------------------------------------------------------
                else:
                    reply_content = None
                    image_url_generated = None
                    qr_url_generated = None

                    messages_history = [SystemMessage(content=SYSTEM_PROMPT)]
                    for m in st.session_state.messages[:-1]:
                        if m["role"] == "user":
                            messages_history.append(HumanMessage(content=m["content"]))
                        else:
                            messages_history.append(m["content"])
                    messages_history.append(HumanMessage(content=user_prompt))

                    for api_key in groq_keys:
                        try:
                            llm_main = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.3, api_key=api_key)
                            llm_main_with_tools = llm_main.bind_tools(tools)
                            
                            ai_response = llm_main_with_tools.invoke(messages_history)

                            if ai_response.tool_calls:
                                tool_call = ai_response.tool_calls[0]
                                tool_name = tool_call['name']
                                selected_tool = tool_map[tool_name]
                                tool_output = selected_tool.invoke(tool_call['args'])

                                if tool_name == "generate_image":
                                    img_data = json.loads(tool_output)
                                    image_url_generated = img_data.get("image_url")
                                    reply_content = f"Ini gambar yang kamu minta untuk **'{user_prompt}'**:"
                                elif tool_name == "generate_qrcode":
                                    qr_data = json.loads(tool_output)
                                    qr_url_generated = qr_data.get("qr_code_url")
                                    reply_content = f"Ini QR Code yang kamu minta untuk **'{qr_data.get('content')}'**:"
                                else:
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
                            
                            if reply_content:
                                break
                        except Exception:
