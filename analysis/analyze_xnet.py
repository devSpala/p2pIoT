#!/usr/bin/env python3
"""
Cross-network (remote) analysis for the control-overlay paper.

Now includes the LIKE-FOR-LIKE remote cloud baseline: both the P2P arm
(relayed via public TURN) and the cloud arm (public MQTT broker) are measured
with the gateway on cellular and the controller on Wi-Fi.

Usage:
  python analyze_xnet.py raw_p2p-browser_cross-isp_relay.csv \
                         raw_cloud-mqtt_cross-isp.csv
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
LAN_P2P={10:21.6,100:11.2,1000:11.8,2000:11.0,5000:13.1,10000:16.6}
LAN_CLOUD={10:764.0,100:554.4,1000:473.3,2000:474.2,5000:472.2,10000:484.0}

def med_by_batch(path):
    r=list(csv.DictReader(open(path)))
    seq=np.array([int(x["seq"]) for x in r]); rtt=np.array([float(x["rtt_ms"]) for x in r])
    o=np.argsort(seq); rtt=rtt[o]; s=0; out={}; p99={}
    for b in B:
        seg=rtt[s:s+b]; out[b]=np.median(seg); p99[b]=np.percentile(seg,99); s+=b
    return out, p99, rtt

def main():
    args=[a for a in sys.argv[1:] if a.endswith(".csv")]
    if len(args)<2:
        print(__doc__); sys.exit(1)
    p2p, p2p99, p2praw = med_by_batch(args[0])
    cld, cld99, cldraw = med_by_batch(args[1])

    # four-regime figure
    fig,ax=plt.subplots(figsize=(7.6,4.9))
    ax.plot(B,[LAN_P2P[b] for b in B],"o-",color="#1f6f5c",lw=2,
            label="P2P direct — same-LAN (best case)")
    ax.plot(B,[p2p[b] for b in B],"^-",color="#2c7fb8",lw=2,
            label="P2P relay — cross-ISP via public TURN")
    ax.plot(B,[cld[b] for b in B],"D-",color="#8e44ad",lw=2,
            label="Cloud broker — cross-ISP (remote, measured)")
    ax.plot(B,[LAN_CLOUD[b] for b in B],"s--",color="#c39bd3",lw=1.6,alpha=.8,
            label="Cloud broker — same-LAN (reference)")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("Batch size (commands)"); ax.set_ylabel("Median command RTT (ms, log)")
    ax.set_title("Four regimes: direct LAN, relayed cross-ISP, cloud (remote vs LAN)")
    ax.legend(fontsize=8); fig.tight_layout()
    fig.savefig(f"{OUT}/x1_threeway.png",bbox_inches="tight"); plt.close(fig)

    # like-for-like remote comparison
    fig,ax=plt.subplots(figsize=(7,4.4))
    ax.plot(B,[p2p[b] for b in B],"^-",color="#2c7fb8",lw=2,label="P2P relay (remote)")
    ax.plot(B,[cld[b] for b in B],"D-",color="#8e44ad",lw=2,label="Cloud broker (remote)")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("Batch size (commands)"); ax.set_ylabel("Median RTT (ms, log)")
    ax.set_title("Like-for-like remote comparison: both endpoints cross-network")
    ax.legend(fontsize=9); fig.tight_layout()
    fig.savefig(f"{OUT}/x4_remote_fair.png",bbox_inches="tight"); plt.close(fig)

    # relay sequence
    fig,ax=plt.subplots(figsize=(9,4.4))
    ax.plot(np.arange(len(p2praw)),p2praw,".",ms=1.2,color="#2c7fb8",alpha=.5)
    s=0
    for b in B: s+=b; ax.axvline(s,color="#ccc",lw=.6)
    ax.set_yscale("log"); ax.set_xlabel("Command sequence"); ax.set_ylabel("RTT (ms, log)")
    ax.set_title("Cross-ISP relay: setup spike, then stable")
    fig.tight_layout(); fig.savefig(f"{OUT}/x2_sequence.png",bbox_inches="tight"); plt.close(fig)

    steady=[b for b in B if b!=10]
    print("=== LIKE-FOR-LIKE REMOTE (both cross-network) ===")
    print(f"{'batch':>6} {'P2P relay':>10} {'Cloud remote':>13} {'ratio':>7}")
    for b in B:
        tag=' (cold-start)' if b==10 else ''
        print(f"{b:>6} {p2p[b]:9.1f} {cld[b]:12.1f} {cld[b]/p2p[b]:6.1f}x{tag}")
    pr=np.median([p2p[b] for b in steady]); cr=np.median([cld[b] for b in steady])
    print(f"\nSTEADY (excl batch-10): P2P {pr:.0f} ms | cloud {cr:.0f} ms | {cr/pr:.1f}x")
    print(f"same-LAN cloud reference: {np.median([LAN_CLOUD[b] for b in steady]):.0f} ms")
    print(f"figures -> ./{OUT}/")

if __name__=="__main__": main()
