"""
SDK MetaMask - Backend API

Implementa o fluxo de autenticação Web3 seguindo o padrão EIP-4361 (Sign-In with Ethereum).
O servidor expõe endpoints para geração de nonce seguro e verificação de assinatura,
conectando o frontend MetaMask ao backend Python de forma totalmente automatizada.
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

import siwe
from siwe import SiweMessage, generate_nonce
from web3 import Web3

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

ALCHEMY_URL = os.getenv("ALCHEMY_API_URL", "")
DOMAIN = os.getenv("DOMAIN", "localhost")
STATEMENT = os.getenv(
    "STATEMENT",
    "Ao assinar esta mensagem, você autentica sua identidade de forma segura e sem senha.",
)
CHAIN_ID = int(os.getenv("CHAIN_ID", "1"))
NONCE_TTL_SECONDS = int(os.getenv("NONCE_TTL_SECONDS", "300"))  # 5 minutos

# ---------------------------------------------------------------------------
# Armazenamento em memória para nonces (em produção, substituir por Redis)
# ---------------------------------------------------------------------------

# Estrutura: { address_lower: {"nonce": str, "expires_at": datetime} }
nonce_store: Dict[str, dict] = {}

# ---------------------------------------------------------------------------
# Inicialização do Web3 (opcional — necessário apenas para EIP-1271)
# ---------------------------------------------------------------------------

web3_provider = None
if ALCHEMY_URL:
    try:
        web3_provider = Web3.HTTPProvider(ALCHEMY_URL)
        logger.info("Provedor Web3 configurado via Alchemy.")
    except Exception as exc:
        logger.warning(f"Não foi possível configurar o provedor Web3: {exc}")

# ---------------------------------------------------------------------------
# Aplicação FastAPI
# ---------------------------------------------------------------------------

app = FastAPI(
    title="SDK MetaMask — Sign-In with Ethereum",
    description=(
        "API de autenticação Web3 baseada no padrão EIP-4361 (SIWE). "
        "Permite que carteiras Ethereum autentiquem usuários sem senhas, "
        "utilizando assinaturas criptográficas verificáveis."
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir o frontend estático
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

# ---------------------------------------------------------------------------
# Modelos de dados
# ---------------------------------------------------------------------------


class NonceResponse(BaseModel):
    nonce: str
    message: str
    expires_in_seconds: int


class VerifyRequest(BaseModel):
    message: str
    signature: str


class VerifyResponse(BaseModel):
    authenticated: bool
    address: str
    did: str
    chain_id: int


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------


def _purge_expired_nonces() -> None:
    """Remove nonces expirados do armazenamento em memória."""
    now = datetime.now(tz=timezone.utc)
    expired = [addr for addr, data in nonce_store.items() if data["expires_at"] < now]
    for addr in expired:
        del nonce_store[addr]
        logger.debug(f"Nonce expirado removido para: {addr}")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Serve o frontend da aplicação."""
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return {"message": "SDK MetaMask API v2.0.0 — acesse /docs para a documentação."}


@app.get(
    "/api/nonce",
    response_model=NonceResponse,
    summary="Gerar nonce de autenticação",
    description=(
        "Gera um nonce criptograficamente seguro e retorna a mensagem SIWE (EIP-4361) "
        "formatada e pronta para ser assinada pelo cliente MetaMask. "
        "O nonce expira automaticamente após o TTL configurado."
    ),
    tags=["Autenticação"],
)
async def get_nonce(address: str, request: Request) -> NonceResponse:
    """
    Recebe o endereço da carteira e retorna uma mensagem SIWE formatada com
    um nonce único e de uso único.
    """
    _purge_expired_nonces()

    # Validação e normalização do endereço
    try:
        checksum_address = Web3.to_checksum_address(address)
    except Exception:
        raise HTTPException(status_code=400, detail="Endereço Ethereum inválido.")

    # Geração do nonce seguro via biblioteca siwe
    nonce = generate_nonce()
    expires_at = datetime.now(tz=timezone.utc) + timedelta(seconds=NONCE_TTL_SECONDS)

    # Construção da mensagem SIWE conforme EIP-4361
    issued_at = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    expiration_time = expires_at.strftime("%Y-%m-%dT%H:%M:%SZ")

    origin = request.headers.get("origin", f"http://{DOMAIN}")
    uri = origin if origin else f"http://{DOMAIN}"

    siwe_message = SiweMessage(
        domain=DOMAIN,
        address=checksum_address,
        statement=STATEMENT,
        uri=uri,
        version="1",
        chain_id=CHAIN_ID,
        nonce=nonce,
        issued_at=issued_at,
        expiration_time=expiration_time,
    )

    formatted_message = siwe_message.prepare_message()

    # Armazena o nonce associado ao endereço
    nonce_store[checksum_address.lower()] = {
        "nonce": nonce,
        "expires_at": expires_at,
    }

    logger.info(f"Nonce gerado para {checksum_address}: {nonce} (expira em {NONCE_TTL_SECONDS}s)")

    return NonceResponse(
        nonce=nonce,
        message=formatted_message,
        expires_in_seconds=NONCE_TTL_SECONDS,
    )


@app.post(
    "/api/verify",
    response_model=VerifyResponse,
    summary="Verificar assinatura SIWE",
    description=(
        "Recebe a mensagem SIWE assinada e a assinatura gerada pelo MetaMask. "
        "Valida a assinatura criptograficamente, verifica o domínio, o nonce e a expiração. "
        "Em caso de sucesso, invalida o nonce (uso único) e retorna o DID do usuário."
    ),
    tags=["Autenticação"],
)
async def verify_signature(body: VerifyRequest) -> VerifyResponse:
    """
    Verifica a assinatura SIWE e autentica o usuário.
    O nonce é invalidado após uso bem-sucedido para prevenir replay attacks.
    """
    _purge_expired_nonces()

    try:
        siwe_message = SiweMessage.from_message(body.message)
    except Exception as exc:
        logger.warning(f"Falha ao parsear mensagem SIWE: {exc}")
        raise HTTPException(status_code=400, detail=f"Mensagem SIWE malformada: {exc}")

    address_lower = siwe_message.address.lower()

    # Verifica se existe um nonce pendente para este endereço
    stored = nonce_store.get(address_lower)
    if not stored:
        raise HTTPException(
            status_code=401,
            detail="Nonce não encontrado ou expirado. Solicite um novo nonce.",
        )

    # Verifica se o nonce da mensagem corresponde ao nonce armazenado
    if siwe_message.nonce != stored["nonce"]:
        raise HTTPException(
            status_code=401,
            detail="Nonce inválido. Possível tentativa de replay attack.",
        )

    # Verifica a assinatura criptográfica via biblioteca siwe
    try:
        siwe_message.verify(
            signature=body.signature,
            domain=DOMAIN,
            nonce=stored["nonce"],
            provider=web3_provider,
        )
    except siwe.ExpiredMessage:
        raise HTTPException(status_code=401, detail="Mensagem SIWE expirada.")
    except siwe.DomainMismatch:
        raise HTTPException(status_code=401, detail="Domínio da mensagem não corresponde ao servidor.")
    except siwe.NonceMismatch:
        raise HTTPException(status_code=401, detail="Nonce da mensagem não corresponde.")
    except siwe.InvalidSignature:
        raise HTTPException(status_code=401, detail="Assinatura criptográfica inválida.")
    except siwe.VerificationError as exc:
        logger.error(f"Erro de verificação SIWE: {exc}")
        raise HTTPException(status_code=401, detail=f"Falha na verificação: {exc}")
    except Exception as exc:
        logger.error(f"Erro inesperado na verificação: {exc}")
        raise HTTPException(status_code=500, detail="Erro interno durante a verificação.")

    # Invalida o nonce após uso bem-sucedido (uso único — previne replay attacks)
    del nonce_store[address_lower]
    logger.info(f"Autenticação bem-sucedida para: {siwe_message.address}")

    return VerifyResponse(
        authenticated=True,
        address=siwe_message.address,
        did=f"did:ethr:{siwe_message.address}",
        chain_id=siwe_message.chain_id,
    )


@app.get(
    "/health",
    summary="Health check",
    tags=["Sistema"],
)
async def health_check():
    """Verifica o status operacional da API."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "domain": DOMAIN,
        "chain_id": CHAIN_ID,
        "active_nonces": len(nonce_store),
    }
