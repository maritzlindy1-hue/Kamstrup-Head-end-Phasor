# Kamstrup Estimated Phasor Viewer

This Streamlit app builds an estimated phasor diagram from Kamstrup/MUC values.

## Data required

CSV columns:

- meter
- phase
- voltage
- current
- pf
- power_direction
- var_direction

Example:

```csv
meter,phase,voltage,current,pf,power_direction,var_direction
28500183,L1,230.5,45.2,0.98,import,lagging
28500183,L2,231.0,42.8,0.96,import,lagging
28500183,L3,229.8,47.5,0.97,import,lagging
```

## Render deployment

Use these settings on Render:

- Build command: `pip install -r requirements.txt`
- Start command: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`

## Important

This is an estimated phasor only. It calculates the current angle from:

`angle = arccos(PF)`

It assumes:

- L1 voltage = 0 degrees
- L2 voltage = -120 degrees
- L3 voltage = +120 degrees
- lagging current = behind voltage
- leading current = ahead of voltage
- export = current vector flipped 180 degrees