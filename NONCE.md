# Entendendo o Conceito de Nonce no Ecossistema Web3

Ao desenvolver aplicações descentralizadas (dApps) e sistemas de autenticação baseados em blockchain, o termo **nonce** (abreviação de *Number Used Once*) é frequentemente mencionado. No entanto, o seu significado e a sua implementação variam drasticamente dependendo do contexto em que é utilizado.

Este documento esclarece a diferença entre os tipos de nonce e demonstra como integrar a autenticação off-chain (como a implementada neste SDK) com a autorização on-chain através de Smart Contracts.

## 1. A Dualidade do Nonce: Off-Chain vs. On-Chain

Para evitar confusões arquiteturais, é fundamental distinguir os dois cenários principais onde o conceito de nonce é aplicado.

### Nonce de Autenticação (Off-Chain)
Este é o nonce utilizado pelo nosso SDK para o fluxo **Sign-In with Ethereum (SIWE)**.
- **Onde vive:** No backend tradicional (servidor, banco de dados ou memória).
- **Propósito:** Prevenir *Replay Attacks* (ataques de repetição) durante o login. Ele garante que uma assinatura criptográfica gerada para acessar o sistema hoje não possa ser interceptada e reutilizada por um invasor amanhã.
- **Ciclo de vida:** Efêmero. O backend gera um valor aleatório, envia ao frontend, o usuário assina e, após a validação bem-sucedida, o nonce é imediatamente invalidado.
- **Por que não colocar no Smart Contract?** Custos de *gas* e latência. Registrar cada tentativa de login na blockchain tornaria o sistema lento e financeiramente inviável, além de expor metadados de acesso do usuário publicamente.

### Nonce de Transação (On-Chain)
Este é o nonce nativo do protocolo Ethereum.
- **Onde vive:** Na própria blockchain.
- **Propósito:** Manter a ordem sequencial das transações de uma carteira e evitar que uma mesma transação de transferência de fundos seja executada duas vezes.
- **Ciclo de vida:** Persistente e incremental. É um contador numérico que aumenta a cada transação confirmada.

## 2. Unindo os Mundos: Autenticação Off-Chain + Autorização On-Chain

Embora a geração do nonce de login não deva ocorrer no Smart Contract, os contratos inteligentes são a ferramenta ideal para a **autorização** (controle de acesso). 

O fluxo ideal para uma aplicação Web3 profissional é:
1. **Autenticação (Off-Chain):** O usuário prova que é dono da carteira assinando a mensagem SIWE (gerenciada por este SDK).
2. **Autorização (On-Chain):** Após o login, o backend consulta um Smart Contract para verificar se aquele endereço possui as permissões necessárias (ex: possui um NFT específico, um token de governança ou está em uma *allowlist*).

### Exemplo de Smart Contract em Solidity

Abaixo está um exemplo de um contrato simples que atua como um sistema de permissões. O backend do SDK pode consultar a função `hasAccess` deste contrato logo após validar a assinatura do usuário.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title AccessControlManager
 * @dev Contrato de exemplo para autorização on-chain.
 * Permite que um administrador conceda ou revogue acesso a endereços específicos.
 */
contract AccessControlManager {
    address public admin;
    
    // Mapeamento que define quem tem acesso à aplicação
    mapping(address => bool) private allowlist;

    // Eventos para rastreabilidade na blockchain
    event AccessGranted(address indexed user);
    event AccessRevoked(address indexed user);

    modifier onlyAdmin() {
        require(msg.sender == admin, "Acesso negado: Apenas o administrador pode executar esta acao");
        _;
    }

    constructor() {
        admin = msg.sender; // O criador do contrato torna-se o admin
    }

    /**
     * @dev Concede acesso a um usuario.
     * @param user Endereco da carteira do usuario.
     */
    function grantAccess(address user) external onlyAdmin {
        allowlist[user] = true;
        emit AccessGranted(user);
    }

    /**
     * @dev Revoga o acesso de um usuario.
     * @param user Endereco da carteira do usuario.
     */
    function revokeAccess(address user) external onlyAdmin {
        allowlist[user] = false;
        emit AccessRevoked(user);
    }

    /**
     * @dev Funcao de leitura (view) utilizada pelo Backend para verificar permissao.
     * Esta chamada nao consome gas.
     * @param user Endereco a ser verificado.
     * @return bool Retorna true se o usuario tiver permissao.
     */
    function hasAccess(address user) external view returns (bool) {
        return allowlist[user];
    }
}
```

## 3. Como Testar o Smart Contract na Prática

Você não precisa gastar dinheiro real para testar a integração do seu backend com um Smart Contract. O ecossistema oferece ferramentas gratuitas para desenvolvimento.

### Passo 1: Utilizar o Remix IDE
O [Remix IDE](https://remix.ethereum.org/) é um ambiente de desenvolvimento integrado diretamente no navegador, padrão na indústria Web3.
1. Acesse o Remix IDE.
2. Crie um novo arquivo chamado `AccessControl.sol` e cole o código acima.
3. Na aba *Solidity Compiler* (ícone de "S" no menu lateral), clique em **Compile AccessControl.sol**.

### Passo 2: Obter Criptomoedas de Teste (Faucets)
Para fazer o deploy do contrato em uma rede de testes (Testnet), você precisará de moedas falsas (ETH de teste) para pagar as taxas de *gas*. A rede de testes mais comum atualmente é a **Sepolia**.

Você pode obter ETH de teste gratuitamente utilizando Faucets como o do Google Web3:
- Acesse o [Google Cloud Web3 Faucet](https://cloud.google.com/application/web3/faucet).
- Conecte sua carteira MetaMask (certifique-se de alterar a rede para "Sepolia" nas configurações da carteira).
- Solicite os fundos de teste.

### Passo 3: Deploy e Interação
1. De volta ao Remix, vá para a aba *Deploy & Run Transactions* (ícone do Ethereum).
2. No campo **Environment**, selecione **Injected Provider - MetaMask**. A MetaMask pedirá confirmação para conectar.
3. Clique no botão **Deploy**. A MetaMask abrirá solicitando a aprovação da transação (usando o ETH de teste obtido no Faucet).
4. Após a confirmação, o contrato aparecerá na seção *Deployed Contracts* na parte inferior esquerda.
5. Você poderá interagir com as funções `grantAccess`, `revokeAccess` e `hasAccess` diretamente pela interface do Remix.

Ao finalizar, você pode copiar o endereço do contrato implantado e utilizá-lo no seu backend Python com a biblioteca `web3.py` para consultar a função `hasAccess(address)` de forma totalmente gratuita.
