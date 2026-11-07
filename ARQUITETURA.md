# Arquitetura — Simulador de Puerto Rico com jogadores automáticos

## Objetivos

1. **Jogar contra bots** com níveis de dificuldade e estilos variados.
2. **Analisar estratégias** rodando milhares de partidas bot × bot.

Escopo da v1: jogo base, 3 a 5 jogadores, interface de terminal, Python 3.13.

## Camadas

```
Interfaces   CLI para jogar · CLI de torneio · (web no futuro)
Execução     GameRunner · Tournament (paralelo) · logs JSONL
Agentes      Random · Heurístico+Perfil · MCTS · Humano · (Evolver)
Análise      estatísticas · ratings (Elo/TrueSkill) · relatórios
Motor        regras puras, sem I/O, determinísticas, clonáveis
```

Dependências só de cima para baixo. O motor não conhece bots, terminal nem arquivos.

## Motor de regras (`puerto_rico/engine`)

| Arquivo | Conteúdo |
|---|---|
| `data.py` | Tabelas estáticas: bens, papéis, prédios, preparação por nº de jogadores |
| `config.py` | `RulesConfig` (nº de jogadores; variantes futuras) |
| `state.py` | `GameState` (estado completo, `clone()` barato) e `Phase` |
| `actions.py` | `Action` (ação atômica) e descrição legível |
| `rules.py` | `new_game`, `legal_actions`, `step`, `apply` e consultas (`building_cost`, ...) |
| `scoring.py` | Pontuação final, bônus dos prédios grandes, desempate |
| `view.py` | `view_for(state, player)`: o que um jogador pode ver |
| `invariants.py` | Verificações de consistência usadas nos testes |

**API:**
```python
s = new_game(num_players=4, seed=42)
s.actor                       # jogador que decide agora
legal_actions(s)              # lista de Action
step(s, action)               # altera s (valida por padrão)
apply(s, action)              # devolve um novo estado
s.is_terminal; final_scores(s); winners(s)
```

**Princípios**
- **Ações atômicas.** Cada decisão é pequena: escolher papel, escolher plantação, colocar *um* colono, construir um prédio, vender um bem, embarcar (bem + navio), guardar bens.
- **Máquina de estados.** `phase` + `actor` dizem quem decide o quê. Não há laços esperando entrada.
- **Decisões forçadas são automáticas.** Se só existe uma jogada válida, o motor a aplica sozinho. Assim os agentes só veem escolhas reais.
- **Determinismo.** Uma partida = `(num_players, seed, ações escolhidas)`, e pode ser reproduzida exatamente.
- **Informação oculta.** Só a ordem da pilha de plantações. `view_for` a esconde (a pilha é ordenada e a semente zerada).

## Agentes (`puerto_rico/agents`)

```python
class Agent(Protocol):
    name: str
    def choose(self, state: GameState, actions: list[Action]) -> Action: ...
```
- `RandomAgent`: testes e linha de base.
- `HeuristicAgent(Profile)`: regras rápidas e configuráveis (inspiradas no DNA do Evolver); também serve de política de simulação do MCTS.
- `MCTSAgent(budget, Profile)`: dificuldade = orçamento + taxa de erro; estilo = Profile.
- `HumanCLIAgent`; `EvolverAgent` (opcional).

## Execução e análise

- `runner/game.py`: `play_game`, `replay`.
- `runner/tournament.py` (etapa 2): sementes controladas, rotação de assentos, multiprocessing, logs JSONL.
- `analysis/` (etapa 6): taxas de vitória, ratings, prédios/papéis × vitória.

## Decisões de interpretação das regras

| Ponto | Decisão |
|---|---|
| Fim do jogo | Ao final da rodada em que: pontos de vitória acabam (no Capitão), alguém ocupa o 12º espaço da cidade, ou faltam colonos para reabastecer o navio no Prefeito |
| Pontos além da reserva | Continuam sendo concedidos (a reserva fica negativa) |
| Prefeito | Cada jogador recolhe todos os seus colonos e os recoloca; não pode deixar colonos em San Juan com espaço livre. As colocações seguem uma ordem canônica (alvos em ordem não decrescente), para não gerar permutações repetidas |
| Reabastecer o navio | max(nº de jogadores, círculos vazios em prédios) |
| Hospice / University | O colono vem da reserva; se ela estiver vazia, do navio |
| Hacienda | Opcional, antes da escolha normal; sem colono do Hospice |
| Capitão | É obrigatório embarcar se possível; para um bem, só são válidos os navios que levam a maior quantidade; um bem que já está num navio (mesmo cheio) não pode ir para um navio vazio. O Wharf é opcional |
| Privilégio do Capitão | +1 PV apenas no primeiro embarque |
| Armazenagem | 1 barril (rosa dos ventos) + tipos inteiros nos armazéns; o motor só oferece opções que guardam o máximo possível |
| Artesão | Falta de bens: distribuição em ordem a partir de quem escolheu o papel. Factory conta os tipos efetivamente recebidos |
| Desempate | Dinheiro + bens |

## Qualidade e desempenho

- pytest: testes por regra e testes de invariantes em partidas aleatórias (conservação de colonos, bens, plantações, prédios e pontos).
- Desempenho: Python puro primeiro. Se faltar velocidade: PyPy, otimizar pontos críticos, ou motor em Rust com a mesma API.

## Roteiro

1. Motor + testes ✅ (46 testes; ~90 partidas aleatórias/s com 4 jogadores — `scripts/bench.py`)
2. Runner, logs, torneio ✅ (`python -m puerto_rico tournament` / `show`; mãos com rotação de assentos; resultado idêntico com qualquer nº de processos)
3. Bot heurístico com perfis ✅ — `agents/heuristic.py`, `evaluation.py`, `mayor.py`, `profiles.py`
   - Avalia cada jogada pelo estado resultante (pontos finais estimados, relativos aos adversários).
   - Papéis: simula a fase inteira com todos jogando pela mesma heurística (níveis médio/difícil).
   - Prefeito: planejador de alocação com pares plantação+prédio (difícil).
   - Calibração (4 jogadores, 120 partidas): difícil 56% · médio 29% · fácil 15% · aleatório 0%.
     Estilos no difícil: exportador 38% · construtor 22% · equilibrado 22% · comerciante 18%.
   - Observação: com esses bots, os assentos 3 e 4 (começam com milho) vencem mais.
4. CLI para jogar
5. MCTS + níveis + calibração por rating
6. Relatórios de análise
7. Opcionais: EvolverAgent, web, expansões
