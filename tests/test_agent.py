from pathlib import Path

from app.agent import AgentePedidos
from app.tools import FerramentasPedido


ARQUIVO_CATALOGO = Path(__file__).resolve().parents[1] / "data" / "restaurants.json"


def criar_agente() -> AgentePedidos:
    return AgentePedidos(FerramentasPedido(ARQUIVO_CATALOGO))


def test_regras_locais_consultam_cardapio() -> None:
    agente = criar_agente()

    resultado = agente.processar("ver cardápio do Verde no Pote")

    assert any(item["id"] == "verde-bowl" for item in resultado)


def test_regras_locais_adicionam_item_com_preco_do_catalogo() -> None:
    agente = criar_agente()

    resultado = agente.processar("quero 2 Bowl de Grãos")

    assert resultado["itens"][0]["preco_unitario"] == 29.0
    assert resultado["subtotal"] == 58.0


def test_regras_locais_removem_item_do_carrinho() -> None:
    agente = criar_agente()
    agente.processar("quero Bowl de Grãos")

    resultado = agente.processar("remover Bowl de Grãos")

    assert resultado["itens"] == []
    assert resultado["restaurante"] is None