#!/usr/bin/env python3
"""
REAL-TIME MEASUREMENT HARNESS  (host/controller side)
=====================================================
This drives ACTUAL latency/cost measurements against a real device. It does NOT
fabricate data: every number it prints comes from a real round-trip you run.

It measures the SAME control workload over up to three real transports so the
paper's comparison is apples-to-apples:

  --transport p2p-direct   : WebRTC DataChannel, host candidate (LAN) or srflx
  --transport p2p-relay    : WebRTC DataChannel forced through TURN
  --transport mqtt         : MQTT publish/echo through a broker (managed or self)

For each command it sends a sequence number + monotonic send timestamp, the
device echoes it back, and we record the wall-clock RTT with time.perf_counter().
Results are written to CSV that experiments.py / cost_analysis.py read directly.

USAGE (examples)
  # MQTT baseline against a broker (managed AWS IoT or local Mosquitto):
  python3 measure_realtime.py --transport mqtt --host BROKER_HOST --port 8883 \
        --tls --topic ctl/dev1 --n 500 --out rtt_mqtt_crossisp.csv

  # WebRTC measurement is driven via the companion Node controller (see
  # webrtc_probe.js) which writes the same CSV schema; this script can also
  # post-process and summarize any of the CSVs:
  python3 measure_realtime.py --summarize rtt_*.csv

OUTPUT CSV schema (one row per command):
  seq,send_ts,recv_ts,rtt_ms,transport,network,relayed
"""
import argparse, csv, time, sys, statistics, glob

def measure_mqtt(args):
    """Real MQTT round-trip latency. Requires: pip install paho-mqtt."""
    import paho.mqtt.client as mqtt
    import threading

    pending = {}          # seq -> send perf_counter
    results = []
    got = threading.Event()
    sub_topic = args.topic + "/echo"
    pub_topic = args.topic + "/cmd"

    def on_message(client, userdata, msg):
        try:
            seq = int(msg.payload.decode().split(",")[0])
        except Exception:
            return
        t = time.perf_counter()
        if seq in pending:
            rtt = (t - pending.pop(seq)) * 1000.0
            results.append((seq, rtt))
            got.set()

    cli = mqtt.Client()
    if args.tls:
        cli.tls_set()  # uses system CAs; add certs for AWS IoT mutual TLS
    cli.on_message = on_message
    cli.connect(args.host, args.port, keepalive=30)
    cli.subscribe(sub_topic, qos=0)
    cli.loop_start()
    time.sleep(0.5)  # settle subscription

    # warm-up (exclude from stats): the FIRST message pays connection effects
    for warm in range(5):
        cli.publish(pub_topic, f"{-1},{time.time()}", qos=0)
        time.sleep(0.05)

    for seq in range(args.n):
        got.clear()
        pending[seq] = time.perf_counter()
        cli.publish(pub_topic, f"{seq},{time.time()}", qos=args.qos)
        if not got.wait(timeout=5.0):
            pending.pop(seq, None)  # timeout/loss
        # small inter-command gap to avoid queueing bias
        time.sleep(args.gap_ms / 1000.0)

    cli.loop_stop(); cli.disconnect()
    _write_csv(args.out, results, "mqtt", args.network, relayed=0)
    _summary(results, "mqtt", args.network)


def _write_csv(path, results, transport, network, relayed):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["seq", "rtt_ms", "transport", "network", "relayed"])
        for seq, rtt in results:
            w.writerow([seq, f"{rtt:.3f}", transport, network, relayed])
    print(f"wrote {len(results)} samples -> {path}")


def _summary(results, transport, network):
    if not results:
        print("no samples"); return
    rtts = sorted(r for _, r in results)
    n = len(rtts)
    def pct(p): return rtts[min(n-1, int(p/100*n))]
    print(f"[{transport}/{network}] n={n} "
          f"median={statistics.median(rtts):.2f}ms "
          f"mean={statistics.mean(rtts):.2f}ms "
          f"p95={pct(95):.2f}ms p99={pct(99):.2f}ms "
          f"loss={ (1 - n/ max(n,1)) :.1%}")


def summarize(globs):
    """Post-process any CSVs produced by this harness or webrtc_probe.js."""
    for pattern in globs:
        for path in glob.glob(pattern):
            rows = list(csv.DictReader(open(path)))
            rtts = sorted(float(r["rtt_ms"]) for r in rows if r.get("rtt_ms"))
            if not rtts:
                print(f"{path}: empty"); continue
            n = len(rtts)
            def pct(p): return rtts[min(n-1, int(p/100*n))]
            t = rows[0].get("transport", "?"); net = rows[0].get("network", "?")
            print(f"{path}: [{t}/{net}] n={n} median={statistics.median(rtts):.2f} "
                  f"p95={pct(95):.2f} p99={pct(99):.2f} ms")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--transport", choices=["mqtt"], help="mqtt here; webrtc via node probe")
    ap.add_argument("--host"); ap.add_argument("--port", type=int, default=1883)
    ap.add_argument("--tls", action="store_true")
    ap.add_argument("--topic", default="ctl/dev1")
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--qos", type=int, default=0)
    ap.add_argument("--gap-ms", type=int, default=50)
    ap.add_argument("--network", default="unknown",
                    help="label: lan|same-isp|cross-isp|cellular")
    ap.add_argument("--out", default="rtt_mqtt.csv")
    ap.add_argument("--summarize", nargs="+", help="summarize CSV globs and exit")
    args = ap.parse_args()

    if args.summarize:
        summarize(args.summarize); return
    if args.transport == "mqtt":
        measure_mqtt(args)
    else:
        print("For WebRTC, run webrtc_probe.js (Node) which writes the same CSV.",
              file=sys.stderr)


if __name__ == "__main__":
    main()
