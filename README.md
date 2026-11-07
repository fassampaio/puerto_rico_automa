# Puerto Rico Automa

Simulador do jogo de tabuleiro **Puerto Rico** (jogo base, 3 a 5 jogadores) com jogadores automáticos, para:

- **jogar contra bots** com níveis de dificuldade e estilos variados;
- **analisar estratégias** rodando milhares de partidas entre bots.

> Projeto de fãs, não oficial e sem fins comerciais. *Puerto Rico* é um jogo de Andreas Seyfarth; nome e marca pertencem às suas editoras. Este repositório implementa apenas a mecânica das regras para fins de simulação e não contém arte, textos do manual nem outros materiais do jogo publicado.

## Situação

| Etapa | Status |
|---|---|
| 1. Motor de regras + testes | ✅ |
| 2. Runner, registro de partidas, torneios | ✅ |
| 3. Bot heurístico com perfis de estilo | ⏳ |
| 4. Interface de terminal para jogar | ⏳ |
| 5. Bot MCTS com níveis de dificuldade | ⏳ |
| 6. Relatórios de análise | ⏳ |

Detalhes do projeto e das interpretações de regras em [ARQUITETURA.md](ARQUITETURA.md).

## Requisitos

Python 3.12 ou mais recente. O motor não tem dependências; os testes usam `pytest`.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/macOS: source .venv/bin/activate)
pip install pytest ruff
```

## Uso

Testes:
```bash
python -m pytest
```

Torneio entre agentes (registra cada partida em JSONL e mostra um resumo):
```bash
python -m puerto_rico tournament --agents random random random random --games 1000 --workers 4 --out logs/torneio.jsonl
```

Narrar uma partida registrada (na tela, ou num arquivo de texto com `-o`):
```bash
python -m puerto_rico show logs/torneio.jsonl --game 0 -o logs/partida0.txt
```

Registros e narrações são gravados só em ASCII (sem acentos nem cedilha).

Velocidade do motor:
```bash
python scripts/bench.py 500 4
```

### Usando o motor em código

```python
from puerto_rico.engine import new_game, legal_actions, step, final_scores

s = new_game(num_players=4, seed=42)
while not s.is_terminal:
    acts = legal_actions(s)   # só aparecem decisões com escolha real
    step(s, acts[0])
print(final_scores(s))
```

## Estrutura

```
puerto_rico/
  engine/     regras puras, determinísticas e clonáveis
  agents/     interface Agent, registro de agentes, RandomAgent
  runner/     partidas, registro JSONL, torneios em paralelo
  analysis/   estatísticas dos torneios
  cli/        linha de comando (python -m puerto_rico)
tests/        testes por regra, de invariantes e do runner
scripts/      utilitários (benchmark)
```

## Licença

[MIT](LICENSE)
