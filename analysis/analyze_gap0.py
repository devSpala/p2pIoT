#!/usr/bin/env python3
"""
Burst (zero-gap) analysis for the control-overlay paper.

Generates the three burst figures and the burst results table from the raw
per-command CSVs produced by iot_experiment.html run with Gap = 0.

Usage:
  python analyze_gap0.py raw_p2p-browser_lan.csv raw_cloud-mqtt_lan.csv
Optionally pass a third arg to override batch schedule, e.g. "10,100,1000".

Outputs -> ./figs_gap0/
  gA_throughput.png   burst throughput vs batch, with paced baselines
  gB_latency.png      burst median/p99 latency vs batch
  gC_burst10k.png     per-command RTT within the largest burst

It also prints a LaTeX-ready results table and the headline numbers.
"""
import sys, os, csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = "figs_gap0"
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"figure.dpi": 130, "savefig.dpi": 190, "font.size": 11,
                     "axes.grid": True, "grid.alpha": 0.3})
COL = {"p2p-browser": "#1f6f5c", "cloud-mqtt": "#8e44ad"}

# Paced baselines to overlay (edit if your paced run differs)
PACED = {"p2p-browser": 93.0, "cloud-mqtt": 66.0}

def parse_batches(arg):
    return [int(x) for x in arg.split(",")] if arg else \
           [10, 100, 1000, 2000, 5000, 10000]

def load_raw(path):
    rows = list(csv.DictReader(open(path)))
    tr = rows[0]["transport"]
    seq = np.array([int(r["seq"]) for r in rows])
    rtt = np.array([float(r["rtt_ms"]) for r in rows])
    o = np.argsort(seq)
    return tr, seq[o], rtt[o]

def load_summary(path):
    """Optional matching summary_*.csv for authoritative throughput values."""
    p = path.replace("raw_", "summary_")
    if not os.path.exists(p):
        return None
    return {int(r["batch"]): r for r in csv.DictReader(open(p))}

def slices(batches, n_total):
    out, s = {}, 0
    for b in batches:
        out[b] = (s, s + b); s += b
    if s != n_total:
        print(f"  WARN: batches sum to {s} but file has {n_total} rows; "
              f"using contiguous best-effort slicing")
    return out

def main():
    args = [a for a in sys.argv[1:] if a.endswith(".csv")]
    override = next((a for a in sys.argv[1:] if not a.endswith(".csv")), None)
    if len(args) < 2:
        print(__doc__); sys.exit(1)
    batches = parse_batches(override)

    data, summ = {}, {}
    for path in args:
        tr, seq, rtt = load_raw(path)
        data[tr] = (seq, rtt)
        summ[tr] = load_summary(path)
        print(f"{tr}: n={len(rtt)} median={np.median(rtt):.1f}ms "
              f"p99={np.percentile(rtt,99):.1f}ms")

    sl = {tr: slices(batches, len(data[tr][1])) for tr in data}

    def thr(tr, b):
        # prefer measured throughput from summary; else compute from raw span
        if summ[tr] and b in summ[tr]:
            return float(summ[tr][b]["throughput_cps"])
        a, z = sl[tr][b]; rtts = data[tr][1][a:z]
        # fallback: batch size / wallclock span is unavailable in raw; approximate
        return np.nan

    # ---- FIG A: throughput ----
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    for tr in data:
        ys = [thr(tr, b) for b in batches]
        ax.plot(batches, ys, "o-", color=COL.get(tr, None), lw=2, label=f"{tr} burst")
        if tr in PACED:
            ax.axhline(PACED[tr], color=COL.get(tr), ls=":", alpha=.7,
                       label=f"{tr} paced ({PACED[tr]:.0f})")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("Batch size (commands)")
    ax.set_ylabel("Achieved throughput (cmd/s, log)")
    ax.set_title("Burst throughput: transport capacity, not paced rate")
    ax.legend(fontsize=8.5)
    fig.tight_layout(); fig.savefig(f"{OUT}/gA_throughput.png", bbox_inches="tight")
    plt.close(fig)

    # ---- FIG B: latency ----
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    for tr in data:
        med = [np.median(data[tr][1][sl[tr][b][0]:sl[tr][b][1]]) for b in batches]
        p99 = [np.percentile(data[tr][1][sl[tr][b][0]:sl[tr][b][1]], 99) for b in batches]
        ax.plot(batches, med, "o-", color=COL.get(tr), lw=2, label=f"{tr} median")
        ax.plot(batches, p99, "s--", color=COL.get(tr), lw=1.6, alpha=.6, label=f"{tr} p99")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("Batch size (commands)"); ax.set_ylabel("RTT under burst (ms, log)")
    ax.set_title("Burst latency: queueing dominates at large bursts")
    ax.legend(fontsize=8.5)
    fig.tight_layout(); fig.savefig(f"{OUT}/gB_latency.png", bbox_inches="tight")
    plt.close(fig)

    # ---- FIG C: inside the largest burst ----
    big = max(batches)
    fig, ax = plt.subplots(figsize=(9, 4.6))
    for tr in data:
        a, z = sl[tr][big]
        ax.plot(np.arange(z - a), data[tr][1][a:z], ".", ms=1.5,
                color=COL.get(tr), alpha=.6, label=tr)
    ax.set_xlabel(f"Command index within the {big:,}-command burst")
    ax.set_ylabel("RTT (ms)")
    ax.set_title(f"Inside the {big:,} burst: queue build-up and drain")
    ax.legend(markerscale=6)
    fig.tight_layout(); fig.savefig(f"{OUT}/gC_burst10k.png", bbox_inches="tight")
    plt.close(fig)

    # ---- LaTeX table + headline ----
    trs = list(data.keys())
    print("\n% ---- LaTeX burst table rows ----")
    for b in batches:
        cells = []
        for tr in trs:
            a, z = sl[tr][b]; r = data[tr][1][a:z]
            cells += [f"{np.median(r):.1f}", f"{np.percentile(r,99):.1f}",
                      f"{thr(tr,b):.0f}"]
        print(f"{b:<6} & " + " & ".join(cells) + r" \\")

    print("\n=== headline ===")
    for b in batches:
        vals = {tr: np.median(data[tr][1][sl[tr][b][0]:sl[tr][b][1]]) for tr in trs}
        if len(trs) == 2:
            a, c = trs
            print(f"batch {b:>6}: {a} {vals[a]:7.1f} ms | {c} {vals[c]:7.1f} ms "
                  f"| {vals[c]/vals[a]:.1f}x")
    print(f"figures -> ./{OUT}/")

if __name__ == "__main__":
    main()
