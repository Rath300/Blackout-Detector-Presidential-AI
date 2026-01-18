# Solixa Blackout Risk Demo

Solixa predicts localized blackout risk by combining inverter anomaly signals with severe weather forecasts and historical outage data. The demo provides a mobile-first PWA, a lightweight API, and real SMS alerts via Twilio.

## Quick Start (API)

1. Install requirements

   ```
   pip install -r requirements.txt
   ```

2. Run the Django API

   ```
   python manage.py runserver
   ```

3. Optional: Run the Streamlit analysis UI

   ```
   streamlit run streamlit_app.py
   ```

## Frontend (React + Tailwind + shadcn)

The new UI lives in `solixa-web/` and uses a shadcn-compatible structure with
components in `src/components/ui`.

If you don't have Node.js installed, install it first (macOS example):

```
brew install node
```

Then run:

```
cd solixa-web
npm install
npm run dev
```

Open `http://localhost:5173`.

### shadcn setup (if you need to reinitialize)

```
npx shadcn-ui@latest init
```

Keep components in `src/components/ui` to match shadcn defaults.

### Local .env loading

- Backend reads `.env` from the repo root automatically.
- Frontend uses Vite `.env` in `solixa-web/`.

## Environment Variables (Twilio SMS)

Set these before sending real SMS alerts:

```
export TWILIO_ACCOUNT_SID="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export TWILIO_AUTH_TOKEN="your_auth_token"
export TWILIO_FROM_NUMBER="+1xxxxxxxxxx"
export TWILIO_TO_NUMBER="+1xxxxxxxxxx"
```

## Environment Variables (Azure OpenAI Chatbot)

```
export AZURE_OPENAI_RESPONSES_URL="https://<your-resource>.cognitiveservices.azure.com/openai/responses?api-version=2025-04-01-preview"
export AZURE_OPENAI_KEY="YOUR_AZURE_OPENAI_KEY"
export AZURE_OPENAI_MODEL="gpt-5-mini-2"
```

## API Endpoints

- `GET /api/v1/geocode?query=...`
- `GET /api/v1/weather/forecast?lat=...&lon=...&hours=72`
- `GET /api/v1/weather/alerts?lat=...&lon=...`
- `GET /api/v1/outages/history?state=...&days=365`
- `POST /api/v1/anomalies/score` (JSON body with `records` array or CSV file upload)
- `POST /api/v1/anomalies/sample` (uses bundled `Anomaly_Data.csv`)
- `GET /api/v1/blackout/risk?lat=...&lon=...&facilityType=...`
- `POST /api/v1/alerts/subscribe`
- `POST /api/v1/alerts/test`
- `GET /api/v1/model/metrics`
- `GET /api/v1/model/evaluation`
- `POST /api/v1/chat/county`

## Demo Story (AI Challenge)

Solixa targets hospitals, schools, and emergency services by forecasting blackout risk at a neighborhood level. It combines:

- Inverter anomaly detection (Isolation Forest)
- Weather severity signals (wind, precipitation, active alerts)
- Historical outage patterns (DOE OE-417 sample dataset)

The result is a proactive alert system that surfaces risk ahead of outages, enabling community services to prepare earlier.

## Datasets & Model (County-Level AI)

Recommended datasets for the AI risk model:
- NOAA Storm Events (county-level severe weather history)
- DOE OE-417 annual outage summaries (state-level outage context)
- CDC SVI (county-level vulnerability index)
- NOAA/NWS alerts (real-time severity)
- Open-Meteo forecast (real-time severity)

This demo trains a **Gradient Boosting Classifier** using Storm Events data to learn an outage-likelihood signal, then aggregates county scores for a choropleth map. You can retrain the model with:

```
python -m core.ml.train_risk_model
```

Storm Events files are read from the project root using:
`StormEvents_details-*.csv.gz`
