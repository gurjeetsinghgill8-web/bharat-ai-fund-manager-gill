# Standard Ticker list for Bharat AI Fund Manager Gill
# Indian Stock Tickers (Yahoo Finance requires '.NS' suffix for National Stock Exchange of India)

STOCKS = {
    "Large Cap": [
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", 
        "BHARTIARTL.NS", "SBIN.NS", "ITC.NS", "HINDUNILVR.NS", "LICI.NS", 
        "HCLTECH.NS", "LT.NS", "AXISBANK.NS", "SUNPHARMA.NS", "KOTAKBANK.NS", 
        "MARUTI.NS", "COALINDIA.NS", "NTPC.NS", "ULTRACEMCO.NS", "TITAN.NS", 
        "ONGC.NS", "ASIANPAINT.NS", "ADANIENT.NS", "POWERGRID.NS", "TATASTEEL.NS", 
        "BAJFINANCE.NS", "BAJAJFINSV.NS", "NESTLEIND.NS", "JSWSTEEL.NS", "M&M.NS", 
        "GRASIM.NS", "TATACONSUM.NS", "TECHM.NS", "WIPRO.NS", "CIPLA.NS", 
        "APOLLOHOSP.NS", "HINDALCO.NS", "SBILIFE.NS", "DRREDDY.NS", "ADANIPORTS.NS", 
        "BPCL.NS", "EICHERMOT.NS", "DIVISLAB.NS", "HEROMOTOCO.NS", "INDUSINDBK.NS", 
        "LTIM.NS", "SHRIRAMFIN.NS", "BRITANNIA.NS", "TATACOMM.NS"
    ],
    "Mid Cap": [
        "PAGEIND.NS", "ESCORTS.NS", "CUMMINSIND.NS", "CONCOR.NS", "BHARATFORG.NS", 
        "VOLTAS.NS", "RECLTD.NS", "PFC.NS", "TATAPOWER.NS", "CHOLAFIN.NS", 
        "MRF.NS", "ASHOKLEY.NS", "MAXHEALTH.NS", "BALKRISIND.NS", "POLYCAB.NS", 
        "BHEL.NS", "TRENT.NS", "BEL.NS", "HAL.NS", "GMRINFRA.NS", "COFORGE.NS", 
        "PERSISTENT.NS", "DIXON.NS", "ASTRAL.NS", "AUROPHARMA.NS", "BANDHANBNK.NS", 
        "FEDERALBNK.NS", "IDFCFIRSTB.NS", "JUBLFOOD.NS", "LICHSGFIN.NS", "L&TFH.NS", 
        "NMDC.NS", "SAIL.NS", "TATAELXSI.NS", "YESBANK.NS", "IRFC.NS", "RVNL.NS", 
        "OBEROIRLTY.NS", "PIIND.NS", "PETRONET.NS", "IPCALAB.NS", "IGL.NS"
    ],
    "Small Cap": [
        "CDSL.NS", "ANGELONE.NS", "BSE.NS", "HUDCO.NS", "IRCON.NS", "SJVN.NS", 
        "SUZLON.NS", "NBCC.NS", "TRIDENT.NS", "ZENSARTECH.NS", "HFCL.NS", 
        "IFCI.NS", "TATAINVEST.NS", "IEX.NS", "TATACHEM.NS", "RADICO.NS", 
        "PNB.NS", "MCX.NS", "SIGNATURE.NS", "BECTORFOOD.NS", "ROUTE.NS", 
        "HAPPYFORGE.NS", "MAPMYINDIA.NS", "SHYAMMETL.NS", "KARURVYSYA.NS", "RAMCOCEM.NS", 
        "EASEMYTRIP.NS", "INFIBEAM.NS", "CENTURYTEX.NS", "NCC.NS", "IRCTC.NS", 
        "NHPC.NS", "SWANENERGY.NS", "WELCORP.NS", "GPIL.NS", "PPLPHARMA.NS"
    ]
}

def get_all_tickers():
    all_tickers = []
    for cap, tickers in STOCKS.items():
        all_tickers.extend(tickers)
    return list(set(all_tickers))

def get_category(ticker):
    for cap, tickers in STOCKS.items():
        if ticker in tickers:
            return cap
    return "Unknown"
