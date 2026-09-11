import re
from urllib.parse import urlparse

import streamlit as st
from duckduckgo_search import DDGS

st.set_page_config(page_title="Provera izvora", page_icon="🔎", layout="wide")

PRIMARY_DOMAINS = {
    "gov.rs", "parlament.gov.rs", "rik.parlament.gov.rs", "mup.gov.rs",
    "sud.rs", "ustavni.sud.rs", "echr.coe.int", "coe.int", "osce.org",
    "odihr.osce.org", "europa.eu", "ec.europa.eu", "un.org", "ohchr.org",
}

WIRE_AND_PUBLIC_SERVICE = {
    "reuters.com", "apnews.com", "afp.com", "bbc.com", "bbc.co.uk",
    "dw.com", "rferl.org", "slobodnaevropa.org",
}

SERBIAN_NEWS = {
    "n1info.rs", "rts.rs", "insajder.net", "vreme.com", "nova.rs",
    "danas.rs", "021.rs", "beta.rs", "fonet.rs",
}

LOW_SIGNAL_HINTS = (
    "opinion", "kolumna", "blog", "forum", "reddit", "facebook",
    "instagram", "tiktok", "youtube", "x.com", "twitter",
)

STOPWORDS = {
    "da", "li", "je", "su", "se", "u", "na", "i", "a", "za", "od",
    "do", "po", "sa", "ko", "sta", "šta", "kako", "zasto", "zašto",
    "the", "is", "are", "was", "were", "of", "to", "in", "on", "and",
}


def host_of(url: str) -> str:
    return urlparse(url).netloc.lower().replace("www.", "")


def domain_matches(host: str, domains: set[str]) -> bool:
    return any(host == d or host.endswith("." + d) for d in domains)


def source_type(url: str) -> tuple[str, int]:
    host = host_of(url)
    path = urlparse(url).path.lower()
    if domain_matches(host, PRIMARY_DOMAINS):
        return "Primarni / zvanični izvor", 40
    if domain_matches(host, WIRE_AND_PUBLIC_SERVICE):
        return "Međunarodni nezavisni medij", 30
    if domain_matches(host, SERBIAN_NEWS):
        return "Domaći informativni medij", 20
    if any(h in host or h in path for h in LOW_SIGNAL_HINTS):
        return "Komentar / društvena mreža / niži signal", 0
    return "Ostali izvor", 10


def tokenize(text: str) -> set[str]:
    words = re.findall(r"[A-Za-zČĆŽŠĐčćžšđ0-9]{3,}", text.lower())
    return {w for w in words if w not in STOPWORDS}


def relevance_score(query: str, title: str, snippet: str) -> int:
    q = tokenize(query)
    if not q:
        return 0
    title_tokens = tokenize(title)
    snippet_tokens = tokenize(snippet)
    title_hits = len(q & title_tokens)
    snippet_hits = len(q & snippet_tokens)
    return min(40, title_hits * 8 + snippet_hits * 3)


def build_queries(query: str) -> list[str]:
    return [
        query,
        f'{query} official document report statement',
        f'{query} Reuters AP BBC RFE',
    ]


def search_web(query: str, max_results: int = 12):
    collected = {}
    per_query = max(6, min(12, max_results))
    with DDGS() as ddgs:
        for q in build_queries(query):
            try:
                rows = ddgs.text(q, max_results=per_query)
            except Exception:
                rows = []
            for r in rows:
                url = r.get("href") or r.get("url")
                if not url:
                    continue
                title = r.get("title", "") or ""
                snippet = r.get("body", "") or ""
                host = host_of(url)
                kind, authority = source_type(url)
                relevance = relevance_score(query, title, snippet)
                rank = authority + relevance
                row = {
                    "title": title,
                    "url": url,
                    "snippet": snippet,
                    "host": host,
                    "kind": kind,
                    "authority": authority,
                    "relevance": relevance,
                    "rank": rank,
                }
                old = collected.get(url)
                if old is None or row["rank"] > old["rank"]:
                    collected[url] = row

    results = sorted(collected.values(), key=lambda x: (-x["rank"], -x["relevance"], x["host"]))
    final = []
    host_counts = {}
    for r in results:
        host_counts[r["host"]] = host_counts.get(r["host"], 0)
        if host_counts[r["host"]] >= 2:
            continue
        final.append(r)
        host_counts[r["host"]] += 1
        if len(final) >= max_results:
            break
    return final


def coverage_score(results):
    if not results:
        return "Nema dovoljno izvora", 0
    independent_hosts = len({r["host"] for r in results})
    primary = sum(1 for r in results if r["kind"] == "Primarni / zvanični izvor")
    strong_media = sum(1 for r in results if r["kind"] == "Međunarodni nezavisni medij")
    relevant = sum(1 for r in results if r["relevance"] >= 12)
    score = min(100, independent_hosts * 5 + primary * 15 + strong_media * 10 + relevant * 4)
    if score >= 75:
        label = "Jaka pokrivenost — više nezavisnih i/ili primarnih izvora"
    elif score >= 50:
        label = "Dobra pokrivenost — zaključak proveri u primarnim izvorima"
    elif score >= 25:
        label = "Ograničena pokrivenost — potrebna dodatna provera"
    else:
        label = "Slaba pokrivenost — ne izvodi čvrst zaključak"
    return label, score


st.title("🔎 Provera izvora")
st.caption("Pretraga koja rangira relevantnost, primarne izvore i nezavisno potvrđivanje.")

query = st.text_area(
    "Unesi tvrdnju, temu ili pitanje",
    placeholder="Primer: Da li je 15. marta 2025. korišćeno zvučno oružje protiv demonstranata?",
)

col1, col2 = st.columns([1, 3])
with col1:
    count = st.slider("Broj rezultata", 6, 15, 10)
with col2:
    st.info("Rangiranje nije ocena istine. Više rangira relevantne, primarne i nezavisne izvore, a spušta komentare i društvene mreže.")

if st.button("Proveri", type="primary", use_container_width=True):
    if not query.strip():
        st.warning("Unesi pitanje ili tvrdnju.")
    else:
        with st.spinner("Tražim i rangiram više vrsta izvora..."):
            results = search_web(query, count)
            label, score = coverage_score(results)

        st.subheader("Procena kvaliteta pokrivenosti")
        st.progress(score / 100)
        st.write(f"**{label}** — {score}/100")

        primary_results = [r for r in results if r["kind"] == "Primarni / zvanični izvor"]
        media_results = [r for r in results if r["kind"] in {"Međunarodni nezavisni medij", "Domaći informativni medij"}]
        other_results = [r for r in results if r not in primary_results and r not in media_results]

        if primary_results:
            st.subheader("1. Primarni i zvanični izvori")
            for r in primary_results:
                st.markdown(f"**[{r['title'] or r['host']}]({r['url']})**")
                if r["snippet"]:
                    st.write(r["snippet"])
                st.caption(f"{r['host']} · relevantnost {r['relevance']}/40 · rang {r['rank']}")

        if media_results:
            st.subheader("2. Nezavisno izveštavanje")
            for r in media_results:
                with st.expander(f"{r['title'] or r['host']} — {r['host']}"):
                    st.write(r["snippet"] or "Nema dostupnog sažetka.")
                    st.markdown(f"[Otvori izvor]({r['url']})")
                    st.caption(f"{r['kind']} · relevantnost {r['relevance']}/40 · rang {r['rank']}")

        if other_results:
            st.subheader("3. Ostali rezultati")
            for r in other_results:
                with st.expander(f"{r['title'] or r['host']} — {r['host']}"):
                    st.write(r["snippet"] or "Nema dostupnog sažetka.")
                    st.markdown(f"[Otvori izvor]({r['url']})")
                    st.caption(f"{r['kind']} · relevantnost {r['relevance']}/40 · rang {r['rank']}")

        if not results:
            st.warning("Nisam našao dovoljno rezultata. Probaj kraću ili precizniju formulaciju tvrdnje.")

        st.subheader("Kako čitati rezultat")
        st.markdown("""
- **Primarni izvor** ima prednost za pitanje šta je institucija zaista odlučila, objavila ili rekla.
- Za sporne događaje traži **najmanje dva međusobno nezavisna izvora**.
- Visoko rangiran medij nije automatski dokaz da je tvrdnja tačna; proveri na čemu zasniva zaključak.
- Ako primarni izvori i nezavisni mediji daju različitu sliku, tretiraj tvrdnju kao **spornu**, ne kao potvrđenu.
        """)

st.divider()
st.caption("Neutralni alat: rangira kvalitet i relevantnost izvora, ali ne proglašava političke tvrdnje istinitim bez dokaza.")
