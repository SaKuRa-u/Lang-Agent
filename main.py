import sys
from src.state import normalize_ticker
from src.graph import graph


def main():
    ticker = normalize_ticker(sys.argv[1] if len(sys.argv) > 1 else "BBCA.JK")
    init = {"ticker": ticker, "news": [], "fundamentals": {}, "sentiment": "", "report": "", "recommendation": "", "history": [], "messages": []}
    out = graph.invoke(init)
    print(f"\n=== {out['ticker']} -> {out.get('recommendation')} ===\n")
    print(out.get("report", ""))


if __name__ == "__main__":
    main()
