Run a short vocal warm-up drill for recording narration for one of the FixFlux videos
(`fixflux/VIDEO_SCRIPT.md`): $ARGUMENTS

Read the target video's scenes first if a video number is given, and pull the actual terms that
appear in it rather than only using the generic list below — the point is rehearsing the words
that will actually be said on camera.

### Generic FixFlux term drill (say each 3x, deliberately, before touching any scene's real lines)

**Protocol / financial jargon**
- FIX protocol — "fix," not spelled out, not "F-I-X"
- MiFID II — "MIF-id two"
- New Order Single, ExecType, ClOrdID
- notional cap, fat-finger check, price-time priority
- best bid, best ask, mid price
- wash trading, rapid-fire, volume spike

**Infra / stack names — these get mispronounced on the first take almost every time**
- Redpanda — "red-PAN-da," not "red-panda" said flat
- Kafka — "KAHF-ka"
- Prometheus — "pro-MEE-thee-us"
- Grafana — "gruh-FAH-na"
- Tempo, Loki, Postgres ("POST-gress," not "post-gray-ess")
- DigitalOcean, Droplet
- kafka-python, aiokafka (say both back to back once, deliberately, since one video explains why
  this repo uses the former and not the latter — don't let them blur together)
- OpenTelemetry — "OH-pen tel-EM-uh-tree"

**Tongue-twister lines pulled from actual scene voice scripts** (say slowly first, then at
speaking pace)
- "Python's sort is stable, so ties keep their original order."
- "The trace ID and span ID get written straight into the dict."
- "A hundred-unit buy comes in against two resting fifty-unit sells."
- "Every service already logs the same way — timestamp, level, module, message."

### Before recording a specific video

1. Open the target `## Video N` section in `VIDEO_SCRIPT.md`.
2. Read every `**Voice Script:**` line once, silently, then once aloud at half speed.
3. Flag (to the user, don't just silently fix) any line that's awkward to say aloud — a script
   that reads fine on the page can still be a bad sentence to *speak*. Suggest a rephrase, keep
   the technical content identical.
4. Do a full read-through of the video at target pace once before the "real" take.
