"""
SCRIPT DE MIGRACAO -- JSON -> SQLite

Uso:
    cd c:\\Projetos\\1.Megasena
    python scripts/migrar_json_para_sqlite.py
"""

import sys
import os
import json
import glob

# Ajusta path para importar modules/ sem instalar como pacote
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.db import (
    inicializar_banco,
    salvar_cartoes_db,
    salvar_historico_db,
    salvar_backtesting_db,
    get_connection,
)


def _ler_json(path: str, default=None):
    if not os.path.exists(path):
        print(f"  [SKIP] {path} não encontrado.")
        return default
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"  [ERRO] {path}: {e}")
        return default


def migrar_cartoes():
    """Migra meus_cartoes.json + data/cartoes_arquivo_*.json"""
    print("\n=== CARTÕES ===")
    total = 0

    fontes = ["meus_cartoes.json"] + sorted(
        glob.glob(os.path.join("data", "cartoes_arquivo_*.json"))
    )

    ids_vistos = set()

    for fonte in fontes:
        dados = _ler_json(fonte, [])
        if not dados:
            continue

        cartoes = []
        for i, c in enumerate(dados, 1):
            if isinstance(c, list):
                c = {
                    'id': f'LEGADO-{fonte}-{i}',
                    'dezenas': c,
                    'estrategia': 'Importado',
                    'vai_jogar': False,
                    'verificado': False,
                    'concurso_alvo': None,
                    'status': 'importado',
                    'data_criacao': None,
                }

            cartao_id = c.get('id')
            if not cartao_id:
                c['id'] = f'LEGADO-{fonte}-{i}'
                cartao_id = c['id']

            if cartao_id in ids_vistos:
                continue
            ids_vistos.add(cartao_id)
            cartoes.append(c)

        ok = salvar_cartoes_db(cartoes)
        print(f"  {fonte}: {len(cartoes)} cartões {'OK' if ok else 'ERRO'}")
        total += len(cartoes)

    print(f"  Total migrado: {total} cartões")
    return total


def migrar_historico():
    """Migra historico_analises.json"""
    print("\n=== HISTÓRICO DE ANÁLISES ===")
    dados = _ler_json("historico_analises.json", [])
    if not dados:
        return 0

    total = 0
    for registro in dados:
        concurso = registro.get('concurso')
        data_analise = registro.get('data_analise', '')
        dezenas = registro.get('dezenas_sorteadas')
        estatisticas = registro.get('estatisticas', {})

        if not concurso or not estatisticas:
            continue

        ok = salvar_historico_db(concurso, data_analise, estatisticas, dezenas)
        if ok:
            total += len(estatisticas)

    print(f"  Registros migrados: {total} linhas (estratégia × concurso)")
    return total


def migrar_backtesting():
    """Migra data/backtesting_resultado.json"""
    print("\n=== BACKTESTING ===")
    dados = _ler_json(os.path.join("data", "backtesting_resultado.json"), {})
    if not dados:
        return 0

    ranking = dados.get('ranking', [])
    parametros = dados.get('parametros', {})

    resultados_formatados = []
    for r in ranking:
        resultados_formatados.append({
            'estrategia': r.get('estrategia'),
            'versao': r.get('versao'),
            'media': r.get('media_por_cartao'),
            'std': r.get('desvio_por_cartao'),
            'ic_inf': r.get('ic95_inf'),
            'ic_sup': r.get('ic95_sup'),
            'quadras_pct': r.get('taxa_jogo_quadra_ou_mais', 0) * 100,
            'quinas_pct': r.get('taxa_jogo_quina_ou_mais', 0) * 100,
        })

    ok = salvar_backtesting_db(resultados_formatados, parametros)
    print(f"  {len(resultados_formatados)} estratégias {'OK' if ok else 'ERRO'}")
    return len(resultados_formatados)


def verificar_banco():
    """Exibe contagens do banco após migração."""
    print("\n=== VERIFICAÇÃO DO BANCO ===")
    conn = get_connection()
    cur = conn.cursor()

    tabelas = ['cartoes', 'historico_analises', 'backtesting', 'config']
    for tabela in tabelas:
        cur.execute(f"SELECT COUNT(*) FROM {tabela}")
        count = cur.fetchone()[0]
        print(f"  {tabela}: {count} registros")

    conn.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    print("=" * 60)
    print("MIGRACAO JSON -> SQLite -- Mega Sena Analyzer")
    print("=" * 60)

    inicializar_banco()
    print(f"\nBanco inicializado em: {os.path.abspath(os.path.join('data', 'megasena.db'))}")

    migrar_cartoes()
    migrar_historico()
    migrar_backtesting()
    verificar_banco()

    print("\n" + "=" * 60)
    print("Migracao concluida. Os arquivos JSON foram mantidos como backup.")
    print("Verifique o banco e entao voce pode arquivar os JSONs em data/backup_json/")
    print("=" * 60)
