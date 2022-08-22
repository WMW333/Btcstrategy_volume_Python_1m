import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import csv
%matplotlib inline
pd.options.display.max_rows = 99999

def import_file(filename):
    dati = pd.read_csv(r'C:\Users\Arco\Desktop\BTCUSDT_Binance_futures_data_minute_1.csv', parse_dates = ["date"]) #, "ora"])
    dati.drop(0, inplace=True)
    dati["timestamp"] = pd.to_numeric(dati["unix"])
    dati.sort_values(by=["timestamp"], ascending = True, inplace=True)
    dati.drop(["unix"], axis = 1, inplace=True)
    dati.set_index("date", inplace = True)
    dati.drop(["tradecount::"], axis = 1, inplace=True)
    dati.drop(["timestamp"], axis = 1, inplace=True)
    dati.drop(["symbol"], axis = 1, inplace=True)
    dati.drop(["VolumeUsdt"], axis = 1, inplace=True)
    return dati
FILENAME = "BTCUSDT_Binance_futures_data_minute_1.csv"
dati = import_file(FILENAME)

def avgprice(O,C,L,H):
    avg = ((O + C + L + H) / 4)
    return avg
dati["avg"] = avgprice(dati.open, dati.low, dati.close, dati.high)

dati['Range'] = round(dati.high - dati.low, 2)
dati['Body'] = abs(dati.open - dati.close,)
dati['CO'] = round(dati.close - dati.open, 2)
dati['OL'] = round(dati.open - dati.low, 2)
dati['HO'] = round(dati.high - dati.open, 2)
dati['LC'] = round(dati.low - dati.close, 2)
dati['HC'] = round(dati.high - dati.close, 2)
dati['BodyPerc'] = (dati.close - dati.open) / dati.close * 100

def atr():
    df = pd.concat([dati.Range, dati.HC, dati.LC] , axis = 1)
    TrueRange = np.max(df, axis = 1)
    atr = TrueRange.rolling(14).mean()
    return atr

dati["atr"] = atr()


#Inserire Soglie Spike, Volumi in BTC e ATR
SogliaSpikeUp = 0.28
SogliaSpikeDown = - 0.28
SogliaVolumi = 1910
SogliaATR = 100


spikeDown = (dati.low - dati.close) / dati.close * 100
spikeUp = (dati.high - dati.close) / dati.close * 100
dati["SpikeUp"] = (dati.high - dati.close) / dati.close * 100
dati["SpikeDown"] = (dati.low - dati.close) / dati.close * 100
dati["SpikeUp_TF"] = np.where((dati.SpikeUp.shift(1) > SogliaSpikeUp) & (dati.SpikeDown.shift(1) > -0.03) & 
                              (dati.SpikeUp.shift(1) < 0.49), 1,0)
dati["SpikeDown_TF"] = np.where((dati.SpikeDown.shift(1) < SogliaSpikeDown) & (dati.SpikeUp.shift(1) < 0.03) &
                                (dati.SpikeUp.shift(1) > - 0.49), 1,0)

dati["Volume_TF"] = np.where((dati.VolumeBTC.shift(1) > SogliaVolumi), 1,0)


conditionlist = [
((dati["Volume_TF"] == 1) & (dati["SpikeUp_TF"] == 1) & (dati["BodyPerc"] <= 0.29) & (dati["BodyPerc"] >= -0.1) &
(dati["atr"] < SogliaATR)) , 
((dati["Volume_TF"] == 1) & (dati["SpikeDown_TF"] == 1) & (dati["BodyPerc"] >= -0.29) & (dati["BodyPerc"] <= 0.1) &
(dati["atr"] < SogliaATR)) , 
((dati["Volume_TF"] == 1) & (dati["SpikeDown_TF"] == 1) & (dati["SpikeUp_TF"] == 1))]
#(dati["Volume_TF"] == 0)]  
choicelist = [2, 1, 0] # 0 = niente , 1 = long, 2 = Short
dati["Apri_Posizione"] = np.select(conditionlist, choicelist, default=0)


#Inserire $ per ogni posizione da aprire e fees per entrata e uscita
money = 10000
fees = 0.0

dati["stocks"] = (money / dati.open).apply(lambda x: round(x,6)) #qtà in btc
#memory_avg["position"] = np.where((bt.Apri_Posizione == 1) &
                                #(memory_avg.open <= memory_avg.avgpr.shift(1)),1,0)

dati["entry"] = np.where((dati.Apri_Posizione == 1) | (dati.Apri_Posizione == 2),
                         dati.open, 0) #np.where(memory_avg.open <= memory_avg.dap.shift(1), 
                                #memory_avg.open, memory_avg.open)

#dati["exit"] = np.where((dati.Apri_Posizione==1)#(dati.high.shift(-3)
conditionexit = [
(dati["Apri_Posizione"] == 1), 
(dati["Apri_Posizione"] == 2), 
(dati["Apri_Posizione"] == 0)]
#(dati["Volume_TF"] == 0)]  
choiceexit = [dati.close.shift(-5), dati.close.shift(-5), 0] # 0 = niente , 1 = nuovo high.shift(-n), 2 = nuovo.low.shift(n)
dati["exit"] = np.select(conditionexit, choiceexit, default=0)
                   

dati["trade"] = (dati.exit - dati.entry) * dati.stocks #calcoliamo l'ammontare del nostro guadagno o perdita

dati["gainLong"] = np.where((dati.Apri_Posizione == 1), (dati.trade), 0)
gainshort = ((dati.entry - dati.exit) * dati.stocks)
dati["gainShort"] = np.where((dati.Apri_Posizione == 2), (gainshort), 0)
dati["Fees"] = np.where((dati.Apri_Posizione != 0), ((money * fees) / 100), 0)
dati["GainCumNet"] = (dati.gainShort + dati.gainLong) - dati.Fees
dati["equity"] = dati.GainCumNet.cumsum()


################

ROI = round(((dati.equity.iloc[724576] / money) * 100),2)
print("ROI = " + str(ROI) + "%")

########
strategy = dati.copy()

strategy.drop(["CO", "avg", "Range", "OL", "HO", "LC", "atr", 
              "BodyPerc", "SpikeUp", "SpikeDown", "Body"], axis = 1, inplace=True)
              
SL = - 29
TP = 59
Shortstoploss = (((strategy.entry - strategy.high.shift(-10)) * strategy.stocks))
Shorttakeprofit = ((((strategy.entry - strategy.low.shift(-10)) * strategy.stocks)))
Longstoploss = ((((strategy.low.shift(-10)) - dati.entry) * dati.stocks))
Longtakeprofit = ((((strategy.high.shift(-10)) - strategy.entry) * strategy.stocks))
strategy["LongSL"] = np.where((dati.Apri_Posizione == 2) &
                              (Longstoploss < SL) , "SL", 0)
strategy["LongTP"] = np.where((dati.Apri_Posizione == 2) & 
                               (Longtakeprofit > TP) , "TP", 0)
strategy["ShortSL"] = np.where((dati.Apri_Posizione == 1) &
                               (Shortstoploss < SL) , "SL", 0)
strategy["ShortTP"] = np.where((dati.Apri_Posizione == 1)&
                               (Shorttakeprofit > TP) , "TP", 0)
#strategy.head()

#######################

Posizioni = []

for x in dati["Apri_Posizione"]:
    if x == 2:
        Posizioni.append("Short")
    elif x == 1:
        Posizioni.append("Long")
    else:
        Posizioni.append("N")
        
strategy["Posizioni"] = Posizioni
#strategy["GainCum"] = np.where(strategy["GainCum"] != 0, strategy["GainCum"], np.nan)

#strategy.Apri_Posizione[strategy.Apri_Posizione != 0].dropna()
strategy["Posizioni"].value_counts()


percGain = strategy.GainCumNet[strategy.GainCumNet != 0].dropna()
percGain.describe()
