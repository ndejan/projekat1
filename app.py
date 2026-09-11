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

STRONG_MEDIA = {
    "reuters.com", "apnews.com", "afp.com", "bbc.com", "bbc.co.uk",
    "dw.com", "rferl.org", "slobodnaevropa.org", "n1info.rs", "rts.rs",
    "insajder.net", "vreme.com", "nova.rs", "danas.rs", "021.rs",
    "beta.rs", "fonet.rs", "bg.ac.rs",
}

LOW_SIGNAL_HINTS = (
    "amazon.", "bestbuy.", "costco.", "rule34", "pinterest.", "reddit.",
    "facebook.", "instagram.", "tiktok.", "youtube.", "x.com", "twitter.",
)

STOPWORDS = {
    "da", "li", "je", "su", "se", "u", "na", "i", "a", "za", "od", "do",
    "po", "sa", "ko", "sta", "šta", "kako", "zasto", "zašto", "ovaj", "ova",
    "the", "is", "are", "was", "were", "of", "to", "in", "on", "and",
}


def host_of(url: str) -> str:
    return urlparse(url).netloc.lower().replace("www.", "")


def domain_matches(host: str, domains: set[str]) -> bool:
    return any(host == d or host.endswith("." + d) for d in domains)


def tokenize(text: str) -> set[str]:
    words = re.findall(r"[A-Za-zČĆŽŠĐčćžšđ0-9]{3,}", text.lower())
    return {w for w in words if w not in STOPWORDS}


def source_type(url: str) -> tuple[str, int]:
    host = host_of(url)
    if any(x in host for x in LOW_SIGNAL_HINTS):
        return "Nerelevantan / nizak signal", -100
    if domain_matches(host, PRIMARY_DOMAINS):
        return "Primarni / zvanični izvor", 30
    if domain_matches(host, STRONG_MEDIA):
        return "Informativni izvor", 20
    return "Ostali izvor", 5


def relevance(query: str, title: str, snippet: str) -> tuple[int, int]:
    q = tokenize(query)
    text = tokenize(f"{title} {snippet}")
    hits = len(q & text)
    if not q:
        return 0, 0
    score = round((hits / len(q)) * 60)
    return score, hits


def build_queries(query: str) -> list[str]:
    return [query, f"{query} Srbija", f'"{query}"']


def run_text_search(query: str, limit: int):
    ddgs = DDGS(timeout=12)
    errors = []
    for backend in ("bing", "html", "lite", "auto"):
        try:
            rows = ddgs.text(
                query,
                region="wt-wt",
                safesearch="moderate",
                backend=backend,
                max_results=limit,
            )
            if rows:
                return rows, backend, None
        except Exception as exc:
            errors.append(f"{backend}: {type(exc).__name__}")
    return [], None, "; ".join(errors)


def search_web(query: str, max_results: int = 10):
    collected = {}
    qtokens = tokenize(query)
    min_hits = 1 if len(qtokens) <= 2 else 2
    debug = []

    for q in build_queries(query):
        rows, backend, error = run_text_search(q, max(12, max_results))
        debug.append({"query": q, "backend": backend, "count": len(rows), "error": error})

        for r in rows or []:
            url = r.get("href") or r.get("url")
            if not url:
                continue
            title = (r.get("title") or "").strip()
            snippet = (r.get("body") or r.get("excerpt") or "").strip()
            host = host_of(url)
            kind, authority = source_type(url)
            rel, hits = relevance(query, title, snippet)

            if hits < min_hits or authority < 0:
                continue

            rank = rel + authority
            row = {
                "title": title or host,
                "url": url,
                "snippet": snippet,
                "host": host,
                "kind": kind,
                "relevance": rel,
                "rank": rank,
            }
            old = collected.get(url)
            if old is None or rank > old["rank"]:
                collected[url] = row

    results = sorted(collected.values(), key=lambda x: (-x["rank"], -x["relevance"], x["host"]))

    final = []
    per_host = {}
    for r in results:
        if per_host.get(r["host"], 0) >= 2:
            continue
        final.append(r)
        per_host[r["host"]] = per_host.get(r["host"], 0) + 1
        if len(final) >= max_results:
            break
    return final, debug


def coverage(results):
    if not results:
        return "Nema dovoljno relevantnih izvora", 0
    hosts = len({r["host"] for r in results})
    strong = sum(1 for r in results if r["kind"] != "Ostali izvor")
    highly_relevant = sum(1 for r in results if r["relevance"] >= 40)
    score = min(100, hosts * 6 + strong * 8 + highly_relevant * 5)
    if score >= 70:
        return "Dobra pokrivenost", score
    if score >= 40:
        return "Srednja pokrivenost", score
    return "Ograničena pokrivenost", score


st.title("🔎 Provera izvora")
st.caption("Alat odbacuje nerelevantne rezultate i pokušava više search backend-a ako jedan ne radi.")

query = st.text_area(
    "Unesi tvrdnju, temu ili pitanje",
    placeholder="Primer: studenti su u Beogradu",
)
count = st.slider("Broj rezultata", 5, 15, 10)

if st.button("Proveri", type="primary", use_container_width=True):
    if not query.strip():
        st.warning("Unesi pitanje ili tvrdnju.")
    else:
        with st.spinner("Tražim relevantne izvore..."):
            results, debug = search_web(query.strip(), count)
            label, score = coverage(results)

        st.subheader("Procena pokrivenosti")
        st.progress(score / 100)
        st.write(f"**{label}** — {score}/100")

        if not results:
            st.warning("Pretraga nije našla dovoljno relevantnih rezultata. To ne znači da je tvrdnja netačna.")
            with st.expander("Tehnički detalji pretrage"):
                st.json(debug)
        else:
            for i, r in enumerate(results, 1):
                with st.expander(f"{i}. {r['title']} — {r['host']}", expanded=i <= 3):
                    if r["snippet"]:
                        st.write(r["snippet"])
                    st.markdown(f"[Otvori izvor]({r['url']})")
                    st.caption(f"{r['kind']} · relevantnost {r['relevance']}/60")

st.divider()
st.caption("Rezultat pretrage nije automatska presuda da je tvrdnja tačna ili netačna.")
