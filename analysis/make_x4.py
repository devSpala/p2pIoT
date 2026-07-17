#!/usr/bin/env python3
"""
Regenerate x4_remote_fair.png (like-for-like remote comparison) WITHOUT the
annotation/arrow that collided with the x-axis label.

Both transports were measured with the gateway on cellular and the controller
on Wi-Fi. P2P was relayed via public TURN; cloud used a public MQTT broker.

Usage:
    python make_x4.py raw_p2p-browser_cross-isp_relay.csv raw_cloud-mqtt_cross-isp.csv
Output: ./x4_remote_fair.png
"""
import sys, csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 190, "font.size": 11,
    "axes.grid": True, "grid.alpha": 0.3,
})

BATCHES = [10, 100, 1000, 2000, 5000, 10000]


def median_by_batch(path):
    """Return {batch: median RTT} from a raw per-command CSV (seq,rtt_ms,...)."""
    rows = list(csv.DictReader(open(path)))
    seq = np.array([int(r["seq"]) for r in rows])
    rtt = np.array([float(r["rtt_ms"]) for r in rows])
    rtt = rtt[np.argsort(seq)]
    out, start = {}, 0
    for b in BATCHES:
        out[b] = float(np.median(rtt[start:start + b]))
        start += b
    return out


def main():
    args = [a for a in sys.argv[1:] if a.endswith(".csv")]
    if len(args) < 2:
        print(__doc__)
        sys.exit(1)
    p2p = median_by_batch(args[0])
    cloud = median_by_batch(args[1])

    fig, ax = plt.subplots(figsize=(7, 4.4))
    ax.plot(BATCHES, [p2p[b] for b in BATCHES], "^-",
            color="#2c7fb8", lw=2, label="P2P relay (remote)")
    ax.plot(BATCHES, [cloud[b] for b in BATCHES], "D-",
            color="#8e44ad", lw=2, label="Cloud broker (remote)")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Batch size (commands)")
    ax.set_ylabel("Median RTT (ms, log)")
    ax.set_title("Like-for-like remote comparison: both endpoints cross-network")
    ax.legend(fontsize=9)
    # Annotation placed in the open right-side area (between the two lines) with
    # an arrow to the P2P steady region, so it never overlaps the x-axis label.
    ax.annotate(
        "steady: 167 vs 627 ms\n= 3.8x faster",
        xy=(5000, p2p[5000]), xytext=(1500, 320),
        fontsize=9, ha="left", va="center",
        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#999", alpha=0.9),
        arrowprops=dict(arrowstyle="->", color="#333", lw=1.2,
                        connectionstyle="arc3,rad=-0.2"),
    )
    fig.tight_layout()
    fig.savefig("x4_remote_fair.png", bbox_inches="tight")
    plt.close(fig)

    steady = [b for b in BATCHES if b != 10]  # exclude batch-10 cold start
    pr = np.median([p2p[b] for b in steady])
    cr = np.median([cloud[b] for b in steady])
    print(f"steady P2P {pr:.0f} ms | cloud {cr:.0f} ms | {cr/pr:.1f}x faster")
    print("wrote x4_remote_fair.png")


if __name__ == "__main__":
    main()
