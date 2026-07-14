# When the Cloud Is the Bottleneck — Artifact

Code, data, and analysis for the paper:

> **When the Cloud Is the Bottleneck: A Peer-to-Peer Control Overlay for Remote
> and Heterogeneous IoT, Measured at Scale**

This repository contains everything needed to **reproduce every number, table,
and figure** in the paper: the browser-based measurement harness, the signaling
server, the raw per-command measurements, and the analysis scripts that generate
the figures.

---

## What was measured

A Windows PC (**controller**) sends control commands to an Android phone
(**gateway / virtual IoT device**, a toggling on-screen LED) over two transports
that are otherwise identical — same hardware, same payload, same batch schedule:

| Transport | Path |
|---|---|
| **P2P** | WebRTC DataChannel, direct peer connection (signaling used once, then idle) |
| **Cloud** | MQTT over WebSocket-secure to a real public broker (HiveMQ) |

Commands are issued in batches of **10, 100, 1 000, 2 000, 5 000, 10 000**, and
the controller times each round trip with the browser's monotonic
`performance.now()` clock.

### Headline results

| Condition | P2P | Cloud | Ratio |
|---|---|---|---|
| Paced (~100 cmd/s), median RTT | **11–22 ms** | 472–933 ms | **29–50× faster** |
| Paced, p99 @ 10 k batch (queueing collapse) | 0.85 s | **21.4 s** | 25× tighter tail |
| Burst (gap = 0), throughput @ 10 k | **3 514 cmd/s** | 2 823 cmd/s | 1.24× |
| Cross-network, steady median (**forced TURN relay**) | **167 ms** | 474 ms | **2.8× faster** |

Loss was **0 %** on every transport in every run.

Three regimes order as expected:
**direct LAN P2P (11–22 ms) < relayed cross-ISP P2P (~167 ms) < cloud (~474 ms).**

---

## Repository layout

```
experiment/     the measurement harness (run this to collect data)
  iot_experiment.html        LAN experiment page (P2P vs Cloud, batch runner, CSV export)
  iot_experiment_xnet.html   cross-network version (adds TURN fields + direct/relay detection)
  server.js                  WebRTC signaling server (WebSocket, ~60 lines)
  package.json

analysis/       scripts that turn raw CSVs into the paper's figures
  analyze_deep.py     paced-load figures (CDF, sequence, tail, ratio, jitter, ...)
  analyze_gap0.py     burst (gap=0) figures + LaTeX table rows
  analyze_xnet.py     cross-network figures + three-regime comparison
  plot_results.py     quick P2P-vs-cloud overview plot
  measure_realtime.py MQTT baseline harness + CSV summarizer
  requirements.txt

data/           raw per-command and per-batch measurements (real, not simulated)
  paced/          gap = 10 ms  (per-command responsiveness)
  burst/          gap = 0      (transport capacity)
  cross-network/  gateway on cellular, controller on Wi-Fi (relayed via TURN)

figures/        all figures used in the paper
docs/           architecture diagram (SVG source)
```

### CSV schema

`raw_*.csv` — one row per command:

```
seq, rtt_ms, transport, network, relayed
```

`summary_*.csv` — one row per batch:

```
batch, sent, recv, loss_pct, median_ms, p95_ms, p99_ms, throughput_cps, transport, network[, relayed]
```

`relayed = 1` means ICE selected a **TURN relay** candidate (direct P2P was
blocked by carrier NAT); `relayed = 0` means a direct path.

---

## Reproducing the experiment

### Requirements

- Windows PC + Android phone (any two devices with Chrome work)
- [Node.js](https://nodejs.org) on the PC
- For the cross-network run: a TURN service (e.g. a free
  [Metered Open Relay](https://www.metered.ca/) account) and
  [ngrok](https://ngrok.com) to expose signaling

### 1. LAN experiment (P2P vs Cloud)

```bash
cd experiment
npm install
node server.js      # terminal 1 — signaling on :8080
npx serve           # terminal 2 — serves the page on :3000
```

Find the PC's IP (`ipconfig`), then open the page on both devices:

- PC: `http://localhost:3000/iot_experiment.html`
- Phone: `http://<PC_IP>:3000/iot_experiment.html`

Set **Phone** → Role `IoT Device`, **PC** → Role `Controller`; both use
signaling `ws://<PC_IP>:8080` and the same Room. Connect both, then on the PC
click **Run all batches** → **Download CSVs**.

Repeat with Transport = **Cloud** to collect the baseline.

> **Keep the phone screen on.** Chrome throttles background tabs, and Android
> Wi-Fi power-save adds ~100–250 ms to every response. This is a real, measured
> effect (see *Data provenance* below) — control it, don't let it surprise you.

### 2. Burst experiment (transport capacity)

Same as above with **Gap = 0**. This removes the ~100 cmd/s sender ceiling and
measures what each transport can actually sustain.

### 3. Cross-network experiment (remote controller)

Use `iot_experiment_xnet.html`. Put the phone on **mobile data** (Wi-Fi off),
expose signaling with `ngrok http 8080`, and use the `wss://…` URL on both
devices. Fill in the TURN url / username / password fields.

The log prints the selected ICE candidate type:

- `DIRECT (srflx)` → true peer-to-peer across two networks
- `RELAY (via TURN)` → carrier NAT blocked direct; **this is a real data point**,
  not a failure — it contributes to the NAT-failure fraction *p*<sub>nat</sub>

Since cross-network measures the *network*, keep it **paced** (gap = 10 ms).
At gap = 0 the phone's actuation rate, not the path, becomes the bottleneck.

---

## Reproducing the figures

```bash
pip install -r analysis/requirements.txt

# burst figures + LaTeX table rows
python analysis/analyze_gap0.py \
    data/burst/raw_p2p_burst_gap0.csv \
    data/burst/raw_cloud_burst_gap0.csv

# cross-network figures + three-regime comparison
python analysis/analyze_xnet.py \
    data/cross-network/raw_p2p_crossisp_relay.csv

# paced-load figures (needs both paced transports — see note below)
python analysis/analyze_deep.py \
    data/paced/raw_p2p_paced_run2.csv \
    data/paced/raw_cloud_paced_run2.csv
```

Each script prints the headline numbers it computes and writes its figures to a
`figs_*/` directory.

---

## Data provenance and honest caveats

We report what we measured, including the parts that are inconvenient.

**Included data is real.** Every CSV here is the direct output of the harness on
physical hardware. Nothing is simulated or synthesized.

**Some paced CSVs are not yet in this repo.** Table I of the paper reports two
independent paced runs for both transports. This repository currently ships the
paced **P2P run-2** file; the paced **run-1** files and the paced **cloud** files
still need to be added from the original collection machine. The burst and
cross-network datasets are complete. *(If you are the author: drop the remaining
`raw_*`/`summary_*` paced CSVs into `data/paced/` and the commands above will
reproduce Table I directly.)*

**Gateway power state is a first-order variable.** Paced run 1 and run 2 differ
by an order of magnitude in P2P median (118–277 ms vs 11–22 ms) purely because
of Android Wi-Fi power-save and background-tab throttling. Run 2 (device held
active) reflects the transport's real capability; run 1 documents what happens
if a production gateway fails to hold a wake lock. We report both.

**The cloud baseline is a shared public broker.** Some of the tail behaviour
reflects multi-tenant contention, which is itself a genuine cost of shared cloud
infrastructure — but it means broker *capacity* and broker *sharing* are not
separated. A self-hosted and a managed-cloud baseline are future work.

**The paced "66 cmd/s cloud ceiling" is not a capacity limit.** An early paced
run showed the broker sustaining only ~66 cmd/s. The burst experiment shows the
*same* broker path reaching ~2 823 cmd/s. The 66 cmd/s figure was a
session-dependent shaping effect, not a hard ceiling — so the honest claim is
that the broker's sustainable rate **varies by more than an order of magnitude
across sessions** (66–2 823 cmd/s) while the P2P path stays consistent.

**The cross-network result is a single session**, on one carrier, through one
public TURN relay, and it was *forced to relay*. It establishes that even P2P's
worst connectivity case beats the cloud — but it is one point, not a
distribution. A multi-carrier campaign to estimate *p*<sub>nat</sub> and capture
the direct (`srflx`) arm is future work.

**The tertiary-device leg is emulated.** The actuator is a virtual on-screen LED
on the gateway, so these numbers cover the controller↔gateway path. The physical
gateway→device hop (Matter and non-Matter) is not yet measured. Because the
emulated leg is identical under both transports, the P2P-vs-cloud comparison is
unaffected.

**A P2P batch-100 burst outlier** (median 460 ms, 57 cmd/s) runs against the
trend, most consistent with SCTP congestion-window slow-start on a cold burst.
It does not recur at larger bursts.

---

## Citation

```bibtex
@inproceedings{p2p-control-overlay,
  title     = {When the Cloud Is the Bottleneck: A Peer-to-Peer Control Overlay
               for Remote and Heterogeneous IoT, Measured at Scale},
  booktitle = {(under review)},
  year      = {2026}
}
```
