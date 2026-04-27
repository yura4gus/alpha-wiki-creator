# Дизайн скила `wiki-creator`

> Универсальный скилл для бутстрапа LLM-вики как памяти для агентов.
> Референсы: Karpathy LLM Wiki + OmegaWiki + skill-creator (Anthropic).

---

## 1. Что делает скилл (одной фразой)

Берёт пустой репозиторий (или существующий проект) и **разворачивает в нём всю инфраструктуру LLM-Wiki**: структуру директорий, runtime-схему `CLAUDE.md`, хуки автоматизации, базовые скиллы для операций (ingest/ask/lint/review), CI для периодического review. На выходе — рабочая память для агентов, в которую можно сразу начинать ингестить материалы.

Принципиально это **не сама вики**, а **генератор вики-инфраструктуры под произвольный проект**. Вики наполняется потом, в ходе работы агентов.

---

## 2. Концептуальная база (что унаследовано от референсов)

### От Karpathy (gist 442a6bf)

Три слоя, ничего больше:
- **Raw** — иммутабельные источники (read-only)
- **Wiki** — LLM-генерируемый markdown, структурированный, с кросс-ссылками
- **Schema** — `CLAUDE.md`, runtime-контракт «как агенту работать с этой вики»

Три операции: **ingest**, **query**, **lint**.
Два служебных файла: **index.md** (каталог), **log.md** (хронология append-only).

### От OmegaWiki (skyllwt/OmegaWiki)

Продакшен-расширения, которые делают идею Карпате реально работающей:
- **Типизированные сущности** (Paper/Concept/Topic/Person/Idea/Experiment/Claim/Summary/Foundations) с YAML-frontmatter и фиксированными секциями.
- **Типизированный граф рёбер** (`graph/edges.jsonl`): `extends`, `contradicts`, `supports`, `inspired_by`, `tested_by`, `invalidates`, `supersedes`, `addresses_gap`, `derived_from`.
- **Bidirectional links enforcement** — при записи forward-ссылки обязательна обратная (формализовано в CLAUDE.md таблицей правил).
- **Auto-generated `graph/`** — `context_brief.md` (≤8000 символов сжатого контекста для агента) и `open_questions.md` собираются скриптом, а не руками.
- **Lint c режимами** `--fix` / `--suggest` / `--dry-run` — детерминированные починки автоматом, эвристики — как саджесты.
- **Скиллы как slash-команды** в `.claude/skills/` (у них 20 штук — `/init`, `/ingest`, `/ask`, `/check` и т.д.).
- **GitHub Actions cron** для периодической работы (у них `daily-arxiv` ежедневно).
- **Anti-repetition memory** — failed ideas с `failure_reason` чтобы агент не возвращался в тупики.

### Что добавляем сверх референсов (твои требования)

1. **Универсальность по доменам** — OmegaWiki жёстко заточен под research (papers/claims/experiments). Наш скилл предлагает **preset-паки** типов сущностей под разные домены (research / software / product / personal / knowledge-base) или композицию своего набора.
2. **Session-end хуки** — после каждой сессии Claude Code автоматически прогоняется review/lint, лог обновляется, агент предлагает что вытащить в wiki из текущего диалога.
3. **Review cycle как явный этап** — не только lint, но и ревью эволюции wiki: контрадикции, устаревшие тезисы, орфаны, дыры в кросс-ссылках, мёртвые тупики.
4. **Слот для встроенных агент-скиллов** — `.claude/agents/` и `.claude/skills/` зарезервированы как часть результата; каждый будущий агент проекта = один скилл, живущий в этой же вики.
5. **Bootstrap-скрипт** — одной командой создаётся вся структура, не надо копировать файлы вручную.

---

## 3. Артефакт на выходе (что появляется в проекте)

```
<project-root>/
├── CLAUDE.md                    # Runtime schema — entry point для агентов
├── README.md                    # Human-facing, кратко описывает зачем wiki
│
├── wiki/                        # Слой LLM-генерируемого знания
│   ├── index.md                 #   Каталог (YAML, content-oriented)
│   ├── log.md                   #   Хронология (append-only, parseable: ## [date] op | desc)
│   ├── <entity-type-N>/         #   Директории по типам сущностей (зависят от пресета)
│   ├── outputs/                 #   Сгенерированные артефакты (отчёты, диаграммы, drafts)
│   └── graph/                   #   AUTO-GENERATED — никогда не редактируется руками
│       ├── edges.jsonl          #     Типизированные рёбра графа
│       ├── context_brief.md     #     Сжатый контекст ≤8000 символов
│       └── open_questions.md    #     Дыры и открытые вопросы
│
├── raw/                         # Иммутабельные источники (read-only кроме /init)
│   ├── docs/                    #   Документы, спеки, white papers
│   ├── transcripts/             #   Транскрипты звонков, встреч
│   ├── chats/                   #   Экспортированные диалоги Claude/прочих LLM
│   └── web/                     #   Сохранённые веб-страницы (md/html)
│
├── .claude/                     # Конфиг агентского рантайма
│   ├── skills/                  #   Slash-команды (см. раздел 5)
│   │   ├── wiki-init/SKILL.md
│   │   ├── wiki-ingest/SKILL.md
│   │   ├── wiki-ask/SKILL.md
│   │   ├── wiki-edit/SKILL.md
│   │   ├── wiki-lint/SKILL.md
│   │   ├── wiki-review/SKILL.md
│   │   └── wiki-prefill/SKILL.md
│   ├── agents/                  #   Слот под будущих агентов проекта (пустой при bootstrap)
│   ├── hooks/                   #   Хуки сессии и операций
│   │   ├── session-end.sh
│   │   ├── post-ingest.sh
│   │   └── pre-commit.sh
│   └── settings.local.json      #   Project-local настройки
│
├── tools/                       # Детерминированные Python-утилиты (не LLM)
│   ├── wiki_engine.py           #   CLI: add-edge, rebuild-context-brief, rebuild-open-questions
│   ├── lint.py                  #   Структурная валидация (broken links, missing fields, orphans)
│   └── _env.py                  #   Загрузка ENV из ~/.env и ./.env
│
├── .github/workflows/           # CI-автоматизация
│   ├── wiki-review.yml          #   Еженедельный /review, автокоммит саджестов в issue
│   └── wiki-lint.yml            #   На каждый push: lint, fail если 🔴
│
├── tests/                       # Тесты для tools/ и валидации скилла
│
├── .env.example
└── .gitignore
```

### Опциональные расширения, не входят в bootstrap по умолчанию

- `mcp-servers/` — если нужен cross-model review через сторонний LLM (как у OmegaWiki).
- `i18n/` — двуязычная вики (как у OmegaWiki: en/ канон + переводы).
- Obsidian-vault конфиг — если пользователь хочет открывать `wiki/` в Obsidian, добавляется `.obsidian/` с настройками graph view, Dataview, hotkeys.

---

## 4. Структура wiki/: три слоя настройки

Структура определяется тремя **ортогональными** параметрами, не одним пресетом. Bootstrap создаёт минимальный жизнеспособный скелет, дальше структура растёт.

| Слой | Что определяет | Когда задаётся |
| --- | --- | --- |
| **A. Preset** | Какой домен (software / research / product / ...) — диктует базовый набор сущностей | На бутстрапе |
| **B. Architectural overlay** | Какая архитектурная оптика (none / clean / hexagonal / ddd / layered) — диктует макро-структуру `wiki/` | На бутстрапе |
| **C. Dynamic evolution** | Какие новые слоты появляются по мере поступления raw-артефактов | Через ingest, по решению пользователя |

Финальная структура = preset × overlay × накопленные через evolution слоты.

---

### 4.1 Слой A — Presets

#### Preset: `software-project` (предполагаемый дефолт для тебя)

Базовый набор (без overlay):

| Тип | Директория | Назначение |
| --- | --- | --- |
| **module** | `modules/` | Архитектурный модуль (BFF, Harvester, CORTEX) |
| **component** | `components/` | UI-компонент или код-юнит внутри модуля |
| **decision** | `decisions/` | ADR — architecture decision record |
| **spec** | `specs/` | Спецификация (PRD, API, протокол) |
| **entity** | `entities/` | Доменная сущность (User, OutputCard, Widget) |
| **contract** | `contracts/` | API-контракт, схема данных (см. 4.3 — раскладывается дальше) |
| **person** | `people/` | Член команды или внешний контакт |
| **task** | `tasks/` | Рабочий элемент (planned → in_progress → done / blocked) |

#### Preset: `research` (как OmegaWiki)

papers / concepts / topics / people / ideas / experiments / claims / foundations / summary

#### Preset: `product`

features / personas / flows / decisions / metrics / experiments / competitors

#### Preset: `personal` (PARA + Zettelkasten)

projects / areas / resources / permanent / fleeting / journals / goals / archive

#### Preset: `knowledge-base` (минимальный универсальный)

entities / concepts / decisions / sources / summaries

#### Composition: `custom`

Skill интервьюирует пользователя по каждой сущности (frontmatter поля, lifecycle, разрешённые связи) и собирает свой пакет.

---

### 4.2 Слой B — Architectural Overlays

Накладывается поверх preset-а. Заменяет/расширяет макро-структуру `wiki/` так, чтобы она отражала выбранный архитектурный паттерн. Влияет также на cross-reference rules (некоторые направления связей запрещаются — например, dependency rule в Clean Architecture).

#### `overlay: none` (default)

Preset разворачивается как есть, без архитектурной обёртки.

#### `overlay: clean` — Clean Architecture (Uncle Bob)

```
wiki/
├── domains/             # Layer 1 — Enterprise business rules (entities)
├── use-cases/           # Layer 2 — Application business rules
├── adapters/            # Layer 3 — Interface adapters
│   ├── controllers/
│   ├── presenters/
│   └── gateways/
├── infrastructure/      # Layer 4 — Frameworks & drivers
├── contracts/           # Cross-cutting (см. 4.3)
├── decisions/
├── modules/             # Физические code-модули с маппингом на слои
├── people/
└── tasks/
```

Cross-ref правило (dependency rule): страницы `domains/` НЕ могут ссылаться на `adapters/` или `infrastructure/`. Lint флагает нарушения.

#### `overlay: hexagonal` — Ports & Adapters

```
wiki/
├── core/
│   ├── entities/
│   ├── value-objects/
│   ├── aggregates/
│   └── domain-events/
├── ports/
│   ├── inbound/         # Driving ports (use case interfaces)
│   └── outbound/        # Driven ports (repo interfaces, etc.)
├── adapters/
│   ├── inbound/         # HTTP / CLI / gRPC handlers
│   └── outbound/        # DB / external APIs / brokers
├── application/         # Use cases — оркестрация портов
├── contracts/
├── decisions/
├── people/
└── tasks/
```

Cross-ref правило: `core/` ссылается только на `core/` и `ports/`. `adapters/` обязаны ссылаться на свой `port/`.

#### `overlay: ddd` — Domain-Driven Design (комбинируется с clean / hexagonal)

```
wiki/
├── bounded-contexts/
│   ├── billing/         # Каждый BC имеет внутри структуру от outer overlay
│   │   ├── core/        # (если ddd + hexagonal)
│   │   ├── ports/
│   │   ├── adapters/
│   │   └── application/
│   ├── identity/
│   └── catalog/
├── shared-kernel/       # Общее между BC
├── context-map.md       # Отношения между BC (upstream/downstream, ACL, conformist)
├── contracts/           # Контракты на стыках BC — first-class
├── decisions/
├── people/
└── tasks/
```

#### `overlay: layered` — классические 3 слоя

presentation / business-logic / data-access — простой вариант для legacy / monolith.

---

### 4.3 Contracts как first-class категория

Для software-project (с любым overlay) `contracts/` — не плоская папка, а структурированная под транспорт:

```
contracts/
├── rest/                # REST APIs (OpenAPI specs в raw/openapi/)
│   ├── auth-api.md
│   └── billing-api.md
├── graphql/             # GraphQL schemas
├── grpc/                # protobuf-based services
├── events/              # Async — Kafka topics, RabbitMQ exchanges, SQS queues
├── webhooks/            # Inbound webhooks (Stripe, GitHub, etc.)
├── rpc/                 # JSON-RPC и прочее
└── data-models/         # Wire formats без транспорта (DTO, схемы файлов)
```

Frontmatter страницы контракта:

```yaml
---
title: "Auth API"
slug: "auth-api"
transport: rest
service: "[[module-auth-service]]"   # Кто провайдит
consumers: []                          # Кто потребляет (auto-filled через backlinks)
version: "v2.1.0"
status: stable                         # draft | beta | stable | deprecated
source_file: "raw/openapi/auth-v2.yaml"
breaking_changes: []
date_updated: YYYY-MM-DD
---
```

Дополнительные cross-ref правила (расширяют таблицу из секции 7):

| Forward action | Required reverse |
| --- | --- |
| `contracts/X` пишет `service: [[module-S]]` | `modules/S` добавляет X в `## Provides` |
| `modules/M` пишет `consumes: [[contract-X]]` | `contracts/X` добавляет M в `consumers` |
| `contracts/X` пишет `flows: [[entity-E]]` | `entities/E` добавляет X в `## Used in contracts` |

Дополнительный lint-чек: при изменении frontmatter поля `version` страницы контракта проверяется наличие записи в `## Migration notes` для каждого consumer.

---

### 4.4 Слой C — Dynamic schema evolution

**Принцип**: bootstrap создаёт минимум, схема растёт через использование. Ingest распознаёт что не лезет в существующие слоты, и предлагает создать новый — с фиксацией изменения в CLAUDE.md.

**Механика `/wiki-ingest`:**

```
1. File-type detection      ─ расширение, MIME, frontmatter
2. Content classification   ─ LLM-классификатор: что это за артефакт?
                              (OpenAPI / ADR / migration / sequence diagram /
                               meeting transcript / threat model / ...)
3. Slot matching            ─ поиск подходящей категории в текущей схеме
4a. Match found             ─ обычный flow: создать страницу
4b. No match                ─ schema-evolve flow ↓
```

**Schema-evolve flow (пример):**

```
[ingest] raw/migrations/2026_04_27_add_users_table.sql

Это database migration. Подходящего слота в схеме нет.

Варианты создания:
  (a) Новая категория верхнего уровня: data/migrations/
      • Frontmatter: title, status, target_table, applied_at, rollback
      • Cross-ref: → entities/{table}, → adapters/outbound/postgres/
  (b) Под infrastructure/: infrastructure/migrations/
      • Те же поля
  (c) Привязать как раздел `## Migrations` к entities/users/

Если (a) или (b):
  ─ обновляю CLAUDE.md (добавляю page type, frontmatter, cross-ref)
  ─ создаю scripts/add-entity-type-{type}.sql
  ─ коммичу с тегом [schema-change]: добавлен тип migrations
  ─ ингещу файл в новый слот

Какой вариант?
```

**Какие классы артефактов скилл умеет распознавать из коробки** (база для классификатора):

- API specs: OpenAPI, GraphQL schema, protobuf, AsyncAPI
- Architecture artifacts: ADR, C4 diagrams (PlantUML/Mermaid), sequence diagrams
- Code artifacts: source files, migrations, terraform plans, k8s manifests
- Process docs: PRD, RFC, threat models, runbooks, postmortems
- Communication: meeting transcripts, slack export, email threads
- Tests: test plans, Postman collections, fixture data
- Data: schema files (SQL DDL, JSON Schema, Avro), sample datasets

Каждый из этих классов имеет рекомендованный preset слота — пользователь видит дефолт, может его переопределить.

**Каждое schema-change событие фиксируется** в `wiki/log.md`:

```
## [2026-04-27] schema-change | added type: migrations (data/migrations/) | trigger: ingest of raw/migrations/2026_04_27_add_users_table.sql
```

Это даёт два важных свойства:
- Bootstrap минимален — не надо угадывать всё заранее.
- Схема рефлексирует историю проекта — структура говорит «вот такие артефакты мы видели», а не «вот такие классы мы предположили».

---

## 5. Workflow operations (skills как slash-команды)

Все ниже — отдельные SKILL.md внутри `.claude/skills/`, генерируются скилом-бутстрапером:

| Slash-команда | Что делает |
| --- | --- |
| `/wiki-init <project-description>` | Бутстрап: создаёт всю структуру, заполняет CLAUDE.md под выбранный preset, делает первичную обзорную страницу из того, что лежит в raw/ |
| `/wiki-prefill <domain>` | Опционально: предзаполняет foundations/ и concepts/ базовыми понятиями домена (типа «Kafka», «OAuth» для software, «attention» для research) |
| `/wiki-ingest <source-path>` | Принимает один или несколько файлов из raw/, читает, создаёт/обновляет wiki-страницы, обновляет index.md, log.md, graph/ |
| `/wiki-ask <question>` | Запрос к вики. Сначала читает index.md, потом релевантные страницы, синтезирует ответ. Хороший ответ может быть зафайлен обратно в outputs/ или новой страницей |
| `/wiki-edit <request>` | Точечное редактирование (добавить страницу, переименовать, изменить frontmatter) с автоматическим обновлением обратных ссылок |
| `/wiki-evolve <type-name>` | Явное добавление нового типа сущности к схеме (вызывается автоматически из `/wiki-ingest` при schema-evolve flow или вручную) — обновляет CLAUDE.md, frontmatter templates, cross-ref правила, фиксирует [schema-change] коммитом |
| `/wiki-lint [--fix] [--suggest]` | Структурная проверка: битые wikilinks, отсутствующие обратные ссылки, orphan pages, missing required frontmatter, дубликаты по aliases, нарушения dependency rules от architectural overlay |
| `/wiki-contracts-check` | Контракт-специфичный lint: для каждой страницы `contracts/*` проверяется наличие `service`, наличие consumers с обратными ссылками, что при bumped version у каждого consumer есть запись в `## Migration notes` |
| `/wiki-review` | Семантический ревью: контрадикции, устаревшие тезисы, концепции упомянутые но не имеющие страницы, дыры в кросс-ссылках |
| `/wiki-rollup [period]` | Сворачивание: за период (week/month/quarter) собирает дельту изменений в Summary/-страницу |

---

## 6. Хуки и автоматизация (это то что ты явно просил)

### Уровень 1 — Session hooks (Claude Code)

Через механизм хуков Claude Code (`.claude/settings.local.json` + `.claude/hooks/*.sh`):

| Хук | Когда срабатывает | Что делает |
| --- | --- | --- |
| `session-start` | На старте сессии | `cat wiki/graph/context_brief.md` — подгружает сжатый контекст в начало сессии |
| `pre-tool-use` (Write/Edit на wiki/) | Перед записью в wiki/ | Валидирует frontmatter, проверяет наличие обратной ссылки если пишется forward link |
| `post-tool-use` (Write на wiki/) | После записи | Дёргает `tools/wiki_engine.py rebuild-context-brief` |
| `session-end` | По завершении сессии | 1) `lint --suggest` 2) Просит агента предложить что из текущей сессии достойно вытащить в wiki 3) Аппендит запись в log.md 4) Регенерирует context_brief.md |

### Уровень 2 — Git hooks

| Хук | Что делает |
| --- | --- |
| `pre-commit` | `lint --fix` для безопасных починок + блокировка commit-а если остались 🔴 |
| `post-commit` | Регенерация `graph/edges.jsonl` если затронуты файлы wiki/ |

### Уровень 3 — CI / Scheduled (GitHub Actions)

| Workflow | Расписание | Что делает |
| --- | --- | --- |
| `wiki-lint.yml` | on push | Полный lint, fail PR если есть 🔴 |
| `wiki-review.yml` | weekly cron (Mon 09:00 UTC) | `/wiki-review`, результат публикует issue с тегом `wiki-review` |
| `wiki-rollup.yml` | monthly cron | `/wiki-rollup month`, коммитит Summary/-страницу |

---

## 7. Cross-reference rules (правила двусторонних ссылок)

Канон унаследован из OmegaWiki, но генерируется под выбранный preset. Пример для `software-project`:

| Forward action | Required reverse action |
| --- | --- |
| `modules/A` пишет `depends_on: [[module-B]]` | `modules/B` добавляет A в `dependents` |
| `decisions/D` пишет `affects: [[module-A]]` | `modules/A` добавляет D в `## Decisions` |
| `specs/S` пишет `implements: [[component-C]]` | `components/C` добавляет S в `## Specs` |
| `tasks/T` пишет `target_module: [[module-A]]` | `modules/A` добавляет T в `## Active tasks` |
| `entities/E` пишет `defined_in: [[spec-S]]` | `specs/S` добавляет E в `## Entities` |

Эти правила формализуются таблицей в CLAUDE.md и проверяются `tools/lint.py`.

---

## 8. CLAUDE.md как runtime-контракт (что в нём)

Генерируемый CLAUDE.md содержит ровно те разделы, которые есть в OmegaWiki, плюс адаптацию под наш preset:

1. **Project overview** — что эта вики собирает, для каких агентов
2. **Directory structure** — литеральный tree
3. **Page types table** — таблица типов с путями
4. **Page templates** — frontmatter и секции для каждого типа
5. **Link syntax** — Obsidian wikilinks, naming convention (lowercase-hyphen)
6. **Cross-reference rules** — таблица forward → reverse
7. **index.md format** — YAML-схема каталога
8. **log.md format** — `## [YYYY-MM-DD] op | desc`
9. **Constraints** — raw read-only, graph auto-generated, bidirectional обязательно
10. **Skills table** — список slash-команд и их триггеры
11. **Python environment** — как агенту запускать tools/ (venv-detection)
12. **Hooks behavior** — что происходит при session-end и почему

CLAUDE.md — это контракт, по которому агент ведёт себя как дисциплинированный wiki-maintainer, а не свободный chatbot.

---

## 9. Интеграция с агентами и встроенными скиллами (твоя долгосрочная цель)

Твой план: «один агент = один скилл», и агенты живут в репо проекта вместе с вики.

Скилл бутстрапит **слоты под это** (но конкретных агентов не создаёт — они придут под конкретный проект):

```
.claude/
├── skills/                      # Скиллы, в т.ч. под агентов
│   ├── wiki-*/SKILL.md          #   Базовые wiki-скиллы (создаются bootstrap-ом)
│   └── <agent-skill>/SKILL.md   #   Сюда добавляются скиллы агентов проекта
└── agents/
    └── <agent>.md               #   Описания агентов (роль, какие скиллы вызывает)
```

Агент проекта типизированно работает с вики через её CLAUDE.md и через `tools/wiki_engine.py`. Память агента = `graph/context_brief.md`, читается на старте сессии хуком `session-start`.

В будущем (вне scope этого скилла, но поддержано архитектурой):
- `wiki-creator` сам можно будет расширить пресетом «agentic-project», который при бутстрапе сразу создаст orchestrator/builder/reviewer/lint-агентов аналогично твоей текущей KROS-настройке (8 agents в `.claude/agents/`).
- Можно сделать sub-skill `/wiki-spawn-agent <name> <role>` который добавляет нового агента + его скилл к существующей вики.

---

## 10. Структура самого скила wiki-creator (что лежит внутри `wiki-creator/`)

```
wiki-creator/
├── SKILL.md                              # Главные инструкции (≤500 строк)
│
├── references/                           # Подгружаемые в контекст по требованию
│   ├── concept.md                        # Karpathy + OmegaWiki философия (выжимка)
│   ├── presets/
│   │   ├── software-project.md
│   │   ├── research.md
│   │   ├── product.md
│   │   ├── personal.md
│   │   ├── knowledge-base.md
│   │   └── README.md                     # Как выбрать пресет / собрать custom
│   ├── overlays/                         # NEW — архитектурные overlay-и
│   │   ├── clean.md                      #   Clean Architecture: layout + dependency rules
│   │   ├── hexagonal.md                  #   Ports & Adapters: layout + правила
│   │   ├── ddd.md                        #   Bounded contexts + context map
│   │   ├── layered.md                    #   Classic 3-tier
│   │   └── README.md                     #   Как выбрать overlay / комбинации
│   ├── contracts/                        # NEW — first-class contracts deep-dive
│   │   ├── rest.md                       #   OpenAPI workflow
│   │   ├── graphql.md
│   │   ├── grpc.md
│   │   ├── events.md                     #   AsyncAPI / Kafka / etc.
│   │   ├── webhooks.md
│   │   └── README.md
│   ├── classifier.md                     # NEW — таксономия классов raw-артефактов и схема классификации
│   ├── claude-md-template.md             # Эталон CLAUDE.md с placeholder-ами
│   ├── page-templates.md                 # Все frontmatter и секции по типам
│   ├── cross-reference-rules.md          # Каноны двусторонних ссылок (включая overlay-specific)
│   ├── hooks-design.md                   # Подробности по session/git/CI хукам
│   ├── review-cycle.md                   # Что именно проверяется в /wiki-review
│   ├── schema-evolution.md               # NEW — как растёт схема через ingest
│   ├── agent-integration.md              # Как агенты подключаются
│   └── examples/
│       ├── omegawiki-walkthrough.md      # Разбор OmegaWiki как референса
│       └── karpathy-original.md          # Оригинальный gist (выжимка)
│
├── assets/                               # Файлы, копируемые в результат
│   ├── claude-md.tmpl                    # Шаблон CLAUDE.md (с {{placeholders}})
│   ├── readme.tmpl
│   ├── index-md.tmpl
│   ├── log-md.tmpl
│   ├── frontmatter/
│   │   ├── module.yaml
│   │   ├── decision.yaml
│   │   ├── spec.yaml
│   │   └── ... (по одному на каждый возможный тип сущности)
│   ├── hooks/
│   │   ├── session-start.sh
│   │   ├── session-end.sh
│   │   ├── post-ingest.sh
│   │   └── pre-commit.sh
│   ├── workflows/
│   │   ├── wiki-lint.yml
│   │   ├── wiki-review.yml
│   │   └── wiki-rollup.yml
│   ├── tools/
│   │   ├── wiki_engine.py                # CLI: add-edge, rebuild-context-brief, rebuild-open-questions
│   │   ├── lint.py                       # Lint с --fix/--suggest/--dry-run
│   │   └── _env.py
│   ├── child-skills/                     # Скиллы, копируемые в .claude/skills/ результата
│   │   ├── wiki-init/SKILL.md
│   │   ├── wiki-ingest/SKILL.md
│   │   ├── wiki-ask/SKILL.md
│   │   ├── wiki-edit/SKILL.md
│   │   ├── wiki-evolve/SKILL.md          # NEW — schema evolution
│   │   ├── wiki-lint/SKILL.md
│   │   ├── wiki-contracts-check/SKILL.md # NEW — contract-specific lint
│   │   ├── wiki-review/SKILL.md
│   │   └── wiki-prefill/SKILL.md
│   └── env.example
│
└── scripts/                              # Исполняемая часть скила
    ├── bootstrap.py                      # Главный скрипт развёртывания
    ├── add_entity_type.py                # Добавить новый тип сущности к существующей вики
    ├── classify_artifact.py              # NEW — классификатор raw-артефактов (по расширению + LLM)
    └── interview.py                      # Интерактивный диалог для custom-preset / overlay choice
```

---

## 11. Trigger phrases (description для frontmatter)

Драфт description (в духе skill-creator-овского «push-овости»):

> Use this skill whenever the user wants to bootstrap a wiki, knowledge base, or persistent memory layer for an LLM agent or multi-agent system. Triggers include: "create a wiki", "set up a knowledge base", "bootstrap project memory", "agent memory layer", "Karpathy LLM wiki", "OmegaWiki style", "Obsidian + Claude Code workflow", "set up CLAUDE.md", "wiki for my project", "memory for agents". Also use when the user describes wanting raw → wiki → schema separation, persistent compounding knowledge instead of RAG, or session-end automation that keeps documentation current. Use even if the user does not literally say "wiki" but describes a structured, LLM-maintained knowledge base with cross-references and lifecycle. Do NOT use for one-off doc generation, single-file summaries, or static documentation that won't be incrementally maintained.

---

## 12. Workflow самого скилла (что Клод делает когда триггерится)

```
1. INTERVIEW (5-10 минут диалога)
   ├─ Что за проект? (домен, размер, существующая дока)
   ├─ Где разворачиваем? (новый repo / поверх существующего)
   ├─ Слой A — какой preset? (software / research / product / personal / kb / custom)
   ├─ Слой B — architectural overlay? (none / clean / hexagonal / ddd / layered)
   │   • Только если preset = software-project
   │   • Можно комбинировать ddd с clean или hexagonal
   ├─ Если custom — какие сущности и их lifecycle
   ├─ Уровень автоматизации? (минимальный / полный с CI / только session hooks)
   ├─ Schema-evolve mode? (с гейтом — спрашиваем при каждом новом типе / автоматически)
   ├─ Obsidian? (генерим .obsidian или нет)
   └─ Bilingual? (en-only / en+другой)

2. PROPOSE PLAN
   └─ Показывает какие файлы будут созданы, итоговый tree, key decisions
      (gate перед записью)

3. BOOTSTRAP
   ├─ scripts/bootstrap.py с параметрами из interview
   ├─ Копирует assets/ → результат
   ├─ Рендерит claude-md.tmpl с подставленными значениями
   ├─ Генерирует CLAUDE.md, README.md, index.md (пустой), log.md
   ├─ Копирует hooks, workflows, tools, child-skills
   ├─ Создаёт пустые директории под выбранные entity types
   └─ git init + первый commit "wiki bootstrap"

4. FIRST INGEST (опционально, но рекомендуется)
   ├─ Если в проекте уже есть документы — предложить положить их в raw/
   ├─ Дёрнуть /wiki-ingest на 1-2 ключевых документа
   └─ Показать пользователю первые сгенерированные wiki-страницы

5. HANDOFF
   ├─ Объяснить как пользоваться (3 главные команды + где смотреть результат)
   ├─ Объяснить session-end хук (что произойдёт после этой же сессии)
   └─ Подсказать следующий шаг: добавить агента, ингестить ещё, поднять Obsidian
```

---

## 13. Открытые решения, которые я хочу с тобой провалидировать

Все эти выборы я сделал по-умолчанию, но они спорны. Если что-то не нравится — меняем.

| # | Вопрос | Моё решение | Альтернатива |
|---|---|---|---|
| 1 | Опинионированность пресетов | Жёсткий software-project как дефолт + 4 alt-пресета + custom | Только OmegaWiki-схема (research) с возможностью переименовать сущности |
| 2 | Tools на чём писать | Python (твой стек) | Bash-only / Node |
| 3 | Где живёт wiki/ | На top-level (как OmegaWiki) | `.wiki/` (скрытая) |
| 4 | Хуки автоустанавливаются | Генерим + опт-ин в установку | Только генерим, симлинков не делаем |
| 5 | Скиллы внутри `.claude/skills/` или глобально | Project-scoped (как у тебя в KROS) | Глобально в `~/.claude/skills/` |
| 6 | Obsidian-конфиг | Опционально, спрашиваем | Всегда генерим |
| 7 | i18n | Опционально, спрашиваем | EN-only |
| 8 | MCP-серверы (cross-model review) | Не входит в bootstrap, упоминаем как extension | Сразу разворачиваем |
| 9 | Миграция из существующей доки | v2 (отдельный sub-skill) | В основном workflow |
| 10 | Описание сущностей под software-project: достаточно ли 8? | Базовый набор = 8, можно резать или добавлять при interview | Стартовый минимум 4 (modules/decisions/specs/people) |
| 11 | Что в context_brief.md для агента | Active claims + open questions + recent log entries (≤8000 символов) | Другая структура |
| 12 | Lint правила приоритеты | OmegaWiki-набор (broken links, missing reverse, orphans, missing fields) + дубликаты по aliases | Минимальный набор |
| 13 | Architectural overlay по дефолту | `none` для всех presets кроме software-project; для software-project спрашиваем явно (не подсовываем дефолт) | Всегда `none` / Всегда `clean` |
| 14 | Comp-режим overlay-ев (clean+ddd) | Поддерживаем только `ddd` как комбинируемый с другими; clean+hexagonal не имеет смысла | Любые комбинации |
| 15 | Dependency rules enforcement | Lint флагает нарушения как 🟡 (warning), не 🔴 (error) — чтобы не блокировать commits во время ранней разработки | Строго 🔴 / только saggesty |
| 16 | Schema-evolve: автоматический или с гейтом | С гейтом — всегда спрашиваем пользователя перед добавлением нового типа | Автоматически создавать (с возможностью отката) |
| 17 | Granularity contracts/-структуры | Предлагать все 7 под-папок (rest/graphql/grpc/events/webhooks/rpc/data-models), но в bootstrap создавать только пустые директории. Реальные подпапки появятся через schema-evolve когда туда что-то ингестится | Создавать сразу все / Только flat contracts/ без под-категорий |
| 18 | Классификатор артефактов в `/wiki-ingest` | LLM-классификатор с фиксированным набором классов (см. раздел 4.4) + extensible через CLAUDE.md | Только по расширению файла / только эвристики |

---

## 14. Что НЕ входит в этот скилл (явные out-of-scope)

- **Сама вики проекта** — скилл создаёт каркас, наполнение делается потом через `/wiki-ingest`.
- **Конкретные агенты твоего проекта** — слот под `.claude/agents/` создаётся, но агентов под KROS/Seldon/etc. этот скилл не пишет. Это будут отдельные скиллы.
- **Эмбеддинги / vector search** — Карпате явно говорит что index.md достаточно до ~100 источников. Если у проекта вырастет — отдельная история (упомянем qmd, OpenSearch, Milvus как опции в references).
- **Redis / база данных** — это не скилл инфраструктуры рантайма, это скилл документного слоя.
- **Frontend / UI для wiki** — Obsidian / GitHub web view достаточно. Karpathy-dashboard-like UI вне scope.

---

## 15. Размер и сложность

- **SKILL.md** — целюсь в 300-450 строк (под лимит skill-creator-а в 500).
- **references/** — 8-10 файлов по 100-300 строк каждый.
- **assets/** — ≈25-35 файлов суммарно (templates, hooks, workflows, child-skills).
- **scripts/** — 3 Python-скрипта по 100-300 строк.
- **Тестовые кейсы для evals** — 6-8 промптов разных пресетов и edge-cases (для skill-creator-овского цикла оптимизации триггера).

Финальный bootstrap пустой вики — несколько секунд. Первый ingest 5-10 документов — несколько минут.

---

## 16. Минимальный пример «как это выглядит со стороны пользователя»

```
[user] Хочу развернуть wiki для нового проекта Seldon-CRM, у меня уже есть PRD и AUDIT_TASKS.md.

[claude] Запускаю wiki-creator. Вопросы перед бутстрапом:

  1. Слой A — preset: software-project? (modules / decisions / specs / entities /
     contracts / people / tasks)
  2. Слой B — architectural overlay: какой подход у проекта?
       • none (плоско)
       • clean (Uncle Bob)
       • hexagonal (Ports & Adapters)
       • ddd (bounded contexts) — комбинируется с clean/hexagonal
       • layered (3-tier)
  3. CI с еженедельным review через GitHub Actions подключаем?
  4. Schema-evolve mode: с гейтом (спрашивать при новом типе) или авто?
  5. Obsidian-вью генерим?
  6. Положить PRD и AUDIT_TASKS.md в raw/ сразу и сделать первый ingest?

[user] software-project, hexagonal, да CI, с гейтом, да Obsidian, да сразу ingest.

[claude] [показывает план: dir-tree с core/ports/adapters/application + contracts/
         с под-категориями rest/graphql/grpc/events/, ~95 файлов]
        [после "ok" — bootstrap, 4 секунды]
        [запускает /wiki-ingest raw/PRD.md raw/AUDIT_TASKS.md]
        
        [через 1 минуту, во время ingest-а]:

   raw/PRD.md ingested:
     ─ создано 4 страницы core/entities/, 6 страниц application/
     ─ создано 3 страницы decisions/

   raw/AUDIT_TASKS.md ingested:
     ─ создано 14 страниц tasks/

   ⚠ schema-evolve обнаружен:
   В PRD упоминается «Telegram bot integration» — не подходит ни в один
   существующий слот. Варианты:
     (a) Под adapters/inbound/: adapters/inbound/telegram/
     (b) Новая категория integrations/ верхнего уровня
     (c) Просто как раздел в существующем модуле

[user] (a)

[claude]
   ✓ schema-change: добавил тип adapters-inbound-telegram
     ─ обновил CLAUDE.md
     ─ создал frontmatter template
     ─ закоммитил [schema-change]: added adapters/inbound/telegram/
   ✓ создал adapters/inbound/telegram/seldon-bot.md
   
   Итого первый прогон:
     ─ 4 страницы core/entities/
     ─ 6 страниц application/
     ─ 1 страница adapters/inbound/telegram/
     ─ 3 страницы decisions/
     ─ 14 страниц tasks/
     ─ index.md, log.md, graph/edges.jsonl, graph/context_brief.md
     ─ 1 schema-change в логе

Следующие шаги:
  - Открой wiki/ в Obsidian → graph view покажет hexagonal-структуру
  - В CLAUDE.md прочти "Cross-reference rules" и "Dependency rules from hexagonal"
  - В новой сессии Claude Code session-start хук подгрузит graph/context_brief.md
  - Когда будет готов добавить агента — /wiki-spawn-agent
```

---

## 17. Что мне нужно от тебя сейчас

Чтобы перейти к написанию самого скила, мне нужно по этому документу:

1. **Утверждение общей архитектуры** (разделы 1-4) — три слоя, артефакт, page type presets.
2. **Решения по 12 пунктам** в разделе 13 (можно просто «всё ок как ты предложил» или поправить точечно).
3. **Подтверждение out-of-scope** (раздел 14) — точно ли мы не лезем в эмбеддинги / vector search / агентов проекта.
4. **Дефолтный preset** — для тебя имеет смысл `software-project` как первичный, или ты хочешь чтобы скилл по дефолту спрашивал без предположения?
5. **Окружение для bootstrap-скрипта** — Python 3.10+ ок? Используем `pip install --user` или `venv`?

Как только это согласуем — собираю SKILL.md, references, assets, scripts и пакую в финальный артефакт.
