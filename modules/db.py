"""
================================================================================
MÓDULO DE BANCO DE DADOS — SQLite
================================================================================
Schema, conexão e inicialização do banco megasena.db

Tabelas:
  cartoes            — cartões gerados/salvos (substitui meus_cartoes.json)
  historico_analises — resultados por concurso/estratégia (substitui historico_analises.json)
  backtesting        — resultados de backtesting (substitui data/backtesting_*.json)
  config             — pares chave/valor de configuração (substitui partes do piloto_config.json)
================================================================================
"""

import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "megasena.db")


def get_connection() -> sqlite3.Connection:
    """Retorna uma conexão SQLite com row_factory configurada."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def inicializar_banco():
    """Cria todas as tabelas se não existirem. Seguro para chamar múltiplas vezes."""
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript("""
        -- ── CARTÕES ──────────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS cartoes (
            id                TEXT PRIMARY KEY,
            dezenas           TEXT NOT NULL,          -- JSON array [3,12,15,21,31,40]
            estrategia        TEXT NOT NULL DEFAULT 'desconhecido',
            estrategia_versao TEXT,
            concurso_alvo     INTEGER,
            vai_jogar         INTEGER NOT NULL DEFAULT 0,  -- 0/1
            verificado        INTEGER NOT NULL DEFAULT 0,  -- 0/1
            status            TEXT NOT NULL DEFAULT 'gerado',
            acertos           INTEGER,
            resultado_concurso TEXT,                  -- JSON array das dezenas sorteadas
            data_criacao      TEXT,
            data_verificacao  TEXT,
            qtd_numeros       INTEGER,
            score_ml          REAL,
            prob_media_ml     REAL,
            notas             TEXT                    -- campo livre JSON para extras
        );

        CREATE INDEX IF NOT EXISTS idx_cartoes_concurso   ON cartoes(concurso_alvo);
        CREATE INDEX IF NOT EXISTS idx_cartoes_estrategia ON cartoes(estrategia);
        CREATE INDEX IF NOT EXISTS idx_cartoes_verificado ON cartoes(verificado);
        CREATE INDEX IF NOT EXISTS idx_cartoes_vai_jogar  ON cartoes(vai_jogar);

        -- ── HISTÓRICO DE ANÁLISES ─────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS historico_analises (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            concurso        INTEGER NOT NULL,
            data_analise    TEXT,
            data_registro   TEXT,
            dezenas_sorteadas TEXT,                   -- JSON array
            estrategia      TEXT NOT NULL,
            total_jogos     INTEGER DEFAULT 0,
            total_acertos   INTEGER DEFAULT 0,
            senas           INTEGER DEFAULT 0,
            quinas          INTEGER DEFAULT 0,
            quadras         INTEGER DEFAULT 0,
            ternos          INTEGER DEFAULT 0,
            melhor_acerto   INTEGER DEFAULT 0,
            media_acertos   REAL DEFAULT 0.0,
            UNIQUE(concurso, estrategia)
        );

        CREATE INDEX IF NOT EXISTS idx_hist_concurso   ON historico_analises(concurso);
        CREATE INDEX IF NOT EXISTS idx_hist_estrategia ON historico_analises(estrategia);

        -- ── BACKTESTING ───────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS backtesting (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            data_execucao       TEXT NOT NULL,
            estrategia          TEXT NOT NULL,
            versao              TEXT,
            n_concursos         INTEGER,
            cartoes_por_sorteio INTEGER,
            qtd_numeros         INTEGER,
            media_acertos       REAL,
            desvio_acertos      REAL,
            ic95_inf            REAL,
            ic95_sup            REAL,
            taxa_ternos         REAL,
            taxa_quadras        REAL,
            taxa_quinas         REAL,
            taxa_senas          REAL,
            p_valor_mann_whitney REAL,
            parametros          TEXT                  -- JSON com parametros extras
        );

        CREATE INDEX IF NOT EXISTS idx_bt_estrategia ON backtesting(estrategia);
        CREATE INDEX IF NOT EXISTS idx_bt_data       ON backtesting(data_execucao);

        -- ── CONFIGURAÇÕES ─────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS config (
            chave       TEXT PRIMARY KEY,
            valor       TEXT NOT NULL,
            atualizado  TEXT
        );
    """)

    conn.commit()
    conn.close()


# Inicializa automaticamente na importação
inicializar_banco()


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS INTERNOS
# ─────────────────────────────────────────────────────────────────────────────

def _to_json(val) -> str:
    if isinstance(val, str):
        return val
    return json.dumps(val, ensure_ascii=False)


def _from_json(val):
    if val is None:
        return None
    if isinstance(val, (list, dict)):
        return val
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return val


def _row_to_cartao(row) -> dict:
    """Converte sqlite3.Row para dict no formato legado."""
    d = dict(row)
    d['dezenas'] = _from_json(d.get('dezenas'))
    d['resultado_concurso'] = _from_json(d.get('resultado_concurso'))
    d['notas'] = _from_json(d.get('notas'))
    d['vai_jogar'] = bool(d.get('vai_jogar', 0))
    d['verificado'] = bool(d.get('verificado', 0))
    return d


# ─────────────────────────────────────────────────────────────────────────────
# API — CARTÕES
# ─────────────────────────────────────────────────────────────────────────────

def salvar_cartoes_db(cartoes: list) -> bool:
    """
    Upsert de uma lista de cartões no banco.
    Substitui o registro existente pelo id se já existir.
    """
    if not cartoes:
        return True
    try:
        conn = get_connection()
        cur = conn.cursor()
        for c in cartoes:
            cur.execute("""
                INSERT INTO cartoes (
                    id, dezenas, estrategia, estrategia_versao, concurso_alvo,
                    vai_jogar, verificado, status, acertos, resultado_concurso,
                    data_criacao, data_verificacao, qtd_numeros, score_ml,
                    prob_media_ml, notas
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    dezenas=excluded.dezenas,
                    estrategia=excluded.estrategia,
                    estrategia_versao=excluded.estrategia_versao,
                    concurso_alvo=excluded.concurso_alvo,
                    vai_jogar=excluded.vai_jogar,
                    verificado=excluded.verificado,
                    status=excluded.status,
                    acertos=excluded.acertos,
                    resultado_concurso=excluded.resultado_concurso,
                    data_criacao=excluded.data_criacao,
                    data_verificacao=excluded.data_verificacao,
                    qtd_numeros=excluded.qtd_numeros,
                    score_ml=excluded.score_ml,
                    prob_media_ml=excluded.prob_media_ml,
                    notas=excluded.notas
            """, (
                c.get('id'),
                _to_json(c.get('dezenas', [])),
                c.get('estrategia', 'desconhecido'),
                c.get('estrategia_versao'),
                c.get('concurso_alvo'),
                int(bool(c.get('vai_jogar', False))),
                int(bool(c.get('verificado', False))),
                c.get('status', 'gerado'),
                c.get('acertos'),
                _to_json(c.get('resultado_concurso')),
                c.get('data_criacao'),
                c.get('data_verificacao'),
                c.get('qtd_numeros'),
                c.get('score_ml'),
                c.get('prob_media_ml'),
                _to_json(c.get('notas')),
            ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[db] Erro ao salvar cartões: {e}")
        return False


def carregar_cartoes_db(
    concurso_alvo: int = None,
    verificado: bool = None,
    vai_jogar: bool = None,
    estrategia: str = None,
    limit: int = None,
) -> list:
    """
    Carrega cartões com filtros opcionais.
    Retorna lista de dicts no formato legado.
    """
    conn = get_connection()
    cur = conn.cursor()

    where = []
    params = []

    if concurso_alvo is not None:
        where.append("concurso_alvo = ?")
        params.append(concurso_alvo)
    if verificado is not None:
        where.append("verificado = ?")
        params.append(int(verificado))
    if vai_jogar is not None:
        where.append("vai_jogar = ?")
        params.append(int(vai_jogar))
    if estrategia is not None:
        where.append("estrategia = ?")
        params.append(estrategia)

    sql = "SELECT * FROM cartoes"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY data_criacao DESC"
    if limit:
        sql += f" LIMIT {int(limit)}"

    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return [_row_to_cartao(r) for r in rows]


def deletar_cartao_db(cartao_id: str) -> bool:
    try:
        conn = get_connection()
        conn.execute("DELETE FROM cartoes WHERE id = ?", (cartao_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[db] Erro ao deletar cartão {cartao_id}: {e}")
        return False


def stats_cartoes_db() -> dict:
    """Retorna contagens rápidas sobre os cartões."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            COUNT(*)                                  AS total,
            SUM(CASE WHEN verificado=1 THEN 1 ELSE 0 END) AS verificados,
            SUM(CASE WHEN verificado=0 THEN 1 ELSE 0 END) AS pendentes,
            SUM(CASE WHEN vai_jogar=1  THEN 1 ELSE 0 END) AS vai_jogar,
            COUNT(DISTINCT concurso_alvo)             AS concursos_distintos,
            COUNT(DISTINCT estrategia)                AS estrategias_distintas
        FROM cartoes
    """)
    row = dict(cur.fetchone())
    conn.close()
    return row


# ─────────────────────────────────────────────────────────────────────────────
# API — HISTÓRICO DE ANÁLISES
# ─────────────────────────────────────────────────────────────────────────────

def salvar_historico_db(concurso: int, data_analise: str,
                        estatisticas: dict, dezenas_sorteadas: list = None) -> bool:
    """
    Upsert de estatísticas por concurso/estratégia.
    `estatisticas` é dict {estrategia: {total_jogos, quadras, quinas, ...}}
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        data_registro = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        dez_json = _to_json(dezenas_sorteadas) if dezenas_sorteadas else None

        for estrategia, stats in estatisticas.items():
            cur.execute("""
                INSERT INTO historico_analises (
                    concurso, data_analise, data_registro, dezenas_sorteadas,
                    estrategia, total_jogos, total_acertos, senas, quinas,
                    quadras, ternos, melhor_acerto, media_acertos
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(concurso, estrategia) DO UPDATE SET
                    data_analise=excluded.data_analise,
                    data_registro=excluded.data_registro,
                    dezenas_sorteadas=excluded.dezenas_sorteadas,
                    total_jogos=excluded.total_jogos,
                    total_acertos=excluded.total_acertos,
                    senas=excluded.senas,
                    quinas=excluded.quinas,
                    quadras=excluded.quadras,
                    ternos=excluded.ternos,
                    melhor_acerto=excluded.melhor_acerto,
                    media_acertos=excluded.media_acertos
            """, (
                concurso,
                data_analise,
                data_registro,
                dez_json,
                estrategia,
                stats.get('total_jogos', 0),
                stats.get('total_acertos', 0),
                stats.get('senas', 0),
                stats.get('quinas', 0),
                stats.get('quadras', 0),
                stats.get('ternos', 0),
                stats.get('melhor_acerto', 0),
                stats.get('media_acertos', 0.0),
            ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[db] Erro ao salvar histórico: {e}")
        return False


def carregar_historico_db() -> list:
    """
    Retorna histórico no formato legado:
    [{concurso, data_analise, dezenas_sorteadas, estatisticas: {est: {...}}, data_registro}]
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT concurso, data_analise, data_registro, dezenas_sorteadas,
               estrategia, total_jogos, total_acertos, senas, quinas,
               quadras, ternos, melhor_acerto, media_acertos
        FROM historico_analises
        ORDER BY concurso DESC, estrategia
    """)
    rows = cur.fetchall()
    conn.close()

    por_concurso = {}
    for r in rows:
        c = r['concurso']
        if c not in por_concurso:
            por_concurso[c] = {
                'concurso': c,
                'data_analise': r['data_analise'],
                'data_registro': r['data_registro'],
                'dezenas_sorteadas': _from_json(r['dezenas_sorteadas']),
                'estatisticas': {},
            }
        por_concurso[c]['estatisticas'][r['estrategia']] = {
            'total_jogos': r['total_jogos'],
            'total_acertos': r['total_acertos'],
            'senas': r['senas'],
            'quinas': r['quinas'],
            'quadras': r['quadras'],
            'ternos': r['ternos'],
            'melhor_acerto': r['melhor_acerto'],
            'media_acertos': r['media_acertos'],
        }
    return list(por_concurso.values())


# ─────────────────────────────────────────────────────────────────────────────
# API — BACKTESTING
# ─────────────────────────────────────────────────────────────────────────────

def salvar_backtesting_db(resultados: list, parametros: dict) -> bool:
    """
    Persiste resultados de uma sessão de backtesting.
    `resultados` = lista de dicts por estratégia (saída de pagina_backtesting).
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        data_exec = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        params_json = _to_json(parametros)

        for r in resultados:
            cur.execute("""
                INSERT INTO backtesting (
                    data_execucao, estrategia, versao, n_concursos,
                    cartoes_por_sorteio, qtd_numeros, media_acertos,
                    desvio_acertos, ic95_inf, ic95_sup,
                    taxa_ternos, taxa_quadras, taxa_quinas, taxa_senas,
                    p_valor_mann_whitney, parametros
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                data_exec,
                r.get('estrategia'),
                r.get('versao'),
                parametros.get('n_concursos'),
                parametros.get('cartoes_por_sorteio'),
                parametros.get('qtd_numeros'),
                r.get('media'),
                r.get('std'),
                r.get('ic_inf'),
                r.get('ic_sup'),
                r.get('quadras_pct', 0) / 100 if r.get('quadras_pct') else None,
                r.get('quinas_pct', 0) / 100 if r.get('quinas_pct') else None,
                None,
                None,
                None,
                params_json,
            ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[db] Erro ao salvar backtesting: {e}")
        return False


def carregar_backtesting_db(limit: int = 10) -> list:
    """Retorna as últimas sessões de backtesting."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM backtesting
        ORDER BY data_execucao DESC
        LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# API — CONFIGURAÇÃO
# ─────────────────────────────────────────────────────────────────────────────

def salvar_config_db(chave: str, valor) -> bool:
    try:
        conn = get_connection()
        conn.execute("""
            INSERT INTO config (chave, valor, atualizado)
            VALUES (?, ?, ?)
            ON CONFLICT(chave) DO UPDATE SET
                valor=excluded.valor,
                atualizado=excluded.atualizado
        """, (chave, _to_json(valor), datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[db] Erro ao salvar config '{chave}': {e}")
        return False


def carregar_config_db(chave: str, default=None):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT valor FROM config WHERE chave = ?", (chave,))
        row = cur.fetchone()
        conn.close()
        if row:
            return _from_json(row['valor'])
        return default
    except Exception:
        return default


def carregar_todas_configs_db() -> dict:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT chave, valor FROM config")
        rows = cur.fetchall()
        conn.close()
        return {r['chave']: _from_json(r['valor']) for r in rows}
    except Exception:
        return {}
