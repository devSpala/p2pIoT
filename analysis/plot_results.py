#!/usr/bin/env python3
"""Plot P2P vs Cloud comparison from the experiment summary CSVs.
Usage:  python plot_results.py summary_p2p-browser_lan.csv summary_cloud-mqtt_lan.csv
Produces comparison.png with latency-vs-batch and throughput-vs-batch panels."""
import sys, csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

series = {}
for path in sys.argv[1:]:
    rows = list(csv.DictReader(open(path)))
    if not rows: continue
    key = rows[0]["transport"]
    series[key] = rows

colors = {"p2p-browser": "#1f6f5c", "cloud-mqtt": "#8e44ad"}
fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(14, 4.2))
for key, rows in series.items():
    b   = [int(r["batch"]) for r in rows]
    med = [float(r["median_ms"]) for r in rows]
    p99 = [float(r["p99_ms"]) for r in rows]
    thr = [float(r["throughput_cps"]) for r in rows]
    loss= [float(r["loss_pct"]) for r in rows]
    c = colors.get(key, None)
    ax1.plot(b, med, "o-", color=c, label=key+" median")
    ax1.plot(b, p99, "s--", color=c, alpha=.5, label=key+" p99")
    ax2.plot(b, thr, "o-", color=c, label=key)
    ax3.plot(b, loss, "o-", color=c, label=key)
for ax, ylab, title in [(ax1,"RTT (ms)","Latency vs batch size"),
                        (ax2,"commands/sec","Throughput vs batch size"),
                        (ax3,"loss (%)","Loss vs batch size")]:
    ax.set_xscale("log"); ax.set_xlabel("batch size (commands)")
    ax.set_ylabel(ylab); ax.set_title(title); ax.grid(alpha=.3); ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig("comparison.png", dpi=180)
print("wrote comparison.png")
