# 🎰 Mega Sena Analyzer - Estrutura Modular

Sistema inteligente de análise e geração de jogos para Mega Sena com estrutura modular organizada.

## 🚀 Início Rápido

```bash
streamlit run megasena_app_simple.py
```

**Login:**
- Usuário: `leonardo`
- Senha: `mega2025`

## 📁 Estrutura do Projeto

```
megasena-analyzer/
│
├── 📱 APLICAÇÃO PRINCIPAL
│   └── megasena_app_simple.py      # App modular (use este!)
│
├── 📦 MÓDULOS
│   └── modules/
│       ├── auth.py                 # Autenticação e login
│       ├── data_manager.py         # Gerenciamento de dados
│       ├── statistics.py           # Cálculos estatísticos
│       ├── game_generator.py       # Geração de jogos
│       ├── visualizations.py       # Gráficos e visualizações
│       └── ui_components.py        # Componentes de interface
│
├── 📚 DOCUMENTAÇÃO
│   └── docs/
│       ├── README_MODULAR.md           # Documentação completa
│       ├── MODULARIZACAO_COMPLETA.md   # Resumo da modularização
│       ├── INICIO_RAPIDO.md            # Guia rápido
│       └── MODULARIZACAO_RESUMO.txt    # Estatísticas
│
├── 🔧 SCRIPTS AUXILIARES
│   └── scripts/
│       ├── testar_estrutura.py         # Verifica estrutura
│       ├── exemplos_uso_modulos.py     # Exemplos de código
│       └── mostrar_estrutura.py        # Diagrama visual
│
├── 💾 DADOS DO USUÁRIO
│   ├── meus_cartoes.json           # Seus cartões salvos
│   ├── usuarios.json               # Usuários do sistema
│   └── data/                       # Simulações e resultados
│
├── 📂 BACKUP (Arquivos Antigos)
│   └── backup/
│       ├── megasena_app.py         # App original (7.388 linhas)
│       └── outros arquivos antigos...
│
└── ⚙️ CONFIGURAÇÃO
    ├── requirements.txt            # Dependências Python
    ├── runtime.txt                # Versão Python (deploy)
    ├── packages.txt               # Pacotes sistema (deploy)
    ├── .streamlit/                # Config Streamlit
    ├── LICENSE                    # Licença MIT
    ├── README.md                  # Este arquivo
    ├── CHANGELOG.md               # Histórico de mudanças
    ├── DOCUMENTACAO.md            # Documentação geral
    └── DEPLOY.md                  # Guia de deploy
```

## ✨ Funcionalidades

### 🎲 Geração de Jogos
- **8 Estratégias Inteligentes:**
  - Atrasados
  - Quentes
  - Equilibrado
  - Misto
  - Escada
  - Consenso
  - Atraso Recente
  - Aleatório Smart

### 📊 Análises Estatísticas
- Frequência Total e Recente
- Atrasos de Números
- Escada Temporal (Inversões)
- Candidatos Ouro
- Análise por Quadrantes
- Soma Gaussiana
- Linhas e Colunas

### 📈 Visualizações
- Gráficos interativos (Plotly)
- Heatmaps
- Distribuições
- Comparações

### 💾 Gerenciamento
- Salvar cartões
- Marcar jogos para apostar
- Verificar resultados
- Histórico de simulações

## 🛠️ Instalação

### 1. Instalar dependências

```bash
pip install -r requirements.txt
```

### 2. Executar aplicação

```bash
streamlit run megasena_app_simple.py
```

### 3. Acessar no navegador

Abre automaticamente em: `http://localhost:8501`

## 📖 Documentação

- **Documentação Completa:** [docs/README_MODULAR.md](docs/README_MODULAR.md)
- **Guia Rápido:** [docs/INICIO_RAPIDO.md](docs/INICIO_RAPIDO.md)
- **Sobre a Modularização:** [docs/MODULARIZACAO_COMPLETA.md](docs/MODULARIZACAO_COMPLETA.md)

## 🧩 Módulos

### auth.py (130 linhas)
Autenticação e controle de acesso
- Login/Logout
- Gerenciamento de usuários
- Controle de sessão

### data_manager.py (216 linhas)
Dados e cartões
- Carrega dados da API
- Salva/carrega cartões
- Verifica resultados

### statistics.py (338 linhas)
Análises estatísticas
- Frequências e atrasos
- Escada temporal
- Candidatos ouro
- Quadrantes
- Soma gaussiana

### game_generator.py (222 linhas)
Geração de jogos
- 8 estratégias diferentes
- Validação de jogos
- Geração avançada

### visualizations.py (278 linhas)
Visualizações
- Gráficos Plotly
- Cards visuais
- Componentes formatados

### ui_components.py (284 linhas)
Interface
- Headers e métricas
- Botões e tags
- Componentes reutilizáveis

## 🧪 Scripts Úteis

### Testar estrutura
```bash
python scripts/testar_estrutura.py
```

### Ver exemplos
```bash
python scripts/exemplos_uso_modulos.py
```

### Diagrama visual
```bash
python scripts/mostrar_estrutura.py
```

## 📊 Estatísticas

- **Arquivo Principal:** 438 linhas (era 7.388)
- **Redução:** 94.1%
- **Módulos:** 6 arquivos especializados
- **Total Modular:** 1.473 linhas

## 🔄 Migração

O arquivo original (`megasena_app.py`) está preservado em `backup/` caso precise consultar alguma funcionalidade antiga.

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

## 📝 Licença

MIT License - veja [LICENSE](LICENSE) para detalhes

## 👤 Autor

**Leonardo Rocha**
- GitHub: [@Leonardorochagit](https://github.com/Leonardorochagit)

## 📮 Suporte

Para problemas ou dúvidas:
1. Consulte a [documentação](docs/README_MODULAR.md)
2. Verifique os [exemplos](scripts/exemplos_uso_modulos.py)
3. Abra uma [issue](https://github.com/Leonardorochagit/megasena-analyzer/issues)

---

**Versão:** 2.1.0 (Modular)  
**Última Atualização:** 13 de Dezembro de 2025

✨ **Estrutura limpa e organizada!** ✨
