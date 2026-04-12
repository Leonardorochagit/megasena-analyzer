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


def _formatar_moeda_br(valor):
    """Formata valor numérico em padrão brasileiro (R$ 1.234,56)."""
    try:
        v = float(valor)
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return None


def enviar_whatsapp(telefone, apikey, mensagem):
    """
    Envia mensagem via CallMeBot WhatsApp API.
    
    Args:
        telefone: Número com código do país (ex: 5511999999999)
        apikey: Chave da API obtida no registro do CallMeBot
        mensagem: Texto da mensagem
    
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

    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return {'sucesso': True, 'mensagem': 'Mensagem enviada com sucesso!'}
        else:
            return {'sucesso': False, 'mensagem': f'Erro HTTP {response.status_code}: {response.text[:200]}'}
    except requests.exceptions.Timeout:
        return {'sucesso': False, 'mensagem': 'Timeout — CallMeBot não respondeu em 30s'}
    except requests.exceptions.ConnectionError:
        return {'sucesso': False, 'mensagem': 'Erro de conexão — verifique sua internet'}
    except Exception as e:
        return {'sucesso': False, 'mensagem': f'Erro inesperado: {str(e)[:200]}'}


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

    linhas.append("_Enviado pelo Piloto Automático MegaSena_")
    return "\n".join(linhas)
