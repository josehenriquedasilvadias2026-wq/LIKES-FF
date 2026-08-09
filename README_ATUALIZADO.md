# FreeFire API — versão atualizada

Esta é uma API Flask para consultar informações públicas de jogadores do Free Fire por região e UID. A versão configurada do protocolo é **OB54**.

## Instalação

```bash
pip install -r requirements.txt
python app.py
```

A API inicia por padrão na porta `5000`.

## Endpoint principal

```text
GET /api/infor?region=BR&uid=12335431037
```

Exemplo com `curl`:

```bash
curl "http://127.0.0.1:5000/api/infor?region=BR&uid=12335431037"
```

A resposta é um JSON resumido com nome, UID, bio, likes, nível, experiência, região, data de criação, último login, patentes BR/CS, clã, pet e passe.

## Regiões

As contas regionais são lidas de `Configuration/AccountConfiguration.json`. As regiões suportadas dependem das entradas existentes nesse arquivo, incluindo BR, IND, SG, RU, ID, TW, US, VN, TH, ME, PK, CIS e BD.

## Configuração da conta guest

A API depende de uma conta guest técnica por região para autenticação nos serviços externos do jogo. O arquivo de configuração contém credenciais sensíveis. Não publique esse arquivo em repositórios ou servidores públicos; gere credenciais novas caso elas tenham sido expostas.

## Rotas legadas

As rotas anteriores de estatísticas, perfil detalhado e busca continuam no arquivo `app.py`. A rota recomendada para clientes é `/api/infor`, que aceita apenas `region` e `uid`.

## Limitações

A integração depende de endpoints internos e não oficiais do jogo. Alterações no protocolo, indisponibilidade do serviço de login, expiração de credenciais ou bloqueios regionais podem causar respostas 401, 502 ou timeout.

O servidor embutido do Flask é apropriado para testes locais. Para produção, use um servidor WSGI, autenticação própria, rate limit, logs seguros e variáveis de ambiente para as credenciais.
