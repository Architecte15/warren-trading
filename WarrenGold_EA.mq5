//+------------------------------------------------------------------+
//|                                                 WarrenGold_EA.mq5 |
//|                        Warren Trading — MASTERY TRIADE framework |
//+------------------------------------------------------------------+
//
// Starter skeleton for an XAU/USD Expert Advisor built around the
// discretionary rules documented for this project:
//   - Risk 1-2% of equity per trade, never more.
//   - Minimum accepted Risk:Reward ratio is 1:2.
//   - Three operating modes: AUTO, SEMI_AUTO, SIGNAL_ONLY.
//
// This file provides the risk-management and order-execution scaffolding
// that is broker/account agnostic. It does NOT yet implement full market-
// structure detection (POI, liquidity sweep, pinbar/engulfing) in MQL5 --
// that logic is currently prototyped and tested in Python
// (structure_analysis.py / backtest.py). Port the confirmed logic here
// once it is validated, or connect this EA to an external signal source
// via the JSON-bridge pattern already used by AvaBridgeEA.
//
// ALWAYS test on a demo account before enabling AUTO mode on a real one.
//+------------------------------------------------------------------+
#property copyright "Warren Trading"
#property version   "0.10"
#property strict

//--- Operating modes
enum ENUM_EA_MODE
{
   MODE_AUTO,          // Places and manages trades automatically
   MODE_SEMI_AUTO,     // Draws the setup on chart, requires manual confirmation to place the order
   MODE_SIGNAL_ONLY    // Only alerts / logs the setup, never touches the order book
};

//--- Inputs
input ENUM_EA_MODE InpMode            = MODE_SIGNAL_ONLY; // Operating mode
input double       InpRiskPercent     = 1.0;              // Risk per trade (% of equity), max 2.0
input double       InpMinRiskReward   = 2.0;               // Minimum accepted R:R ratio
input int          InpMagicNumber     = 20260001;           // Magic number for this EA's orders
input int          InpMaxSpreadPoints = 50;                 // Skip signals if spread exceeds this (points)
input bool         InpMoveToBreakEven = true;                // Move SL to entry once price has moved 1R in favor

//--- Globals
double g_riskPercentClamped;

//+------------------------------------------------------------------+
//| Expert initialization function                                    |
//+------------------------------------------------------------------+
int OnInit()
{
   // Hard safety clamp: never allow more than 2% risk regardless of input
   g_riskPercentClamped = MathMin(InpRiskPercent, 2.0);
   if(InpRiskPercent > 2.0)
      PrintFormat("WarrenGold_EA: InpRiskPercent (%.2f) clamped to 2.0 per the 1-2%% rule.", InpRiskPercent);

   PrintFormat("WarrenGold_EA initialized. Mode=%s Risk=%.2f%% MinRR=1:%.1f",
               EnumToString(InpMode), g_riskPercentClamped, InpMinRiskReward);
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                  |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   Print("WarrenGold_EA deinitialized.");
}

//+------------------------------------------------------------------+
//| Position sizing: mirrors position_sizing.py's calculate_lot_size  |
//+------------------------------------------------------------------+
double CalculateLotSize(double stopLossDistancePoints)
{
   double equity    = AccountInfoDouble(ACCOUNT_EQUITY);
   double riskMoney = equity * (g_riskPercentClamped / 100.0);

   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double point     = SymbolInfoDouble(_Symbol, SYMBOL_POINT);

   if(tickValue <= 0 || tickSize <= 0 || point <= 0)
   {
      Print("WarrenGold_EA: invalid symbol info, cannot size position.");
      return(0.0);
   }

   double valuePerPoint = (tickValue / tickSize) * point;
   double slValueTotal  = stopLossDistancePoints * valuePerPoint;
   if(slValueTotal <= 0) return(0.0);

   double rawLot = riskMoney / slValueTotal;

   double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double minLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);

   double steppedLot = MathFloor(rawLot / lotStep) * lotStep;
   steppedLot = MathMax(steppedLot, minLot);
   steppedLot = MathMin(steppedLot, maxLot);

   return(NormalizeDouble(steppedLot, 2));
}

//+------------------------------------------------------------------+
//| Validate Risk:Reward before allowing any trade                    |
//+------------------------------------------------------------------+
bool PassesRiskRewardFilter(double entry, double stopLoss, double takeProfit)
{
   double risk   = MathAbs(entry - stopLoss);
   double reward = MathAbs(takeProfit - entry);
   if(risk <= 0) return(false);
   double rr = reward / risk;
   return(rr >= InpMinRiskReward);
}

//+------------------------------------------------------------------+
//| Placeholder: plug in the ported structure/POI/pattern detection   |
//| logic here. Return true and fill entry/sl/tp if a setup is found. |
//+------------------------------------------------------------------+
bool DetectSetup(double &entry, double &stopLoss, double &takeProfit, bool &isBuy)
{
   // TODO: port detect_liquidity_sweep / is_pinbar / is_engulfing /
   // build_poi_zones from structure_analysis.py, or read a signal
   // produced by that Python script via a JSON file bridge (see
   // AvaBridgeEA for the existing bridge pattern).
   return(false);
}

//+------------------------------------------------------------------+
//| Execute a trade according to the current mode                     |
//+------------------------------------------------------------------+
void HandleSetup(double entry, double stopLoss, double takeProfit, bool isBuy)
{
   if(!PassesRiskRewardFilter(entry, stopLoss, takeProfit))
   {
      Print("WarrenGold_EA: setup rejected, below minimum R:R.");
      return;
   }

   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double slDistancePoints = MathAbs(entry - stopLoss) / point;
   double lot = CalculateLotSize(slDistancePoints);
   if(lot <= 0)
   {
      Print("WarrenGold_EA: computed lot size is zero, skipping.");
      return;
   }

   string msg = StringFormat("%s setup: entry=%.2f SL=%.2f TP=%.2f lot=%.2f",
                              isBuy ? "BUY" : "SELL", entry, stopLoss, takeProfit, lot);

   switch(InpMode)
   {
      case MODE_SIGNAL_ONLY:
         Print("SIGNAL: " + msg);
         Alert(msg);
         break;

      case MODE_SEMI_AUTO:
         // Draw the levels on chart and alert; a human confirms manually.
         Print("SEMI-AUTO (manual confirmation required): " + msg);
         Alert(msg);
         // TODO: draw horizontal lines for entry/SL/TP using ObjectCreate.
         break;

      case MODE_AUTO:
         Print("AUTO: placing order — " + msg);
         // TODO: call CTrade::Buy / CTrade::Sell (Trade.mqh) with
         // lot, stopLoss, takeProfit, magic = InpMagicNumber.
         break;
   }
}

//+------------------------------------------------------------------+
//| Expert tick function                                              |
//+------------------------------------------------------------------+
void OnTick()
{
   double spreadPoints = (double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   if(spreadPoints > InpMaxSpreadPoints)
      return;

   double entry, stopLoss, takeProfit;
   bool isBuy;

   if(DetectSetup(entry, stopLoss, takeProfit, isBuy))
      HandleSetup(entry, stopLoss, takeProfit, isBuy);

   if(InpMoveToBreakEven)
      ManageBreakEven();
}

//+------------------------------------------------------------------+
//| Move SL to entry once a trade has run 1R in favor                 |
//+------------------------------------------------------------------+
void ManageBreakEven()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(!PositionSelectByTicket(ticket)) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) continue;

      double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl         = PositionGetDouble(POSITION_SL);
      double currentPrice = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY)
                              ? SymbolInfoDouble(_Symbol, SYMBOL_BID)
                              : SymbolInfoDouble(_Symbol, SYMBOL_ASK);

      double initialRisk = MathAbs(openPrice - sl);
      if(initialRisk <= 0) continue;

      bool isBuy = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY);
      double movedInFavor = isBuy ? (currentPrice - openPrice) : (openPrice - currentPrice);

      if(movedInFavor >= initialRisk && MathAbs(sl - openPrice) > _Point)
      {
         // TODO: call CTrade::PositionModify(ticket, openPrice, PositionGetDouble(POSITION_TP));
         PrintFormat("WarrenGold_EA: ticket %I64u reached 1R, move SL to break-even (%.2f).", ticket, openPrice);
      }
   }
}
//+------------------------------------------------------------------+
