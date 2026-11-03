"""Interpreta pedidos por regras locais ou solicita uma ferramenta a um LLM."""

from __future__ import annotations

import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from app.tools import FerramentasPedido


def _normalizar(texto: str) -> str:
    sem_acentos = unicodedata.normalize("NFKD", texto.casefold())
    return "".join(caractere for caractere in sem_acentos if not unicodedata.combining(caractere))


class AgentePedidos:
    """Escolhe ferramentas locais; qualquer preço exibido vem das ferramentas."""

    def __init__(self, ferramentas: FerramentasPedido) -> None:
        self.ferramentas = ferramentas

    def processar(self, mensagem: str) -> Any:
        """Tenta tool calling opcional; se indisponível, interpreta por regras."""
        if os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"):
            try:
                decisao = self._decidir_com_llm(mensagem)
                if decisao:
                    nome, argumentos = decisao
                    return self.executar_ferramenta(nome, argumentos)
            except Exception:
                pass
        return self._interpretar_local(mensagem)

    def executar_ferramenta(self, nome: str, argumentos: dict[str, Any]) -> Any:
        """Executa somente as seis ferramentas públicas permitidas."""
        ferramentas = {
            "buscar_restaurantes": self.ferramentas.buscar_restaurantes,
            "ver_cardapio": self.ferramentas.ver_cardapio,
            "adicionar_ao_carrinho": self.ferramentas.adicionar_ao_carrinho,
            "remover_do_carrinho": self.ferramentas.remover_do_carrinho,
            "ver_carrinho": self.ferramentas.ver_carrinho,
            "finalizar_pedido": self.ferramentas.finalizar_pedido,
        }
        if nome not in ferramentas:
            raise ValueError(f"Ferramenta desconhecida: {nome}.")
        return ferramentas[nome](**argumentos)

    def _interpretar_local(self, mensagem: str) -> Any:
        texto = _normalizar(mensagem)
        if any(palavra in texto for palavra in ("finalizar", "fechar pedido", "concluir pedido")):
            return self.ferramentas.finalizar_pedido()
        if any(palavra in texto for palavra in ("remover", "tirar do carrinho")):
            item_encontrado = self._encontrar_item(texto)
            if item_encontrado is None:
                raise ValueError("Não identifiquei qual item você quer remover.")
            _, item = item_encontrado
            return self.ferramentas.remover_do_carrinho(item["id"])
        if "carrinho" in texto or "meu pedido" in texto:
            return self.ferramentas.ver_carrinho()

        restaurante = self._encontrar_restaurante(texto)
        categoria = next(
            (r["categoria"] for r in self.ferramentas.restaurantes if _normalizar(r["categoria"]) in texto),
            None,
        )
        if any(palavra in texto for palavra in ("buscar", "procurar", "opcoes", "restaurante")) or categoria:
            teto_match = re.search(r"ate\s+r?\$?\s*(\d+(?:[.,]\d{1,2})?)", texto)
            teto = float(teto_match.group(1).replace(",", ".")) if teto_match else None
            return self.ferramentas.buscar_restaurantes(categoria, teto)

        if "cardapio" in texto or "menu" in texto:
            if restaurante is None:
                raise ValueError("Diga o nome do restaurante para consultar o cardápio.")
            return self.ferramentas.ver_cardapio(restaurante["id"])

        item_encontrado = self._encontrar_item(texto, restaurante)
        if item_encontrado and any(palavra in texto for palavra in ("adicionar", "colocar", "quero", "pedir", "adiciona")):
            restaurante_item, item = item_encontrado
            quantidade_match = re.search(r"\b(\d+)\b", texto)
            quantidade = int(quantidade_match.group(1)) if quantidade_match else 1
            return self.ferramentas.adicionar_ao_carrinho(restaurante_item["id"], item["id"], quantidade)

        raise ValueError(
            "Não entendi. Peça para buscar restaurantes, ver um cardápio, adicionar item, ver o carrinho ou finalizar."
        )

    def _encontrar_restaurante(self, texto: str) -> dict[str, Any] | None:
        return next(
            (r for r in self.ferramentas.restaurantes if _normalizar(r["nome"]) in texto or r["id"] in texto),
            None,
        )

    def _encontrar_item(
        self,
        texto: str,
        restaurante: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]] | None:
        restaurantes = [restaurante] if restaurante else self.ferramentas.restaurantes
        for candidato in restaurantes:
            for item in candidato["cardapio"]:
                if _normalizar(item["nome"]) in texto or item["id"] in texto:
                    return candidato, item
        return None

    @staticmethod
    def _definicoes_openai() -> list[dict[str, Any]]:
        parametros = {
            "buscar_restaurantes": {
                "type": "object", "properties": {
                    "categoria": {"type": ["string", "null"]},
                    "preco_maximo": {"type": ["number", "null"]},
                }, "required": ["categoria", "preco_maximo"], "additionalProperties": False,
            },
            "ver_cardapio": {"type": "object", "properties": {"restaurante_id": {"type": "string"}}, "required": ["restaurante_id"], "additionalProperties": False},
            "adicionar_ao_carrinho": {"type": "object", "properties": {"restaurante_id": {"type": "string"}, "item_id": {"type": "string"}, "quantidade": {"type": "integer"}}, "required": ["restaurante_id", "item_id", "quantidade"], "additionalProperties": False},
            "remover_do_carrinho": {"type": "object", "properties": {"item_id": {"type": "string"}}, "required": ["item_id"], "additionalProperties": False},
            "ver_carrinho": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
            "finalizar_pedido": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        }
        return [
            {"type": "function", "function": {"name": nome, "description": f"Executa {nome} usando dados validados do catálogo.", "parameters": schema}}
            for nome, schema in parametros.items()
        ]

    def _decidir_com_llm(self, mensagem: str) -> tuple[str, dict[str, Any]] | None:
        """Recebe a escolha do modelo, mas nunca aceita dele valores de preço."""
        catalogo = json.dumps(self.ferramentas.restaurantes, ensure_ascii=False)
        orientacao = (
            "Escolha no máximo uma ferramenta para a mensagem. Use IDs existentes no catálogo. "
            "Não invente restaurantes nem itens; ferramentas calculam todos os preços. "
            f"Catálogo JSON: {catalogo}\nMensagem: {mensagem}"
        )
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            corpo = {
                "model": "gpt-4o-mini", "messages": [{"role": "user", "content": orientacao}],
                "tools": self._definicoes_openai(), "tool_choice": "auto", "temperature": 0,
            }
            request = Request(
                "https://api.openai.com/v1/chat/completions", data=json.dumps(corpo).encode("utf-8"),
                headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}, method="POST",
            )
            with urlopen(request, timeout=15) as response:
                mensagem_modelo = json.loads(response.read())["choices"][0]["message"]
            chamadas = mensagem_modelo.get("tool_calls", [])
            if not chamadas:
                return None
            chamada = chamadas[0]["function"]
            return chamada["name"], json.loads(chamada["arguments"])

        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            ferramentas = [
                {"name": definicao["function"]["name"], "description": definicao["function"]["description"], "input_schema": definicao["function"]["parameters"]}
                for definicao in self._definicoes_openai()
            ]
            corpo = {"model": "claude-3-5-haiku-latest", "max_tokens": 400, "messages": [{"role": "user", "content": orientacao}], "tools": ferramentas}
            request = Request(
                "https://api.anthropic.com/v1/messages", data=json.dumps(corpo).encode("utf-8"),
                headers={"x-api-key": anthropic_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}, method="POST",
            )
            with urlopen(request, timeout=15) as response:
                blocos = json.loads(response.read())["content"]
            chamada = next((bloco for bloco in blocos if bloco.get("type") == "tool_use"), None)
            if chamada is None:
                return None
            return chamada["name"], chamada["input"]
        return None