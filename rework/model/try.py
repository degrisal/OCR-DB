import re

def extract_amount(text):
    # Регулярное выражение для поиска суммы
    # Здесь предполагается, что сумма может быть в формате "500000р", "500000 р", "500 000 рублей" и т.д.
    amount_pattern = re.compile(r'(\d+[\s\d]*)(?:\s*(?:р|руб|рублей|долларов|$))', re.IGNORECASE)
    
    match = amount_pattern.search(text)
    if match:
        amount = match.group(1).replace(' ', '')  # Убираем пробелы между цифрами
        return amount
    
    return None

# Пример использования
texts = [
    "Сумма: 500000р (пятьсот тысяч рублей)",
    "Выплата составляет 1 250 000 рублей",
    "Общая сумма: 300000 долларов",
    "Сумма к оплате: 75000р"
]

for text in texts:
    amount = extract_amount(text)
    if amount:
        print(f'Найдена сумма: {amount}')
    else:
        print('Сумма не найдена')
