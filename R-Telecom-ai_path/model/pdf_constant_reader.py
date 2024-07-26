import fitz  # PyMuPDF
import cv2
import numpy as np
import easyocr
import mysql.connector

# Подключение к базе данных MySQL
connection = mysql.connector.connect(
    host="MySQL-5.7",
    user="root",
    password="",
    database="test2"
)

# Инициализация курсора для выполнения SQL-запросов
cursor = connection.cursor()

# Список координат рамок
rectangles = [
    ((661, 70), (956, 94)),    # дата договора
    ((159, 96), (680, 114)),   # первая сторона
    ((160, 186), (734, 204)),  # вторая сторона
    ((478, 491), (799, 508)),  # сумма
    ((157, 149), (944, 167)),  # первые реквизиты
    ((154, 239), (949, 257))   # вторые реквизиты
]

# Открываем PDF файл
pdf_document = fitz.open(r"C:\Users\Данила\Desktop\R-Telecom-ai_path\model\images\img_3.pdf")

# Убедимся, что у нас есть хотя бы одна страница
if len(pdf_document) > 0:
    page = pdf_document.load_page(0)  # Загружаем первую страницу

    # Увеличиваем разрешение
    zoom = 2  # Масштабирование в 2 раза
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)

    # Преобразуем Pixmap в формат, поддерживаемый OpenCV
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    
    # Преобразуем изображение в формат BGR для OpenCV
    if pix.n == 4:  # RGBA
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGRA)
    else:  # RGB
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    # Улучшение резкости изображения
    kernel = np.array([[0, -1, 0],
                       [-1, 5, -1],
                       [0, -1, 0]])
    img = cv2.filter2D(img, -1, kernel)

    # Изменение размера изображения для удобного просмотра
    img_resized = cv2.resize(img, (1000, 1000))
    img = img_resized.copy()

    # Инициализация easyocr Reader без дополнительных параметров
    reader = easyocr.Reader(['ru', 'en'], gpu=False)  # Используем русский и английский языки для распознавания

    # Инициализируем переменные для хранения извлеченных данных
    contract_data = {
        'contract_number': None,
        'contract_date': None,
        'first_party': None,
        'second_party': None,
        'contract_amount': None,
        'requisites_1': None,
        'requisites_2': None
    }

    # Отрисовка всех рамок с номерами
    for i, (start, end) in enumerate(rectangles):
        # Извлекаем текст из текущей рамки
        x1, y1 = start
        x2, y2 = end
        sub_img = img[y1:y2, x1:x2]

        # Распознаем текст с помощью easyocr
        result = reader.readtext(sub_img)

        # Проверяем, есть ли распознанный текст
        if result:
            # Выводим распознанный текст в консоль
            print(f"Результаты распознавания для рамки #{i+1}:")
            for res in result:
                recognized_text = res[1]
                print(recognized_text)  # выводим только текст

                # Сохраняем данные в соответствующую переменную
                key = list(contract_data.keys())[i]  # получаем ключ по индексу
                contract_data[key] = recognized_text

    # Пример вставки данных в таблицу Contracts
    sql_insert_query = """
    INSERT INTO Contracts (contract_number, contract_date, first_party, second_party, contract_amount, requisites_1, requisites_2)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    contract_values = (
        contract_data['contract_number'],
        contract_data['contract_date'],
        contract_data['first_party'],
        contract_data['second_party'],
        contract_data['contract_amount'],
        contract_data['requisites_1'],
        contract_data['requisites_2']
    )
    cursor.execute(sql_insert_query, contract_values)
    connection.commit()
    print("Данные успешно добавлены в базу данных")

    # Закрываем курсор (необходимо для освобождения ресурсов)
    cursor.close()

    # Закрываем соединение с базой данных
    connection.close()

else:
    print("PDF файл не содержит страниц.")
