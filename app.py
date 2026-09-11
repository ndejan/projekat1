import streamlit as st
from duckduckgo_search import DDGS
from urllib.parse import urlparse

st.set_page_config(page_title="Provera izvora", page_icon="🔎", layout="wide")

TRUSTED_DOMAINS = {
    "reuters.com": 5,
    "apnews.com": 5,
    "afp.com": 5,
    "bbc.com": 4,
    "dw.com": 4,
    "n1info.rs": 3,
    "rts.rs": 3,
    "rik.parlament.gov.rs": 5,
    "parlament.gov.rs": 5,
    "osce.org": 5,
    "odihr.osce.org": 5,
    "coe.int": 5,
    "echr.coe.int": 5,
}

def domain_score(url: str) -> int:
    host = urlparse(url).netloc.lower().replace("www.", "")
    for domain, score in TRUSTED_DOMAINS.items():
        if host == domain or host.endswith("." + domain):
            return score
    return 2

def search_web(query: str, max_results: int = 10):
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            url = r.get("href") or r.get("url")
            if not url:
                continue
            results.append({
                "title": r.get("title", ""),
                "url": url,
                "snippet": r.get("body", ""),
                "score": domain_score(url),
            })
    return results

def classify_sources(results):
    if not results:
        return "Nema dovoljno izvora", 0
    high = sum(1 for r in results if r["score"] >= 4)
    diversity = len(set(urlparse(r["url"]).netloc for r in results))
    score = min(100, high * 18 + diversity * 5)
    if score >= 70:
        label = "Dobra pokrivenost iz više izvora"
    elif score >= 40:
        label = "Mešovita pokrivenost — proveri pažljivo"
    else:
        label = "Slaba pokrivenost — ne izvodi čvrst zaključak"
    return label, score

st.title("🔎 Provera izvora")
st.caption("Neutralni alat za pronalaženje više izvora i razlikovanje činjenica, tvrdnji i komentara.")

query = st.text_area(
    "Unesi tvrdnju, temu ili pitanje",
    placeholder="Primer: Da li je X rekao Y? Šta se tačno dogodilo na protestu...?"
)

col1, col2 = st.columns([1, 3])
with col1:
    count = st.slider("Broj rezultata", 5, 15, 10)
with col2:
    st.info("Ocena ispod nije 'ocena istine'. Ona meri samo raznovrsnost i prisustvo jačih/primarnih izvora.")

if st.button("Proveri", type="primary", use_container_width=True):
    if not query.strip():
        st.warning("Unesi pitanje ili tvrdnju.")
    else:
        with st.spinner("Tražim više izvora..."):
            results = search_web(query, count)
            label, score = classify_sources(results)

        st.subheader("Brza procena pokrivenosti")
        st.progress(score / 100)
        st.write(f"**{label}** — {score}/100")

        st.subheader("Pronađeni izvori")
        for i, r in enumerate(results, 1):
            host = urlparse(r["url"]).netloc.replace("www.", "")
            with st.expander(f"{i}. {r['title'] or host} — {host}"):
                st.write(r["snippet"] or "Nema dostupnog sažetka.")
                st.markdown(f"[Otvori izvor]({r['url']})")
                st.caption(f"Heuristička ocena izvora: {r['score']}/5")

        st.subheader("Kako da doneseš zaključak")
        st.markdown("""
- Traži **primarni izvor**: dokument, snimak, transkript, odluku institucije ili originalnu izjavu.
- Potvrdi važnu tvrdnju u **najmanje dva međusobno nezavisna izvora**.
- Odvoji **činjenicu** od **tumačenja** i političkog komentara.
- Ako se ozbiljni izvori ne slažu, tretiraj zaključak kao **neizvestan**.
- Ne deli naslov ili isečak bez otvaranja originalnog teksta.
        """)

st.divider()
st.caption("Ovaj alat ne bira političku stranu i ne određuje automatski šta je istina. Namenjen je lakšem proveravanju izvora.")
