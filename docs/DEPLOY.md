# 🚀 Guia de Deploy - Mega Sena Analyzer

## 📋 Pré-requisitos

- Conta no [GitHub](https://github.com)
- Conta no [Streamlit Cloud](https://streamlit.io/cloud) (gratuita)
- Git instalado localmente

## 🔧 Passo 1: Preparar Repositório GitHub

### 1.1 Criar repositório no GitHub

1. Acesse [github.com/new](https://github.com/new)
2. Nome: `megasena-analyzer` (ou outro nome de sua escolha)
3. Descrição: "Sistema de análise e geração inteligente de jogos da Mega-Sena"
4. **Importante**: Deixe **PRIVADO** (para proteger seus dados)
5. NÃO marque "Add README" (já temos um)
6. Clique em **Create repository**

### 1.2 Enviar código para o GitHub

Abra o terminal na pasta do projeto e execute:

```bash
# Inicializar Git (se ainda não foi feito)
git init

# Adicionar todos os arquivos
git add .

# Fazer o primeiro commit
git commit -m "Initial commit - Mega Sena Analyzer v2.1.0"

# Conectar com o repositório remoto (substitua SEU-USUARIO)
git remote add origin https://github.com/SEU-USUARIO/megasena-analyzer.git

# Enviar para o GitHub
git branch -M main
git push -u origin main
```

## ☁️ Passo 2: Deploy no Streamlit Cloud

### 2.1 Fazer login no Streamlit Cloud

1. Acesse [share.streamlit.io](https://share.streamlit.io)
2. Faça login com sua conta GitHub
3. Autorize o Streamlit a acessar seus repositórios

### 2.2 Criar novo app

1. Clique em **"New app"**
2. Preencha os campos:
   - **Repository**: `SEU-USUARIO/megasena-analyzer`
   - **Branch**: `main`
   - **Main file path**: `megasena_app.py`
   - **App URL**: `megasena-analyzer` (ou nome personalizado)

### 2.3 Configurar Python Version (IMPORTANTE para PyCaret!)

**Para o PyCaret funcionar**, você DEVE configurar Python 3.11:

1. Clique em **"Advanced settings"**
2. Na seção **"Python version"**, selecione **"3.11"**
3. ⚠️ **NÃO use Python 3.13** (PyCaret ainda não é compatível)

### 2.4 Configurar Secrets (IMPORTANTE!)

**Configure os usuários e senhas**:

1. Ainda em **"Advanced settings"**
2. Na seção **"Secrets"**, copie e cole o conteúdo abaixo:

```toml
[usuarios.leonardo]
senha = "mega2025"
nome = "Leonardo"
email = "leonardo@example.com"
admin = true

[usuarios.demo]
senha = "demo123"
nome = "Usuário Demo"
email = "demo@example.com"
admin = false
```

3. **IMPORTANTE**: Altere as senhas padrão por senhas seguras!
4. Adicione mais usuários se necessário (copie o padrão acima)

### 2.5 Deploy

1. Clique em **"Deploy!"**
2. Aguarde 2-5 minutos para o deploy completar
3. Seu app estará disponível em: `https://megasena-analyzer.streamlit.app`

## 🔐 Segurança

### ✅ O que está protegido:

- ✅ `usuarios.json` - NÃO vai para o GitHub (.gitignore)
- ✅ `meus_cartoes.json` - Seus cartões salvos ficam locais
- ✅ `.streamlit/secrets.toml` - Senhas NÃO vão para o GitHub
- ✅ Autenticação obrigatória para usar o app

### ⚠️ Recomendações:

1. **Sempre use senhas fortes** no Streamlit Cloud
2. **Repositório privado** - Mantenha seu repo privado no GitHub
3. **Backup local** - Seus dados em `meus_cartoes.json` são locais
4. **Atualize senhas** periodicamente no painel do Streamlit

## 🔄 Atualizações

Para atualizar o app após mudanças no código:

```bash
# Fazer commit das alterações
git add .
git commit -m "Descrição da atualização"

# Enviar para o GitHub
git push

# O Streamlit Cloud vai atualizar automaticamente!
```

## 👥 Gerenciar Usuários

### Adicionar novo usuário:

1. Acesse seu app no Streamlit Cloud
2. Vá em **Settings > Secrets**
3. Adicione o novo usuário:

```toml
[usuarios.novo_usuario]
senha = "senha_segura_123"
nome = "Nome do Usuário"
email = "email@example.com"
admin = false
```

4. Salve e o app reiniciará automaticamente

### Alterar senha:

1. **No Streamlit Cloud**: Settings > Secrets > Edite a senha
2. **Localmente**: Edite `usuarios.json` e reinicie o app

## 📊 Monitoramento

No painel do Streamlit Cloud você pode:

- Ver logs em tempo real
- Monitorar uso de recursos
- Ver quantidade de acessos
- Gerenciar versões do app

## ❓ Problemas Comuns

### App não inicia:

- Verifique se `requirements.txt` está correto
- Veja os logs no painel do Streamlit Cloud
- Confirme que os Secrets estão configurados

### Erro de autenticação:

- Verifique se os Secrets foram configurados corretamente
- Confira a formatação TOML (indentação, aspas)

### App lento:

- O plano gratuito tem recursos limitados
- Considere otimizar cache com `@st.cache_data`

## 🎉 Pronto!

Seu app está no ar! Acesse de qualquer lugar:

🌐 **URL**: `https://seu-app.streamlit.app`

👤 **Login**: Use as credenciais configuradas nos Secrets

---

📝 **Dúvidas?** Consulte a [documentação oficial do Streamlit Cloud](https://docs.streamlit.io/streamlit-community-cloud)
