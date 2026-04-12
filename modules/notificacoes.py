"""
================================================================================
📲 MÓDULO: NOTIFICAÇÕES (WhatsApp via CallMeBot)
================================================================================
Envio de mensagens via WhatsApp usando a API gratuita do CallMeBot.
Registro: envie "I allow callmebot to send me messages" para +34 644 59 71 67
================================================================================
"""

import requests
import urllib.parse
import time
from datetime import datetime


def _formatar_moeda_br(valor):
    """Formata valor numérico em padrão brasileiro (R$ 1.234,56)."""
    try:
        v = float(valor)
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return None


def enviar_whatsapp(telefone, apikey, mensagem, max_tentativas=3, delay_base=5):
    """
    Envia mensagem via CallMeBot WhatsApp API com retry e backoff exponencial.
    
    Args:
        telefone: Número com código do país (ex: 5511999999999)
        apikey: Chave da API obtida no registro do CallMeBot
        mensagem: Texto da mensagem
        max_tentativas: Número máximo de tentativas (padrão: 3)
        delay_base: Delay em segundos entre tentativas (padrão: 5)
    
    Returns:
        dict: {'sucesso': bool, 'mensagem': str}
    """
    if not telefone or not apikey:
        return {'sucesso': False, 'mensagem': 'Telefone ou API key não configurados'}

    telefone_limpo = ''.join(c for c in str(telefone) if c.isdigit())
    texto_codificado = urllib.parse.quote(mensagem)

    url = (
        f"https://api.callmebot.com/whatsapp.php"
        f"?phone={telefone_limpo}"
        f"&text={texto_codificado}"
        f"&apikey={apikey}"
    )

    ultimo_erro = ''
    for tentativa in range(1, max_tentativas + 1):
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                return {'sucesso': True, 'mensagem': 'Mensagem enviada com sucesso!'}
            ultimo_erro = f'Erro HTTP {response.status_code}: {response.text[:200]}'
        except requests.exceptions.Timeout:
            ultimo_erro = 'Timeout — CallMeBot não respondeu em 30s'
        except requests.exceptions.ConnectionError:
            ultimo_erro = 'Erro de conexão — verifique sua internet'
        except Exception as e:
            ultimo_erro = f'Erro inesperado: {str(e)[:200]}'

        if tentativa < max_tentativas:
            time.sleep(delay_base * tentativa)

    return {'sucesso': False, 'mensagem': f'{ultimo_erro} (após {max_tentativas} tentativas)'}


def formatar_resultado_concurso(dados_conferencia):
    """
    Formata os dados de conferência em mensagem legível para WhatsApp.
    
    Args:
        dados_conferencia: dict retornado por _auto_conferir() com status='conferido'
    
    Returns:
        str: Mensagem formatada
    """
    conferidos = dados_conferencia.get('conferidos', [])
    if not conferidos:
        return "Nenhum concurso conferido."

    linhas = ["🎰 *MEGA-SENA — RESULTADO*", ""]

    for conf in conferidos:
        concurso = conf['concurso']
        resultado = conf['resultado']
        total_jogos = conf['total_jogos']
        melhor = conf['melhor_acerto']
        stats = conf.get('stats', {})

        nums = " - ".join(f"{n:02d}" for n in sorted(resultado))
        linhas.append(f"📌 *Concurso {concurso}*")
        linhas.append(f"Resultado: {nums}")
        linhas.append(f"Jogos verificados: {total_jogos}")

        acumulou = conf.get('acumulou')
        if acumulou is True:
            linhas.append("Acumulou: Sim")
        elif acumulou is False:
            linhas.append("Acumulou: Não")

        valor_prox = conf.get('valor_proximo_concurso')
        valor_prox_fmt = _formatar_moeda_br(valor_prox)
        if valor_prox_fmt:
            linhas.append(f"Próximo prêmio estimado: {valor_prox_fmt}")

        linhas.append("")

        # Destaque de acertos
        if melhor >= 4:
            premio = {6: "SENA 🏆🏆🏆", 5: "QUINA 🏆🏆", 4: "QUADRA 🏆"}
            linhas.append(f"🎉 *MELHOR ACERTO: {melhor} ({premio.get(melhor, '')})!*")
        else:
            linhas.append(f"Melhor acerto: {melhor}")
        linhas.append("")

        # Contar premiações totais
        total_senas = sum(s.get('senas', 0) for s in stats.values())
        total_quinas = sum(s.get('quinas', 0) for s in stats.values())
        total_quadras = sum(s.get('quadras', 0) for s in stats.values())

        if total_senas or total_quinas or total_quadras:
            linhas.append("🏅 *Premiações:*")
            if total_senas:
                linhas.append(f"  Senas: {total_senas}")
            if total_quinas:
                linhas.append(f"  Quinas: {total_quinas}")
            if total_quadras:
                linhas.append(f"  Quadras: {total_quadras}")
            linhas.append("")

        # Ranking de todas as estratégias
        if stats:
            ranking = sorted(
                stats.items(),
                key=lambda x: x[1].get('melhor_acerto', 0),
                reverse=True
            )

            linhas.append("📊 *Estratégias:*")
            medalhas = ["🥇", "🥈", "🥉"]
            for i, (est, dados) in enumerate(ranking):
                prefixo = medalhas[i] if i < 3 else "▪️"
                partes = []
                if dados.get('senas'):
                    partes.append(f"{dados['senas']} sena")
                if dados.get('quinas'):
                    partes.append(f"{dados['quinas']} quina")
                if dados.get('quadras'):
                    partes.append(f"{dados['quadras']} quadra")
                if dados.get('ternos'):
                    partes.append(f"{dados['ternos']} terno")
                resumo = " / ".join(partes) if partes else "sem prêmio"
                linhas.append(f"  {prefixo} {est}: {resumo}")

        linhas.append("")

        # Dezenas faltantes para cartões com 3+ acertos
        cartoes_raw = conf.get('cartoes_raw', [])
        quase_acertos = [c for c in cartoes_raw if c.get('acertos', 0) >= 3]
        if quase_acertos:
            linhas.append("🎯 *Quase lá:*")
            for cartao in sorted(quase_acertos, key=lambda c: c.get('acertos', 0), reverse=True)[:5]:
                ac = cartao['acertos']
                faltantes = sorted(set(resultado) - set(cartao['dezenas']))
                est = cartao.get('estrategia', '?')
                nivel = {3: "terno→quadra", 4: "quadra→quina", 5: "quina→sena"}
                linhas.append(f"  [{est}] {ac} ac. — faltou: *{' '.join(f'{n:02d}' for n in faltantes)}* ({nivel.get(ac, '')})")
            linhas.append("")

    linhas.append("_Enviado pelo Piloto Automático MegaSena_")
    return "\n".join(linhas)


# ── Custos importados de helpers (fonte única) ────────────────
from helpers import CUSTOS_CARTAO


def formatar_alerta_bolao(proximo_concurso, valor_premio, config=None):
    """
    Formata mensagem de alerta especial para bolão quando prêmio ≥ threshold.

    Args:
        proximo_concurso: Número do próximo concurso
        valor_premio: Valor estimado do prêmio
        config: Dict com configurações (bolao_qtd_numeros, bolao_estrategias)

    Returns:
        str: Mensagem formatada
    """
    config = config or {}
    qtd = config.get('bolao_qtd_numeros', 13)
    estrategias = config.get('bolao_estrategias', ['misto', 'consenso'])
    custo = CUSTOS_CARTAO.get(qtd, 0)

    linhas = [
        "🚨🚨🚨 *ALERTA DE BOLÃO* 🚨🚨🚨",
        "",
        f"💰 *Prêmio estimado: {_formatar_moeda_br(valor_premio)}*",
        f"📌 Próximo concurso: *{proximo_concurso}*",
        "",
        "📋 *Sugestão de bolão:*",
        f"  Números por cartão: {qtd}",
        f"  Custo por cartão: {_formatar_moeda_br(custo)}",
        f"  Estratégias recomendadas: {', '.join(estrategias)}",
    ]

    if custo > 0:
        cotas_50 = max(1, round(custo / 50))
        valor_cota = round(custo / cotas_50, 2)
        linhas.extend([
            "",
            f"👥 *Bolão sugerido:*",
            f"  ~{cotas_50} cotas de {_formatar_moeda_br(valor_cota)}",
        ])

        # Simulação de prêmio rateado
        premio_quina_est = valor_premio * 0.19  # ~19% do prêmio vai para quina
        if cotas_50 > 0:
            por_cota_sena = valor_premio / cotas_50
            por_cota_quina = premio_quina_est / cotas_50
            linhas.extend([
                "",
                f"💎 *Se ganhar:*",
                f"  Sena: ~{_formatar_moeda_br(por_cota_sena)} por cota",
                f"  Quina: ~{_formatar_moeda_br(por_cota_quina)} por cota",
            ])

    linhas.extend([
        "",
        "⚡ _Acesse o app para gerar os jogos otimizados!_",
        "_Enviado pelo Piloto Automático MegaSena_",
    ])

    return "\n".join(linhas)


def formatar_ranking_global(ranking):
    """
    Formata ranking acumulado de estratégias para WhatsApp.

    Args:
        ranking: dict {estrategia: {total_jogos, senas, quinas, quadras, ternos,
                       media_acertos, taxa_quadra, taxa_terno, concursos, ...}}

    Returns:
        str: Mensagem formatada
    """
    if not ranking:
        return "Nenhum dado de ranking disponível."

    # Ordenar por score: sena*10000 + quina*1000 + quadra*100 + terno*10 + media
    def score(dados):
        return (dados['senas'] * 10000 + dados['quinas'] * 1000 +
                dados['quadras'] * 100 + dados['ternos'] * 10 +
                dados['media_acertos'])

    ordenado = sorted(ranking.items(), key=lambda x: score(x[1]), reverse=True)

    linhas = [
        "📊 *RANKING GLOBAL DE ESTRATÉGIAS*",
        f"📅 Atualizado: {datetime.now().strftime('%d/%m/%Y')}",
        "",
    ]

    medalhas = ["🥇", "🥈", "🥉"]
    for i, (est, d) in enumerate(ordenado):
        prefixo = medalhas[i] if i < 3 else f"{i+1}."
        linhas.append(f"{prefixo} *{est}*")
        concursos = d.get('concursos', '-')
        total_jogos = d.get('total_jogos', d.get('jogos', '-'))
        linhas.append(f"  {concursos} concursos | {total_jogos} jogos")

        premios = []
        if d['senas']:
            premios.append(f"{d['senas']} sena")
        if d['quinas']:
            premios.append(f"{d['quinas']} quina")
        if d['quadras']:
            premios.append(f"{d['quadras']} quadra")
        if d['ternos']:
            premios.append(f"{d['ternos']} terno")
        if premios:
            linhas.append(f"  🏆 {' / '.join(premios)}")
        linhas.append(f"  Média: {d.get('media_acertos', '-')} | Quadra: {d.get('taxa_quadra', '-')}% | Terno: {d.get('taxa_terno', '-')}%")
        linhas.append("")

    linhas.append("_Ranking semanal — Piloto Automático MegaSena_")
    return "\n".join(linhas)


def formatar_dezenas_faltantes(conferidos):
    """
    Para cartões com 3+ acertos, mostra quais números faltaram para quadra/quina.

    Args:
        conferidos: Lista de dicts com dados de conferência (inclui cartões raw)

    Returns:
        str ou None: Mensagem formatada ou None se não houver quase-acertos
    """
    if not conferidos:
        return None

    linhas = ["🎯 *QUASE LÁ — Dezenas faltantes:*", ""]
    tem_conteudo = False

    for conf in conferidos:
        resultado = set(conf['resultado'])
        stats_est = conf.get('stats', {})

        # Usar dados brutos dos cartões se disponíveis
        cartoes_raw = conf.get('cartoes_raw', [])
        for cartao in cartoes_raw:
            acertos = cartao.get('acertos', 0)
            if acertos < 3:
                continue

            dezenas_cartao = set(cartao['dezenas'])
            acertadas = sorted(dezenas_cartao & resultado)
            faltantes = sorted(resultado - dezenas_cartao)

            nivel = {3: "TERNO→QUADRA", 4: "QUADRA→QUINA", 5: "QUINA→SENA"}
            est = cartao.get('estrategia', '?')

            linhas.append(f"  [{est}] {acertos} acertos ({nivel.get(acertos, '')})")
            linhas.append(f"    Acertou: {' '.join(f'{n:02d}' for n in acertadas)}")
            linhas.append(f"    Faltou: *{' '.join(f'{n:02d}' for n in faltantes)}*")
            linhas.append("")
            tem_conteudo = True

    if not tem_conteudo:
        return None

    return "\n".join(linhas)
