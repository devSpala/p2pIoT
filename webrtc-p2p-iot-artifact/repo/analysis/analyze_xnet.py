#!/usr/bin/env python3
"""
Cross-network (remote) analysis for the control-overlay paper.
Builds the three-way regime figure and the relay sequence/CDF figures, and
prints the LaTeX table rows, from the cross-ISP relay CSV.

Usage:
  python analyze_xnet.py raw_p2p-browser_cross-isp_relay.csv
Optional: pass LAN and cloud summary CSVs to overlay real baselines instead of
the built-in constants:
  python analyze_xnet.py raw_..._relay.csv summary_p2p_lan.csv summary_cloud.csv
Outputs -> ./figs_xnet/
"""
import sys, os, csv
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT="figs_xnet"; os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"figure.dpi":130,"savefig.dpi":190,"font.size":11,
                     "axes.grid":True,"grid.alpha":0.3})
B=[10,100,1000,2000,5000,10000]
# built-in baselines (edit or override with summary CSVs)
LAN={10:21.6,100:11.2,1000:11.8,2000:11.0,5000:13.1,10000:16.6}
CLOUD={10:764.0,100:554.4,1000:473.3,2000:474.2,5000:472.2,10000:484.0}

def load_raw(p):
    r=list(csv.DictReader(open(p)))
    seq=np.array([int(x["seq"]) for x in r]); rtt=np.array([float(x["rtt_ms"]) for x in r])
    o=np.argsort(seq); return seq[o],rtt[o]

def med_by_batch(summary_path):
    d={}
    for row in csv.DictReader(open(summary_path)):
        d[int(row["batch"])]=float(row["median_ms"])
    return d

def main():
    args=[a for a in sys.argv[1:] if a.endswith(".csv")]
    if not args: print(__doc__); sys.exit(1)
    relay_raw=args[0]
    lan, cloud = LAN, CLOUD
    if len(args)>=3:
        lan=med_by_batch(args[1]); cloud=med_by_batch(args[2])
    sx,rx=load_raw(relay_raw)
    o={}; s=0
    for b in B: o[b]=(s,s+b); s+=b
    xr={b:np.median(rx[o[b][0]:o[b][1]]) for b in B}

    # three-way
    fig,ax=plt.subplots(figsize=(7.6,4.7))
    ax.plot(B,[lan.get(b,np.nan) for b in B],"o-",color="#1f6f5c",lw=2,label="P2P direct — same-LAN")
    ax.plot(B,[xr[b] for b in B],"^-",color="#2c7fb8",lw=2,label="P2P relay — cross-ISP (TURN)")
    ax.plot(B,[cloud.get(b,np.nan) for b in B],"s-",color="#8e44ad",lw=2,label="Cloud — away (MQTT)")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("Batch size (commands)"); ax.set_ylabel("Median RTT (ms, log)")
    ax.set_title("Three regimes: direct LAN vs relayed cross-ISP vs cloud")
    ax.legend(fontsize=8.5); fig.tight_layout()
    fig.savefig(f"{OUT}/x1_threeway.png",bbox_inches="tight"); plt.close(fig)

    # sequence
    fig,ax=plt.subplots(figsize=(9,4.4))
    ax.plot(np.arange(len(rx)),rx,".",ms=1.2,color="#2c7fb8",alpha=.5)
    for b in B: ax.axvline(o[b][1],color="#ccc",lw=.6)
    ax.set_yscale("log"); ax.set_xlabel("Command sequence"); ax.set_ylabel("RTT (ms, log)")
    ax.set_title("Cross-ISP relay: setup spike, then stable")
    fig.tight_layout(); fig.savefig(f"{OUT}/x2_sequence.png",bbox_inches="tight"); plt.close(fig)

    # steady CDF
    steady=[b for b in B if b!=10]
    allsteady=np.concatenate([rx[o[b][0]:o[b][1]] for b in steady])
    fig,ax=plt.subplots(figsize=(7,4.6))
    x=np.sort(allsteady); y=np.arange(1,len(x)+1)/len(x)
    ax.plot(x,y,color="#2c7fb8",lw=2); ax.axvline(np.median(x),color="#2c7fb8",ls="--",alpha=.6)
    ax.set_xscale("log"); ax.set_xlabel("RTT (ms, log)"); ax.set_ylabel("CDF")
    ax.set_title("Cross-ISP relay steady-state RTT")
    fig.tight_layout(); fig.savefig(f"{OUT}/x3_cdf.png",bbox_inches="tight"); plt.close(fig)

    print("% LaTeX rows (batch, median, p95, p99, cps):")
    for b in B:
        seg=rx[o[b][0]:o[b][1]]
        print(f"{b:<6} & {np.median(seg):.1f} & {np.percentile(seg,95):.1f} & "
              f"{np.percentile(seg,99):.1f} & --- \\\\")
    xs=np.median([xr[b] for b in steady]); cs=np.median([cloud[b] for b in steady])
    print(f"\nsteady relay median {xs:.1f} ms vs cloud {cs:.1f} ms ({cs/xs:.1f}x)")
    print(f"figures -> ./{OUT}/")

if __name__=="__main__": main()
