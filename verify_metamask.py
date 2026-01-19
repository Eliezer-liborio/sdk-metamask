import os
from web3 import Web3
from eth_account.messages import encode_defunct
from dotenv import load_dotenv
import logging

# Configurar logging para debug
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente
load_dotenv()

# Verificar se a variável de ambiente está carregada
ALCHEMY_URL = os.getenv("ALCHEMY_API_URL")
if not ALCHEMY_URL:
    raise ValueError("ALCHEMY_API_URL não encontrada no arquivo .env")

logger.info(f"Conectando à Alchemy em: {ALCHEMY_URL}")

# Configuração do Web3 com Alchemy
web3 = Web3(Web3.HTTPProvider(ALCHEMY_URL))

# Verificar conexão
if not web3.is_connected():
    raise ConnectionError("Não foi possível conectar ao nó Ethereum")

def generate_nonce(address):
    """Gera um nonce baseado no número de transações da wallet."""
    try:
        nonce = web3.eth.get_transaction_count(address)
        logger.info(f"Nonce gerado para {address}: {nonce}")
        return nonce
    except Exception as e:
        logger.error(f"Erro ao gerar nonce: {e}")
        raise

def verify_signature(address, signature, nonce):
    """Verifica se a assinatura corresponde ao endereço e nonce."""
    message = f"Login E-commerce - Nonce: {nonce}"
    logger.info(f"Verificando mensagem: {message}")
    
    try:
        # Prepara a mensagem no formato Ethereum
        encoded_message = encode_defunct(text=message)
        
        # Recupera o endereço
        recovered_address = web3.eth.account.recover_message(
            encoded_message,
            signature=signature
        )
        logger.info(f"Endereço recuperado: {recovered_address}")
        
        return recovered_address.lower() == address.lower()
    except Exception as e:
        logger.error(f"Erro na verificação: {e}")
        return False

if __name__ == "__main__":
    try:
        user_address = ""
        logger.info(f"Iniciando verificação para: {user_address}")
        
        nonce = generate_nonce(user_address)
        print(f"\nNonce gerado para {user_address}: {nonce}")
        print(f"\n1. Assine a mensagem: 'Login E-commerce - Nonce: {nonce}'")
        
        signature = input("2. Cole a assinatura gerada: ").strip()
        logger.info(f"Assinatura recebida: {signature}")
        
        if verify_signature(user_address, signature, nonce):
            print("\n✅ Assinatura válida! Usuário autenticado.")
            print(f"DID do usuário: did:ethr:{user_address}")
        else:
            print("\n❌ Assinatura inválida! Possível fraude.")
    except Exception as e:
        logger.error(f"Erro no processo principal: {e}")
        print(f"\n⚠️ Erro durante a execução: {e}")
