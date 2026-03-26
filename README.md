# SDK MetaMask - Sign-In with Ethereum (SIWE)

Este repositório fornece uma implementação de referência completa para autenticação descentralizada (Web3) utilizando carteiras Ethereum. O projeto demonstra como substituir sistemas tradicionais baseados em senhas por autenticação via assinaturas criptográficas, garantindo segurança, privacidade e integridade da identidade do usuário.

A arquitetura foi modernizada para adotar o padrão da indústria **EIP-4361 (Sign-In with Ethereum)**, mitigando vulnerabilidades comuns como *Replay Attacks* e *Phishing*.

## Arquitetura 

A versão atual do SDK introduz uma arquitetura robusta dividida entre Frontend e Backend, eliminando a necessidade de processos manuais e garantindo a segurança criptográfica em todas as etapas.

### 1. Padrão Sign-In with Ethereum (EIP-4361)
O sistema não utiliza mais mensagens de texto simples. A implementação adota o padrão SIWE, que estrutura a mensagem de assinatura incluindo o domínio da aplicação, a URI de origem, o identificador da rede (Chain ID) e o tempo de expiração. Isso impede que uma assinatura gerada para a aplicação "A" seja maliciosamente reutilizada na aplicação "B".

### 2. Geração de Nonce Criptograficamente Seguro
O método anterior, que baseava o nonce na contagem de transações da carteira (`get_transaction_count`), foi substituído. O uso de transações como nonce é vulnerável a *Replay Attacks*, pois o valor permanece estático até que uma nova transação on-chain ocorra. 
A nova arquitetura gera um nonce aleatório, criptograficamente seguro e de uso único (One-Time Use) no backend, com um *Time-To-Live* (TTL) rigoroso. Após a verificação bem-sucedida, o nonce é imediatamente invalidado.

### 3. API Backend Integrada (FastAPI)
O processo de verificação foi encapsulado em uma API RESTful de alta performance construída com FastAPI. O backend é responsável por:
- Gerar e armazenar temporariamente nonces seguros.
- Construir a mensagem padronizada SIWE.
- Receber o payload assinado do frontend.
- Validar a assinatura criptográfica (`personal_sign`) contra a chave pública derivada.
- Validar as restrições de domínio, expiração e integridade do nonce.

### 4. Frontend SPA Minimalista
A interface de usuário foi refatorada em uma Single Page Application (SPA) em HTML/JS puro, sem dependências externas complexas. Ela gerencia o ciclo de vida da conexão com o provedor injetado (`window.ethereum`), orquestra as chamadas à API e provê feedback visual contínuo do estado da autenticação.

## Estrutura do Projeto

O repositório está organizado da seguinte forma:

```text
sdk-metamask/
├── backend/
│   ├── main.py              # Aplicação FastAPI e lógica de validação SIWE
│   ├── requirements.txt     # Dependências Python
│   └── .env.example         # Template de variáveis de ambiente
├── frontend/
│   └── index.html           # Interface de usuário e integração Web3
└── README.md                # Documentação técnica
```

## Requisitos do Sistema

- Python 3.9 ou superior
- Pip (Gerenciador de pacotes Python)
- Navegador com extensão MetaMask (ou carteira compatível com EIP-1193) instalada

## Instruções de Instalação e Execução

### 1. Configuração do Backend

Navegue até o diretório do backend e instale as dependências necessárias:

```bash
cd backend
pip install -r requirements.txt
```

Crie o arquivo de configuração de ambiente:

```bash
cp .env.example .env
```

Edite o arquivo `.env` conforme necessário. Para testes locais, os valores padrão são suficientes. Caso necessite validar assinaturas de *Smart Contract Wallets* (EIP-1271), forneça uma URL de provedor RPC válida (ex: Alchemy ou Infura).

### 2. Execução do Servidor

Inicie o servidor FastAPI utilizando o Uvicorn:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

A API estará disponível em `http://localhost:8000`.
A documentação interativa da API (Swagger UI) pode ser acessada em `http://localhost:8000/docs`.

### 3. Acesso à Aplicação

O servidor FastAPI está configurado para servir os arquivos estáticos do frontend. Com o servidor em execução, abra seu navegador e acesse:

```text
http://localhost:8000/
```

## Fluxo de Autenticação (Sequence)

1. **Conexão:** O usuário clica em "Conectar MetaMask". O frontend invoca `eth_requestAccounts` para obter o endereço público.
2. **Desafio (Challenge):** O frontend solicita um nonce ao backend via `GET /api/nonce?address=0x...`.
3. **Geração SIWE:** O backend gera um nonce seguro, constrói a mensagem SIWE (EIP-4361), armazena o nonce em memória e retorna a mensagem ao frontend.
4. **Assinatura:** O frontend apresenta a mensagem ao usuário via MetaMask (`personal_sign`). O usuário assina a mensagem utilizando sua chave privada.
5. **Verificação:** O frontend envia a mensagem original e a assinatura resultante para o backend via `POST /api/verify`.
6. **Autenticação:** O backend recupera o endereço a partir da assinatura, verifica se corresponde ao endereço reivindicado, valida o nonce (prevenindo *replay*), valida o domínio e o tempo de expiração. Em caso de sucesso, o nonce é invalidado e a sessão é autorizada.

## Considerações de Segurança para Produção

Para implantação em ambiente de produção, as seguintes adaptações são estritamente recomendadas:

- **Armazenamento de Nonce:** Substituir o dicionário em memória (`nonce_store`) por um armazenamento persistente de chave-valor com suporte a expiração nativa, como Redis.
- **Gerenciamento de Sessão:** Após a verificação bem-sucedida em `/api/verify`, o backend deve emitir um token de sessão seguro (ex: JWT em cookie *HttpOnly*) para autenticar requisições subsequentes.
- **CORS e Domínios:** Configurar as políticas de CORS no FastAPI para aceitar apenas a origem exata do frontend em produção. Garantir que a variável `DOMAIN` no `.env` reflita o domínio real.
- **TLS/SSL:** Todo o tráfego deve ser roteado exclusivamente via HTTPS. A injeção do provedor Web3 no navegador por parte de carteiras modernas frequentemente requer contextos seguros.

## Referências

- [EIP-4361: Sign-In with Ethereum](https://eips.ethereum.org/EIPS/eip-4361)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [MetaMask Docs: Signing Data](https://docs.metamask.io/wallet/how-to/sign-data/)
