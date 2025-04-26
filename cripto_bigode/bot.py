import ccxt
import pandas as pd
import ta
import time
import telebot
from datetime import datetime
import csv
import os

# 🧠 Configurações do bot
TOKEN = '8165557546:AAEiKshBi7tir2EjAy62NDa7mvXGr4h19Lg'
CHAT_ID = '2091781134'

bot = telebot.TeleBot(TOKEN)
exchange = ccxt.binance()

# 🔍 Pares para acompanhar
symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT']
timeframe = '1h'

open_trades = {}
csv_file = 'historico_operacoes.csv'

# 📋 Criar CSV se não existir
if not os.path.isfile(csv_file):
    with open(csv_file, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Data Entrada', 'Data Fechamento', 'Par', 'Direção', 'Resultado', 'Lucro/Prejuízo'])

# 🔔 Mensagem de inicialização
bot.send_message(CHAT_ID, "🚀 Bot de Trade iniciado com sucesso!\nAguardando sinais...")

def get_data(symbol):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)

    df['EMA9'] = ta.trend.ema_indicator(df['close'], window=9)
    df['EMA21'] = ta.trend.ema_indicator(df['close'], window=21)
    df['RSI'] = ta.momentum.rsi(df['close'], window=14)

    return df

def save_trade(entry_time, close_time, pair, direction, result, pl_value):
    with open(csv_file, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([entry_time, close_time, pair, direction, result, round(pl_value, 2)])

def check_signals():
    global open_trades

    for symbol in symbols:
        df = get_data(symbol)
        last = df.iloc[-1]
        prev = df.iloc[-2]
        price = last['close']

        if symbol not in open_trades:
            # 📈 Entrada de compra
            if prev['EMA9'] < prev['EMA21'] and last['EMA9'] > last['EMA21'] and last['RSI'] > 50:
                sl = price * 0.98
                tp = price * 1.02
                open_trades[symbol] = {
                    'entry': price,
                    'sl': sl,
                    'tp': tp,
                    'time': datetime.now(),
                    'side': 'buy'
                }
                bot.send_message(CHAT_ID, f"🟢 NOVA COMPRA {symbol}\n💰 Entrada: {price:.2f}\n🎯 TP: {tp:.2f}\n🛑 SL: {sl:.2f}")
            
            # 🔻 Entrada de venda
            elif prev['EMA9'] > prev['EMA21'] and last['EMA9'] < last['EMA21'] and last['RSI'] < 50:
                sl = price * 1.02
                tp = price * 0.98
                open_trades[symbol] = {
                    'entry': price,
                    'sl': sl,
                    'tp': tp,
                    'time': datetime.now(),
                    'side': 'sell'
                }
                bot.send_message(CHAT_ID, f"🔴 NOVA VENDA {symbol}\n💰 Entrada: {price:.2f}\n🎯 TP: {tp:.2f}\n🛑 SL: {sl:.2f}")

def update_open_trades():
    global open_trades
    symbols_to_remove = []

    for symbol, trade in open_trades.items():
        df = get_data(symbol)
        last = df.iloc[-1]
        price = last['close']
        entry = trade['entry']
        sl = trade['sl']
        tp = trade['tp']
        side = trade['side']

        if side == 'buy':
            if price >= tp:
                bot.send_message(CHAT_ID, f"✅ LUCRO: {symbol} atingiu o TP ({tp:.2f})\n🏆 Lucro: {tp-entry:.2f}")
                save_trade(trade['time'], datetime.now(), symbol, side, 'Ganho', tp-entry)
                symbols_to_remove.append(symbol)
            elif price <= sl:
                bot.send_message(CHAT_ID, f"❌ STOP: {symbol} atingiu o SL ({sl:.2f})\n💔 Prejuízo: {entry-sl:.2f}")
                save_trade(trade['time'], datetime.now(), symbol, side, 'Perda', sl-entry)
                symbols_to_remove.append(symbol)
            else:
                bot.send_message(CHAT_ID, f"📊 {symbol} (Compra) aberto\nAtual: {price:.2f} | Entrada: {entry:.2f} | TP: {tp:.2f} | SL: {sl:.2f}")

        elif side == 'sell':
            if price <= tp:
                bot.send_message(CHAT_ID, f"✅ LUCRO: {symbol} atingiu o TP ({tp:.2f})\n🏆 Lucro: {entry-tp:.2f}")
                save_trade(trade['time'], datetime.now(), symbol, side, 'Ganho', entry-tp)
                symbols_to_remove.append(symbol)
            elif price >= sl:
                bot.send_message(CHAT_ID, f"❌ STOP: {symbol} atingiu o SL ({sl:.2f})\n💔 Prejuízo: {sl-entry:.2f}")
                save_trade(trade['time'], datetime.now(), symbol, side, 'Perda', entry-sl)
                symbols_to_remove.append(symbol)
            else:
                bot.send_message(CHAT_ID, f"📊 {symbol} (Venda) aberto\nAtual: {price:.2f} | Entrada: {entry:.2f} | TP: {tp:.2f} | SL: {sl:.2f}")

    # Remover operações encerradas
    for symbol in symbols_to_remove:
        del open_trades[symbol]

# 🔁 LOOP principal
while True:
    check_signals()
    update_open_trades()
    time.sleep(900)  # 15 minutos
