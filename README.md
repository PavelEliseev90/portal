# Git README — шпаргалка команд

Кратко и по делу. Команды сгруппированы по задачам. Примеры безопасны по умолчанию.

> Примечание: `main` может быть `master`. Заменяйте под свой репозиторий.

---

## 1) Старт проекта и базовые операции

```bash
git init                           # инициализация репозитория в текущей папке
git clone <url>                    # клонирование удалённого репо
git status                         # статус рабочего дерева и индекса
git add <file|dir|.>               # добавить изменения в индекс (стейджинг)
git restore --staged <path>        # убрать из индекса обратно в рабочее дерево
git restore <path>                 # откатить изменения в файлах к версии из индекса/HEAD
git commit -m "msg"                # создать коммит
git commit --amend                 # переписать последний коммит (сообщение/содержимое)
git log --oneline --graph --all    # компактная история с ветками
git show <commit>                  # показать детали коммита/объекта
```

---

## 2) Ветки

```bash
git branch                         # список локальных веток
git branch -r                      # список удалённых веток
git branch -a                      # все ветки
git branch <name>                  # создать ветку от текущего HEAD
git checkout <name>                # переключиться на ветку
git checkout -b <name>             # создать и переключиться
git switch <name>                  # альтернативный способ переключиться
git switch -c <name>               # создать и переключиться
git branch -d <name>               # удалить локальную ветку (если слита)
git branch -D <name>               # принудительно удалить локальную ветку
git push origin --delete <name>    # удалить удалённую ветку
```

Публикация ветки и привязка к удалённой:
```bash
git push -u origin <branch>        # первый пуш с установкой upstream
git push                            # следующие пуши
git pull                            # получить и слить изменения из upstream
```

---

## 3) Слияние, ребейз, черри-пик

```bash
git merge <branch>                 # слить <branch> в текущую ветку (merge-коммит)
git rebase <branch>                # переписать историю поверх <branch>
git rebase -i HEAD~N               # интерактивный ребейз последних N коммитов
git cherry-pick <commit>           # применить один коммит поверх текущей ветки
git revert <commit>                # создать обратный коммит, отменяющий <commit>
```

Разрешение конфликтов:
```bash
# правим конфликтующие файлы вручную
git add <resolved-files>           # пометить как решённые
git merge --continue               # или: git rebase --continue / git cherry-pick --continue
git merge --abort                  # откатить конфликтный merge
git rebase --abort                 # откатить конфликтный rebase
```

---

## 4) Отмена и восстановление

```bash
git restore <path>                 # откат незакоммиченных изменений файла
git checkout -- <path>             # старый эквивалент отката файла
git reset --soft HEAD~1            # убрать последний коммит в индекс, файлы не трогать
git reset --mixed HEAD~1           # убрать коммит и из индекса (по умолчанию)
git reset --hard HEAD~1            # жёсткий откат (осторожно, потеря незакоммиченного)
git reflog                         # журнал перемещений HEAD (для спасения утерянных коммитов)
git reset --hard <reflog-id>       # вернуться к состоянию из reflog
```

Потерянную ветку можно вернуть по хэшу её последнего коммита:
```bash
git checkout -b <branch> <commit>
```

---

## 5) Работа с удалённым репозиторием

```bash
git remote -v                      # список remotes
git remote add origin <url>        # привязать удалённый репозиторий
git remote set-url origin <url>    # сменить URL
git fetch                          # скачать ссылки и объекты без слияния
git fetch -p                       # подчистить удалённые-мертвые ссылки
git pull --rebase                  # предпочтительно: вытянуть с ребейзом
git push                           # отправить коммиты
git push --force-with-lease        # безопаснее, чем --force, при переписанной истории
```

---

## 6) Теги (релизы)

```bash
git tag                            # список тегов
git tag <v1.0.0>                   # лёгкий тег
git tag -a <v1.0.0> -m "release"   # аннотированный тег
git show <tag>                     # показать содержимое тега
git push origin <tag>              # отправить тег
git push origin --tags             # отправить все теги
git tag -d <tag>                   # удалить локально
git push origin :refs/tags/<tag>   # удалить тег на сервере
```

---

## 7) Stash: временно спрятать изменения

```bash
git stash push -m "wip"            # спрятать незакоммиченное
git stash list                     # список
git stash show -p stash@{0}        # diff содержимого
git stash pop                      # достать и удалить из стэша
git stash apply stash@{n}          # применить, не удаляя
git stash drop stash@{n}           # удалить конкретный
git stash clear                    # очистить всё
```

---

## 8) Просмотр, поиск, диффы

```bash
git diff                           # разница рабочее дерево ↔ индекс
git diff --staged                  # индекс ↔ HEAD
git diff <rev1>..<rev2>            # разница между ревизиями
git blame <file>                   # кто и когда правил строки
git grep "pattern"                 # поиск по истории/рабочему дереву
git shortlog -sn                   # список авторов и количество коммитов
```

---

## 9) Подмодули (submodules)

```bash
git submodule add <url> path       # добавить подмодуль
git submodule update --init --recursive   # инициализация/обновление
git submodule foreach git pull     # обновить все подмодули
```

---

## 10) Большие файлы (Git LFS)

```bash
git lfs install
git lfs track "*.psd"
git add .gitattributes
git add <bigfile>
git commit -m "track big files"
git push
```

---

## 11) Продвинутые приёмы

```bash
git bisect start                   # бинарный поиск «ломающего» коммита
git bisect good <rev>              # отметить хорошее
git bisect bad <rev>               # отметить плохое
git bisect reset                   # завершить

git worktree add ../wt <branch>    # отдельная рабочая директория для ветки
git sparse-checkout init --cone    # частичная выборка содержимого
git sparse-checkout set <dirs>     # задать папки для sparse
```

---

## 12) Конфигурация

```bash
git config --global user.name "Имя"
git config --global user.email "email@example.com"
git config --global core.autocrlf input    # для Unix / macOS
git config --global core.autocrlf true     # для Windows
git config --global init.defaultBranch main
git config --list --show-origin            # показать значения и файлы, откуда взяты
```

Локальная конфигурация в репозитории:
```bash
git config user.name "Имя"
git config user.email "email@example.com"
```

Глобальные алиасы:
```bash
git config --global alias.st "status -sb"
git config --global alias.lg "log --oneline --graph --decorate --all"
git config --global alias.co "checkout"
git config --global alias.br "branch"
git config --global alias.cm "commit -m"
```

---

## 13) Типовые сценарии

Создать фичу от актуального main:
```bash
git checkout main
git pull --rebase
git switch -c feature/xyz
# код
git add .
git commit -m "feat: xyz"
git push -u origin feature/xyz
```

Обновить фичу поверх свежего main через rebase:
```bash
git checkout feature/xyz
git fetch origin
git rebase origin/main
# решаем конфликты → add → rebase --continue
git push --force-with-lease
```

Отменить «сломавший» коммит в main без переписывания истории:
```bash
git checkout main
git pull
git revert <bad_commit>
git push
```

Восстановить удалённую ветку из reflog:
```bash
git reflog
# находим нужный SHA
git checkout -b resurrected <sha>
git push -u origin resurrected
```

---

## 14) Полезные флаги

- `-n` или `--dry-run` — пробный запуск без изменений (там, где доступно).
- `--force-with-lease` — безопаснее, чем `--force`.
- `--no-ff` при merge — всегда создавать merge-коммит.
- `--autosquash` c rebase -i — авто‑сквош фиксов `fixup!/squash!`.

---

## 15) Быстрая памятка

```bash
# Инициализация и первый пуш
git init && git add . && git commit -m "init"
git branch -M main
git remote add origin <url>
git push -u origin main
```

```bash
# Обновление ветки от main
git fetch origin
git rebase origin/main
```

```bash
# Удаление веток
git branch -d <name>            # локально
git push origin --delete <name>  # на сервере
```

```bash
# Спасение через reflog
git reflog
git reset --hard <sha>
```

---

Если нужна узкая команда, которой нет в шпаргалке, уточни сценарий и я добавлю пример.
