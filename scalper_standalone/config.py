# config.py - إعدادات استراتيجية السكالبر المتقدمة

SYMBOLS_CONFIG = {
    # 🏆 العملات القيادية (LEADER)
    'BTC/USDT:USDT': {'type': 'LEADER', 'volatility': 'low'},
    'ETH/USDT:USDT': {'type': 'LEADER', 'volatility': 'low'},
    'SOL/USDT:USDT': {'type': 'LEADER', 'volatility': 'low'},
    'BNB/USDT:USDT': {'type': 'LEADER', 'volatility': 'low'},
    'LTC/USDT:USDT': {'type': 'LEADER', 'volatility': 'low'},
    'XRP/USDT:USDT': {'type': 'LEADER', 'volatility': 'medium'},
    
    # 📈 عملات النمو العالي (HIGH_GROWTH)
    'ADA/USDT:USDT': {'type': 'HIGH_GROWTH', 'volatility': 'medium'},
    'AVAX/USDT:USDT': {'type': 'HIGH_GROWTH', 'volatility': 'medium'},
    'DOT/USDT:USDT': {'type': 'HIGH_GROWTH', 'volatility': 'medium'},
    'HBAR/USDT:USDT': {'type': 'HIGH_GROWTH', 'volatility': 'medium'},
    'ARB/USDT:USDT': {'type': 'HIGH_GROWTH', 'volatility': 'high'},
    'OP/USDT:USDT': {'type': 'HIGH_GROWTH', 'volatility': 'high'},
    'LINK/USDT:USDT': {'type': 'HIGH_GROWTH', 'volatility': 'medium'},
    'ONDO/USDT:USDT': {'type': 'HIGH_GROWTH', 'volatility': 'high'},
    'MKR/USDT:USDT': {'type': 'HIGH_GROWTH', 'volatility': 'medium'},
    'TAO/USDT:USDT': {'type': 'HIGH_GROWTH', 'volatility': 'high'},
    'RNDR/USDT:USDT': {'type': 'HIGH_GROWTH', 'volatility': 'high'},
    'FET/USDT:USDT': {'type': 'HIGH_GROWTH', 'volatility': 'high'},
    
    # 🚀 عملات الزخم (MOMENTUM)
    'XLM/USDT:USDT': {'type': 'MOMENTUM', 'volatility': 'medium'},
    'MATIC/USDT:USDT': {'type': 'MOMENTUM', 'volatility': 'medium'},
}

CORRELATION_GROUPS = {
    'LAYER1': [
        'BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT', 
        'BNB/USDT:USDT', 'ADA/USDT:USDT', 'LTC/USDT:USDT',
        'DOT/USDT:USDT', 'AVAX/USDT:USDT', 'HBAR/USDT:USDT'
    ],
    'L2': ['ARB/USDT:USDT', 'OP/USDT:USDT', 'MATIC/USDT:USDT'],
    'ORACLES_RWA': ['LINK/USDT:USDT', 'ONDO/USDT:USDT', 'MKR/USDT:USDT'],
    'AI_DEPIN': ['TAO/USDT:USDT', 'RNDR/USDT:USDT', 'FET/USDT:USDT'],
    'PAYMENTS': ['XRP/USDT:USDT', 'XLM/USDT:USDT']
}

SCALPER_CONFIG = {
    'initial_capital': 1000,
    'max_leverage': 10.0,
    'risk_per_trade': 0.02,  # 2% risk per trade
    'timeframes': {'entry': '5m', 'trend': '15m'},
    'filters': {
        'min_adx': 35,
        'min_volume_ratio': 1.5,
        'require_bos': True,
        'require_fvg': True,
    },
    'exit_strategy': {
        'tp1_pct': 0.40, 
        'tp1_level': 0.006,    # 40% at 0.6% gain
        'tp2_pct': 0.35, 
        'tp2_level': 0.012,    # 35% at 1.2% gain
        'tp3_pct': 0.25, 
        'tp3_trailing': True,  # Let runner go with trailing stop
        'sl_atr_mult': 1.5
    }
}
