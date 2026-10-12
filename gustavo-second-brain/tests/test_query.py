import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from db import get_connection, init_db  # noqa: E402
import query as query_module  # noqa: E402
from query import expand_query, _concepts_matched, _fold  # noqa: E402


def test_synonym_match_counts_as_one_concept_not_two():
    concepts, _ = expand_query("¿Cómo define Gustavo el bias diario?")
    # "direccion" (a synonym of "bias") alone should satisfy the bias
    # concept without needing the literal word "bias" too.
    text = "aqui hablamos de la direccion del precio todos los dias"
    assert _concepts_matched(text, concepts) >= 2


def test_single_coincidental_word_does_not_satisfy_two_concepts():
    concepts, _ = expand_query("¿Qué opina Gustavo sobre invertir en bienes raices en Japon?")
    # only "invertir" appears, in an unrelated sense ("invertir tiempo")
    text = "uno puede invertir mucho tiempo en pantalla sin resultados"
    assert _concepts_matched(text, concepts) < 2


def test_fold_strips_accents_and_lowercases():
    assert _fold("Días") == _fold("dias") == "dias"


def test_expand_query_deduplicates_repeated_word():
    concepts, terms = expand_query("estrategia estrategia estrategia")
    assert len(concepts) == 1
    assert "estrategia" in terms


# --- search(): knowledge-base filter + privacy warning (regression guards) --

def _seed_chunk(conn, source_id, channel, title, url, privacy, include_kb,
                 chunk_id, text, published_at="2024-01-01"):
    conn.execute(
        """INSERT INTO sources
            (source_id, source_type, original_title, original_url, channel,
             published_at, youtube_privacy_status, include_in_knowledge_base)
           VALUES (?, 'youtube', ?, ?, ?, ?, ?, ?)""",
        (source_id, title, url, channel, published_at, privacy, include_kb),
    )
    conn.execute(
        "INSERT INTO chunks (chunk_id, source_id, start_sec, end_sec, text, source_url) "
        "VALUES (?, ?, 0, 10, ?, ?)",
        (chunk_id, source_id, text, url),
    )
    conn.execute("INSERT INTO chunks_search (chunk_id, text) VALUES (?, ?)", (chunk_id, text))


def test_search_excludes_sources_with_include_in_knowledge_base_false(tmp_path):
    db_path = tmp_path / "t.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        _seed_chunk(conn, "YT_A_short", "CanalA", "Un short", "https://y/short", "PUBLIC", 0,
                    "c1", "hablamos de estrategia de trading")
        _seed_chunk(conn, "YT_A_long", "CanalA", "Clase completa", "https://y/long", "PUBLIC", 1,
                    "c2", "hablamos de estrategia de trading a fondo")
        conn.commit()
    finally:
        conn.close()

    results = query_module.search("estrategia trading", min_concept_matches=1, db_path=db_path)

    source_ids = {r["source_id"] for r in results}
    assert "YT_A_long" in source_ids
    assert "YT_A_short" not in source_ids  # excluido: include_in_knowledge_base=0


def test_search_flags_non_public_source_with_privacy_warning_and_no_deep_link_in_cli(tmp_path):
    db_path = tmp_path / "t2.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        _seed_chunk(conn, "YT_A_priv", "CanalA", "Clase VIP", "https://y/priv", "PRIVATE", 1,
                    "c1", "gestion de riesgo y stop loss en la clase privada")
        conn.commit()
    finally:
        conn.close()

    results = query_module.search("riesgo", min_concept_matches=1, db_path=db_path)

    assert len(results) == 1
    assert results[0]["is_public"] is False
    assert results[0]["privacy_warning"] == query_module.PRIVACY_WARNING
    assert "FUENTE PRIVADA" in results[0]["privacy_warning"]


def test_search_public_source_has_no_warning_and_includes_deep_link(tmp_path):
    db_path = tmp_path / "t3.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        _seed_chunk(conn, "YT_A_pub", "CanalA", "Clase publica", "https://y/pub", "PUBLIC", 1,
                    "c1", "gestion de riesgo y stop loss explicado")
        conn.commit()
    finally:
        conn.close()

    results = query_module.search("riesgo", min_concept_matches=1, db_path=db_path)

    assert len(results) == 1
    assert results[0]["is_public"] is True
    assert results[0]["privacy_warning"] is None
    assert results[0]["deep_link"] == "https://y/pub&t=0s"


def test_search_includes_source_id_and_published_at_in_results(tmp_path):
    db_path = tmp_path / "t4.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        _seed_chunk(conn, "YT_A_meta", "CanalA", "Clase", "https://y/m", "PUBLIC", 1,
                    "c1", "sobre el metodo y la estrategia de Gustavo", published_at="2023-07-15")
        conn.commit()
    finally:
        conn.close()

    results = query_module.search("estrategia metodo", min_concept_matches=1, db_path=db_path)

    assert results[0]["source_id"] == "YT_A_meta"
    assert results[0]["published_at"] == "2023-07-15"
