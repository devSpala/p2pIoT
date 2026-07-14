#!/usr/bin/env python3
"""
Deep analysis of the REAL PC<->Android experiment data.
Produces 7 additional figures from the raw per-command CSVs.

Usage:
  python analyze_deep.py raw_p2p-browser_lan.csv raw_cloud-mqtt_lan.csv
Figures -> ./figs_deep/
"""
import sys, os, csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = "figs_deep"
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"figure.dpi":130,"savefig.dpi":190,"font.size":11,
                     "axes.grid":True,"grid.alpha":0.3})
COL = {"p2p-browser":"#1f6f5c","cloud-mqtt":"#8e44ad"}
BATCHES = [10,100,1000,2000,5000,10000]

def load(path):
    rows = list(csv.DictReader(open(path)))
    tr = rows[0]["transport"]
    seq = np.array([int(r["seq"]) for r in rows])
    rtt = np.array([float(r["rtt_ms"]) for r in rows])
    order = np.argsort(seq)
    return tr, seq[order], rtt[order]

def batch_slices(n_total):
    """Global seq is contiguous across batches in run order."""
    out, start = {}, 0
    for b in BATCHES:
        out[b] = (start, start+b)
        start += b
    assert start == n_total, f"expected {start} rows, got {n_total}"
    return out

data = {}
for path in sys.argv[1:]:
    tr, seq, rtt = load(path)
    data[tr] = (seq, rtt)
    print(f"{tr}: n={len(rtt)} median={np.median(rtt):.1f}ms "
          f"p99={np.percentile(rtt,99):.1f}ms max={rtt.max():.0f}ms")

# ================= FIG 1: full-run RTT CDF =================
fig, ax = plt.subplots(figsize=(7,4.6))
for tr,(seq,rtt) in data.items():
    x = np.sort(rtt); y = np.arange(1,len(x)+1)/len(x)
    ax.plot(x, y, color=COL[tr], lw=2, label=tr)
    ax.axvline(np.median(x), color=COL[tr], ls="--", alpha=.5)
ax.set_xscale("log")
ax.set_xlabel("Command RTT (ms, log)"); ax.set_ylabel("CDF")
ax.set_title("RTT distribution, all 18,110 commands (dashed = median)")
ax.legend()
fig.tight_layout(); fig.savefig(f"{OUT}/f1_cdf.png", bbox_inches="tight"); plt.close(fig)

# ================= FIG 2: RTT vs sequence (queueing dynamics) =================
fig, axes = plt.subplots(2,1, figsize=(9,6), sharex=True)
for ax,(tr,(seq,rtt)) in zip(axes, data.items()):
    ax.plot(seq, rtt, ".", ms=1.2, color=COL[tr], alpha=.5)
    sl = batch_slices(len(rtt))
    for b,(a,z) in sl.items():
        ax.axvline(z, color="#999", lw=.6)
        ax.text((a+z)/2, ax.get_ylim()[1]*0.9 if False else rtt.max()*0.85,
                str(b), ha="center", fontsize=8, color="#555")
    ax.set_yscale("log"); ax.set_ylabel(f"{tr}\nRTT (ms, log)")
axes[1].set_xlabel("Command sequence number (batches labeled)")
axes[0].set_title("Per-command RTT across the whole run — queueing dynamics")
fig.tight_layout(); fig.savefig(f"{OUT}/f2_sequence.png", bbox_inches="tight"); plt.close(fig)

# ================= FIG 3: box plots per batch =================
fig, ax = plt.subplots(figsize=(9,4.8))
width=.35
for i,(tr,(seq,rtt)) in enumerate(data.items()):
    sl = batch_slices(len(rtt))
    groups = [rtt[a:z] for b,(a,z) in sl.items()]
    pos = np.arange(len(BATCHES)) + (i-0.5)*width
    bp = ax.boxplot(groups, positions=pos, widths=width*.9, showfliers=False,
                    patch_artist=True)
    for p in bp["boxes"]: p.set_facecolor(COL[tr]); p.set_alpha(.6)
    for med in bp["medians"]: med.set_color("k")
ax.set_yscale("log")
ax.set_xticks(np.arange(len(BATCHES))); ax.set_xticklabels(BATCHES)
ax.set_xlabel("Batch size"); ax.set_ylabel("RTT (ms, log)")
ax.set_title("RTT spread per batch (boxes: IQR; whiskers: 1.5 IQR)")
handles=[plt.Rectangle((0,0),1,1,fc=COL[t],alpha=.6) for t in data]
ax.legend(handles, list(data.keys()))
fig.tight_layout(); fig.savefig(f"{OUT}/f3_box.png", bbox_inches="tight"); plt.close(fig)

# ================= FIG 4: tail zoom p90..p99.9 =================
fig, ax = plt.subplots(figsize=(7,4.6))
qs = np.linspace(90, 99.9, 60)
for tr,(seq,rtt) in data.items():
    ax.plot(qs, [np.percentile(rtt,q) for q in qs], color=COL[tr], lw=2, label=tr)
ax.set_yscale("log")
ax.set_xlabel("Percentile"); ax.set_ylabel("RTT (ms, log)")
ax.set_title("Tail latency zoom (p90–p99.9), all commands")
ax.legend()
fig.tight_layout(); fig.savefig(f"{OUT}/f4_tail.png", bbox_inches="tight"); plt.close(fig)

# ================= FIG 5: cloud/p2p improvement ratio per batch =================
fig, ax = plt.subplots(figsize=(7,4.6))
sl_p = batch_slices(len(data["p2p-browser"][1]))
sl_c = batch_slices(len(data["cloud-mqtt"][1]))
for stat, name, mk in [(np.median,"median","o-"),
                       (lambda x: np.percentile(x,95),"p95","s--"),
                       (lambda x: np.percentile(x,99),"p99","^:")]:
    ratio=[]
    for b in BATCHES:
        a,z = sl_p[b]; p = stat(data["p2p-browser"][1][a:z])
        a,z = sl_c[b]; c = stat(data["cloud-mqtt"][1][a:z])
        ratio.append(c/p)
    ax.plot(BATCHES, ratio, mk, lw=2, label=f"{name} ratio")
ax.axhline(1, color="#999", ls="--")
ax.set_xscale("log")
ax.set_xlabel("Batch size"); ax.set_ylabel("cloud RTT / P2P RTT  (x)")
ax.set_title("How many times faster is P2P? (ratio > 1 = P2P wins)")
ax.legend()
fig.tight_layout(); fig.savefig(f"{OUT}/f5_ratio.png", bbox_inches="tight"); plt.close(fig)

# ================= FIG 6: jitter (rolling IQR) =================
fig, ax = plt.subplots(figsize=(9,4.4))
W=200
for tr,(seq,rtt) in data.items():
    n=len(rtt); idx=np.arange(0,n-W,W//2); jit=[]
    for a in idx:
        w=rtt[a:a+W]; jit.append(np.percentile(w,75)-np.percentile(w,25))
    ax.plot(idx+W//2, jit, color=COL[tr], lw=1.5, label=tr)
ax.set_yscale("log")
ax.set_xlabel("Command sequence"); ax.set_ylabel(f"Rolling IQR over {W} cmds (ms, log)")
ax.set_title("Jitter across the run — stability of each transport")
ax.legend()
fig.tight_layout(); fig.savefig(f"{OUT}/f6_jitter.png", bbox_inches="tight"); plt.close(fig)

# ================= FIG 7: histogram overlay (log bins) =================
fig, ax = plt.subplots(figsize=(7,4.6))
bins = np.logspace(np.log10(30), np.log10(max(r.max() for _,r in data.values())*1.05), 70)
for tr,(seq,rtt) in data.items():
    ax.hist(rtt, bins=bins, alpha=.55, color=COL[tr], label=tr)
ax.set_xscale("log")
ax.set_xlabel("RTT (ms, log)"); ax.set_ylabel("Commands")
ax.set_title("RTT histogram, all commands (log bins)")
ax.legend()
fig.tight_layout(); fig.savefig(f"{OUT}/f7_hist.png", bbox_inches="tight"); plt.close(fig)

# ---- headline numbers ----
print("\n=== headline numbers from YOUR data ===")
for b in BATCHES:
    a,z = sl_p[b]; p = np.median(data["p2p-browser"][1][a:z])
    a,z = sl_c[b]; c = np.median(data["cloud-mqtt"][1][a:z])
    print(f"batch {b:>6}: P2P median {p:7.1f} ms | cloud {c:7.1f} ms | P2P {c/p:4.1f}x faster")
p_all = data["p2p-browser"][1]; c_all = data["cloud-mqtt"][1]
print(f"\noverall: P2P median {np.median(p_all):.1f} vs cloud {np.median(c_all):.1f} ms "
      f"({np.median(c_all)/np.median(p_all):.1f}x)")
print(f"p99     : P2P {np.percentile(p_all,99):.0f} vs cloud {np.percentile(c_all,99):.0f} ms "
      f"({np.percentile(c_all,99)/np.percentile(p_all,99):.1f}x)")
print(f"figures -> ./{OUT}/")
