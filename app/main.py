"""Interface interativa do agente de pedidos."""

from pathlib import Path

from app.agent import AgentePedidos
from app.tools import FerramentasPedido


def main() -> None:
    arquivo = Path(__file__).resolve().parents[1] / "data" / "restaurants.json"
    agente = AgentePedidos(FerramentasPedido(arquivo))
    print("Agente de pedidos (catálogo fictício). Digite 'sair' para encerrar.")
    while True:
        try:
            mensagem = input("\nVocê: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAté logo!")
            break
        if mensagem.casefold() in {"sair", "exit", "quit"}:
            print("Até logo!")
            break
        try:
            print(f"\nAgente: {agente.processar(mensagem)}")
        except ValueError as erro:
            print(f"\nAgente: {erro}")


if __name__ == "__main__":
    main()