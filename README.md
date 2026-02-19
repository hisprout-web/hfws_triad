# HFWS-TRIAD Dashboard v1

Streamlit dashboard for semi-automatic Draft->Final trade planning using a fixed hedge-fund triad and SEC 13F data.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

## Configuration

- Edit `config/funds.yaml` with funds and 10-digit CIK values.
- If CIK is missing/invalid, that fund is skipped in v1.
- Tuning lives in `config/params.yaml`.
- Anchor window in `config/anchor_windows.yaml`.

## Outputs

- `outputs/universe.csv`
- `outputs/signals_today.csv`
- `outputs/trade_tickets.json`
- `outputs/signals_log.csv`
