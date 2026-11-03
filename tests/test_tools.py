from pathlib import Path

import pytest

from app.tools import FerramentasPedido


ARQUIVO_CATALOGO = Path(__file__).resolve().parents[1] / "data" / "restaurants.json"


@pytest.fixture
def ferramentas() -> FerramentasPedido:
    return FerramentasPedido(ARQUIVO_CATALOGO)


def test_preco_do_carrinho_usa_valor_do_json(ferramentas: FerramentasPedido) -> None:
    carrinho = ferramentas.adicionar_ao_carrinho("rest-ipe", "ipe-prato", 2)

    assert carrinho["itens"][0]["preco_unitario"] == 32.0
    assert carrinho["subtotal"] == 64.0
    assert carrinho["total"] == 70.0


def test_bloqueia_itens_de_dois_restaurantes(ferramentas: FerramentasPedido) -> None:
    ferramentas.adicionar_ao_carrinho("rest-ipe", "ipe-prato", 1)

    with pytest.raises(ValueError, match="um restaurante por vez"):
        ferramentas.adicionar_ao_carrinho("rest-forno", "forno-marguerita", 1)


@pytest.mark.parametrize("quantidade", [0, -1, 1.5, True])
def test_quantidade_deve_ser_inteira_positiva(
    ferramentas: FerramentasPedido,
    quantidade: int | float | bool,
) -> None:
    with pytest.raises(ValueError, match="inteiro e positivo"):
        ferramentas.adicionar_ao_carrinho("rest-ipe", "ipe-prato", quantidade)


def test_item_inexistente_retorna_erro_claro(ferramentas: FerramentasPedido) -> None:
    with pytest.raises(ValueError, match="Item inexistente"):
        ferramentas.adicionar_ao_carrinho("rest-ipe", "item-inventado", 1)