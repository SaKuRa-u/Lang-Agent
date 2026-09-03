import sys
from src.state import normalize_ticker
from src.graph import graph


def run_hitl(ticker, db_path="checkpoints.sqlite"):
    from src.graph import build_hitl_graph
    from src.state import normalize_ticker
    ticker = normalize_ticker(ticker)
    g = build_hitl_graph(db_path)
    cfg = {"configurable": {"thread_id": ticker}}
    init = {"ticker": ticker, "news": [], "fundamentals": {}, "sentiment": "", "report": "", "recommendation": "", "history": [], "messages": []}
    out = g.invoke(init, config=cfg)
    print(f"Sentimen: {out.get('sentiment')}\nFundamental: {out.get('fundamentals')}")
    if input("lanjut ke rekomendasi? [y/n]: ").lower() != "y":
        print("dibatalkan."); return
    out = g.invoke(None, config=cfg)
    print(f"\n=== {out['ticker']} -> {out.get('recommendation')} ===\n{out.get('report', '')}")


def main():
    args = [a for a in sys.argv[1:] if a != "--hitl"]
    use_hitl = "--hitl" in sys.argv
    ticker = normalize_ticker(args[0] if args else "BBCA.JK")
    if use_hitl:
        run_hitl(ticker)
        return
    init = {"ticker": ticker, "news": [], "fundamentals": {}, "sentiment": "", "report": "", "recommendation": "", "history": [], "messages": []}
    out = graph.invoke(init)
    print(f"\n=== {out['ticker']} -> {out.get('recommendation')} ===\n")
    print(out.get("report", ""))


if __name__ == "__main__":
    main()
