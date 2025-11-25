# Guia de Implantação no Streamlit Cloud

## 1. Atualizar o Código no GitHub
O código da aplicação foi corrigido e testado localmente. Agora você precisa enviar essas alterações para o seu repositório no GitHub.

No terminal (ou usando sua ferramenta Git preferida), execute:

```bash
git add .
git commit -m "Fix: Correção de carregamento de dados e autenticação via Secrets"
git push
```

## 2. Configurar Segredos no Streamlit Cloud
Para que a aplicação funcione na nuvem e acesse o Google Sheets, você precisa configurar as credenciais do `service_account.json` como um "Secret".

1. Acesse o painel do seu aplicativo no [Streamlit Cloud](https://share.streamlit.io/).
2. Clique nos três pontos (⋮) ao lado do seu app e vá em **Settings**.
3. Clique na aba **Secrets**.
4. Cole o conteúdo do seu arquivo `service_account.json` (que está na pasta do projeto) no formato TOML, conforme o exemplo abaixo:

```toml
[gsheets]
type = "service_account"
project_id = "seu-project-id"
private_key_id = "seu-private-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\n..."
client_email = "seu-email@..."
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```

**Dica:** Você pode copiar o conteúdo do seu arquivo `service_account.json` e adaptar para o formato TOML acima, ou simplesmente colar o JSON dentro de uma chave, mas o formato TOML com a chave `[gsheets]` é o que o código espera:

```toml
[gsheets]
type = "service_account"
... (copie as chaves e valores do seu JSON)
```
*Atenção: Certifique-se de que a chave `private_key` inclua todas as quebras de linha (`\n`).*

## 3. Verificar a Aplicação
Após salvar os secrets e o deploy ser atualizado (o Streamlit Cloud detectará o push no GitHub), acesse a URL do seu aplicativo e verifique se os dados estão carregando corretamente.
