import os
import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_community.tools import TavilySearchResults
from web3 import Web3

# Load .env
load_dotenv()

app = Flask(__name__)
CORS(app) # Biar Web/APK bisa akses server ini

RPC_URL = "https://eth-mainnet.g.alchemy.com/v2/alch_5iYsxcDP0cS2bzLC6Rt8e"
w3 = Web3(Web3.HTTPProvider(RPC_URL))
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

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
    description="Gunakan alat ini HANYA untuk mencari informasi luar seperti harga HP, berita, produk, atau fakta dunia."
)

tools = [get_eth_balance, get_crypto_price, web_search_tool]
llm_with_tools = llm.bind_tools(tools)

tool_map = {
    "get_eth_balance": get_eth_balance,
    "get_crypto_price": get_crypto_price,
    "tavily_search_results_json": web_search_tool
}

def process_agent_message(user_prompt: str) -> str:
    ai_response = llm_with_tools.invoke([
        ("system", SYSTEM_PROMPT),
        ("user", user_prompt)
    ])

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
        return final_response.content
    else:
        return ai_response.content

# Endpoint API Chat
@app.route('/chat', methods=['POST'])
def chat_endpoint():
    data = request.get_json()
    user_message = data.get('message', '')
    if not user_message:
        return jsonify({'error': 'Pesan kosong'}), 400
    
    reply = process_agent_message(user_message)
    return jsonify({'reply': reply})

# Route Utama
@app.route('/', methods=['GET'])
def home():
    return "Server AI nex Aktif!"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
