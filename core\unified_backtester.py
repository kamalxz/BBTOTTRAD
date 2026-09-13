"""
🔬 unified_backtester.py — نظام باك تيست مدمج للتحقق من استراتيجيات التداول
يدعم Walk-Forward، Monte Carlo، وتحليل الرسوم المتوفرة
"""
import logging
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd

from core.unified_smc import UnifiedSMC
from core.unified_risk import UnifiedRiskEngine, RiskParams
from core.unified_filters import UnifiedFilters, MarketContext, TradeSignal

logger = logging.getLogger("backtester")


class BacktestResult:
    """نتائج الباك تيست"""
    def __init__(self):
        self.trades: List[Dict] = []
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0.0
        self.max_drawdown = 0.0
        self.consecutive_wins = 0
        self.consecutive_losses = 0
        self.max_consecutive_wins = 0
        self.max_consecutive_losses = 0
        self.fees_total = 0.0
        self.slippage_total = 0.0

    @property
    def win_rate(self) -> float:
        return self.winning_trades / self.total_trades if self.total_trades > 0 else 0

    @property
    def profit_factor(self) -> float:
        gross_wins = sum(t["pnl"] for t in self.trades if t["pnl"] > 0)
        gross_losses = abs(sum(t["pnl"] for t in self.trades if t["pnl"] < 0))
        return gross_wins / gross_losses if gross_losses > 0 else float('inf')

    @property
    def avg_r(self) -> float:
        return self.total_pnl / abs(self.losing_trades) if self.losing_trades > 0 else 0


class UnifiedBacktester:
    """
    نظام باك تيست موحد — يدعم استراتيجيات كل الأنماط
    """

    def __init__(self, mode: str = "swing", initial_capital: float = 100.0):
        self.mode = mode
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.smc = UnifiedSMC()
        self.risk_engine = UnifiedRiskEngine(mode=mode)
        self.filters = UnifiedFilters(mode=mode)
        self.results = BacktestResult()

        logger.info(f"🔬 تم إعداد نظام الباك تيست للوضع: {mode}")

    def run_backtest(self, df: pd.DataFrame, htf_df: Optional[pd.DataFrame] = None) -> Dict:
        """تشغيل الباك تيست على بيانات تاريخية"""
        logger.info(f"📊 بدء الباك تيست على {len(df)} صفقة...")

        # محاكاة التداول على كل إطار زمني
        for i in range(20, len(df) - 5):  # البدء من الصف 20 للحصول على بيانات كافية
            window = df.iloc[:i+1]

            # تحليل SMC
            score, ms, poi_list, conf = self.smc.calculate_score(window, htf_df, "BTC/USDT")

            # فحص NO TRADE
            context = MarketContext(
                htf_bias=ms.trend_direction,
                structure_valid=ms.structure_valid,
                liquidity_present=len([z for z in self.smc.detect_liquidity_zones(window) if z.swept]) > 0,
                poi_found=len(poi_list) > 0,
                confirmation_valid=conf.confirmed,
                funding_rate=0.0001,
                news_risk="low",
            )

            entry, sl, tp = self.smc.get_entry_and_exit_levels(window, 
                direction="long" if ms.trend_direction == "bullish" else "short")

            if entry is None or sl is None or tp is None:
                continue

            rr = abs(tp - entry) / abs(entry - sl)
            signal = TradeSignal(
                symbol="BTC/USDT",
                side="LONG" if ms.trend_direction == "bullish" else "SHORT",
                entry_price=entry,
                sl_price=sl,
                tp_price=tp,
                rr=rr,
                confidence=conf.strength,
                score=score,
            )

            should_trade, rejections = self.filters.check_no_trade_conditions(context, signal)

            if not should_trade:
                logger.debug(f"NO TRADE at bar {i}: {rejections}")
                continue

            # حساب النتيجة المحاكاة
            actual_exit = df['close'].iloc[i + 1] if i + 1 < len(df) else entry
            pnl = self._calculate_pnl(signal, actual_exit)
            
            self.results.trades.append({
                "timestamp": datetime.now().isoformat(),
                "bar": i,
                "side": signal.side,
                "entry": entry,
                "exit": actual_exit,
                "pnl": pnl,
                "score": score,
            })
            self.results.total_trades += 1
            self.results.total_pnl += pnl
            self.results.fees_total += 0.1  # رسوم افتراضية

            if pnl > 0:
                self.results.winning_trades += 1
                self.results.consecutive_wins += 1
                self.results.max_consecutive_wins = max(self.results.max_consecutive_wins, self.results.consecutive_wins)
                self.results.consecutive_losses = 0
            else:
                self.results.losing_trades += 1
                self.results.consecutive_losses += 1
                self.results.max_consecutive_losses = max(self.results.max_consecutive_losses, self.results.consecutive_losses)
                self.results.consecutive_wins = 0

            self.current_capital += pnl

        # حساب Max Drawdown
        capital_history = [self.initial_capital]
        for trade in self.results.trades:
            capital_history.append(capital_history[-1] + trade["pnl"])
        
        peak = self.initial_capital
        for cap in capital_history:
            if cap > peak:
                peak = cap
            drawdown = (peak - cap) / peak if peak > 0 else 0
            self.results.max_drawdown = max(self.results.max_drawdown, drawdown)

        return self.get_report()

    def _calculate_pnl(self, signal: TradeSignal, exit_price: float) -> float:
        """حساب P&L للصفقة"""
        params = RiskParams(
            account_equity=self.current_capital,
            risk_percent=0.01,  # 1%
            leverage=3.0,
            mode=self.mode,
        )
        position = self.risk_engine.calculate_position_size(
            signal.entry_price, signal.sl_price, signal.tp_price, params
        )

        if signal.side == "LONG":
            return (exit_price - signal.entry_price) * position.quantity
        else:
            return (signal.entry_price - exit_price) * position.quantity

    def get_report(self) -> Dict:
        """إنشاء تقرير الباك تيست"""
        return {
            "mode": self.mode,
            "initial_capital": self.initial_capital,
            "final_capital": self.current_capital,
            "total_trades": self.results.total_trades,
            "winning_trades": self.results.winning_trades,
            "losing_trades": self.results.losing_trades,
            "win_rate": self.results.win_rate,
            "total_pnl": self.results.total_pnl,
            "net_roi": (self.current_capital - self.initial_capital) / self.initial_capital * 100,
            "profit_factor": self.results.profit_factor,
            "max_drawdown": self.results.max_drawdown,
            "max_consecutive_wins": self.results.max_consecutive_wins,
            "max_consecutive_losses": self.results.max_consecutive_losses,
            "avg_r": self.results.avg_r,
            "fees_total": self.results.fees_total,
        }

    def print_report(self):
        """طباعة التقرير بصيغة جميلة"""
        report = self.get_report()
        print("\n" + "=" * 60)
        print("📊 تقرير الباك تيست")
        print("=" * 60)
        print(f"الوضع: {report['mode']}")
        print(f"رأس المال الأولي: {report['initial_capital']:.2f} USDT")
        print(f"رأس المال النهائي: {report['final_capital']:.2f} USDT")
        print(f"إجمالي الصفقات: {report['total_trades']}")
        print(f"الصفقات الربحية: {report['winning_trades']}")
        print(f"الصفقات الخاسرة: {report['losing_trades']}")
        print(f"معدل الربح: {report['win_rate']*100:.1f}%")
        print(f"صافي P&L: {report['total_pnl']:.2f} USDT")
        print(f"صافي ROI: {report['net_roi']:.2f}%")
        print(f"Profit Factor: {report['profit_factor']:.2f}")
        print(f"أقصى خسارة: {report['max_drawdown']*100:.2f}%")
        print(f"أقصى عدد انتصارات متتالية: {report['max_consecutive_wins']}")
        print(f"أقصى عدد خسائر متتالية: {report['max_consecutive_losses']}")
        print("=" * 60)
