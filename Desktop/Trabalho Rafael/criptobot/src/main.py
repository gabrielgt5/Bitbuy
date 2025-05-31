import os
import time
import requests
import praw
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from dotenv import load_dotenv

load_dotenv()

# Variáveis de ambiente
CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
USER_AGENT = os.getenv("REDDIT_USER_AGENT")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CRIPTO = os.getenv("CRIPTO", "bitcoin")
INTERVALO_MIN = 15
ARQUIVO_PRECO = "preco_compra.txt"

# Inicializa o Reddit e o Analisador
reddit = praw.Reddit(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    user_agent=USER_AGENT
)
analisador = SentimentIntensityAnalyzer()

def get_posts(subreddit_name="CryptoCurrency", termo="bitcoin", limite=30):
    subreddit = reddit.subreddit(subreddit_name)
    posts = subreddit.search(termo, limit=limite)
    return [post.title + " " + post.selftext for post in posts]

def analisar(posts):
    scores = [analisador.polarity_scores(p)['compound'] for p in posts]
    return sum(scores) / len(scores) if scores else 0

def get_preco():
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={CRIPTO}&vs_currencies=usd"
    r = requests.get(url)
    return r.json()[CRIPTO]["usd"]

def enviar_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

while True:
    print(f"\n🔁 Verificando sentimento sobre '{CRIPTO}'...")
    try:
        posts = get_posts(termo=CRIPTO)
        media = analisar(posts)
        preco = get_preco()

        if media > 0.1:
            sinal = "COMPRAR"
        elif media < -0.1:
            sinal = "VENDER"
        else:
            sinal = "NEUTRO"

        mensagem = f"🔎 Criptomoeda: {CRIPTO}\n🧠 Sentimento: {media:.3f}\n📈 Preço atual: ${preco:.2f}\n📊 Sinal: {sinal}"

        if sinal == "COMPRAR":
            if not os.path.exists(ARQUIVO_PRECO):
                with open(ARQUIVO_PRECO, "w") as f:
                    f.write(str(preco))
                mensagem += f"\n💵 Compra registrada a ${preco:.2f}"
            else:
                mensagem += "\n⏳ Já estamos com uma posição aberta. Aguardando venda."

        elif sinal == "VENDER":
            if os.path.exists(ARQUIVO_PRECO):
                with open(ARQUIVO_PRECO, "r") as f:
                    preco_compra = float(f.read())
                lucro = preco - preco_compra
                perc = (lucro / preco_compra) * 100
                resultado = "💰 Lucro" if lucro > 0 else "📉 Prejuízo"
                mensagem += f"\n{resultado}: {perc:.2f}%"
                os.remove(ARQUIVO_PRECO)
            else:
                mensagem += "\n⚠️ Nenhuma compra registrada. Ignorando venda."

        else:
            mensagem += "\n⚖️ Tendência neutra. Nenhuma ação tomada."

        mensagem += f"\n⏱️ Próxima análise em {INTERVALO_MIN} minutos."
        print(mensagem)
        enviar_telegram(mensagem)

    except Exception as e:
        print("❌ Erro:", e)
        enviar_telegram("❌ Ocorreu um erro ao processar a análise.")

    time.sleep(INTERVALO_MIN * 60)
