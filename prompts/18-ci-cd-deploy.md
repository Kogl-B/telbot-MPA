# 18 — CI/CD и деплой

> **Аннотация:** Промпт для создания пайплайнов CI/CD, Dockerfile, конфигураций деплоя. Покрывает тестирование, сборку, деплой и мониторинг.

## Когда использовать

- Настройка CI/CD для нового проекта
- Переход на новую платформу деплоя
- Оптимизация пайплайна
- Контейнеризация приложения

---

## Промпт: CI/CD Pipeline

```
# Роль
Ты — DevOps Engineer, настраивающий CI/CD для ${projectType}.

# Контекст
- Платформа CI: ${ciPlatform} (GitHub Actions / GitLab CI / Jenkins)
- Деплой на: ${deployTarget} (Vercel / AWS / Docker / K8s)
- Стек: ${techStack}
- Ветвление: ${branchStrategy} (GitFlow / Trunk-based)
- Среды: ${environments} (dev / staging / production)

# Задача
Создай полный CI/CD пайплайн.

# Требования
## Build
- Установка зависимостей (с кэшированием)
- Линтинг и проверка типов
- Компиляция / сборка

## Test
- Unit-тесты
- Интеграционные тесты
- E2E (на staging)
- Порог покрытия: ${coverageThreshold}%

## Deploy
- Staging: автоматически на push в develop
- Production: на push в main (после апрувов)
- Rollback стратегия
- Health checks

## Secrets
- Как хранить: ${secretsStorage}
- Какие нужны: ${secretsList}

# Формат
Полный YAML-файл пайплайна с комментариями.
```

## Промпт: Dockerfile

```
Создай оптимизированный Dockerfile для ${appType}.

Стек: ${techStack}
Порт: ${port}

Требования:
- Multi-stage build (минимальный размер)
- Non-root user
- .dockerignore
- Health check
- Environment variables через ARG/ENV
- docker-compose.yml для локальной разработки
```

---

## Советы

- Указывайте стратегию ветвления — это определяет триггеры
- Для монорепо: укажите пути для conditional builds
- Прикладывайте текущий пайплайн для оптимизации

## Роль в агентной системе

CI/CD = автоматизация `init.sh` + E2E.
В CI пайплайн включи: линтинг, тесты, E2E-проверку features.json.

## ⚠️ Антипаттерны

- **Security Neglect**: Секреты только в CI secrets, никогда в YAML
- **Trust Everything**: Пайплайн должен fallback'ить на ошибках
- **Hallucination**: Проверь YAML синтаксис — ИИ часто ошибается в отступах
