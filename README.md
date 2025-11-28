# MedSched — Agenda Médica (FastAPI + React/shadcn)

Aplicação completa para agendamento de consultas médicas, organizada em dois módulos independentes:

- **backend/**: FastAPI com domínio rico, regras de agendamento e armazenamento em memória.
- **frontend/**: React + Vite com componentes no estilo shadcn/tailwind consumindo a API em tempo real.

Toda a nomenclatura e textos da aplicação estão em português para favorecer o contexto clínico local.

---

## Arquitetura

- **Domínio centralizado** (`backend/app/domain`): entidades (Usuário, Paciente, Médico, Agenda, SlotAgenda, Consulta), enums (Perfil, StatusConsulta) e regras em `AgendamentoService`. Erros específicos (`ValidationError`, `SchedulingError`) garantem mensagens claras para a UI.
- **API FastAPI** (`backend/app/main.py`): expõe rotas REST para médicos, pacientes, slots de agenda e consultas, incluindo confirmar/cancelar/remarcar. Middleware de CORS liberado para permitir o consumo pelo frontend.
- **Autenticação simples** (`/auth/login`): tokens em memória com perfis ADMIN, MEDICO, PACIENTE. Controle de permissões em cada rota.
- **Persistência híbrida** (`backend/app/storage.py` + `backend/app/db.py`): usuários (admin/médico/paciente) são persistidos em SQLite; slots/consultas continuam em memória para simplicidade de demonstração.
- **Frontend React** (`frontend/src`): Vite + TypeScript, componentes base estilo shadcn (Button, Card, Badge, Select, Input) e dashboards separados para Admin (criação de contas), Médico (gerir agenda) e Paciente (agendar/gerir consultas).
- **Comunicação**: JSON sobre HTTP. Datas trafegam em ISO 8601 e são formatadas no cliente. Após qualquer operação, o frontend refaz o fetch das consultas e slots para refletir o estado do backend.

Estrutura de pastas resumida:

```
medsched/
├── backend/
│   ├── app/
│   │   ├── domain/            # entidades, enums, exceptions, serviços
│   │   ├── main.py            # rotas FastAPI
│   │   ├── schemas.py         # modelos de entrada/saída
│   │   ├── storage.py         # repositório em memória + seed
│   │   ├── __init__.py | __main__.py
│   └── requirements.txt
├── frontend/
│   ├── src/                   # React + shadcn-like components
│   ├── package.json | tsconfig.json | vite.config.ts | tailwind.config.js
└── README.md
```

---

## Como executar

### Backend (FastAPI)
1. Crie um ambiente virtual e instale dependências:
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   # .venv\Scripts\activate   # Windows
   pip install -r requirements.txt
   ```
2. Suba a API (porta padrão 8000):
   ```bash
   # a partir da raiz do repositório:
   uvicorn backend.app.main:app --reload
   # ou dentro de backend/:
   cd backend && uvicorn app.main:app --app-dir ./app --reload
   ```
   A API inicializa já com médicos, pacientes e slots prontos para uso.

### Frontend (React + Vite)
1. Instale dependências:
   ```bash
   cd frontend
   npm install
   ```
2. Crie um arquivo `.env` (opcional) apontando para a API:
   ```bash
   VITE_API_URL=http://localhost:8000
   ```
3. Rode em modo desenvolvimento (porta padrão 5173):
   ```bash
   npm run dev
   ```

---

## Principais rotas da API
- `POST /auth/login` — autenticação simples (Bearer token retornado).
- `GET /me` — dados do usuário logado.
- `GET /medicos?especializacao=cardio` — lista médicos (filtro por especialização).
- `POST /medicos` — cria médico (apenas ADMIN).
- `GET/POST /pacientes` — cria e lista pacientes (apenas ADMIN).
- `GET /agendas/{medico_id}/slots` — slots livres (já desconsidera bloqueios e consultas ativas).
- `POST /agendas/{medico_id}/slots` — médico ou admin libera/bloqueia horários.
- `POST /consultas` — paciente agenda consulta.
- `POST /consultas/{id}/confirmar|cancelar|remarcar` — gerir ciclo de vida com permissão por perfil.
- `GET /consultas` — lista consultas; pacientes/médicos só veem as suas, admin vê todas.

Todas retornam mensagens de erro claras (400) quando alguma regra de negócio é violada.

---

## Fluxo na interface
- **Admin**: faz login, cadastra médicos (múltiplas especializações) e pacientes. Visualiza todas as consultas.
- **Paciente**: filtra médicos por especialização, agenda, cancela ou remarca suas consultas com os médicos que têm slots livres.
- **Médico**: libera novos horários na agenda, vê consultas que lhe pertencem e pode cancelar/remarcar para os pacientes (mantendo histórico).
- A UI sempre refaz a leitura do backend após ações para manter o estado sincronizado.

---

## Decisões de projeto
- **Regra no domínio**: toda validação de horário, bloqueio e conflito fica em `AgendamentoService`, mantendo a API fina e fácil de testar.
- **Seed em memória**: permite demonstrar o app completo sem banco; a troca por persistência real exige apenas implementar repositórios e substituir `MemoryStore`.
- **Autorização pragmática**: controle de papéis (admin/médico/paciente) direto nas rotas para simplificar o exemplo. Apenas médicos confirmam consultas; enquanto pendentes, o slot permanece disponível.
- **UI reativa**: cada operação dispara um novo fetch, evitando estados divergentes; componentes shadcn-like garantem consistência visual.
- **Internacionalização simplificada**: textos e status em português, mantendo enum em maiúsculas para compatibilidade com o backend.

Sinta-se à vontade para expandir com autenticação, repositórios reais ou novas telas seguindo a mesma separação de responsabilidades.

---

## Credenciais seed para teste rápido
- Admin: `admin@medsched.com` / `admin123`
- Médicos: `ana@clinic.com` / `ana123`, `bruno@clinic.com` / `bruno123`
- Pacientes: `joao@email.com` / `joao123`, `maria@email.com` / `maria123`
