
# LabPlanBot

LabPlanBot — это телеграм-бот, предназначенный для оптимизации работы в лабораториях. Он помогает организовывать студентов путём создания расписания.
# 🚀 Telegram Bot для Управления Расписанием  

Этот бот помогает директорам создавать расписание, а ассистентам выполнять задачи в удобном формате.  

## 🔹 Как работает бот?

### 1️⃣ Директор создает стандартные задачи
- Выбирает **добавление новой задачи**.  
- Указывает **кабинет** и **устройство**, к которому привязана задача.  
- Вводит **название** задачи.  
- Определяет, **выполняется ли задача параллельно** с другими.  
- Указывает **продолжительность выполнения**.  
- **Подтверждает** добавление задачи в систему.  

### 2️⃣ Директор создает протокол  
- Выбирает **создание нового протокола**.  
- Вводит **название** протокола.  
- Последовательно выбирает **задачи**, которые войдут в протокол.  
- **Завершает** формирование протокола.  

### 3️⃣ Директор добавляет протокол в расписание  
- Выбирает **добавление протокола в расписание**.  
- Выбирает **нужный протокол**.  
- Бот автоматически **распределяет задачи** в пределах рабочего дня, учитывая доступность оборудования.  
- Получает **подтверждение** о добавлении протокола в расписание.  

---

## 🔹 Работа ассистента 

### 4️⃣ Ассистент берет протокол на выполнение
- Выбирает **доступные протоколы** на день.  
- Просматривает **детали протокола**.  
- **Подтверждает** своё участие в выполнении протокола.  

### 5️⃣ Ассистент выполняет задачи 
- Просматривает **своё расписание** с указанием задач, времени, кабинетов и оборудования.  
- Выполняет задачи в установленное время.  
- При необходимости **сообщает о завершении выполнения**.  

---

## 🔹 Итоговый процесс
✔ **Директор** формирует задачи → объединяет их в протокол → добавляет в расписание.  
✔ **Ассистент** выбирает протокол → включает себя в выполнение → выполняет задачи.  

## 📌 Технологии  
- **Python** + **Aiogram**  
- **PostgreSQL (JSONB) для хранения данных**  
- **Асинхронная обработка**  
- **FSM (Finite State Machine) для управления состояниями**  

---

## Авторы
### Виктор Ма
- [@Viktor3911](https://github.com/Viktor3911)
- 📧 Email: ma.vv@dvfu.ru
- 💬 Telegram: [@adontus12](https://t.me/adontus12)
### Прокопенко Сергей
- [@serptid](https://github.com/serptid)
- 📧 Email: prokopenko.si@dvfu.ru
- 💬 Telegram: [@ProkopenkoSR](https://t.me/ProkopenkoSR)
## Со Авторы
### Кириллов Олег
- 💬 Telegram: [@olegrover](https://t.me/olegrover)
### Есина Маргарита
- 💬 Telegram: [@queen_oftheball](https://t.me/queen_oftheball)
### Улько Данила
- 💬 Telegram: [@Nothdan](https://t.me/Nothdan)
### Пятых Алексей
- 💬 Telegram: [@Ghost0fBabel](https://t.me/Ghost0fBabel)
