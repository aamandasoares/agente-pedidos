# Agente de pedidos

Agente de terminal que busca restaurantes fictícios, consulta cardápios e monta um carrinho usando ferramentas Python. Os cinco restaurantes, seus itens, preços, taxas e tempos são todos fictícios e existem apenas no arquivo `data/restaurants.json`.

## Fluxo

```text
mensagem -> regras locais (ou LLM opcional escolhe ferramenta)
         -> validação da ferramenta -> leitura do JSON -> resultado do carrinho
```

Sem chave, regras de palavras-chave escolhem uma operação sem internet. Com `OPENAI_API_KEY` ou `ANTHROPIC_API_KEY`, o modelo pode escolher uma ferramenta por tool calling. A função Python executa a operação e calcula o valor usando os dados do JSON; não há parâmetro de preço nas ferramentas de adicionar item. A quantidade precisa ser inteira e positiva, e o carrinho impede itens de restaurantes diferentes.

`buscar_restaurantes(categoria, preco_maximo)` considera o menor preço de item de cada restaurante no limite informado. A taxa de entrega e o total são somados pelas ferramentas com os valores do catálogo.

## Tecnologias

- Python 3.11 ou superior
- JSON e biblioteca padrão do Python
- pytest para os testes
- APIs OpenAI ou Anthropic opcionais para escolha de ferramenta; exigem internet e podem gerar custos

## Como rodar

No terminal, entre nesta pasta e execute:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m app.main
```

No macOS ou Linux, ative o ambiente com `source .venv/bin/activate`. O `.env.example` lista as chaves opcionais. A aplicação não carrega `.env` automaticamente; defina a variável no ambiente. Sem chave, nenhuma conexão externa é feita.

## Testes

Com o ambiente virtual ativado, execute `python -m pytest -q`.

## Exemplo de conversa

```text
Você: buscar restaurantes vegana
Agente: [{'id': 'rest-verde', 'nome': 'Verde no Pote', ...}]
Você: ver cardápio do Verde no Pote
Agente: [{'id': 'verde-bowl', 'nome': 'Bowl de Grãos', 'preco': 29.0}, ...]
Você: quero 2 Bowl de Grãos
Agente: {'restaurante': 'Verde no Pote', 'itens': [...], 'subtotal': 58.0, 'taxa_entrega': 5.0, 'total': 63.0}
```

## Limitações e próximos passos

O interpretador local cobre operações simples com palavras-chave e não mantém conversa livre nem endereços de entrega. O modo com LLM depende de conexão, chave e disponibilidade do provedor; erros retornam ao interpretador local. Próximos passos: criar uma suíte de frases variadas para avaliar a interpretação, persistir pedidos e adicionar confirmação explícita antes da finalização.