# Provera izvora

Neutralna Streamlit aplikacija za proveru tvrdnji kroz više javno dostupnih izvora.

## Pokretanje lokalno

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

## Javni link

Aplikacija je postavljena na Streamlit Community Cloud:

https://blank-app-0jwopabbb1om.streamlit.app/

## QR kod

Za pravljenje novog QR koda:

```bash
python qr.py https://blank-app-0jwopabbb1om.streamlit.app/
```

To kreira fajl `qr_provera_izvora.png`.

## Napomena

Ocena izvora nije automatska ocena istinitosti tvrdnje. Aplikacija prvenstveno meri raznovrsnost izvora i prisustvo jačih ili primarnih izvora.
