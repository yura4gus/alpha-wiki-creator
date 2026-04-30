# План реализации на основе новых проектных документов

Дата: 2026-04-30

## 1) Что зафиксировано документами

- Архитектура из 3 независимых слоёв: **Alpha-Wiki** (memory), **AgentOps** (операционная модель), **Superpowers** (дисциплина исполнения, опционально).
- Жёсткие границы ответственности закреплены ADR-001..006.
- В Phase 1 приоритет — **не ломать существующий alpha-wiki-creator**, а доукреплять его in-place.
- Интеграция между слоями только через адаптеры AgentOps (wiki-backend-adapter, superpowers-adapter), без runtime-импортов чужих слоёв.

## 2) Цели реализации (MVP)

### Цель A — закрыть Phase 1a (harden alpha-wiki-creator)
1. Привести 8 существующих skills к 15-мерному operational-manual стандарту.
2. Добавить 3 новых skills: `contracts-check`, `claims-check`, `daily-maintenance`.
3. Разрешить статус `review`/`rollup` (подтвердить существование и доработать или реализовать).
4. Закрыть выявленные в аудите критичные P1/P2 дефекты bootstrap/hooks/CI.

### Цель B — подготовить почву под Phase 1b (AgentOps repo)
1. Зафиксировать интерфейсы интеграции в текущем репо (без реализации AgentOps здесь).
2. Подготовить проверочный чеклист для приёмки будущего `agentops`-репо.

## 3) Реализационный бэклог (приоритетный)

## P0 — обязательные перед релизом alpha-wiki

1. **Безопасный bootstrap для существующих репозиториев**
   - Ввести режим `--safe-existing` (или аналог) с запретом silent overwrite `README.md`, `pyproject.toml`, `.gitignore`, `CLAUDE.md`.
   - Добавить dry-run отчёт по конфликтам.

2. **Корректная поддержка `wiki_dir` во всех hook/CI артефактах**
   - Проброс `wiki_dir` в generated hooks.
   - Унификация `wiki` vs `.wiki` в workflow и runtime scripts.

3. **Не разрушать graph-артефакты при upgrade**
   - На upgrade выполнять selective rebuild; не стирать `edges/context/open_questions` без необходимости.

4. **Реально учитывать режим выбора hooks (`session|git|all`)**
   - Копировать/рендерить только выбранный набор.

5. **Post-tool hook должен пересобирать весь граф**
   - Не только `context_brief`, но и `edges.jsonl`, `open_questions.md`.

## P1 — функциональное закрытие Phase 1a

6. Добавить/доработать deterministic tools:
   - `tools/ingest_pipeline.py`, `tools/classifier.py`, `tools/contradiction_detector.py`,
   - `tools/wiki_search.py`, `tools/status_report.py`, `tools/contracts_check.py`, `tools/claims_check.py`.

7. Привести skill-доки к 15 измерениям:
   - `init`, `ingest`, `query`, `lint`, `evolve`, `status`, `spawn-agent`, `render`.

8. Закрыть contingent skills:
   - `review`, `rollup` — decision + реализация/хардненинг.

9. Покрыть pressure-тестами по roadmap (минимум +26 новых сценариев к текущему набору).

## P2 — release hardening

10. Обновить README/CHANGELOG/версию.
11. Прогнать smoke на Seldon-CRM артефактах (как в roadmap).
12. Зафиксировать release-gate evidence (команды + результаты).

## 4) Пошаговый план выполнения (2 спринта)

## Спринт 1 (5–7 дней): стабилизация core

- Шаг 1: закрыть P0.1–P0.5 (bootstrap + hooks + CI + graph rebuild).
- Шаг 2: добавить тесты регрессий на каждый зафиксированный дефект.
- Шаг 3: обновить docs/skills, чтобы поведение и контракт совпадали.

**Definition of Done спринта 1:**
- Все новые регрессионные тесты зелёные.
- `bootstrap` безопасен для existing repo.
- `.wiki` режим не ломает hooks/CI.

## Спринт 2 (7–10 дней): функциональное расширение Phase 1a

- Шаг 4: внедрить новые tools (claims/contracts/status/search/ingest pipeline).
- Шаг 5: довести 8+3 skills до целевого стандарта.
- Шаг 6: закрыть `review`/`rollup` + новые pressure-тесты.
- Шаг 7: release prep + smoke test.

**Definition of Done спринта 2:**
- Приняты задачи T1a.1–T1a.16 из roadmap.
- Coverage не ниже текущего baseline; критические пути с новыми тестами.
- Подготовлен релиз-кандидат Phase 1a.

## 5) Риски и контрмеры

1. **Риск:** scope creep из-за параллельного дизайна AgentOps.
   - **Контрмера:** в этом репо реализуем только Phase 1a; интеграционные контракты — документально.

2. **Риск:** несовпадение docs и фактических команд/флагов.
   - **Контрмера:** добавить contract-тесты CLI/help + snapshot для генерируемых артефактов.

3. **Риск:** деградация UX при ужесточении bootstrap.
   - **Контрмера:** safe defaults + `--force` только с явным подтверждением и логом изменений.

## 6) Чеклист запуска реализации (next actions)

1. Создать epic: `phase-1a-hardening`.
2. Завести 5 P0 issue (по каждому найденному дефекту).
3. Завести 8 issue на хардненинг skills + 3 issue на новые skills.
4. Завести issue на `review/rollup decision`.
5. Зафиксировать target release: `v0.x+1` после прохождения smoke.

