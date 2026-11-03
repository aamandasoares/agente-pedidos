"""Ferramentas de pedidos que leem preços exclusivamente do catálogo JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class FerramentasPedido:
    """Mantém o catálogo e um carrinho de um único restaurante por vez."""

    def __init__(self, arquivo_dados: Path) -> None:
        self.restaurantes: list[dict[str, Any]] = json.loads(arquivo_dados.read_text(encoding="utf-8"))
        self._carrinho: list[dict[str, Any]] = []
        self._restaurante_id: str | None = None

    def _restaurante(self, restaurante_id: str) -> dict[str, Any]:
        for restaurante in self.restaurantes:
            if restaurante["id"] == restaurante_id:
                return restaurante
        raise ValueError(f"Restaurante inexistente: {restaurante_id}.")

    def _item(self, restaurante: dict[str, Any], item_id: str) -> dict[str, Any]:
        for item in restaurante["cardapio"]:
            if item["id"] == item_id:
                return item
        raise ValueError(f"Item inexistente no cardápio de {restaurante['nome']}: {item_id}.")

    def buscar_restaurantes(
        self,
        categoria: str | None = None,
        preco_maximo: float | None = None,
    ) -> list[dict[str, Any]]:
        """Lista restaurantes por categoria e menor preço de item até o máximo."""
        if preco_maximo is not None and preco_maximo < 0:
            raise ValueError("O preço máximo não pode ser negativo.")
        encontrados = []
        for restaurante in self.restaurantes:
            if categoria and categoria.casefold() not in restaurante["categoria"].casefold():
                continue
            menor_preco = min(item["preco"] for item in restaurante["cardapio"])
            if preco_maximo is not None and menor_preco > preco_maximo:
                continue
            encontrados.append(
                {
                    "id": restaurante["id"],
                    "nome": restaurante["nome"],
                    "categoria": restaurante["categoria"],
                    "menor_preco_item": menor_preco,
                    "tempo_entrega_min": restaurante["tempo_entrega_min"],
                    "taxa_entrega": restaurante["taxa_entrega"],
                }
            )
        return encontrados

    def ver_cardapio(self, restaurante_id: str) -> list[dict[str, Any]]:
        """Retorna nomes, identificadores e preços lidos do JSON do restaurante."""
        restaurante = self._restaurante(restaurante_id)
        return [dict(item) for item in restaurante["cardapio"]]

    def adicionar_ao_carrinho(self, restaurante_id: str, item_id: str, quantidade: int) -> dict[str, Any]:
        """Adiciona um item com quantidade positiva e preço oficial do catálogo."""
        if type(quantidade) is not int or quantidade <= 0:
            raise ValueError("A quantidade deve ser um número inteiro e positivo.")
        restaurante = self._restaurante(restaurante_id)
        item = self._item(restaurante, item_id)
        if self._restaurante_id is not None and self._restaurante_id != restaurante_id:
            raise ValueError("O carrinho só pode conter itens de um restaurante por vez.")

        self._restaurante_id = restaurante_id
        linha_existente = next((linha for linha in self._carrinho if linha["item_id"] == item_id), None)
        if linha_existente:
            linha_existente["quantidade"] += quantidade
        else:
            self._carrinho.append(
                {
                    "item_id": item_id,
                    "nome": item["nome"],
                    "preco_unitario": item["preco"],
                    "quantidade": quantidade,
                }
            )
        return self.ver_carrinho()

    def remover_do_carrinho(self, item_id: str) -> dict[str, Any]:
        """Remove uma linha pelo identificador; informa claramente se não existir."""
        linha = next((linha for linha in self._carrinho if linha["item_id"] == item_id), None)
        if linha is None:
            raise ValueError(f"Item não encontrado no carrinho: {item_id}.")
        self._carrinho.remove(linha)
        if not self._carrinho:
            self._restaurante_id = None
        return self.ver_carrinho()

    def ver_carrinho(self) -> dict[str, Any]:
        """Mostra itens, subtotais e taxa calculados com os valores do catálogo."""
        if self._restaurante_id is None:
            return {"restaurante": None, "itens": [], "subtotal": 0.0, "taxa_entrega": 0.0, "total": 0.0}
        restaurante = self._restaurante(self._restaurante_id)
        itens = [
            {**linha, "subtotal": round(linha["preco_unitario"] * linha["quantidade"], 2)}
            for linha in self._carrinho
        ]
        subtotal = round(sum(linha["subtotal"] for linha in itens), 2)
        taxa = restaurante["taxa_entrega"]
        return {
            "restaurante": restaurante["nome"],
            "itens": itens,
            "subtotal": subtotal,
            "taxa_entrega": taxa,
            "total": round(subtotal + taxa, 2),
        }

    def finalizar_pedido(self) -> dict[str, Any]:
        """Confirma um resumo do pedido e limpa o carrinho após a finalização."""
        if not self._carrinho:
            raise ValueError("O carrinho está vazio; adicione um item antes de finalizar.")
        pedido = self.ver_carrinho()
        self._carrinho.clear()
        self._restaurante_id = None
        return pedido