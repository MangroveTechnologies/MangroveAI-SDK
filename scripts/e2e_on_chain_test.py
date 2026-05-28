"""SDK e2e: real customer-shape path through SDK -> HTTP -> backend -> Nansen."""
import sys, os, json, subprocess, threading, time

sys.path.insert(0, '/tmp/MangroveRoots-nansen-expansion')
sys.path.insert(0, '/tmp/MangroveAI-nansen-expansion/src')
sys.path.insert(0, '/tmp/MangroveAI-SDK-nansen-expansion/src')

import mangrove_ai
assert 'MangroveAI-SDK-nansen-expansion' in mangrove_ai.__file__
os.environ["ENVIRONMENT"] = "local"
os.environ["GCP_PROJECT_ID"] = "mangroveai-dev"

import requests
def _ua(orig):
    def w(*a, **kw):
        h = kw.get("headers", {}); h["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        kw["headers"] = h
        return orig(*a, **kw)
    return w
requests.post = _ua(requests.post); requests.get = _ua(requests.get)

import shutil
shutil.copy('/home/darrahts/mangrove/MangroveAI/src/MangroveAI/config/local-config.json',
            '/tmp/MangroveAI-nansen-expansion/src/MangroveAI/config/local-config.json')
os.chdir('/tmp/MangroveAI-nansen-expansion/src/MangroveAI')

import MangroveAI.utils.shared_data_directory as _sdd; _sdd.setup_strategies_directory = lambda *a,**kw: None
import MangroveAI.domains.ai_copilot.services as _aics; _aics._recover_stale_processing_sessions = lambda *a,**kw: 0
import MangroveAI.domains.backtesting.db as _bdb; _bdb.reset_interrupted_backtests = lambda *a,**kw: 0

from MangroveAI import create_app
print("[setup] booting Flask app")
app = create_app()

from werkzeug.serving import make_server
PORT = 5195
server = make_server("127.0.0.1", PORT, app, threaded=True)
threading.Thread(target=server.serve_forever, daemon=True).start()
time.sleep(2)

from mangrove_ai import MangroveAI
class MgmtAuth:
    def __init__(self, k): self._k = k
    def apply(self, h):
        h["X-Mgmt-API-Key"] = self._k
        h["X-Admin-Invocation"] = "true"
        return h

# Local app's MGMT_API_KEY is 'test' per local-config.json (literal, not secret-resolved)
client = MangroveAI(base_url=f"http://127.0.0.1:{PORT}/api/v1")
client._core_transport._auth = MgmtAuth("test")

print("\n" + "=" * 80)
print(" Real customer path: SDK -> POST -> backend -> NansenClient -> live Nansen Pro")
print("=" * 80)

def show(label, resp):
    print(f"\n[{label}]")
    if resp is None:
        print("  (None)"); return
    d = resp.model_dump() if hasattr(resp, "model_dump") else dict(resp)
    for k, v in list(d.items())[:9]:
        if isinstance(v, list):
            if v and isinstance(v[0], dict):
                print(f"  {k}: [{len(v)} items] first.keys={list(v[0].keys())[:6]}")
            else:
                print(f"  {k}: [{len(v)} items]")
        elif isinstance(v, dict):
            print(f"  {k}: {json.dumps(v)[:140]}")
        else:
            print(f"  {k}: {v!r}")

passed, failed = 0, 0
def check(label, fn, *a, expect_exception=None, **kw):
    global passed, failed
    try:
        r = fn(*a, **kw)
        if expect_exception:
            print(f"\n[{label}]\n  EXPECTED {expect_exception.__name__}, got: {r}")
            failed += 1
            return None
        show(label, r)
        passed += 1
        return r
    except Exception as e:
        if expect_exception and isinstance(e, expect_exception):
            print(f"\n[{label}]\n  OK -- {type(e).__name__}: {str(e)[:140]}")
            passed += 1
        else:
            print(f"\n[{label}]\n  FAIL {type(e).__name__}: {str(e)[:200]}")
            failed += 1
        return None

try:
    check("1) historical_holdings(chains=eth, date_from=05-22, date_to=05-28, per_page=3)",
          client.on_chain.get_smart_money_historical_holdings,
          chains=["ethereum"], date_from="2026-05-22", date_to="2026-05-28", per_page=3)

    check("2) dex_trades(chains=eth, per_page=3) minimal",
          client.on_chain.get_smart_money_dex_trades, chains=["ethereum"], per_page=3)

    check("3) dex_trades + filters=Fund + order_by ts DESC -- FULL NANSEN PASSTHROUGH",
          client.on_chain.get_smart_money_dex_trades,
          chains=["ethereum"],
          filters={"include_smart_money_labels": ["Fund"]},
          order_by=[{"field": "block_timestamp", "direction": "DESC"}],
          per_page=3)

    check("4) perp_trades() Hyperliquid",
          client.on_chain.get_smart_money_perp_trades, per_page=3)

    check("5) token_dex_trades(uniswap, date range, per_page=3)",
          client.on_chain.get_token_dex_trades,
          "uniswap", chain="ethereum",
          date_from="2026-05-22", date_to="2026-05-28", per_page=3)

    check("6) token_flows(uniswap, date range, per_page=3)",
          client.on_chain.get_token_flows,
          "uniswap", chain="ethereum",
          date_from="2026-05-22", date_to="2026-05-28", per_page=3)

    from mangrove_ai.exceptions import NotFoundError
    check("7) token_flows(usd-coin) stablecoin -- expect NotFoundError",
          client.on_chain.get_token_flows,
          "usd-coin", chain="ethereum", per_page=3,
          expect_exception=NotFoundError)

    check("8) regression: sentiment(BTC) -- existing GET route still works",
          client.on_chain.get_smart_money_sentiment, "BTC")

    print(f"\n{'=' * 80}\nRESULT: {passed} passed, {failed} failed\n{'=' * 80}")
finally:
    server.shutdown()
