import time
import tweepy
import os
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# === CONFIGURAÇÕES ===
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CRIPTO = "bitcoin"
INTERVALO_MINUTOS = 30

# === PREÇO ATUAL DA COIN ===
def get_preco_atual(cripto="bitcoin", moeda="usd"):
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={cripto}&vs_currencies={moeda}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data[cripto][moeda]
    except Exception as e:
        print(f"Erro ao obter preço: {e}")
        return None

# === ANALISAR SENTIMENTO DOS TWEETS ===
def analisar_sentimento():
    client = tweepy.Client(bearer_token=BEARER_TOKEN)
    query = f"{CRIPTO}"
    resposta = client.search_recent_tweets(query=query, max_results=50)

    if not resposta.data:
        return None, "❌ Nenhum tweet encontrado."

    tweets = [tweet.text for tweet in resposta.data]
    analisador = SentimentIntensityAnalyzer()
    scores = [analisador.polarity_scores(t)['compound'] for t in tweets]
    media = sum(scores) / len(scores)

    if media > 0.1:
        sinal = "COMPRAR"
    elif media < -0.1:
        sinal = "VENDER"
    else:
        sinal = "NEUTRO"

    return media, sinal

# === ENVIAR MENSAGEM PARA TELEGRAM ===
def enviar_telegram(texto):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": texto}
    requests.post(url, data=data)

# === LOOP PRINCIPAL ===
while True:
    print(f"\n🔁 Verificando sentimento sobre '{CRIPTO}'...")
    try:
        media, sinal = analisar_sentimento()
        preco_atual = get_preco_atual(CRIPTO)

        if preco_atual is None:
            enviar_telegram("❌ Erro ao obter preço atual. A análise foi ignorada.")
            time.sleep(INTERVALO_MINUTOS * 60)
            continue

        mensagem = f"🔎 Criptomoeda: {CRIPTO}\n🧠 Sentimento: {media:.3f}\n📊 Sinal: {sinal}"

        if sinal == "COMPRAR":
            if not os.path.exists(ARQUIVO_PRECO):
                with open(ARQUIVO_PRECO, "w") as f:
                    f.write(str(preco_atual))
                mensagem += f"\n💵 Compra registrada a ${preco_atual:.2f}"
            else:
                mensagem += "\n📌 Já estamos com uma posição comprada. Aguardando sinal de venda."

        elif sinal == "VENDER":
            if os.path.exists(ARQUIVO_PRECO):
                with open(ARQUIVO_PRECO, "r") as f:
                    preco_compra = float(f.read())
                lucro = preco_atual - preco_compra
                perc = (lucro / preco_compra) * 100
                resultado = "💰 Lucro" if lucro > 0 else "📉 Prejuízo"
                mensagem += f"\n{resultado}: {perc:.2f}%"
                os.remove(ARQUIVO_PRECO)
            else:
                mensagem += "\n⚠️ Nenhuma compra registrada. Nada a vender."

        else:
            mensagem += "\n⚖️ Tendência neutra. Sem ações por enquanto."

        mensagem += f"\n⏱️ Próxima análise em {INTERVALO_MINUTOS} minutos."
        print(mensagem)
        enviar_telegram(mensagem)

    except Exception as e:
        print("❌ Erro:", str(e))
        enviar_telegram("❌ Ocorreu um erro ao processar o sinal.")

    time.sleep(INTERVALO_MINUTOS * 60)
