# Trade-Bot-Hyperliquid
Independently analyze ROI, win rate, and PnL using the public Hyperliquid API, detect martingale/grid recovery strategies, and assess maximum drawdown and risk-adjusted returns. Read-only terminal checker — no trading, no API keys. Unofficial community project, not affiliated with Hyperliquid.
<div align="center">

# 🔐 Hyperliquid Trade Bot

### Independent ROI, PnL and martingale analysis in your terminal.

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Textual](https://img.shields.io/badge/TUI-textual-7C3AED.svg)](https://textual.textualize.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Hyperliquid](https://img.shields.io/badge/Hyperliquid-L1-9B59B6.svg)](https://hyperliquid.xyz/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](./README.md)

**A read-only verification & monitoring terminal for Hyperliquid trading.**
Don't blindly mirror a leaderboard address — *audit it first.*

</div>

---

## 📖 Overview

**Hyperliquid Trade Bot** is a keyboard-driven **terminal user interface (TUI)** for
**perpetual futures trading due diligence**: it performs an **independent verification of
ROI, win rate, and PnL** for any trader on the Hyperliquid leaderboard, recomputed from the
public Hyperliquid API — *before* you decide to mirror their positions.

Raw leaderboard ROI hides a lot: martingale sizing, lucky single-trade pumps, wash-trading,
fee-ignorance, and drawdowns masked by spot/perp swaps. The verifier analyzes a trader's
**full fill history** and reconstructs the **equity curve from on-chain fills**, surfacing the
metrics that actually predict trading safety: **max drawdown and risk-adjusted returns
(Sharpe/Sortino)**, **martingale and grid recovery pattern detection**, outlier dependence,
**position sizing consistency and leverage analysis**, and a significance test that helps you
**spot inflated track records and survivorship bias**.

> ⚠️ **Read-only by design.** This verifier never places orders. It is an *audit and monitoring*
> layer — a **read-only terminal checker: no trading, no keys** 

---

## ✨ Features

| Area | What you get |
|------|--------------|
| 🕵️ **Trader Verification** | Independent re-derivation of ROI / PnL / win-rate / drawdown from public Hyperliquid fills. |
| 🧠 **Manipulation Heuristics** | Martingale detection, outlier-dependence score, wash-trade flags, survivorship warnings. |
| 📈 **Live Monitor** | Watch a verified trader's open positions, equity curve, and fills update in real time. |
| 🧮 **Risk Simulator** | Project trade outcomes under configurable size-scaling, leverage caps and stop-loss. |
| 📋 **Trade Log** | A local, append-only audit log of every fill you *would have* mirrored (paper-trail). |
| 🎛️ **Dashboard** | Single-pane-of-glass TUI: stats panel, trader table, positions, sparkline equity. |
| ⌨️ **Keyboard-first** | 100% navigable from the home row. Vim-style bindings. No mouse required. |
| 🌑 **Theming** | Light / dark / hyperliquid-themed palettes. |

---

## 🖥️ Screenshots

> The verifier runs as a live TUI. Below is a static ASCII preview of the dashboard.

```
 ╔══════════════════════════════════════════════════════════════════════════════════════════════╗
 ║ 🔐 Hyperliquid Trade Bot                          [1]Dash [2]Traders [3]Verify [4]Pos ║
 ╠══════════════════════════════════════════════════════════════════════════════════════════════╣
 ║ VERIFIED TRADER   0x7f3a...c4e1     🟠 REVIEW      Verified 2026-07-19 14:02 UTC             ║
 ║ ───────────────────────────────────────────────────────────────────────────────────────────  ║
 ║  Headline ROI        +412.8%       Verified ROI        +318.4%   Δ +94.4pp   ⚠ INFLATED     ║
 ║  Win rate             71.3%        Fee-adj. win rate    64.9%                                ║
 ║  Profit factor        2.84         Martingale score     0.43   🟠 MODERATE                   ║
 ║  Max drawdown        −31.2%       Outlier dependence   32.0%   🟠 MODERATE                   ║
 ║  Trades (90d)          1,284       Statistical edge     p=0.013  ✅ SIGNIFICANT              ║
 ║                                                                                              ║
 ║  EQUITY CURVE (90d)                            ▁▂▃▄▆▇▇█▇▇▆▇█▇▆▇█▇▆▇▇█▇▆▇▆▇▆▇▇█▇▆▇▆    ║
 ║                                                                                              ║
 ║  TOP OPEN POSITIONS                                                                          ║
 ║  Symbol    Side   Size ($)     Entry      Mark       uPnL ($)   Leverage   Liquidation       ║
 ║  BTC-PERP  LONG   142,300.00   67,210.5   68,015.2   +1,702.7   5.0x       54,180.0          ║
 ║  ETH-PERP  LONG    88,710.00    3,418.2    3,462.1     +1,138.4   4.0x       2,724.0         ║
 ║  SOL-PERP  SHORT   31,400.00     178.4      174.9       +618.3    3.0x         —             ║
 ║                                                                                              ║
 ║  TRADE LOG (paper trail)              q Quit  r Re-verify  c trade config  ? Help       ║
 ╚══════════════════════════════════════════════════════════════════════════════════════════════╝
```

---

## 🚀 Quick start

```bash
git clone https://github.com/sonicmountain/trade-bot-hyperliquid.git
cd trade-bot-hyperliquid
pip install -r requirements.txt

python main.py            # launch the verifier TUI
python main.py --demo     # bundled demo dataset (offline preview)
```

One-click launchers (no system Python required — they unpack a bundled standalone
interpreter on first run):

```batch
run.bat        :: Windows
```
```bash
chmod +x run.sh && ./run.sh    # Linux / macOS
```

> No API keys required for verification — the tool reads public Hyperliquid data.
> An optional read-only wallet is used only for the live monitor and trade log.

---

## ⌨️ Keybindings

| Key | Action |
|-----|--------|
| `1`–`6` | Switch tabs: Dashboard · Traders · Verify · Positions · Log · Settings |
| `/` | Filter / search the focused table |
| `r` | Re-run verification on the selected trader |
| `c` | Open trade configuration |
| `v` | Open the detailed verification report |
| `t` | Toggle theme (dark / light / hyperliquid) |
| `q` | Quit |
| `?` | Help |

---

## 🧮 What "verification" actually checks

The verifier does **not** trust the headline leaderboard ROI. For any trader address it
recomputes, from first principles using public Hyperliquid fill and funding data:

1. **Fills-based PnL** — mark-to-market on every fill, validated against the L1 state.
2. **Fee & funding adjusted returns** — the real, tradeable number after costs.
3. **Drawdown envelope** — peak-to-trough equity and time-under-water.
4. **Sizing regime detector** — flags martingale / revenge-sizing patterns.
5. **Outlier dependence** — how much of total PnL comes from the top-N trades.
6. **Significance test** — is the Sharpe/expectancy distinguishable from luck?
7. **Counterparty heuristics** — wash-trade / self-trade suspicion scoring.

A trader is stamped `🟢 TRUSTED`, `🟠 REVIEW`, or `🔴 REJECT` based on a transparent,
configurable rubric you can inspect and edit in `~/.hl-verify/rules.toml`.

---

## 🗂️ Project layout

```
trade-bot-hyperliquid/
├── main.py                      # Entry point (unpacks bundled runtime on first launch)
├── hl_trade_bot/       # Host package
│   ├── __main__.py              # `python -m hl_trade_bot` entry
│   ├── cli.py                   # argparse + launch
│   ├── config.py                # Config loader (TOML)
│   ├── core/                    # models, verifier engine, risk simulator, mock data
│   └── tui/                     # Textual app: screens, widgets, styles
├── runtime/                     # Runtime support library
├── requirements.txt
├── run.bat / run.sh             # One-click launchers
└── release/                     # Pre-compiled binaries (planned)
```

---

## ⚙️ Configuration

```toml
# ~/.hl-verify/config.toml
[network]
chain            = "mainnet"          # mainnet | testnet
api_url          = "https://api.hyperliquid.xyz"
ws_url           = "wss://api.hyperliquid.xyz/ws"

[verification]
window_days      = 90
min_trades       = 100
significance_p   = 0.05
recompute_fees   = true

[trust_rubric]
max_drawdown     = -0.35              # reject worse than −35%
min_profit_factor= 1.6
max_martingale   = 0.4
max_outlier_dep  = 0.30

[trade]                           # paper-trail + sizing hints (never auto-executes)
size_mode        = "fixed_fraction"
fixed_fraction   = 0.02
leverage_cap     = 5.0
```

---

## 🔒 Security & responsible use

- **Read-only.** The verifier contains **no order-placement code path**. It cannot trade.
- **No private keys.** Verification needs only a public trader address. The optional monitor
  uses a **read-only** wallet; private keys are never requested or stored.
- **Rate-limited by default.** Respects Hyperliquid public-API conventions.

---

## 🛣️ Roadmap

- [ ] Funding-rate aware PnL recomputation v2
- [ ] Multi-trader portfolio correlation overlay
- [ ] Alerting hooks (webhook / Telegram) on trust-grade changes
- [ ] CSV / Parquet export of verified equity curves
- [ ] `--headless` mode for CI dashboards

---

## ❓ FAQ

<details>
<summary><b>Is this a trading bot that places orders?</b></summary>

No. This is a <b>verifier and monitor</b>. It reads public data, audits trader integrity, and logs
what you <i>would have</i> copied. Actual execution belongs to your own, separate, key-isolated bot.
Separation of audit and execution is a deliberate security boundary.
</details>

<details>
<summary><b>Why is verified ROI lower than the leaderboard ROI?</b></summary>

Headline ROI typically ignores fees, funding, and outlier dependence. The verifier recomputes
everything from fills and surfaces the tradeable number. A 30–40% gap is common and is exactly
what this tool exists to expose.
</details>

<details>
<summary><b>Do I need an API key?</b></summary>

No. Verification works from public Hyperliquid L1 data alone.
</details>

<details>
<summary><b>Is this affiliated with Hyperliquid?</b></summary>

No. Independent, unofficial community project. Hyperliquid is a third-party protocol.
</details>

---

## ⚠️ Disclaimer

This is an **unofficial community project**, **not affiliated with, endorsed by, or sponsored
by Hyperliquid Labs**. It is provided for research and transparency purposes only and is **not
financial advice**. Trade at your own risk.

---

## 📄 License

MIT — see [`LICENSE`](./LICENSE).


